"""Normalize supported exterior sources without equating daily outlooks to observations."""
from dataclasses import replace
from datetime import timedelta
import math
from homeassistant.util import dt as dt_util
from .const import SOURCES
from .engine.sources import normalize, Reading


def exterior_reading(state, key, spec, *, now, max_age):
    entity_id = spec["entity_id"]
    if spec.get("adapter") == "hestia_air":
        # Hestia Weather's index from its chosen source, already on Atmo's 1 to 6 scale.
        index = spec.get("index")
        if not isinstance(index, int) or not 1 <= index <= 6:
            return Reading(None, "unknown", source=entity_id, detail="unavailable")
        # Like ATMO: an index can flag the precaution, never prove the air at these windows is good now.
        # Hestia Weather's time of calculation, to five minutes: it computes every minute (PLAN-OPTIMISATION.md, point 11).
        at = dt_util.parse_datetime(spec["at"]) if isinstance(spec.get("at"), str) else None
        at = (at - timedelta(minutes=at.minute % 5, seconds=at.second, microseconds=at.microsecond)).isoformat() if at else spec.get("at")
        return Reading(index >= spec.get("block_from", 4), "estimated", source=entity_id, received_at=at, detail="hestia_weather_air")
    if not state:
        return Reading(None, "unknown", source=entity_id, detail="unavailable")
    adapter = spec.get("adapter", "direct")
    if adapter == "direct" or adapter == "binary":
        kind = SOURCES.get(key, key)
        return normalize(kind, state.state, state.attributes.get("unit_of_measurement"), source=entity_id,
                         reported_at=state.last_reported, now=now, max_age=None if adapter == "binary" else max_age)
    if adapter == "rain_rate":
        unit = state.attributes.get("unit_of_measurement")
        try:
            rate = float(state.state)
            if not math.isfinite(rate) or rate < 0 or unit not in ("mm/h", "in/h"):
                raise ValueError
        except (TypeError, ValueError):
            return Reading(None, "unknown", source=entity_id, detail="invalid_rain_rate")
        reading = normalize("rain", rate > 0, source=entity_id, reported_at=state.last_reported, now=now, max_age=max_age)
        return replace(reading, detail="rain_rate_observed")
    if adapter == "atmo_daily":
        label = state.attributes.get("Libellé")
        labels = ("Bon", "Moyen", "Dégradé", "Mauvais", "Très mauvais", "Extrêmement mauvais")
        stamp = state.attributes.get("Date de mise à jour")
        reported = dt_util.parse_datetime(stamp) if isinstance(stamp, str) else None
        if not reported or not reported.tzinfo or label not in labels:
            return Reading(None, "unknown", source=entity_id, detail="invalid_atmo_index")
        # Today's index is published the day before (early afternoon), so yesterday's
        # publication still covers this morning; anything older is a past day's index.
        age_days = (dt_util.as_local(now).date() - dt_util.as_local(reported).date()).days
        if reported > now or age_days not in (0, 1):
            return Reading(None, "stale", source=entity_id, received_at=reported.isoformat(), detail="expired")
        # A daily regional forecast can flag a configured precaution, but never prove
        # that the air at these windows is currently suitable for ventilation.
        return Reading(labels.index(label)+1 >= spec.get("block_from", 4), "estimated",
                       source=entity_id, received_at=reported.isoformat(), detail="atmo_daily_forecast")
    if adapter == "hestia_index":
        try:
            index = float(state.state)
        except (TypeError, ValueError):
            return Reading(None, "unknown", source=entity_id, detail="invalid_air_index")
        if not 1 <= index <= 6:
            return Reading(None, "unknown", source=entity_id, detail="invalid_air_index")
        # Like ATMO: a regional daily index can flag the precaution, never prove the air is good now.
        return Reading(index >= spec.get("block_from", 4), "estimated", source=entity_id,
                       received_at=state.last_reported.isoformat(), detail="atmo_daily_forecast")
    if adapter == "season":
        # The season the home lives in, for the hours an airing can be asked for: a state, never a measure to age.
        from .discovery import SEASONS
        season = SEASONS.get(str(state.state).casefold().strip())
        return Reading(season, "valid" if season else "unknown", source=entity_id, received_at=state.last_reported.isoformat(),
                       detail="season" if season else "unavailable")
    return Reading(None, "unknown", source=entity_id, detail="unsupported_adapter")
