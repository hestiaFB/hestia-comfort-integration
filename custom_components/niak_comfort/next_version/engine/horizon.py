"""« Prochaines heures »: the room over the coming hours, without the advised gesture and with it.

The card draws it under the advice. One room, one twin (engine/twin.py), the Hestia Weather forecast; what is compared
follows the advice of the moment:

- « cool »: a hot room, summer nights. Shut against opened by NADIR's rule (engine/night.py): when to open, the
  coolness left for tomorrow's peak, the sunny hours to keep shut;
- « air »: an airing asked while it is cold outside. What the room loses, and when it is back, thanks to its walls;
- « sun »: a cool room the sun will warm by itself. The room without the sun and with it: what the sun brings, a reason
  not to heat;
- « dry »: a damp room. The humidity without airing and with the airing advised, now or at the better moment.

Two subjects at most: the temperature (one kind at a time, the season decides) and the humidity. The first one is the
banner's. Everything is an estimate, drawn to show a trend, not a decimal.

Each subject says whether it is `needed`: what the gesture changes must be seen on the drawing. Shown from SHOW, kept
down to KEEP while the advice stays the same, so that a graph does not come and go on a few hundredths. A « trend »
(the room's temperature without doing anything) always comes last, never needed: for a card that keeps its graph.
The sun is needed only when the advice is about heating and the sun comes within SOON hours: at night, tomorrow's sun
answers nothing yet. Otherwise it is the forecast such a card shows first.
"""
from datetime import datetime, timedelta

from . import night
from .twin import STEP, mass_after, step

HOURS = 24
# Degrees within which the aired room is « back » to where it would have been.
BACK = 0.2
# Sun on the windows (kW/m²) from which the sun counts as warming the room.
SUNNY = 0.12
# A thermostat holding its set point: the usual share of the half hour it heats, and how much more per degree missing.
HOLD_SHARE, HOLD_GAIN = 0.35, 1.5
COOL_REASONS = ("cooling_possible", "precool_possible", "precool_later", "cooling_unavailable")
DRY_REASONS = ("drying_possible", "drying_later")
AIR_REASONS = ("air_needed", "short_air_change", "optional_air_change")
# What the gesture must change for the graph to be needed (°C, or points of humidity for « dry »): shown from the first,
# kept down to the second while the advice stays the same.
SHOW = {"cool": 0.4, "air": 0.4, "sun": 0.5, "dry": 3.0}
KEEP = {"cool": 0.2, "air": 0.2, "sun": 0.3, "dry": 1.5}
# Hours within which the sun must start warming for its graph to answer the heating now.
SOON = 3


def _r(x, n=1):
    return round(x, n)


def _simulate(model, start, series, *, mass, sun, opened, heated):
    """The room through the series; `opened(time)`: share of the half hour a window stands open; `heated`: a share of
    the half hour, or `heated(ti)` for a thermostat holding its set point."""
    ti, hi = start["ti"], start["hi"]
    mass = ti if mass is None else mass
    rows = []
    for s in series:
        light = sun(s["time"], s["hour"]) if sun else 0.0
        share = opened(s["time"])
        rows.append({"time": s["time"], "ti": ti, "hi": hi, "light": light, "open": share})
        before = ti
        ti, hi = step(model, ti, hi, s["te"], s["he"], light, share, heated(ti) if callable(heated) else heated, mass=mass)
        mass = mass_after(mass, before)
    return rows


def _shape(subject, kind, rows_base, rows_gesture, key, bands=(), extra=(), result=None):
    unit = "%" if key == "hi" else "°C"
    return {"subject": subject, "kind": kind, "unit": unit, "start": rows_base[0]["time"].isoformat(), "step_minutes": 30,
            # Two decimals for the temperature: a smooth curve, not steps of a tenth.
            "base": [_r(r[key], 2 if key == "ti" else 1) for r in rows_base],
            "gesture": [_r(r[key], 2 if key == "ti" else 1) for r in rows_gesture] if rows_gesture else None,
            "bands": [[a.isoformat(), b.isoformat()] for a, b in bands], "extra": [[a.isoformat(), b.isoformat()] for a, b in extra],
            "result": result or {}}


def _spans(rows, test):
    """[(start, end)] of the consecutive half hours where `test(row)` holds."""
    out, current = [], None
    for r in rows:
        if test(r):
            current = [r["time"], r["time"] + STEP] if current is None else [current[0], r["time"] + STEP]
        elif current:
            out.append(tuple(current))
            current = None
    if current:
        out.append(tuple(current))
    return out


# The drawing starts at the next half hour: an airing asked « now » starts there, or it would fall before the first
# step and change nothing (a graph never needed).
def _window(at, minutes):
    end = at + timedelta(minutes=minutes)
    return lambda t: max(0.0, min(1.0, ((min(end, t + STEP) - max(at, t)).total_seconds()) / STEP.total_seconds()))


def cool(model, start, series, *, minimum, mass, sun):
    shut = night._run(model, start, series, minimum=minimum, mass=mass, sun=sun, rule=False)
    aired = night._run(model, start, series, minimum=minimum, mass=mass, sun=sun, rule=True)
    slots = night._slots(aired)
    if not slots:
        return None
    later = [i for i, r in enumerate(aired) if r["time"] >= slots[0]["start"]]
    peak = max(later, key=lambda i: aired[i]["te"])
    low = min(aired, key=lambda r: r["ti"])
    # The sunny hours, shut: opening there would let in more sun than the air takes out.
    keep = _spans([{**r, "light": sun(r["time"], None) if sun else 0.0} for r in aired],
                  lambda r: not r["opened"] and r["light"] >= SUNNY)
    return _shape("temperature", "cool", shut, aired, "ti", [(s["start"], s["end"]) for s in slots[:2]], keep,
                  {"open_from": slots[0]["start"].isoformat(), "open_until": slots[0]["end"].isoformat(),
                   "peak_time": aired[peak]["time"].isoformat(), "shut": _r(shut[peak]["ti"]), "aired": _r(aired[peak]["ti"]),
                   "gain": _r(shut[peak]["ti"] - aired[peak]["ti"]), "minimum": _r(low["ti"]), "minimum_time": low["time"].isoformat()})


def air(model, start, series, *, mass, sun, heated, at, minutes):
    at = max(at, series[0]["time"])
    base = _simulate(model, start, series, mass=mass, sun=sun, opened=lambda t: 0.0, heated=heated)
    aired = _simulate(model, start, series, mass=mass, sun=sun, opened=_window(at, minutes), heated=heated)
    gaps = [b["ti"] - a["ti"] for b, a in zip(base, aired)]
    deepest = max(range(len(gaps)), key=lambda i: gaps[i])
    back = next((aired[i]["time"] for i in range(deepest, len(gaps)) if gaps[i] <= BACK), None)
    return _shape("temperature", "air", base, aired, "ti", [(at, at + timedelta(minutes=minutes))], (),
                  {"at": at.isoformat(), "minutes": minutes, "drop": _r(gaps[deepest]), "back": back.isoformat() if back else None})


def sunny(model, start, series, *, mass, sun, heated, minimum=None):
    base = _simulate(model, start, series, mass=mass, sun=sun, opened=lambda t: 0.0, heated=heated)
    warm = _spans(base, lambda r: r["light"] >= SUNNY)
    if not warm:
        return None
    top = max(base, key=lambda r: r["ti"])
    # Only a room the sun is about to warm: its top comes later, during the sunny hours or just after.
    if (top["ti"] < start["ti"] + 0.3 or top["time"] < base[0]["time"] + timedelta(hours=1)
            or top["time"] > warm[0][1] + timedelta(hours=2)):
        return None
    after = [r for r in base if r["time"] > top["time"]]
    low = min(after, key=lambda r: r["ti"]) if after else None
    # The same room in the shade: the gap between the two curves is what the sun brings.
    shade = _simulate(model, start, series, mass=mass, sun=None, opened=lambda t: 0.0, heated=heated)
    most = max(range(len(base)), key=lambda i: base[i]["ti"] - shade[i]["ti"])
    return _shape("temperature", "sun", shade, base, "ti", warm[:1], (),
                  {"top": _r(top["ti"]), "top_time": top["time"].isoformat(),
                   "gain": _r(base[most]["ti"] - shade[most]["ti"]), "gain_time": base[most]["time"].isoformat(),
                   # A room under its minimum: the sun spares the heating; otherwise it only warms.
                   "cold": minimum is not None and start["ti"] < minimum,
                   "night": _r(low["ti"]) if low else None, "night_time": low["time"].isoformat() if low else None})


def dry(model, start, series, *, mass, sun, heated, at, minutes):
    at = max(at, series[0]["time"])
    base = _simulate(model, start, series, mass=mass, sun=sun, opened=lambda t: 0.0, heated=heated)
    aired = _simulate(model, start, series, mass=mass, sun=sun, opened=_window(at, minutes), heated=heated)
    # Two hours after the airing: what is left once the walls have given some water back.
    when = at + timedelta(minutes=minutes) + timedelta(hours=2)
    i = min(range(len(base)), key=lambda k: abs((base[k]["time"] - when).total_seconds()))
    return _shape("humidity", "dry", base, aired, "hi", [(at, at + timedelta(minutes=minutes))], (),
                  {"at": at.isoformat(), "minutes": minutes, "time": base[i]["time"].isoformat(),
                   "without": _r(base[i]["hi"], 0), "with": _r(aired[i]["hi"], 0)})


def trend(model, start, series, *, mass, sun, heated):
    """The room's temperature without doing anything: the graph of a card that keeps it when no gesture needs one."""
    base = _simulate(model, start, series, mass=mass, sun=sun, opened=lambda t: 0.0, heated=heated)
    top, low = max(base, key=lambda r: r["ti"]), min(base, key=lambda r: r["ti"])
    return _shape("temperature", "trend", base, None, "ti", (), (),
                  {"top": _r(top["ti"]), "top_time": top["time"].isoformat(), "low": _r(low["ti"]), "low_time": low["time"].isoformat()})


def _change(subject, start):
    """What the gesture changes on the drawing, in the subject's unit."""
    r = subject["result"]
    return {"cool": lambda: r.get("gain"), "air": lambda: r.get("drop"), "sun": lambda: r.get("gain"),
            "dry": lambda: r["without"] - r["with"]}[subject["kind"]]() or 0.0


def build(assessment, model, current, hours, now, *, minimum, mass=None, sun=None, previous=None):
    """The subjects to draw, the banner's first, then the trend; [] without a forecast or a measure.
    `previous`: what the last call returned, to keep a needed graph while the advice stays the same."""
    if not current or not all(isinstance(current.get(k), (int, float)) for k in ("ti", "hi")):
        return []
    model = model if isinstance(model, dict) and isinstance(model.get("thermal"), dict) else night.ORDINARY
    start = {"ti": current["ti"], "hi": current["hi"]}
    # A thermostat that heats or rests holds the room where it is: after an airing it heats more, then less.
    target = current["ti"]
    heated = ((lambda ti: max(0.0, min(1.0, HOLD_SHARE + HOLD_GAIN * (target - ti)))) if current.get("holding")
              else 1.0 if current.get("heated") else 0.0)
    reason, action = assessment.get("reason"), assessment.get("action")
    features = assessment.get("features") or {}
    needs = assessment.get("needs") or ()
    shown = (features.get("volume") or {}).get("reason") if reason == "shared_volume" else reason
    out = []
    series = night._series(hours, now, HOURS)
    if len(series) < 4:
        return []
    # The temperature: one kind at a time.
    temperature = None
    if shown in COOL_REASONS or "cool" in needs or "precool" in needs:
        temperature = cool(model, start, night._series(hours, now, night.HORIZON_HOURS), minimum=minimum, mass=mass, sun=sun)
    elif shown in AIR_REASONS and action in ("ouvrir", "ok"):
        te = current.get("te")
        if isinstance(te, (int, float)) and te < current["ti"] - 3:
            span = (features.get("ventilation") or {}).get("duration_minutes") or {}
            temperature = air(model, start, series, mass=mass, sun=sun, heated=heated, at=now,
                              minutes=int(span.get("max") or (5 if shown == "short_air_change" else 10)))
    # The sun answers the heating: needed only when the advice is about it; in between seasons, only drawn.
    heating = "heat" in needs or bool((features.get("warmth") or {}).get("warming"))
    if temperature is None and (heating or (features.get("season") or {}).get("group") == "between"):
        temperature = sunny(model, start, series, mass=mass, sun=sun, heated=heated, minimum=minimum)
    # The humidity: an airing to dry, now or at the better moment.
    humidity = None
    drying = features.get("drying") or {}
    if shown in DRY_REASONS and drying.get("minutes"):
        later = drying.get("later") or {}
        at = datetime.fromisoformat(later["time"]) if shown == "drying_later" and later.get("time") else now
        humidity = dry(model, start, series, mass=mass, sun=sun, heated=heated, at=at, minutes=int(drying["minutes"]))
    # A sun that brings almost nothing is not drawn at all: two curves on top of each other say nothing.
    if temperature and temperature["kind"] == "sun" and temperature["result"]["gain"] < KEEP["sun"]:
        temperature = None
    out = [s for s in (temperature, humidity) if s]
    if humidity and shown in DRY_REASONS:
        out = [humidity] + [s for s in out if s is not humidity]
    advice = f"{shown}|{action}"
    kept = {(p.get("kind"), p.get("advice")) for p in previous or () if p.get("needed")}
    for s in out:
        s["advice"] = advice
        s["needed"] = ((s["kind"] != "sun" or heating and datetime.fromisoformat(s["bands"][0][0]) <= now + timedelta(hours=SOON))
                       and _change(s, start) >= (KEEP if (s["kind"], advice) in kept else SHOW)[s["kind"]])
    out.append({**trend(model, start, series, mass=mass, sun=sun, heated=heated), "advice": advice, "needed": False})
    return out
