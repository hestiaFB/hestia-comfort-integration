"""Tonight, simulated half hour by half hour: when opening really cools, and what it leaves for tomorrow's heat.

After NADIR's method (solal3105.github.io/NADIR2/methodologie.html), on this room's own twin instead of a typical one:

- the room is simulated over the next 30 hours of the Hestia Weather forecast, twice: windows shut, and windows opened
  by the rule below. The mass of the walls (engine/twin.py) carries the coolness of the night into the next day;
- the rule opens when the outside is cooler than the simulated room by OPEN_MARGIN, shuts when it is no longer cooler
  by CLOSE_MARGIN (a hysteresis, so that it does not blink), never under rain, never below the room's minimum;
- the sun is weighed against the air: opening means raising the shutters, and the sun then enters fully. The twin's
  `b` is the sun as it usually comes in, shutters drawn against the heat (NADIR: 30 % passes); open, all of it: the
  extra SOLAR_EXTRA·b·sun, divided by what the open window exchanges (`d`), is in degrees the outdoor air must make up.
  A sunny afternoon stays shut; the night, with no sun, is free.

What comes out is robust where NADIR says it is: the hours when the outside crosses the room (to an hour or so), the
trend, and the comparison between shut and open, whose biases cancel. Not the decimal.
"""
from datetime import datetime, timedelta
import math

from .twin import PRIOR_T, PRIOR_W, STEP, mass_after, step

HORIZON_HOURS = 30
# Degrees the outside must be below the simulated room to open, and above which (still below) it shuts again.
OPEN_MARGIN, CLOSE_MARGIN = 0.75, 0.25
# The sun an open window lets in on top of what passes shutters drawn (NADIR: 30 % passes shut, all of it open).
SOLAR_EXTRA = 0.7 / 0.3
# Rain in an hour (mm) that keeps every window shut.
RAIN_MM = 0.2
# Mean dew point (°C) of an airing above which the coolness comes with damp air (NADIR's « air humide »).
HUMID_DEW_POINT = 16.0
# Degrees saved at tomorrow's peak below which the night is not worth announcing.
WORTH = 0.5
# Until the room's twin has learned, an ordinary room.
ORDINARY = {"thermal": dict(PRIOR_T), "water": dict(PRIOR_W)}


def dew_point(temperature, humidity):
    """Dew point in °C (Magnus formula)."""
    g = math.log(max(humidity, 1.0) / 100) + 17.67 * temperature / (temperature + 243.5)
    return 243.5 * g / (17.67 - g)


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _series(hours, now, horizon):
    """The forecast as half hours from now: temperature and humidity between two hours are interpolated."""
    points = []
    for h in hours or ():
        try:
            when = datetime.fromisoformat(h["time"])
        except (KeyError, TypeError, ValueError):
            continue
        if when.tzinfo is None or not _number(h.get("temperature")):
            continue
        points.append((when, h))
    points.sort(key=lambda p: p[0])
    out = []
    for (t0, h0), (t1, h1) in zip(points, points[1:]):
        if t1 - t0 > timedelta(hours=3):
            continue
        t = t0
        while t < t1:
            if now <= t < now + timedelta(hours=horizon):
                share = (t - t0) / (t1 - t0)
                he0, he1 = h0.get("humidity"), h1.get("humidity")
                he = he0 + share * (he1 - he0) if _number(he0) and _number(he1) else he0 if _number(he0) else 70.0
                out.append({"time": t, "te": h0["temperature"] + share * (h1["temperature"] - h0["temperature"]),
                            "he": min(100.0, max(1.0, he)), "rain": _number(h0.get("precipitation")) and h0["precipitation"] >= RAIN_MM,
                            "hour": h0})
            t += STEP
    return out


def _run(model, start, series, *, minimum, mass, sun, rule):
    """The room through the series; `rule` decides each half hour whether the windows stand open."""
    t, ti, hi = model["thermal"], start["ti"], start["hi"]
    mass = ti if mass is None else mass
    opened, rows = False, []
    for s in series:
        light = sun(s["time"], s["hour"]) if sun else 0.0
        if rule:
            # The sun an open window lets in, in degrees the outdoor air has to make up for.
            penalty = SOLAR_EXTRA * t["b"] * light / t["d"] if t["d"] > 0 else 0.0
            margin = CLOSE_MARGIN if opened else OPEN_MARGIN
            opened = (not s["rain"] and ti > minimum + (0 if opened else 0.5)
                      and s["te"] < ti - margin - penalty)
        rows.append({"time": s["time"], "ti": ti, "opened": opened, "te": s["te"], "he": s["he"]})
        before = ti
        ti, hi = step(model, ti, hi, s["te"], s["he"], light, 1.0 if opened else 0.0, 0.0, mass=mass)
        mass = mass_after(mass, before)
    return rows


def _slots(rows):
    slots, current = [], None
    for r in rows:
        if r["opened"] and current is None:
            current = {"start": r["time"], "end": r["time"] + STEP, "dew": [dew_point(r["te"], r["he"])]}
        elif r["opened"]:
            current["end"] = r["time"] + STEP
            current["dew"].append(dew_point(r["te"], r["he"]))
        elif current is not None:
            slots.append(current)
            current = None
    if current is not None:
        slots.append(current)
    return slots


def plan(model, start, hours, now, *, minimum, mass=None, sun=None, horizon=HORIZON_HOURS):
    """When to open in the next `horizon` hours and what it brings; None without a forecast or a room to start from.

    `model`: the room's twin model (ORDINARY while it learns); `start`: {"ti", "hi"} now; `mass`: the walls' temperature;
    `sun(time, forecast hour)`: kW/m² on the room's windows, as the twin learned the sun."""
    if not start or not _number(start.get("ti")) or not _number(start.get("hi")):
        return None
    series = _series(hours, now, horizon)
    if len(series) < 4:
        return None
    model = model if isinstance(model, dict) and isinstance(model.get("thermal"), dict) else ORDINARY
    shut = _run(model, start, series, minimum=minimum, mass=mass, sun=sun, rule=False)
    aired = _run(model, start, series, minimum=minimum, mass=mass, sun=sun, rule=True)
    slots = _slots(aired)
    if not slots:
        return {"windows": [], "minimum": None, "peak": None, "humid": False, "gain": 0.0}
    # Tomorrow's peak the night can still soften: the hottest forecast half hour after the first opening.
    later = [i for i, r in enumerate(aired) if r["time"] >= slots[0]["start"]]
    peak = max(later, key=lambda i: aired[i]["te"])
    gain = round(shut[peak]["ti"] - aired[peak]["ti"], 1)
    low = min(aired, key=lambda r: r["ti"])
    dew = [d for s in slots for d in s["dew"]]
    return {"windows": [{"start": s["start"].isoformat(), "end": s["end"].isoformat()} for s in slots[:2]],
            "minimum": {"time": low["time"].isoformat(), "temperature": round(low["ti"], 1)},
            "peak": {"time": aired[peak]["time"].isoformat(), "outdoor": round(aired[peak]["te"], 1),
                     "shut": round(shut[peak]["ti"], 1), "aired": round(aired[peak]["ti"], 1)},
            "gain": gain, "worth": gain >= WORTH,
            "humid": bool(dew) and sum(dew) / len(dew) > HUMID_DEW_POINT}
