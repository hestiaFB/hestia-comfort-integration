"""Each source read and normalized, the heating's real action, and the bounce of a window just opened."""
from dataclasses import replace

from homeassistant.helpers import entity_registry as er

from ..const import OPEN_DEBOUNCE_SECONDS
from ..discovery import voc_device_class
from .. import schedule_link
from ..engine import schedule, thermostat as thermostats
from ..engine.sources import Reading, indicator_state, normalize
from .constants import STATE_KINDS


class ReadingsMixin:
    """Part of ComfortCoordinator: its methods use the coordinator's own state (self)."""

    # Contacts and heating report only when they change; Home Assistant marks them
    # unavailable when the device is lost, so their age says nothing about validity.
    def _reading(self, entity_id, kind, now):
        state = self.hass.states.get(entity_id)
        raw = state.state if state else None
        unit = state.attributes.get("unit_of_measurement") if state else None
        if state:
            if kind == "voc":
                voc_class = voc_device_class(self.hass, entity_id)
                if voc_class is None or (unit is None and voc_class != "volatile_organic_compounds_index"):
                    return Reading(None, "unknown", entity_id, state.last_reported.isoformat(), "incompatible_unit")
            if kind == "heating":
                raw, detail = self._heating_action(state)
            elif kind in ("cover", "purifier_speed"):
                raw = state.attributes.get("current_position" if kind == "cover" else "percentage") if state.state not in ("unknown", "unavailable") else None
                unit = "%"
        # HA last_reported tracks reception even when the measured value is unchanged.
        # It is not the sensor's physical sampling time.
        reading = normalize(kind, raw, unit,
                            source=entity_id, reported_at=self._heard(entity_id, state) if state else None,
                            now=now, max_age=None if kind in STATE_KINDS else self.settings.max_age_seconds)
        # Where « heating » or « idle » came from: the thermostat's own action, or the indicator chosen beside it.
        if kind == "heating" and state and reading.usable:
            reading = replace(reading, detail=detail)
        return reading

    def _heating_action(self, state):
        """What the heating does, and from where: off when the thermostat is off; then the indicator chosen
        beside it (a valve, a relay, a « work state »), which the person trusts more; then its own hvac_action."""
        if state.state in ("unknown", "unavailable"):
            return None, None
        if state.state == "off":
            return "off", "hvac_mode"
        indicator = self.sources.get("heating_indicator")
        said = self.hass.states.get(indicator) if indicator else None
        running = indicator_state(said.state) if said else None
        if running is not None:
            return ("cooling" if running == "heating" and state.state == "cool" else running), "indicator"
        action = state.attributes.get("hvac_action")
        return action, "hvac_action" if action is not None else None

    def _heard(self, entity_id, state):
        """When the device last spoke: an unchanged humidity is current if its thermometer just reported."""
        latest = state.last_reported
        registry = er.async_get(self.hass)
        entry = registry.async_get(entity_id)
        if entry and entry.device_id:
            for sibling in er.async_entries_for_device(registry, entry.device_id):
                other = self.hass.states.get(sibling.entity_id)
                if other and other.state not in ("unknown", "unavailable") and other.last_reported > latest:
                    latest = other.last_reported
        return latest

    def _bouncing(self, entity_id, reading, now):
        since = self.opened_since.get(entity_id)
        return (reading.value is True and since is not None and entity_id not in self.followed
                and (now - since).total_seconds() < OPEN_DEBOUNCE_SECONDS)

    def _thermostat(self):
        """What the room's Versatile Thermostat says (engine/thermostat.py), with its schedule's next change; for any
        other heating, that next change alone; None without either."""
        entity_id = self.sources.get("heating")
        entry = er.async_get(self.hass).async_get(entity_id) if entity_id else None
        state = self.hass.states.get(entity_id) if entity_id else None
        # The schedule's next change (ha-chauffage, Scheduler: engine/schedule.py), for any thermostat they plan.
        change = schedule_link.next_change(self.hass, entity_id, {k for k in schedule.PLANNERS if not self._uses(k)})
        if not self._uses(thermostats.PLATFORM) or not entry or entry.platform != thermostats.PLATFORM or not state or state.state in ("unknown", "unavailable"):
            return {"next": change} if change else None
        return {**thermostats.read(state.state, dict(state.attributes)), "next": change}
