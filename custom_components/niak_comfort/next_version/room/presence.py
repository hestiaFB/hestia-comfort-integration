"""Who is at home: the room's people, the alarm, presence sensors, and the extensions turned off."""
import time

from homeassistant.helpers import entity_registry as er

from ..engine import people


# Alarmo's panel, found in the entity registry once every ten minutes (PLAN-OPTIMISATION.md, point 9): each room's
# calculation asked for it twice, through every entity of the home. A panel added or turned off is seen within ten minutes.
ALARMO, ALARMO_KEPT = "hestia_comfort_alarmo", 600


def alarmo(hass):
    """Alarmo's alarm panel, or None."""
    kept = hass.data.get(ALARMO)
    now = time.monotonic()
    if kept is None or now >= kept[0]:
        entities = getattr(er.async_get(hass), "entities", None) or {}
        kept = hass.data[ALARMO] = (now + ALARMO_KEPT, next((e.entity_id for e in entities.values() if e.domain == "alarm_control_panel"
                                                             and e.platform == people.PLATFORM and not e.disabled_by), None))
    return kept[1]


class PresenceMixin:
    """Part of ComfortCoordinator: its methods use the coordinator's own state (self)."""

    def _uses(self, key):
        """False when the person turned this integration off in the general settings."""
        home = self.home_configuration.home if self.home_configuration is not None else {}
        return key not in (home.get("disabled") or [])

    def _alarm_entity(self):
        """The home's alarm panel: the one chosen in the general settings, else Alarmo found by itself; None for none."""
        chosen = (self.home_configuration.home.get("alarm") if self.home_configuration is not None else None)
        if isinstance(chosen, str):
            return chosen or None
        return alarmo(self.hass)

    def _occupancy_entities(self):
        alarm = self._alarm_entity()
        return [*([alarm] if alarm else []), "zone.home", *self.config.get("persons", [])]

    def _people(self):
        """The room's people at home or away (engine/people.py); None when none are chosen."""
        chosen = [e for e in self.config.get("persons", []) if isinstance(e, str)]
        if not chosen:
            return None
        states = [self.hass.states.get(e) for e in chosen]
        return people.people([(str(s.attributes.get("friendly_name") or e) if s else e, s.state if s else None)
                              for e, s in zip(chosen, states)])

    def _alarm(self):
        entity_id = self._alarm_entity()
        state = self.hass.states.get(entity_id) if entity_id else None
        found = people.alarm(state.state if state else None)
        return {**found, "entity_id": entity_id, "name": str(state.attributes.get("friendly_name") or entity_id)} if found else None

    def _off_minutes(self, entity_id, now):
        """Minutes a presence sensor has said « nobody », read from Home Assistant: right even after a restart."""
        state = self.hass.states.get(entity_id)
        if not state or state.state != "off" or state.attributes.get("device_class") not in ("occupancy", "presence"):
            return None
        return max(0.0, (now - state.last_changed).total_seconds() / 60)

    def _occupied(self):
        """True when the room's people (or, without any chosen, the household) are at home, False when not, None when
        nothing says it. An alarm armed « away » or « vacation » means an empty home (engine/people.py)."""
        zone = self.hass.states.get("zone.home")
        count = None
        if zone and zone.attributes.get("persons"):
            try:
                count = float(zone.state)
            except (TypeError, ValueError):
                count = None
        return people.occupied(self._people(), self._alarm(), count)
