"""Learning every night (CAHIER-MOTEUR.md § 8, § 15): each twin relearns its room from the recorded days, and keeps what
it learned only if it forecasts the last day better than before; the gestures seen are counted for the proof (§ 4.1).

Everything here reads plain history (Home Assistant states as dicts, advisor/bench/history.py) and returns plain values:
the integration fetches the history and keeps the twins, this module only learns. No SciPy: the twin's own search.
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

from .bench.history import attribute, contacts, numbers
from .physics.airfit import MOVES, TWINS, _run, score as air_score, values, vector
from .physics.fit import Sample, _nelder_mead, fit, gestures, score
from .physics.sunlight import sun_position, through_windows
from .physics.thermal import STEP, Inputs, Params
from .physics.water import absolute
from .proof import level

# A twin is relearned only from this many recorded days; with fewer, only the gestures are counted.
MIN_DAYS = 3
# The last day is kept out of the search, to judge it: the new twin is kept only if it forecasts that day better.
HELD_OUT = timedelta(hours=24)
# Gestures are remembered this long.
KEEP = timedelta(days=60)
# The searches start from the twin as it is (the heat's pulled back toward it, advisor/physics/fit.py); the water's and
# the air's with moves this much smaller than from scratch: a night nudges, it does not start over.
WARM = 0.3
HEAT_SEARCH, AIR_SEARCH = 300, 400
# Sensor faults, never measures (advisor/bench/air_check.py).
CO2_FLOOR, PM25_CEILING = 300.0, 500.0
DT = timedelta(seconds=STEP)


@dataclass(frozen=True)
class RoomSpec:
    """A room as the learning reads it: its entities and its windows."""
    name: str
    temperature: str
    windows: dict                       # contact → (width, height), m
    humidity: str | None = None
    thermostat: str | None = None       # its Versatile Thermostat: `power_percent`
    orientations: dict = field(default_factory=dict)     # contact → (bearing, sheltered)
    cover: str | None = None            # a connected shutter: `current_position`
    co2: str | None = None
    particles: str | None = None
    voc: str | None = None              # a VOC index (Sensirion), 1 to 500
    declared: frozenset = frozenset({"heat"})            # parameters declared, held by the search (fit.HELD)


def samples(history, spec: RoomSpec, outdoor: str, sun, start, end, location, zone, house_heaters=None) -> list[Sample]:
    """The room every five minutes from `start` to `end`: its measured air and what acted on it. `sun`: the horizontal
    sun (an advisor.observe.Series); `house_heaters`: {thermostat: W} of the house's own heaters."""
    indoor, out = numbers(history, spec.temperature), numbers(history, outdoor)
    power = attribute(history, spec.thermostat, "power_percent", 0.01) if spec.thermostat else None
    position = attribute(history, spec.cover, "current_position", 0.01) if spec.cover in history else None
    house = [(attribute(history, e, "power_percent", 0.01), w) for e, w in (house_heaters or {}).items()]
    windows = [(e, (w * h, h), contacts(history, e)) for e, (w, h) in spec.windows.items()]
    glazing = [(w * h, *spec.orientations[e]) for e, (w, h) in spec.windows.items() if e in spec.orientations]
    oriented = [i for i, (e, _, _) in enumerate(windows) if e in spec.orientations]
    rows, when = [], start
    while when <= end:
        te, local = out.at(when), when.astimezone(zone)
        inputs = None
        if te is not None:
            facade = None
            if glazing:
                light = sun.at(when) or 0.0
                opened = {k for k, i in enumerate(oriented) if windows[i][2].at(when) is True}
                facade = through_windows(light, *sun_position(when, *location), glazing, opened)
            inputs = Inputs(outdoor=te, sun=sun.at(when) or 0.0, heating=(power.at(when) or 0.0) if power else 0.0,
                            windows=tuple(size for _, size, s in windows if s.at(when) is True),
                            hour=local.hour + local.minute / 60,
                            house_heat=sum((s.at(when) or 0.0) * w for s, w in house),
                            shade=1.0 if position is None or position.at(when) is None else max(0.05, position.at(when)),
                            facade=facade)
        rows.append(Sample(when, indoor.at(when), inputs))
        when += DT
    return rows


def _merge(kept, found, start, end, now):
    """The gestures remembered: those seen again between `start` and `end` replace the old ones there."""
    out = [g for g in kept or () if g[0] and not start.isoformat() <= g[0] <= end.isoformat()]
    out += found
    limit = (now - KEEP).isoformat()
    return sorted((g for g in out if g[0] >= limit), key=lambda g: g[0])


# What each twin of the air reads: its sensor, the values that are faults, the outside air's own value.
SENSORS = {"air": ("co2", lambda v: v >= CO2_FLOOR, 420.0), "particles": ("particles", lambda v: v <= PM25_CEILING, 0.0),
           "voc": ("voc", lambda v: 0 < v <= 500, 100.0)}


def _air_rows(key, history, spec, data, outdoor, outdoor_humidity):
    if key == "water":
        rh, te, he = numbers(history, spec.humidity), numbers(history, outdoor), numbers(history, outdoor_humidity)
        return [(s, None if rh.at(s.when) is None or s.measured is None else absolute(s.measured, rh.at(s.when)),
                 None if te.at(s.when) is None or he.at(s.when) is None else absolute(te.at(s.when), he.at(s.when)))
                for s in data]
    sensor, ok, outside = SENSORS[key]
    series = numbers(history, getattr(spec, sensor))
    return [(s, v if (v := series.at(s.when)) is not None and ok(v) else None, outside) for s in data]


def learn_room(spec: RoomSpec, entry: dict, history, sun, now: datetime, outdoor: str, outdoor_humidity: str,
               location, zone, house_heaters=None, start: datetime | None = None) -> tuple[dict, dict]:
    """The room's twins after a night: (the entry to keep, the report). `entry` is the room's twins as kept (jumeaux.json):
    `heat`, `water`, `air`, `particles` with their `…_flow`, and `gestures` ({subject: [[when, forecast, measured]…]})."""
    first = numbers(history, spec.temperature).times[:1] + numbers(history, outdoor).times[:1]
    if start is None:
        start = max(first).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1) if len(first) == 2 else now
    days = max(0.0, (now - start).total_seconds() / 86400)
    entry = {**entry, "gestures": dict(entry.get("gestures") or {})}
    report = {"piece": spec.name, "jours": round(days, 1), "appris": days >= MIN_DAYS}
    if days <= 0:
        return entry, report
    data = samples(history, spec, outdoor, sun, start, now, location, zone, house_heaters)
    split = now - HELD_OUT

    heat = Params(**entry["heat"])
    if days >= MIN_DAYS:
        before = score(heat, data, since=split)
        found = fit(heat, data, until=split, iterations=HEAT_SEARCH, held=spec.declared)
        after = score(found, data, since=split)
        kept = after.hour + after.three < before.hour + before.three
        report["chaleur"] = {"avant": [round(before.hour, 3), round(before.three, 3)],
                             "apres": [round(after.hour, 3), round(after.three, 3)], "garde": kept}
        if kept:
            heat = found
            entry["heat"] = asdict(found)
    seen = [[g["when"].isoformat(), g["forecast"], g["measured"]] for g in gestures(heat, data) if g["kind"] == "window"]
    entry["gestures"]["heat"] = _merge(entry["gestures"].get("heat"), seen, start, now, now)

    for key, kind, subject in TWINS:
        if key not in entry or not getattr(spec, "humidity" if key == "water" else SENSORS[key][0]):
            continue
        rows = _air_rows(key, history, spec, data, outdoor, outdoor_humidity)
        volume = entry[key]["volume"]
        x = vector(kind, entry[key], entry[f"{key}_flow"])
        if days >= MIN_DAYS:
            before = air_score(kind, x, volume, rows, split, now)
            found = _nelder_mead(lambda y: air_score(kind, y, volume, rows, start, split), x,
                                 [m * WARM for m in MOVES[kind]], AIR_SEARCH)
            after = air_score(kind, found, volume, rows, split, now)
            kept = after < before
            report[subject] = {"avant": round(before, 3), "apres": round(after, 3), "garde": kept}
            if kept:
                x = found
                entry[key], entry[f"{key}_flow"] = values(kind, x, volume)
        seen = [[when.isoformat(), forecast, measured]
                for measured, forecast, when in _run(kind, x, volume, rows, start, now)["gestures"]]
        entry["gestures"][subject] = _merge(entry["gestures"].get(subject), seen, start, now, now)

    report["gestes"] = {s: len(g) for s, g in entry["gestures"].items()}
    report["preuves"] = {s: level([(f, m) for _, f, m in g]) for s, g in entry["gestures"].items()}
    return entry, report
