"""Normalize explicitly selected observations without numeric fallbacks."""
from dataclasses import dataclass
from datetime import datetime
import math

WIND_TO_KMH = {"km/h": 1.0, "m/s": 3.6, "mph": 1.609344, "kn": 1.852, "ft/s": 1.09728}


@dataclass(frozen=True)
class Reading:
    value: float | bool | str | None
    quality: str
    source: str | None = None
    received_at: str | None = None
    detail: str | None = None
    unit: str | None = None

    @property
    def usable(self) -> bool:
        return self.quality == "valid" and self.value is not None


def normalize(kind: str, value: object, unit: str | None = None, *,
              source: str | None = None, reported_at: datetime | None = None,
              now: datetime, max_age: float | None = 1800) -> Reading:
    kind = {"switch": "shutter_auto", "position": "cover", "percentage": "purifier_speed"}.get(kind, kind)
    stamp = reported_at.isoformat() if reported_at else None
    def invalid(detail: str, quality: str = "unknown") -> Reading:
        return Reading(None, quality, source, stamp, detail)
    if not source:
        return invalid("not_configured")
    if value is None or str(value).lower() in ("unknown", "unavailable", "none", ""):
        return invalid("unavailable")
    if reported_at is None or reported_at.tzinfo is None or now.tzinfo is None:
        return invalid("missing_timestamp")
    age = (now - reported_at).total_seconds()
    if age < -60:
        return invalid("future_timestamp")
    # A state (contact, heating action) holds until it changes: only measurements expire.
    state_kind = kind.split(":", 1)[0]
    if state_kind in ("window", "rain", "pollution", "heating", "presence", "purifier", "ventilation", "cover", "cover_state", "shutter_auto", "shutter_override", "shutter_sun", "shutter_target"):
        max_age = None
    if max_age is not None and age > max_age:
        return invalid("expired", "stale")
    if state_kind in ("window", "rain", "pollution", "presence", "purifier", "ventilation", "shutter_auto", "shutter_override", "shutter_sun"):
        if isinstance(value, bool):
            result = value
        elif str(value).lower() in ("on", "off"):
            result = str(value).lower() == "on"
        else:
            return invalid("invalid_boolean")
    elif state_kind == "cover_state":
        if value not in ("closed", "open", "opening", "closing"):
            return invalid("unknown_cover_state")
        result = str(value)
    elif kind == "heating":
        if value not in ("heating", "idle", "off", "cooling"):
            return invalid("unknown_action")
        result = str(value)
    else:
        if isinstance(value, bool):
            return invalid("invalid_number")
        try:
            result = float(value)
        except (TypeError, ValueError, OverflowError):
            return invalid("invalid_number")
        if not math.isfinite(result):
            return invalid("non_finite")
        if kind == "temperature":
            if unit == "°F":
                result = (result - 32) * 5 / 9
            elif unit == "K":
                result -= 273.15
            elif unit != "°C":
                return invalid("incompatible_unit")
            bounds = (-80, 80)
        elif state_kind in ("cover", "purifier_speed", "shutter_target") and unit in ("%", None):
            bounds = (0, 100)
        elif kind == "illuminance" and unit in ("lx", "lux"):
            bounds = (0, 1000000)
        elif kind == "pm25" and unit in ("µg/m³", "μg/m³", "ug/m³", "mg/m³"):
            if unit == "mg/m³":
                result *= 1000
            bounds = (0, 1000000)
        elif kind == "voc" and unit in ("µg/m³", "μg/m³", "mg/m³", "ppb", "ppm", "indice", "index", "VOC index", None):
            bounds = (0, 1000000000)
        elif kind == "humidity" and unit == "%":
            bounds = (0, 100)
        elif kind == "co2" and unit == "ppm":
            bounds = (0, 100000)
        elif kind == "wind" and unit in WIND_TO_KMH:
            result *= WIND_TO_KMH[unit]
            bounds = (0, 500)
        elif kind == "irradiance" and unit == "W/m²":
            bounds = (0, 2000)
        elif kind == "bearing" and unit == "°":
            bounds = (0, 360)
        else:
            return invalid("incompatible_unit")
        if not bounds[0] <= result <= bounds[1]:
            return invalid("out_of_range")
    canonical_unit = {"temperature": "°C", "humidity": "%", "co2": "ppm", "wind": "km/h", "irradiance": "W/m²", "bearing": "°", "pm25": "µg/m³", "illuminance": "lx", "purifier_speed": "%", "cover": "%"}.get(state_kind)
    if kind == "voc":
        canonical_unit = unit
    return Reading(result, "valid", source, stamp, unit=canonical_unit)


# A heating indicator (a valve, a relay, a « work state »): the words that say it runs, or that it rests.
INDICATOR_RUNNING = ("on", "heating", "heat", "open", "opened", "true", "active", "running")
INDICATOR_RESTING = ("off", "idle", "close", "closed", "false", "inactive", "stopped", "standby")


def indicator_state(value: object) -> str | None:
    """« heating » or « idle » from what an indicator says; None for anything else, never guessed."""
    if isinstance(value, bool):
        return "heating" if value else "idle"
    word = str(value).strip().casefold() if value is not None else ""
    return "heating" if word in INDICATOR_RUNNING else "idle" if word in INDICATOR_RESTING else None
