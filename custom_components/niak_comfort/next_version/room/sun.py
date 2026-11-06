"""The sun on the room: its windows' bearings, the station's shade, the covers' drivers."""
from dataclasses import replace
from datetime import timedelta

from .. import cover_link
from ..engine import sunlight, twin
from ..engine.assessment import Sun
from .constants import SUN_SMOOTHING


class SunMixin:
    """Part of ComfortCoordinator: its methods use the coordinator's own state (self)."""

    def _unshaded_sun(self, reading, now, outlook):
        """The sun at the station, estimated while its sensor is in the shade of the house (engine/sunlight.py)."""
        if reading.quality != "valid" or not isinstance(reading.value, (int, float)) or not self.sun_shade:
            return reading
        latitude, longitude = self.hass.config.latitude, self.hass.config.longitude
        sky = sunlight.sky_factor(sunlight.nearest_hour((outlook or {}).get("hours"), now))
        seen = sunlight.share(float(reading.value), now, latitude, longitude, self.sun_shade)
        if seen is not None:
            # In the open, the station is the truth: it also says how far the forecast cloud cover is from it.
            self._sun_before = (now, seen)
            if sky is not None and sky >= 0.1:
                self._sky_bias = (now, max(0.3, min(2.0, seen / sky)))
            return reading
        recent = lambda kept: kept[1] if kept and now - kept[0] <= timedelta(hours=3) else None
        bias, before = recent(self._sky_bias), recent(self._sun_before)
        # In the shade: Hestia Weather's cloud cover, set right by what the station measured in the open just before.
        factor = sky * bias if sky is not None and bias is not None else sky
        value, estimated = sunlight.estimate(float(reading.value), now, latitude, longitude, self.sun_shade, factor, before)
        return replace(reading, value=value, detail="shaded_estimate") if estimated else reading

    def _steady_sun(self, reading, now):
        """The sunshine averaged over the last 15 minutes (SUN_SMOOTHING): the advice and the card's tile read the same."""
        if reading.quality != "valid" or not isinstance(reading.value, (int, float)):
            return reading
        self._sun_samples.append((now, float(reading.value)))
        while self._sun_samples and now - self._sun_samples[0][0] > SUN_SMOOTHING:
            self._sun_samples.popleft()
        mean = sum(v for _, v in self._sun_samples) / len(self._sun_samples)
        return replace(reading, value=round(mean, 1), detail=reading.detail if reading.detail == "shaded_estimate" else "mean_15_min")

    def _facades(self):
        """The bearings the room's windows face: the exact angle when known, else the declared exposure."""
        from ..engine.assessment import EXPOSURES
        declared = {**{e: o for p in self.partners for e, o in p["openings"].items()}}
        out = []
        for entity_id in self.windows:
            meta = self.config.get("openings", {}).get(entity_id)
            opening = declared.get(entity_id)
            azimuth = (meta or {}).get("azimuth") if meta else getattr(opening, "azimuth", None)
            exposure = (meta or {}).get("exposure") if meta else getattr(opening, "exposure", None)
            if azimuth is None and getattr(self, "drivers", None) and entity_id in self.drivers:
                azimuth = cover_link.facts(self.hass, self.drivers[entity_id]).get("azimuth")
            bearing = azimuth if isinstance(azimuth, (int, float)) else EXPOSURES.get(exposure)
            if bearing is not None:
                out.append(float(bearing))
        return out

    def _sun_now(self, solar):
        """The sun on the room's windows now, in kW/m², counted as the twin learned it."""
        sun = self._sun()
        light = solar or 0.0
        return (twin.on_facades(light, sun.elevation, sun.azimuth, self._facades()) if sun else light) / 1000

    def _sun_ahead(self):
        """The sun on the room's windows at a forecast time, in kW/m² as the twin learned it: the clear sky, on the
        station's own scale, times what the forecast sky lets through."""
        latitude, longitude, facades = self.hass.config.latitude, self.hass.config.longitude, self._facades()
        scale = (self.sun_shade or {}).get("scale") or 1.0
        def at(when, hour):
            elevation, azimuth = twin.sun_position(when, latitude, longitude)
            sky = sunlight.sky_factor(hour)
            light = sunlight.clear_sky(when, latitude, longitude) * scale * (1.0 if sky is None else sky)
            return (twin.on_facades(light, elevation, azimuth, facades) if facades else light) / 1000
        return at

    def _sun(self):
        state = self.hass.states.get("sun.sun")
        try:
            return Sun(float(state.attributes["elevation"]), float(state.attributes["azimuth"])) if state else None
        except (KeyError, TypeError, ValueError):
            return None

    def _drivers(self):
        """{opening: its driver's entities} for each connected cover driven with the sun; none from a driver turned off."""
        used = {key for key in cover_link.ADAPTERS if self._uses(key)}
        if not used:
            return {}
        try:
            driven = cover_link.find_all(self.hass, used)
        except Exception:  # A changed driver must never stop the room.
            self.logger.warning("The covers' drivers could not be read", exc_info=True)
            return {}
        return {e: driven[m["cover_entity"]] for e, m in self.config.get("openings", {}).items()
                if m.get("shutter") == "connected" and m.get("cover_entity") in driven}
