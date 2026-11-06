"""The sun the station cannot see: where its sensor is shaded, learned from its own history.

A station set against a wall loses the sun at some hours, every sunny day (21 October 2026: Frank's station,
on the east side, falls to a quarter of its measure each afternoon from 16 h, when the sun passes west of the
house). The windows facing that way would be told there is no sun. So, from the station's last days:

- each measure is compared with the clear-sky sun at that moment;
- on the sunny days, the directions of the sun (by 10° of azimuth) where the station keeps less than half of its
  usual share are « shaded »;
- there, the sun is estimated: the clear-sky sun, on the station's scale, times what the sky lets through: the cloud
  cover Hestia Weather forecasts for the hour, set right by how far it was from the station's own measure while in the
  open (the coordinator keeps that gap); without a forecast, the share measured just before the shade.

Nothing is set by hand: a station in the open is never found shaded, and nothing changes for it.
"""
from datetime import datetime, timedelta
import math

from .twin import sun_position

# Directions of the sun, in degrees of azimuth, grouped to learn the shade.
BUCKET = 10
# Below this elevation the sun is low for every station: not learned, not estimated.
LOW_SUN = 8
# A day is sunny when its best measures reach this share of the station's usual clear-sky scale.
SUNNY_DAY = 0.7
# A direction is shaded when, on sunny days, the station keeps less than this share of its day's best.
SHADED = 0.5
# Sunny days seen in a direction before it is called shaded.
SHADED_DAYS = 3
# What a sky lets through, by Home Assistant's weather condition, when no cloud cover is given.
CONDITIONS = {"sunny": 1.0, "windy": 0.85, "windy-variant": 0.6, "partlycloudy": 0.6, "cloudy": 0.25, "fog": 0.15,
              "rainy": 0.15, "snowy": 0.15, "snowy-rainy": 0.15, "lightning": 0.15, "lightning-rainy": 0.1,
              "pouring": 0.1, "hail": 0.1, "exceptional": 0.3}


def clear_sky(when, latitude, longitude):
    """The sun on a horizontal surface under a clear sky, in W/m² (a simple air-mass model)."""
    elevation, _ = sun_position(when, latitude, longitude)
    if elevation <= 0:
        return 0.0
    mass = 1 / math.sin(math.radians(elevation))
    return 1100 * math.sin(math.radians(elevation)) * 0.7 ** (mass ** 0.678)


def bucket(azimuth):
    return int(azimuth // BUCKET * BUCKET) % 360


def _quantile(values, share):
    values = sorted(values)
    return values[min(len(values) - 1, int(share * len(values)))] if values else None


def learn(points, latitude, longitude, zone=None):
    """{"scale", "shaded": [azimuth buckets], "sunny_days"} from (time, W/m²) points; None without enough sun.

    `scale` is the station's measure under a clear sky, against `clear_sky` (its own calibration and setting)."""
    by_day = {}
    for when, value in points:
        if not isinstance(value, (int, float)) or value < 0:
            continue
        elevation, azimuth = sun_position(when, latitude, longitude)
        if elevation < LOW_SUN:
            continue
        ratio = value / clear_sky(when, latitude, longitude)
        by_day.setdefault((when.astimezone(zone) if zone else when).date(), []).append((bucket(azimuth), ratio))
    peaks = {day: _quantile([r for _, r in rows], 0.85) for day, rows in by_day.items() if len(rows) >= 12}
    if not peaks:
        return None
    scale = _quantile(list(peaks.values()), 0.75)
    if not scale or scale <= 0:
        return None
    sunny = {day for day, peak in peaks.items() if peak >= SUNNY_DAY * scale}
    seen, days = {}, {}
    for day in sunny:
        for b, ratio in by_day[day]:
            seen.setdefault(b, []).append(ratio / peaks[day])
            days.setdefault(b, set()).add(day)
    shaded = sorted(b for b, shares in seen.items() if len(days[b]) >= SHADED_DAYS and _quantile(shares, 0.5) < SHADED)
    return {"scale": round(scale, 3), "shaded": shaded, "sunny_days": len(sunny)}


def nearest_hour(hours, now, within=timedelta(minutes=90)):
    """The forecast hour closest to now: the service often starts its list at the next hour."""
    best = None
    for hour in hours or ():
        try:
            when = datetime.fromisoformat(hour["time"])
        except (KeyError, TypeError, ValueError):
            continue
        if when.tzinfo is None:
            continue
        gap = abs((when + timedelta(minutes=30) - now).total_seconds())
        if gap <= within.total_seconds() and (best is None or gap < best[0]):
            best = (gap, hour)
    return best[1] if best else None


def sky_factor(hour):
    """What the sky lets through this hour, from Hestia Weather's forecast: its cloud cover, else its condition."""
    if not hour:
        return None
    cover = hour.get("cloud_coverage")
    if isinstance(cover, (int, float)) and 0 <= cover <= 100:
        return 1 - 0.75 * (cover / 100) ** 3.4
    return CONDITIONS.get(hour.get("condition"))


def shaded(learned, when, latitude, longitude):
    """Is the station in the shade of what surrounds it, at this moment?"""
    if not learned or not learned.get("shaded"):
        return False
    elevation, azimuth = sun_position(when, latitude, longitude)
    return elevation >= LOW_SUN and bucket(azimuth) in learned["shaded"]


def estimate(value, when, latitude, longitude, learned, sky=None, before=None):
    """The sun at the station: its measure, or, while it is shaded, the clear-sky sun on its scale times what the
    sky lets through (`sky`, from the forecast; else `before`, the share measured just before the shade).
    Returns (W/m², estimated?)."""
    if not shaded(learned, when, latitude, longitude):
        return value, False
    factor = sky if sky is not None else before
    if factor is None:
        return value, False
    return round(clear_sky(when, latitude, longitude) * learned["scale"] * max(0.0, min(1.2, factor)), 1), True


def share(value, when, latitude, longitude, learned):
    """What the sky let through at a measure the station saw in full: kept to estimate the shade that follows."""
    clear = clear_sky(when, latitude, longitude)
    if not learned or clear <= 0 or shaded(learned, when, latitude, longitude) or sun_position(when, latitude, longitude)[0] < LOW_SUN:
        return None
    return value / (clear * learned["scale"])


def corrected(points, latitude, longitude, learned, hours=()):
    """The station's history with its shaded measures estimated, for the twin to learn the sun on every window."""
    if not learned or not learned.get("shaded"):
        return list(points)
    sky = {}
    for hour in hours or ():
        factor = sky_factor(hour)
        if factor is not None and hour.get("time"):
            sky[hour["time"][:13]] = factor
    out, before, last = [], None, None
    for when, value in points:
        if not isinstance(value, (int, float)):
            out.append((when, value))
            continue
        seen = share(value, when, latitude, longitude, learned)
        if seen is not None:
            before, last = seen, when
        # A share measured more than three hours before says nothing about the sky now.
        recent = before if last is not None and when - last <= timedelta(hours=3) else None
        estimated, _ = estimate(value, when, latitude, longitude, learned, sky.get(when.isoformat()[:13]), recent)
        out.append((when, estimated))
    return out
