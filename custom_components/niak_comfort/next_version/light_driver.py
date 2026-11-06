"""« Lumières »: the one thing Hestia Confort commands. A coloured light chosen in the hub takes the advice's colour.

The person chose the light, when it may act (already on, or woken for a gesture or an alert; never at night; only when
someone is home) and its look for each state. What the light was before Hestia-FB changed it is kept, and put back when the
advice calms down or a safeguard stops it. A light switched off by hand is left alone until the advice changes.
A WLED segment is a light of its own; when the strip has several, its main light is turned on with it, and put back."""
from datetime import timedelta
import logging

from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .engine import light_plan
from .engine.verdict import strongest
from .entities import partner_coordinators, units
from .websocket import loaded_entries

_LOGGER = logging.getLogger(__name__)
DRIVER = "hestia_comfort_lights"


class LightDriver:
    def __init__(self, hass, configuration):
        self.hass = hass
        self.configuration = configuration
        self.listening = {}
        # By light: how it was before Hestia-FB, the last decision taken, and whether the person switched it off by hand.
        self.kept, self.decided, self.silenced, self.mains = {}, {}, {}, {}
        # By WLED segment whose speed Hestia-FB changed: its speed entity and the speed it had.
        self.speeds = {}

    @callback
    def start(self):
        self.stop = async_track_time_interval(self.hass, callback(lambda _now: self._tick()), timedelta(seconds=60))
        self._tick()

    @callback
    def _tick(self):
        """Every minute: listen to rooms loaded since, and look again at the night and the presence."""
        current = {id(e.runtime_data): e.runtime_data for e in loaded_entries(self.hass) if getattr(e, "runtime_data", None)}
        for key in [k for k in self.listening if k not in current]:
            self.listening.pop(key)()
        for key, coordinator in current.items():
            if key not in self.listening:
                self.listening[key] = coordinator.async_add_listener(self.refresh)
        self.refresh()

    def rules(self):
        lights = self.configuration.home.get("lights") or {}
        if lights.get("mode") == "rooms":
            found = [{**rule, "follow": entry_id} for entry_id, rule in (lights.get("rooms") or {}).items()]
        else:
            found = [lights["home"]] if lights.get("home") else []
        # WLED turned off in Extensions: its lights are no longer driven.
        if "wled" in (self.configuration.home.get("disabled") or []):
            registry = er.async_get(self.hass)
            found = [r for r in found if getattr(registry.async_get(r["entity_id"]), "platform", None) != "wled"]
        return found

    def verdict(self, follow):
        if follow == "home":
            return strongest([v for _, v in units(self.hass, loaded_entries(self.hass))])
        entry = self.hass.config_entries.async_get_entry(follow)
        coordinator = getattr(entry, "runtime_data", None)
        if coordinator is None or not getattr(coordinator, "data", None):
            return None
        views = [coordinator.data, *(c.data for c in partner_coordinators(self.hass, coordinator))]
        return strongest([v["verdict"] for v in views if v and v.get("verdict")])

    def someone_home(self):
        zone = self.hass.states.get("zone.home")
        try:
            return zone is None or float(zone.state) > 0
        except ValueError:
            return True

    @callback
    def refresh(self):
        """Each light's state, decided again; nothing is sent while the decision stays the same."""
        rules = self.rules()
        driven = {rule["entity_id"] for rule in rules}
        # A light no longer chosen goes back to how it was.
        for entity_id in [e for e in self.kept if e not in driven]:
            self._send_restore(entity_id)
        hour, home = dt_util.now().hour, self.someone_home()
        for rule in rules:
            entity_id = rule["entity_id"]
            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unavailable", "unknown"):
                continue
            key = light_plan.state_key(self.verdict(rule.get("follow", "home")))
            decision = (key, light_plan.blocked(rule, hour, home), rule.get("states", {}).get(key) if key else None, rule.get("wake"))
            ours = entity_id in self.kept
            # A light the person turns on while a gesture waits takes its colour then: its own on/off counts until Hestia-FB changes it.
            decision = (*decision, None if ours else state.state == "on")
            if ours and self.decided.get(entity_id, (None,))[0] == "on" and state.state == "off":
                # Switched off by hand while Hestia-FB had changed it: the person's choice, kept until the advice changes.
                self.kept.pop(entity_id, None)
                self.silenced[entity_id] = key
                ours = False
            if self.silenced.get(entity_id) is not None and self.silenced[entity_id] == key:
                continue
            self.silenced.pop(entity_id, None)
            if self.decided.get(entity_id, (None, None))[1] == decision:
                continue
            action = light_plan.plan(rule, key, is_on=state.state == "on", hour=hour, someone_home=home, ours=ours)
            self.decided[entity_id] = (action[0] if action else None, decision)
            if action is None:
                continue
            if action[0] == "restore":
                self._send_restore(entity_id)
                continue
            if not ours:
                self.kept[entity_id] = light_plan.snapshot(state.state, state.attributes)
            if action[0] == "off":
                self._call("turn_off", entity_id, {})
            else:
                self._wake_main(entity_id)
                self._set_speed(entity_id, light_plan.speed(rule, key))
                self._call("turn_on", entity_id, light_plan.fit(action[1], state.attributes))

    def _main_of(self, entity_id):
        """The main light of a WLED strip cut into segments: a segment alone does not light the strip."""
        registry = er.async_get(self.hass)
        entry = registry.async_get(entity_id)
        if entry is None or entry.platform != "wled" or "_" not in (entry.unique_id or ""):
            return None
        return registry.async_get_entity_id("light", "wled", entry.unique_id.rsplit("_", 1)[0])

    def _set_speed(self, entity_id, value):
        """A WLED effect's speed, set on its segment before the effect starts; the speed it had is put back with the light."""
        number = speed_entity(self.hass, entity_id)
        state = self.hass.states.get(number) if number else None
        if value is None or state is None or state.state in ("unavailable", "unknown"):
            return
        self.speeds.setdefault(entity_id, (number, state.state))
        try:
            if float(state.state) == value:
                return
        except ValueError:
            pass
        self._number(number, value)

    def _number(self, entity_id, value):
        self.hass.async_create_task(self.hass.services.async_call("number", "set_value", {"entity_id": entity_id, "value": value}, blocking=False))

    def _wake_main(self, entity_id):
        main = self._main_of(entity_id)
        if not main:
            return
        state = self.hass.states.get(main)
        if main not in self.mains and state is not None:
            self.mains[main] = {"kept": light_plan.snapshot(state.state, state.attributes), "users": set()}
        if main in self.mains:
            self.mains[main]["users"].add(entity_id)
            if state is not None and state.state == "off":
                self._call("turn_on", main, {})

    def _send_restore(self, entity_id):
        kept = self.kept.pop(entity_id, None)
        self.decided.pop(entity_id, None)
        if kept is not None:
            service, data = light_plan.restore(kept)
            self._call(service, entity_id, data)
        if entity_id in self.speeds:
            number, before = self.speeds.pop(entity_id)
            try:
                self._number(number, float(before))
            except ValueError:
                pass
        for main, held in list(self.mains.items()):
            held["users"].discard(entity_id)
            if not held["users"]:
                service, data = light_plan.restore(self.mains.pop(main)["kept"])
                if service == "turn_off":
                    self._call(service, main, data)

    def _call(self, service, entity_id, data):
        self.hass.async_create_task(self.hass.services.async_call("light", service, {"entity_id": entity_id, **data}, blocking=False))


def _segment(registry, entity_id):
    """A WLED segment light: its registry entry, its strip's address and its number (unique id « <mac>_<segment> »)."""
    entry = registry.async_get(entity_id)
    if entry is None or entry.platform != "wled" or "_" not in (entry.unique_id or ""):
        return None
    mac, tail = entry.unique_id.rsplit("_", 1)
    return (entry, mac, int(tail)) if tail.isdigit() else None


def speed_entity(hass, entity_id):
    """The « Vitesse » number of a WLED segment, or None for any other light."""
    registry = er.async_get(hass)
    found = _segment(registry, entity_id)
    return registry.async_get_entity_id("number", "wled", f"{found[1]}_speed_{found[2]}") if found else None


def _leds(hass, config_entry_id, number):
    """How many LEDs a segment has, read from the WLED integration's last update; None when it cannot say."""
    coordinator = getattr(hass.config_entries.async_get_entry(config_entry_id), "runtime_data", None)
    segments = getattr(getattr(getattr(coordinator, "data", None), "state", None), "segments", None)
    if segments is None:
        return None
    segment = segments.get(number) if isinstance(segments, dict) else next((s for s in segments if getattr(s, "segment_id", None) == number), None)
    if segment is None:
        return None
    length = getattr(segment, "length", None)
    if isinstance(length, int):
        return length
    start, stop = getattr(segment, "start", None), getattr(segment, "stop", None)
    return stop - start if isinstance(start, int) and isinstance(stop, int) else None


def _automations(hass, entity_id):
    """The automations already driving a light, by their names: the hub warns before Hestia-FB takes it."""
    try:
        from homeassistant.components.automation import automations_with_entity
        found = automations_with_entity(hass, entity_id)
    except Exception:  # noqa: BLE001 — no automation integration: nothing to warn about.
        return []
    return sorted(str(s.attributes.get("friendly_name") or a) for a in found if (s := hass.states.get(a)) is not None and s.state == "on")


def light_info(hass, entity_id):
    """What the hub shows of a light: a WLED segment's number of LEDs, and each segment of its strip with what drives it."""
    registry = er.async_get(hass)
    found = _segment(registry, entity_id)
    if found is None:
        return {"wled": getattr(registry.async_get(entity_id), "platform", None) == "wled", "leds": None, "segments": []}
    entry, mac, _ = found
    segments = []
    for other in er.async_entries_for_config_entry(registry, entry.config_entry_id):
        if other.domain != "light" or not (seg := _segment(registry, other.entity_id)) or seg[1] != mac:
            continue
        segments.append({"entity_id": other.entity_id, "segment": seg[2], "leds": _leds(hass, entry.config_entry_id, seg[2]),
                         "speed": speed_entity(hass, other.entity_id), "automations": _automations(hass, other.entity_id)})
    segments.sort(key=lambda s: s["segment"])
    own = next((s for s in segments if s["entity_id"] == entity_id), None)
    return {"wled": True, "leds": own["leds"] if own else None, "segments": segments}


async def async_start_lights(hass, configuration):
    """Started once Home Assistant runs; the hub's « Lumières » settings refresh it at once."""
    if DRIVER not in hass.data:
        driver = LightDriver(hass, configuration)
        hass.data[DRIVER] = driver
        driver.start()
    return hass.data[DRIVER]
