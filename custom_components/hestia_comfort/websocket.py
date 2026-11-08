"""Read-only view v1 for the future Lit card; no command endpoint."""
from collections import OrderedDict
import functools
import time

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.messages import construct_event_message
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers import area_registry as ar, floor_registry as fr
from homeassistant.helpers.json import json_bytes
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .engine.home import synthesis
from .engine.i18n import speaking
from .engine.assessment import assess
from .floors import room_floor


# The panel's language, sent with each of its commands: its errors and words come back in it (engine/i18n.py).
LANGUAGE = vol.Optional("language")


def spoken(handler):
    """A panel command answered in the panel's language."""
    @functools.wraps(handler)
    async def answer(hass, connection, msg):
        with speaking(msg.get("language")):
            await handler(hass, connection, msg)
    return answer


@callback
def async_setup_websocket(hass):
    websocket_api.async_register_command(hass, ws_view)
    websocket_api.async_register_command(hass, ws_entries)
    websocket_api.async_register_command(hass, ws_subscribe)
    websocket_api.async_register_command(hass, ws_home_subscribe)
    websocket_api.async_register_command(hass, ws_review)
    websocket_api.async_register_command(hass, ws_periods)
    for command in (ws_configuration, ws_discover, ws_overview, ws_weather, ws_validate, ws_save, ws_remove):
        websocket_api.async_register_command(hass, command)
    for command in (ws_advice_opinion, ws_atelier, ws_trace, ws_relearn, ws_analysis, ws_field_report):
        websocket_api.async_register_command(hass, command)


# A view that did not change is sent again only this often: the cards call a view older than 75 s stale.
HEARTBEAT_SECONDS = 30
# The home card's rooms refreshing together (a shared air, a sensor seen by several) are sent in one message.
HOME_GROUPING_SECONDS = 1.0


def _stable(value):
    """The message without its computing times, to tell a refresh that changed nothing."""
    if isinstance(value, dict):
        return {k: _stable(v) for k, v in value.items() if k != "computed_at"}
    if isinstance(value, list):
        return [_stable(v) for v in value]
    return value


# The last room views turned into text, shared by every card subscribed to them (PLAN-OPTIMISATION.md, point 4): a view
# is converted once per update, not once per card. {id(view): (view, stable text, text)}: the view is kept, so that its
# id is not given to another one while it is here.
_TEXTS = OrderedDict()
TEXTS_KEPT = 32


def _texts(view):
    """The view as text without its computing times (to tell a refresh that changed nothing), and as sent."""
    found = _TEXTS.get(id(view))
    if found is not None and found[0] is view:
        return found[1], found[2]
    stable, text = json_bytes(_stable(view)), json_bytes(view)
    _TEXTS[id(view)] = (view, stable, text)
    _TEXTS.move_to_end(id(view))
    while len(_TEXTS) > TEXTS_KEPT:
        _TEXTS.popitem(last=False)
    return stable, text


class _Sender:
    """Sends a subscription's message when it changed, or as a heartbeat when it did not for HEARTBEAT_SECONDS."""

    def __init__(self, connection, msg_id):
        self.connection, self.msg_id = connection, msg_id
        self.last, self.sent_at = None, 0.0

    def __call__(self, payload, force=False):
        if set(payload) == {"version", "view"} and isinstance(payload["view"], dict):
            stable, text = _texts(payload["view"])
            body = b'{"version":%d,"view":%s}' % (payload["version"], text)
        else:
            stable, body = json_bytes(_stable(payload)), json_bytes(payload)
        now = time.monotonic()
        if not force and stable == self.last and now - self.sent_at < HEARTBEAT_SECONDS:
            return
        self.last, self.sent_at = stable, now
        self.connection.send_message(construct_event_message(self.msg_id, body))


def loaded_entries(hass):
    return sorted((e for e in hass.config_entries.async_entries(DOMAIN)
                   if e.state is ConfigEntryState.LOADED and not e.data.get("home")), key=lambda e: e.title)


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/entries"})
@callback
def ws_entries(hass, connection, msg):
    def volume(entry):
        coordinator = getattr(entry, "runtime_data", None)
        partners = getattr(coordinator, "partners", None) or []
        return [p["entry_id"] for p in partners], getattr(coordinator, "volume_name", None) if partners else None
    # Rooms sharing one air carry their volume, so that a card editor offers them as one choice.
    connection.send_result(msg["id"], [{"entry_id": e.entry_id, "title": e.title, "area_id": {**e.data, **e.options}.get("area_id"),
        "volume": volume(e)[0], "volume_name": volume(e)[1]} for e in loaded_entries(hass)])


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/subscribe", vol.Optional("entry_id"): str})
@callback
def ws_subscribe(hass, connection, msg):
    entries = loaded_entries(hass)
    wanted = msg.get("entry_id")
    entry = next((e for e in entries if e.entry_id == wanted), None) if wanted else entries[0] if len(entries) == 1 else None
    if entry is None:
        code = "not_found" if wanted else "choose_entry" if entries else "not_configured"
        connection.send_error(msg["id"], code, "Choisissez une pièce Hestia Comfort chargée")
        return
    coordinator = entry.runtime_data
    sender = _Sender(connection, msg["id"])

    @callback
    def send():
        if not coordinator.last_update_success or coordinator.data is None:
            sender({"version": 1, "unavailable": True})
            return
        sender({"version": 1, "view": coordinator.data})

    @callback
    def stopped():
        connection.send_message(websocket_api.event_message(msg["id"], {"version": 1, "reload": True}))

    remove_view = coordinator.async_add_listener(send)
    coordinator.stop_listeners.add(stopped)
    removed = False

    @callback
    def unsubscribe():
        nonlocal removed
        if removed:
            return
        removed = True
        remove_view()
        coordinator.stop_listeners.discard(stopped)

    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])
    send()


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/home_subscribe", vol.Optional("changes", default=False): bool})
@callback
def ws_home_subscribe(hass, connection, msg):
    """The home card: every room view plus the synthesis, refreshed when any room changes.

    With `changes` (PLAN-OPTIMISATION.md, point 12): every room once, then only the rooms that changed, with the rooms'
    order and the synthesis — 93 ko each time a single room moved before. A card older than this asks without it and
    gets every room each time; a Hestia Comfort older than this refuses `changes`, and the card asks again without it."""
    entries = loaded_entries(hass)
    if not entries:
        connection.send_error(msg["id"], "not_configured", "Aucune pièce Hestia Comfort chargée")
        return
    coordinators = [e.runtime_data for e in entries]
    sender = _Sender(connection, msg["id"])
    pending = None
    # What each room and the synthesis were when last sent, and when (`changes` only).
    sent = {"rooms": {}, "home": None, "at": 0.0}

    @callback
    def soon():
        nonlocal pending
        if pending is None:
            pending = async_call_later(hass, HOME_GROUPING_SECONDS, send)

    @callback
    def send(_now=None):
        nonlocal pending
        pending = None
        views, keys = [], {}
        for entry in entries:
            c = entry.runtime_data
            live = c.last_update_success and c.data
            view = c.data if live else {
                "version": 1, "entry_id": entry.entry_id, "title": entry.title,
                "area_id": {**entry.data, **entry.options}.get("area_id"),
                "computed_at": dt_util.utcnow().isoformat(),
                "observations": {}, "assessment": assess({}).to_dict()}
            floor = room_floor(hass, {**entry.data, **entry.options})
            views.append({**view, "floor": floor})
            if msg.get("changes"):
                # The room's view as already turned into text for its cards (_texts), and its floor.
                keys[entry.entry_id] = ((_texts(view)[0] if live else json_bytes(_stable(view))), json_bytes(floor))
        home = synthesis(views)
        if not msg.get("changes"):
            sender({"version": 1, "rooms": views, "home": home})
            return
        changed = [v for v in views if keys[v["entry_id"]] != sent["rooms"].get(v["entry_id"])]
        home_key, now = json_bytes(_stable(home)), time.monotonic()
        if not changed and home_key == sent["home"] and now - sent["at"] < HEARTBEAT_SECONDS:
            return
        sent.update(rooms=keys, home=home_key, at=now)
        connection.send_message(construct_event_message(msg["id"], json_bytes(
            {"version": 1, "changed": changed, "order": [v["entry_id"] for v in views], "home": home})))

    @callback
    def stopped():
        connection.send_message(websocket_api.event_message(msg["id"], {"version": 1, "reload": True}))

    removers = [c.async_add_listener(soon) for c in coordinators]
    removers.extend(hass.bus.async_listen(event, callback(lambda _: soon())) for event in
                    (ar.EVENT_AREA_REGISTRY_UPDATED, fr.EVENT_FLOOR_REGISTRY_UPDATED))
    for c in coordinators:
        c.stop_listeners.add(stopped)

    @callback
    def unsubscribe():
        nonlocal pending
        if pending is not None:
            pending()
            pending = None
        for remove in removers:
            remove()
        removers.clear()
        for c in coordinators:
            c.stop_listeners.discard(stopped)

    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])
    send()


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/view", vol.Required("entry_id"): str})
@callback
def ws_view(hass, connection, msg):
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
        connection.send_error(msg["id"], "not_found", "Pièce Hestia Comfort non chargée")
        return
    connection.send_result(msg["id"], entry.runtime_data.data)


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/review"})
@websocket_api.async_response
async def ws_review(hass, connection, msg):
    """The comfort review of the home over the past year (review_source.py)."""
    from .review_source import async_review
    try:
        result = await async_review(hass)
    except Exception as err:  # the recorder may be missing or busy: the page says so instead of hanging
        connection.send_error(msg["id"], "not_available", str(err))
    else:
        connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/home_periods"})
@websocket_api.async_response
async def ws_periods(hass, connection, msg):
    """The home card's last day, week and month (review_source.py)."""
    from .review_source import async_periods
    try:
        result = await async_periods(hass)
    except Exception as err:  # the recorder may be missing or busy: the card says so instead of hanging
        connection.send_error(msg["id"], "not_available", str(err))
    else:
        connection.send_result(msg["id"], result)


from .configuration import get_configuration


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/configuration", LANGUAGE: str})
@websocket_api.require_admin
@websocket_api.async_response
@spoken
async def ws_configuration(hass, connection, msg):
    service = await get_configuration(hass)
    connection.send_result(msg["id"], service.snapshot())


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/discover", LANGUAGE: str, vol.Optional("area_id"): str, vol.Optional("entry_id"): str})
@websocket_api.require_admin
@websocket_api.async_response
@spoken
async def ws_discover(hass, connection, msg):
    service = await get_configuration(hass)
    try:
        result = service.discover(msg.get("area_id"), msg.get("entry_id"))
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_config", str(err))
    else:
        connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/overview", LANGUAGE: str})
@websocket_api.require_admin
@websocket_api.async_response
@spoken
async def ws_overview(hass, connection, msg):
    service = await get_configuration(hass)
    connection.send_result(msg["id"], service.overview())


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/weather_proposal", LANGUAGE: str, vol.Optional("entry_id"): str})
@websocket_api.require_admin
@websocket_api.async_response
@spoken
async def ws_weather(hass, connection, msg):
    service = await get_configuration(hass)
    try:
        connection.send_result(msg["id"], service.weather_proposal(msg.get("entry_id")))
    except ValueError as err:
        connection.send_error(msg["id"], "not_available", str(err))


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/validate_config", LANGUAGE: str, vol.Required("config"): dict, vol.Optional("home", default=False): bool})
@websocket_api.require_admin
@websocket_api.async_response
@spoken
async def ws_validate(hass, connection, msg):
    service = await get_configuration(hass)
    try:
        config, warnings = service.validate(msg["config"], home=msg["home"])
    except (ValueError, TypeError) as err:
        connection.send_error(msg["id"], "invalid_config", str(err))
    else:
        connection.send_result(msg["id"], {"config": config, "warnings": warnings, "revision": service.revision()})


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/save_config", LANGUAGE: str, vol.Required("config"): dict,
    vol.Required("revision"): str, vol.Optional("entry_id"): str, vol.Optional("home", default=False): bool,
    vol.Optional("acknowledged", default=[]): [str]})
@websocket_api.require_admin
@websocket_api.async_response
@spoken
async def ws_save(hass, connection, msg):
    service = await get_configuration(hass)
    try:
        result = await service.save(msg["config"], msg["revision"], msg.get("entry_id"), home=msg["home"], acknowledged=msg["acknowledged"])
    except (ValueError, TypeError) as err:
        connection.send_error(msg["id"], "invalid_config", str(err))
    else:
        connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/remove_room", LANGUAGE: str, vol.Required("entry_id"): str, vol.Required("revision"): str})
@websocket_api.require_admin
@websocket_api.async_response
@spoken
async def ws_remove(hass, connection, msg):
    service = await get_configuration(hass)
    try:
        result = await service.remove(msg["entry_id"], msg["revision"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_config", str(err))
    else:
        connection.send_result(msg["id"], result)


# The 3.0 advisor (advisor_home.py, room/advice.py): what the card and the hub's expert pages ask of it.
OPINIONS = ("faux", "inutile", "pas_maintenant")


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/advice_opinion", vol.Required("entry_id"): str,
                                  vol.Required("avis"): vol.In(OPINIONS), vol.Optional("note", default=""): vol.All(str, vol.Length(max=500))})
@websocket_api.async_response
async def ws_advice_opinion(hass, connection, msg):
    """« Ce conseil ne va pas », sent by the card: the situation kept to be replayed; « Pas maintenant » puts the gesture
    aside for the household's time, until the hour sent back."""
    from .advisor_home import DATA
    home = hass.data.get(DATA)
    advisor = home.advisor_of(msg["entry_id"]) if home else None
    if advisor is None:
        connection.send_error(msg["id"], "not_found", "Pas de conseil 3.0 pour cette pièce")
        return
    connection.send_result(msg["id"], {"jusqu_a": await advisor.opinion(msg["avis"], msg["note"])})


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/atelier"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_atelier(hass, connection, msg):
    """The Atelier's chronology: the advice changes, the snapshots kept, the opinions and the gestures followed."""
    from .advisor_home import DATA
    from .advisor_store import AdvisorFiles
    home = hass.data.get(DATA)
    files = home.files if home else AdvisorFiles(hass.config.path())
    connection.send_result(msg["id"], await hass.async_add_executor_job(files.atelier, dt_util.utcnow()))


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/trace", vol.Required("file"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_trace(hass, connection, msg):
    """One decision's trace, layer by layer, from a snapshot or a reported situation."""
    from .advisor_home import DATA
    from .advisor_store import AdvisorFiles
    home = hass.data.get(DATA)
    files = home.files if home else AdvisorFiles(hass.config.path())
    found = await hass.async_add_executor_job(files.trace, msg["file"])
    if found is None:
        connection.send_error(msg["id"], "not_found", "Instantané introuvable")
    else:
        connection.send_result(msg["id"], found)


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/relearn"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_relearn(hass, connection, msg):
    """The nightly learning now, for the Atelier and the lab (advisor_home.py `learn`): started in the background, its
    report written to apprentissage.jsonl as each night's."""
    from .advisor_home import DATA
    home = hass.data.get(DATA)
    if home is None or home.learning:
        connection.send_result(msg["id"], {"lance": False})
        return
    hass.async_create_background_task(home.learn(), "hestia_comfort relearn")
    connection.send_result(msg["id"], {"lance": True})


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/set_analysis", LANGUAGE: str, vol.Required("enabled"): bool})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_analysis(hass, connection, msg):
    """Our analysis tools on or off (configuration.py `set_analysis`): on at the lab, off by default; set by « Je participe »
    in « À propos » (frontend/panel.ts `fieldTrial`) while the engine is in beta."""
    service = await get_configuration(hass)
    await service.set_analysis(msg["enabled"])
    connection.send_result(msg["id"], {"analysis": msg["enabled"]})


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/field_report", vol.Optional("language"): str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_field_report(hass, connection, msg):
    """« Participez à l'amélioration du moteur » (field_report.py): the anonymous report, and what would make it more
    useful. Nothing is sent anywhere: the panel shows it and the person downloads it."""
    from . import field_report
    from .advisor_home import DATA
    service = await get_configuration(hass)
    connection.send_result(msg["id"], await field_report.build(hass, service, hass.data.get(DATA)))
