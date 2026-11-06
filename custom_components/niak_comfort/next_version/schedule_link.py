"""The heating's schedule for one thermostat, read by engine/schedule.py from the integration that plans it.

ha-chauffage's entities are found by their stable unique id (`{entry_id}_{climate}_{key}`), Scheduler's schedules by
their integration and the `entities` they drive — never by a name. Both refresh on their own; the room's minute tick
reads them, nothing more is followed."""
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .engine import schedule

DOMAINS = {"planned": "sensor", "override": "binary_sensor", "next_change": "sensor"}


def _state(hass, registry, entry_id, climate, role):
    entity_id = registry.async_get_entity_id(DOMAINS[role], schedule.PLATFORM, f"{entry_id}_{climate}_{schedule.KEYS[role]}")
    state = hass.states.get(entity_id) if entity_id else None
    return (state.state, dict(state.attributes)) if state is not None else None


def _loaded(hass, domain):
    return [e for e in hass.config_entries.async_entries(domain) if e.state.value == "loaded"]


def _chauffage(hass, climate):
    entries = _loaded(hass, schedule.PLATFORM)
    if not entries:
        return None
    registry, entry_id = er.async_get(hass), entries[0].entry_id
    found = {role: _state(hass, registry, entry_id, climate, role) for role in DOMAINS}
    if found["planned"] is None:
        return None
    return schedule.next_change(found["planned"], found["override"], found["next_change"], dt_util.now())


def _schedules(hass, climate):
    """Scheduler's schedules that drive this thermostat, as states: the switches of Scheduler installed here, and those
    carrying a schedule's own attributes, copied from another Home Assistant (Remote Home-Assistant)."""
    registry = er.async_get(hass)
    ids = {entity.entity_id for entry in _loaded(hass, schedule.SCHEDULER)
           for entity in er.async_entries_for_config_entry(registry, entry.entry_id) if entity.domain == "switch"}
    return [state for state in hass.states.async_all("switch")
            if (state.entity_id in ids or schedule.is_schedule(state.attributes))
            and climate in (state.attributes.get("entities") or ())]


def _scheduler(hass, climate):
    found = _schedules(hass, climate)
    if not found:
        return None
    thermostat = hass.states.get(climate)
    attrs = dict(thermostat.attributes) if thermostat else {}
    temperatures = attrs.get("preset_temperatures") if isinstance(attrs.get("preset_temperatures"), dict) else attrs
    now = dt_util.now()
    return schedule.earliest(schedule.scheduler_change(s.state, dict(s.attributes), temperatures, now) for s in found)


def next_change(hass, climate, disabled=()):
    """The thermostat's next change, from ha-chauffage, else from Scheduler, each unless turned off (`disabled`); None:
    neither installed, the thermostat scheduled by neither, or nothing ahead."""
    if not climate:
        return None
    change = _chauffage(hass, climate) if schedule.PLATFORM not in disabled else None
    if change is None and schedule.SCHEDULER not in disabled:
        change = _scheduler(hass, climate)
    return change


def planners(hass, climate):
    """The integrations that schedule this thermostat: « chauffage » (its planned preset exists), « scheduler » (a
    schedule drives it, running or not)."""
    if not climate:
        return set()
    out = set()
    entries = hass.config_entries.async_entries(schedule.PLATFORM)
    if entries and er.async_get(hass).async_get_entity_id(
            "sensor", schedule.PLATFORM, f"{entries[0].entry_id}_{climate}_{schedule.KEYS['planned']}"):
        out.add(schedule.PLATFORM)
    if _schedules(hass, climate):
        out.add(schedule.SCHEDULER)
    return out
