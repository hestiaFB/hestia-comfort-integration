"""Bundled admin panel and Lovelace card: one installation, nothing to declare by hand.

The settings live in the shared « Hestia » panel (socle, see socle.py), as the « Confort » tab.
"""
import hashlib
from pathlib import Path
import voluptuous as vol
from aiohttp import web
from homeassistant.components import websocket_api
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.core import callback
from . import advisor_home, domain_migration, health, weather_link
from .engine import feedback
from .light_driver import light_info
from .engine.i18n import language, speaking, t
from homeassistant.util import dt as dt_util
from .configuration import get_configuration
from .const import DOMAIN, VERSION
from .socle import async_register_brick, async_register_card

ASSETS = "/hestia_comfort-assets"
CARD_URL = f"{ASSETS}/hestia-comfort-card.js"


class _LiveCardView(HomeAssistantView):
    """The card of a beta, at its usual address, always checked again by the browser (« no-cache »): a beta is
    rebuilt often, and a browser left alone keeps a script some minutes after a page reload."""
    url = CARD_URL
    name = "hestia_comfort:live_card"
    requires_auth = False

    async def get(self, request):
        return web.FileResponse(Path(__file__).parent / "frontend" / "hestia-comfort-card.js", headers={"Cache-Control": "no-cache"})


def _fingerprint(path):
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:8]
    except OSError:
        return None


async def async_setup_panel(hass):
    if not hass.http or not hasattr(hass.http, "async_register_static_paths"):
        return  # Isolated engine tests and headless HA setups have no frontend.
    if not hass.data.get(DOMAIN + "_panel_asset"):
        # Cached by the browser: every script is asked for with `?v=<version>`, the fonts never change.
        # A beta is tried and rebuilt often: its files are checked again on every load, a page kept by the browser cannot
        # hold an older card. A stable version is cached as before.
        if "b" in VERSION:
            # Declared before the static files: this one address answers first.
            hass.http.register_view(_LiveCardView())
        await hass.http.async_register_static_paths([StaticPathConfig(
            ASSETS, str(Path(__file__).parent / "frontend"), "b" not in VERSION)])
        # The versioned dashboard resource, with a guarded extra module only as fallback.
        # A beta keeps one address, checked again on every load (above): a page the browser kept still gets the new card.
        # A stable version: its version and a fingerprint of the bundle, so every build has its own cached address.
        stamp = None if "b" in VERSION else await hass.async_add_executor_job(_fingerprint, Path(__file__).parent / "frontend" / "hestia-comfort-card.js")
        await async_register_card(hass, CARD_URL, f"{VERSION}-{stamp}" if stamp else f"{VERSION}-dev" if "b" in VERSION else VERSION)
        websocket_api.async_register_command(hass, ws_health)
        websocket_api.async_register_command(hass, ws_twins)
        websocket_api.async_register_command(hass, ws_answer)
        websocket_api.async_register_command(hass, ws_alarm)
        websocket_api.async_register_command(hass, ws_pollen_allergy)
        websocket_api.async_register_command(hass, ws_foyer)
        websocket_api.async_register_command(hass, ws_extension)
        websocket_api.async_register_command(hass, ws_lights)
        websocket_api.async_register_command(hass, ws_light_info)
        hass.data[DOMAIN + "_panel_asset"] = True
    await async_register_brick(hass, {
        "domain": DOMAIN, "name": "Hestia Confort", "slug": "confort", "version": VERSION,
        "icon": "mdi:home-thermometer-outline", "navigation": 3,
        "menu": [["", "Vue d’ensemble", "home"], ["pieces", "Pièces", "rooms"], ["reglages", "Réglages", "settings"],
                 ["apprentissage", "Apprentissage", "learning"], ["extensions", "Extensions", "extensions"], ["bilan", "Bilan", "review"],
                 ["a-propos", "À propos", "info"]], "module_url": f"{ASSETS}/panel.js?v={VERSION}",
        "element": "hestia-comfort-setup", "status": comfort_status, "legacy_path": "hestia-confort",
        "migration": migration_status,
    }, f"{ASSETS}/hestia-socle.js?v={VERSION}")


async def migration_status(hass):
    """Hestia Confort's lines in the hub's « Passage au nom Hestia » (socle 1.16): its rooms and what they learned."""
    status = await domain_migration.async_status(hass)
    if status is None:
        return None
    rooms = [e for e in hass.config_entries.async_entries(DOMAIN) if not e.data.get("home")]
    status["summary"] = {"rooms": len(rooms), "learning": 1 if status["stores"] else 0}
    return status


# The panel's language, sent with each of its commands (engine/i18n.py).
LANGUAGE = vol.Optional("language")


def _count(n, one, many):
    return t(one, n=n) if n == 1 or n == 0 and language() == "fr" else t(many, n=n)


async def comfort_status(hass, lang=None):
    """What the « Hestia » home page says about Hestia Confort, from its own settings only, in the hub's language (socle 1.14)."""
    with speaking(lang):
        return await _status(hass)


async def _status(hass):
    service = await get_configuration(hass)
    rooms = [{"title": e.title, "loaded": e.state.value == "loaded", "entry": e} for e in service.entries()]
    weather = weather_link.status(hass)
    if not rooms:
        return {"level": "action", "summary": t("Aucune pièce suivie pour l’instant."),
                "details": [t("Commencez par le Salon dans l’onglet Confort.")], "links": []}
    followed = _count(len(rooms), "{n} pièce suivie", "{n} pièces suivies")
    # The same points as the « Confort » tab's technical report: one count everywhere.
    checked = health.report(await health.facts(hass, VERSION))
    todo, details, links = [line["text"] for line in checked["todo"]], [], []
    linked = next((p for p in weather.get("places", []) if p["entry_id"] == service.home.get("weather")), None)
    if linked:
        links.append(t("Relié à Hestia Weather · {place}", place=linked["title"]))
    elif weather.get("installed") and weather.get("places"):
        details.append(t("Hestia Weather est installé : il peut remplir l’extérieur pour vous."))
    if todo:
        return {"level": "action", "summary": f"{followed}, " + _count(len(todo), "{n} point à régler.", "{n} points à régler."),
                "details": todo + details, "links": links}
    return {"level": "ok", "summary": f"{followed}, " + t("rien à régler."), "details": details, "links": links}


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/health", LANGUAGE: str})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_health(hass, connection, msg):
    """The home page of the « Confort » tab: what works, what to fix, what could be set better."""
    with speaking(msg.get("language")):
        connection.send_result(msg["id"], health.report(await health.facts(hass, VERSION)))


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/twins", LANGUAGE: str})
@websocket_api.require_admin
@callback
def ws_twins(hass, connection, msg):
    """« Ce que Hestia a appris » : each room's twin, with its last 24 hours replayed against the measures."""
    rooms = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        coordinator = getattr(entry, "runtime_data", None)
        if entry.data.get("home") or coordinator is None:
            continue
        learned = getattr(coordinator, "twin", None) or {"status": "learning", "samples": 0, "days": 0}
        week = feedback.summarize(getattr(coordinator, "feedback", []), dt_util.utcnow())["week"]
        air = (learned.get("model") or {}).get("air") or {}
        rooms.append({"entry_id": entry.entry_id, "title": entry.title,
                      "twin": {k: v for k, v in learned.items() if k != "model"}, "week": week,
                      "progress": coordinator.learning_progress() if hasattr(coordinator, "learning_progress") else None,
                      # Where the station's sensor is shaded, as learned (engine/sunlight.py).
                      "sun_shade": getattr(coordinator, "sun_shade", None),
                      # The air it has learned: CO₂ and VOC with enough open half hours to promise a result.
                      "air": [name for name, model in air.items() if model and model.get("open_samples", 0) >= 6],
                      "questions": _questions(coordinator, msg.get("language")),
                      # The 3.0 advisor's own learning (advisor_home.py): effects and their proof, shown in its place.
                      "advisor": advisor_home.knowing(hass, entry.entry_id)})
    connection.send_result(msg["id"], {"version": 1, "rooms": rooms, "outside": advisor_home.outside(hass)})


def _questions(coordinator, lang):
    if not hasattr(coordinator, "questions"):
        return []
    with speaking(lang):
        return coordinator.questions()


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/set_extension", LANGUAGE: str, vol.Required("key"): str, vol.Required("enabled"): bool})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_extension(hass, connection, msg):
    """A third-party integration used or not (general settings), for every room."""
    try:
        with speaking(msg.get("language")):
            snapshot = await (await get_configuration(hass)).set_extension(msg["key"], msg["enabled"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid", str(err))
        return
    connection.send_result(msg["id"], snapshot)


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/set_alarm", LANGUAGE: str, vol.Required("alarm"): vol.Any(None, str)})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_alarm(hass, connection, msg):
    """The home's alarm (general settings): found by itself, chosen, or none."""
    try:
        with speaking(msg.get("language")):
            snapshot = await (await get_configuration(hass)).set_alarm(msg["alarm"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid", str(err))
        return
    connection.send_result(msg["id"], snapshot)


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/set_pollen_allergy", LANGUAGE: str, vol.Required("allergy"): bool})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_pollen_allergy(hass, connection, msg):
    """Someone at home is allergic to pollens (general settings): airings short and early on days of high pollens."""
    try:
        with speaking(msg.get("language")):
            snapshot = await (await get_configuration(hass)).set_pollen_allergy(msg["allergy"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid", str(err))
        return
    connection.send_result(msg["id"], snapshot)


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/set_foyer", LANGUAGE: str, vol.Required("foyer"): dict})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_foyer(hass, connection, msg):
    """The household's settings (« Réglages du foyer »), saved at once."""
    try:
        with speaking(msg.get("language")):
            snapshot = await (await get_configuration(hass)).set_foyer(msg["foyer"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid", str(err))
        return
    connection.send_result(msg["id"], snapshot)


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/set_lights", LANGUAGE: str, vol.Required("lights"): dict})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_lights(hass, connection, msg):
    """The « Lumières » settings (Extensions, and each room's Notifications tab), saved at once."""
    try:
        with speaking(msg.get("language")):
            snapshot = await (await get_configuration(hass)).set_lights(msg["lights"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid", str(err))
        return
    connection.send_result(msg["id"], snapshot)


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/light_info", vol.Required("entity_id"): str})
@websocket_api.require_admin
@callback
def ws_light_info(hass, connection, msg):
    """A light as the « Lumières » settings show it: a WLED segment's LEDs, its strip's segments and who drives them."""
    connection.send_result(msg["id"], light_info(hass, msg["entity_id"]))


@websocket_api.websocket_command({vol.Required("type"): "hestia_comfort/answer", LANGUAGE: str, vol.Required("entry_id"): str,
                                  vol.Required("key"): str, vol.Required("answer"): vol.In(("yes", "no", "unknown"))})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_answer(hass, connection, msg):
    """An answer to a learning question: it names a cause, or stops a window being taken for an oversight."""
    try:
        with speaking(msg.get("language")):
            await (await get_configuration(hass)).answer(msg["entry_id"], msg["key"], msg["answer"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid", str(err))
        return
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if (coordinator := getattr(entry, "runtime_data", None)) is not None:
        await coordinator.async_request_refresh()
    connection.send_result(msg["id"], {"saved": True})
