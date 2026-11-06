"""Rooms open onto each other: the partners, the sources they share, and one gesture for their shared air."""
from ..engine.assessment import Opening
from ..engine.volume import arbitrate
from .constants import SHARED_SOURCES


class VolumeMixin:
    """Part of ComfortCoordinator: its methods use the coordinator's own state (self)."""

    def _partners(self):
        if not self.home_configuration or not hasattr(self.home_configuration, "volume"):
            return []
        found = []
        for entry_id in self.home_configuration.volume(self.entry_id):
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if entry is None:
                continue
            config = {**entry.data, **entry.options}
            sheltered = config.get("rain_exposed") is False
            declared = config.get("openings", {})
            # Only what the weather needs: the partner room keeps its covers to itself.
            found.append({"entry_id": entry_id, "title": config.get("name") or entry.title, "windows": list(config.get("windows", [])),
                          "sources": len(config.get("sources", {})),
                          "shared": {k: v for k, v in config.get("sources", {}).items() if k in SHARED_SOURCES and v},
                          # Its own temperature and humidity: the twin learns how much they weigh here.
                          "indoor": [config.get("sources", {}).get(k) for k in ("indoor_temperature", "indoor_humidity")],
                          "openings": {e: Opening(**{"sheltered": sheltered, **{k: v for k, v in declared.get(e, {}).items()
                                                                               if k in ("exposure", "kind", "sheltered")}})
                                       for e in config.get("windows", [])}})
        return found

    def _sources(self):
        """Its own sources, plus those of the shared air it has none of: the kitchen open onto the living room is heated
        by its thermostat and breathes the air its CO₂ sensor measures. Its temperature and humidity stay its own."""
        own = dict(self.config.get("sources", {}))
        for partner in self.partners:
            for key, entity_id in partner.get("shared", {}).items():
                if key in ("heating", "heating_indicator") and self.config.get("heated") is False:
                    continue
                # The indicator goes with its thermostat: never laid over the room's own.
                if key == "heating_indicator" and own.get("heating") and "heating" not in partner["shared"]:
                    continue
                own.setdefault(key, entity_id)
        return own

    def inherited(self):
        """The sources this room reads from its shared air, by key: {"heating": "Salon"}."""
        own = self.config.get("sources", {})
        return {key: p["title"] for p in reversed(self.partners) for key in p.get("shared", {}) if key not in own and key in self.sources}

    @property
    def volume_name(self):
        """« Salon · Cuisine »: the rooms sharing one air, the best equipped first; None for a room on its own."""
        if not self.partners:
            return None
        rooms = [(len(self.config.get("sources", {})), self.config.get("name") or self.config_entry.title),
                 *((p["sources"], p["title"]) for p in self.partners)]
        return " · ".join(title for _, title in sorted(rooms, key=lambda r: (-r[0], r[1].casefold())))

    def _volume_air(self, readings):
        """The air shared with the rooms open onto this one: mean water and temperature, and the drying model learned
        from the most openings. None without partners or without humidity on both sides."""
        if not self.partners:
            return None
        def water(t, h):
            return 6.112 * 2.718281828 ** (17.67 * t / (t + 243.5)) * h * 2.1674 / (273.15 + t)
        samples, models = [], [self.drying_model]
        own_t, own_h = readings.get("indoor_temperature"), readings.get("indoor_humidity")
        if own_t and own_h and own_t.usable and own_h.usable:
            samples.append((own_t.value, own_h.value))
        for partner in self.partners:
            entry = self.hass.config_entries.async_get_entry(partner["entry_id"])
            coordinator = getattr(entry, "runtime_data", None)
            data = getattr(coordinator, "data", None) or {}
            obs = data.get("observations", {})
            t, h = obs.get("indoor_temperature") or {}, obs.get("indoor_humidity") or {}
            if t.get("quality") == "valid" and h.get("quality") == "valid" and isinstance(t.get("value"), (int, float)) and isinstance(h.get("value"), (int, float)):
                samples.append((t["value"], h["value"]))
            if coordinator is not None and getattr(coordinator, "drying_model", None):
                models.append(coordinator.drying_model)
        if len(samples) < 2:
            return None
        return {"water": sum(water(t, h) for t, h in samples) / len(samples), "temperature": sum(t for t, _ in samples) / len(samples),
                "rooms": len(samples), "drying_model": max(models, key=lambda m: m.get("openings", 0))}

    def _beside_now(self):
        """The temperature and humidity measured now in the rooms sharing this air, averaged; None without them."""
        found = []
        for partner in self.partners:
            entry = self.hass.config_entries.async_get_entry(partner["entry_id"])
            obs = (getattr(getattr(entry, "runtime_data", None), "data", None) or {}).get("observations", {})
            t, h = obs.get("indoor_temperature") or {}, obs.get("indoor_humidity") or {}
            if t.get("quality") == "valid" and h.get("quality") == "valid" and isinstance(t.get("value"), (int, float)) and isinstance(h.get("value"), (int, float)):
                found.append((t["value"], h["value"]))
        return (sum(t for t, _ in found) / len(found), sum(h for _, h in found) / len(found)) if found else None

    def _settle(self, own):
        """One gesture per shared air: this room follows a partner whose reason outweighs its own."""
        self.own = own
        gesture = (own.get("action"), own.get("reason"))
        if gesture != self._own_gesture and self._own_gesture is not None:
            # The partners settle against this room's new advice at once, not at their next refresh.
            for partner in self.partners:
                entry = self.hass.config_entries.async_get_entry(partner["entry_id"])
                if (coordinator := getattr(entry, "runtime_data", None)) is not None:
                    self.hass.async_create_task(coordinator.async_request_refresh())
        self._own_gesture = gesture
        others = []
        for partner in self.partners:
            entry = self.hass.config_entries.async_get_entry(partner["entry_id"])
            coordinator = getattr(entry, "runtime_data", None)
            if coordinator is not None and getattr(coordinator, "own", None):
                others.append((partner["title"], coordinator.own))
        settled = arbitrate(own, others)
        lead = (settled.get("features", {}).get("volume") or {}).get("lead")
        if lead:
            # The card writes the leading room's advice with its own measures (its CO₂, its humidity).
            partner = next(p for p in self.partners if p["title"] == lead)
            entry = self.hass.config_entries.async_get_entry(partner["entry_id"])
            leader = getattr(entry, "runtime_data", None)
            data = getattr(leader, "data", None) or {}
            settled["features"]["volume"]["observations"] = {k: v for k, v in data.get("observations", {}).items()
                                                             if not k.startswith(("shutter", "cover"))}
            # « Prochaines heures » follows the advice too: drawn on the leading room, for its gesture. This room's own
            # graph answers its own advice, which the card no longer shows.
            led = ((getattr(leader, "own", None) or {}).get("features") or {}).get("horizon")
            if led is not None:
                settled["features"] = {**settled["features"], "horizon": led}
        return settled
