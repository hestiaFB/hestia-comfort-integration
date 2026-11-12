"""Learning every night (CAHIER-MOTEUR.md § 8, § 15): each twin relearns its room from the recorded days, and keeps what
it learned only if it forecasts the last day better than before; the gestures seen are counted for the proof (§ 4.1).

Everything here reads plain history (Home Assistant states as dicts, advisor/bench/history.py) and returns plain values:
the integration fetches the history and keeps the twins, this module only learns. No SciPy: the twin's own search.
"""
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timedelta
import math

from .bench.history import attribute, contacts, lit_power, numbers
from .decide import CROSS, SHUT_SHADE, sides_apart
from .household import AWAY
from .observe import Series
from .physics.thermal import glazing as glazing_of
from .notes import prune, settle
from .physics.airfit import MOVES, TWINS, notes as air_notes, score as air_score, values, vector
from .physics.fit import Sample, _nelder_mead, fit, fit_windows, notes as heat_notes, score
from .physics.sunlight import facing, sun_position, through_windows
from .physics.thermal import STEP, Inputs, Params, shutter_insulation
from .physics.water import absolute
from .proof import level

# A twin is relearned only from this many recorded days; with fewer, only the gestures are counted.
MIN_DAYS = 3
# The last day is kept out of the search, to judge it: the new twin is kept if it forecasts that day no worse than EVEN
# times the twin as it was. One day is a noisy judge (lab, 5 November: the same twin missed its day by half or twice as
# much from one day to the next) and 9 of the 15 twins refused that night were within 5 % of the old one: refused, a
# twin froze on its first days instead of following the recent ones. The night's report says « meilleur », « egal » (kept
# all the same) or « pire » (refused).
HELD_OUT = timedelta(hours=24)
EVEN = 1.05
# Gestures are remembered this long.
KEEP = timedelta(days=60)
# A correction from the gestures' notes (advisor/notes.py) is kept when the last day is forecast no worse than this.
NOTES_TOLERANCE = 1.05
# The searches start from the twin as it is (the heat's pulled back toward it, advisor/physics/fit.py); the water's and
# the air's with moves this much smaller than from scratch: a night nudges, it does not start over.
WARM = 0.3
HEAT_SEARCH, AIR_SEARCH = 300, 400
# The searches read the last days only: a night nudges the twin it starts from, the older days were read on the nights
# before. The gestures are still counted over every recorded day. Lab, 3 November: 11 min for 9 rooms and 3 days on the
# NAS, and a recorder that keeps 60 days would have taken hours.
SEARCH_DAYS = 7
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
    boost: tuple | None = None          # (the VMC's fast speed: a fan or switch, m³/h it adds)
    purifier: tuple | None = None       # (the purifier: a fan, m³/h of clean air it gives)
    declared: frozenset = frozenset({"heat"})            # parameters declared, held by the search (fit.HELD)
    panes: dict = field(default_factory=dict)            # contact → its glazing, « simple », « double », « triple »
    # The windows with a manual shutter, and when the household says it shuts them (HABITUDES-FOYER.md): its habits
    # (advisor/household.py), the home's alarm read in the history for its absences, summer or not.
    manual: frozenset = frozenset()
    habits: object | None = None
    alarm: str | None = None
    summer: bool = False


def _shut_windows(spec: RoomSpec, alarm: Series | None, when, local, location, absences=()) -> set:
    """The manual shutters shut at `when`, as the household said: away, at night, on summer's sunny side. A manual
    shutter is otherwise taken as the learned average: no answer, no change (Salon, 5 November: shut while away, the sun
    counted through them made the twin believe the sun warms the room less than it does)."""
    if not spec.manual or spec.habits is None:
        return set()
    away = spec.habits.away(local, alarm.at(when) if alarm is not None else None, spec.alarm is not None)
    position = sun_position(when, *location) if spec.summer else None
    away_for = (_absence(absences, when) if spec.alarm is not None else spec.habits.empty_hours()) if away else None
    return {e for e in spec.manual
            if spec.habits.shut(local, away, spec.summer,
                                position is not None and facing((spec.orientations.get(e) or (None,))[0], *position), away_for)}


def _absences(history: list, end) -> list:
    """The alarm's absences, (from, to), read back: the night knows how long each lasted (still going at `end`: to it)."""
    spans, since = [], None
    for row in history:
        at, away = datetime.fromisoformat(row["last_changed"]), row["state"] in AWAY
        if away and since is None:
            since = at
        elif not away and since is not None and row["state"] not in ("unknown", "unavailable"):
            spans.append((since, at))
            since = None
    if since is not None:
        spans.append((since, end))
    return spans


def _absence(absences: list, when) -> float | None:
    """Hours of the whole absence `when` falls in; None when it falls in none of them."""
    return next(((to - since).total_seconds() / 3600 for since, to in absences if since <= when <= to), None)


def samples(history, spec: RoomSpec, outdoor: str, sun, start, end, location, zone, house_heaters=None,
            house_idle=None) -> list[Sample]:
    """The room every five minutes from `start` to `end`: its measured air and what acted on it. `sun`: the horizontal
    sun (an advisor.observe.Series); `house_heaters`: {thermostat: W} of the house's own heaters."""
    indoor, out = numbers(history, spec.temperature), numbers(history, outdoor)
    power = attribute(history, spec.thermostat, "power_percent", 0.01) if spec.thermostat else None
    position = attribute(history, spec.cover, "current_position", 0.01) if spec.cover in history else None
    house = [(lit_power(history, e, (house_idle or {}).get(e, 0.0)), w) for e, w in (house_heaters or {}).items()]
    devices = {name: (contacts(history, d[0]), d[1]) for name, d in (("vent", spec.boost), ("purifier", spec.purifier)) if d}
    windows = [(e, (w * h, h), contacts(history, e)) for e, (w, h) in spec.windows.items()]
    glazing = [(w * h, *spec.orientations[e], glazing_of(spec.panes.get(e))[0]) for e, (w, h) in spec.windows.items()
               if e in spec.orientations]
    oriented = [i for i, (e, _, _) in enumerate(windows) if e in spec.orientations]
    alarm = Series([(datetime.fromisoformat(x["last_changed"]), x["state"]) for x in history.get(spec.alarm, ())],
                   keep_none=True) if spec.alarm else None
    absences = _absences(history.get(spec.alarm, ()), end) if spec.alarm else []
    # The connected shutter covers the room's windows: shut, it keeps their heat in (advisor/physics/thermal.py).
    glass = sum(size[0] for _, size, _ in windows)
    rows, when = [], start
    while when <= end:
        te, local = out.at(when), when.astimezone(zone)
        inputs = None
        if te is not None:
            facade = None
            shut = _shut_windows(spec, alarm, when, local, location, absences)
            if glazing:
                light = sun.at(when) or 0.0
                opened = {k for k, i in enumerate(oriented) if windows[i][2].at(when) is True}
                # A manual shutter shut lets in what a connected one does shut (advisor/decide.py SHUT_SHADE).
                seen = [(g[0] * SHUT_SHADE, *g[1:]) if windows[i][0] in shut else g for g, i in zip(glazing, oriented)] \
                    if shut else glazing
                facade = through_windows(light, *sun_position(when, *location), seen, opened)
            shut_area = sum(size[0] for e, size, _ in windows if e in shut)
            open_now = [(e, size) for e, size, s in windows if s.at(when) is True]
            # Open on two sides, the air crosses the room: counted here as in the scenarios (advisor/decide.py).
            apart = len(open_now) > 1 and sides_apart([(spec.orientations.get(e) or (None,))[0] for e, _ in open_now])
            inputs = Inputs(outdoor=te, sun=sun.at(when) or 0.0, heating=(power.at(when) or 0.0) if power else 0.0,
                            windows=tuple(size for _, size in open_now), cross=CROSS if apart else 1.0,
                            hour=local.hour + local.minute / 60,
                            house_heat=sum((s.at(when) or 0.0) * w for s, w in house),
                            shade=(1.0 if position is None or position.at(when) is None else max(0.05, position.at(when)))
                            # Without the windows' sides the sun is the room's whole: the shut share of its glass.
                            * (1 - (1 - SHUT_SHADE) * shut_area / glass if glass and not glazing else 1.0),
                            shutter=(0.0 if position is None or position.at(when) is None
                                     else shutter_insulation(glass, 1 - position.at(when)))
                            + (shutter_insulation(shut_area, 1.0) if shut_area else 0.0),
                            facade=facade,
                            **{name: flow if series.at(when) is True else 0.0 for name, (series, flow) in devices.items()})
        rows.append(Sample(when, indoor.at(when), inputs))
        when += DT
    return rows


# A gesture kept is the same as one found again within this much: the airing noted as it ended (advisor/opening.py), and the
# night's own reading of it.
SAME_GESTURE = timedelta(minutes=30)


def _merge(kept, found, start, end, now):
    """The gestures remembered: those seen again between `start` and `end` replace the old ones there; one the night cannot
    read again (a gap in the recorder) is kept as it was noted."""
    again = [datetime.fromisoformat(g[0]) for g in found]
    out = [g for g in kept or () if g[0] and (not start.isoformat() <= g[0] <= end.isoformat()
                                              or not any(abs(datetime.fromisoformat(g[0]) - t) < SAME_GESTURE for t in again))]
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


def _scaled(rows, boost: float = 1.0, purifier: float = 1.0):
    """The rows with the VMC's fast speed and the purifier at these shares of their declared flows: the flows are seldom
    known (Frank, 2 November: « je ne connais pas son débit »), and 60 m³/h foresaw −9 points in an hour where Chambre P
    lost 2 in four. The shares are learned from their notes (advisor/notes.py)."""
    if boost == 1.0 and purifier == 1.0:
        return rows
    def scaled(u):
        return replace(u, vent=u.vent * boost, purifier=u.purifier * purifier) if u and (u.vent or u.purifier) else u
    return [(replace(r[0], inputs=scaled(r[0].inputs)), *r[1:]) for r in rows]


def judged(before: float, after: float) -> tuple[bool, str]:
    """The new twin against the twin as it was, on the last day's error: (kept, « meilleur », « egal » or « pire »). A
    twin that forecasts nothing (no sensor history: an infinite error) is never kept."""
    if not math.isfinite(after):
        return False, "pire"
    if not math.isfinite(before) or after < before:
        return True, "meilleur"
    return (True, "egal") if after <= EVEN * before else (False, "pire")


def _rounded(value: float) -> float | None:
    """A night's error for its report: None when there was nothing to forecast (Infinity is not JSON)."""
    return round(value, 3) if math.isfinite(value) else None


def _corrected(fit_notes, value, keep_if, now) -> tuple[float, dict]:
    """A category's parameter corrected from its notes (advisor/notes.py `settle`), kept only if `keep_if(value)`."""
    found, _, report = settle(fit_notes, value, now)
    if found == value:
        return value, report
    report["garde"] = keep_if(found)
    return (found if report["garde"] else value), report


def learn_room(spec: RoomSpec, entry: dict, history, sun, now: datetime, outdoor: str, outdoor_humidity: str,
               location, zone, house_heaters=None, start: datetime | None = None,
               share_max: float | None = None, house_idle: dict | None = None) -> tuple[dict, dict]:
    """The room's twins after a night: (the entry to keep, the report). `entry` is the room's twins as kept (jumeaux.json):
    `heat`, `water`, `air`, `particles` with their `…_flow`, and `gestures` ({subject: [[when, forecast, measured]…]}).
    `share_max`: the most of the house's heat (a stove) this room may receive, the other rooms' shares set aside
    (advisor_home.py `share_caps`)."""
    first = numbers(history, spec.temperature).times[:1] + numbers(history, outdoor).times[:1]
    if start is None:
        start = max(first).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1) if len(first) == 2 else now
    days = max(0.0, (now - start).total_seconds() / 86400)
    # The gestures put aside during the day (something else acted while the room settled): the night leaves them out too.
    skipped = prune(entry.get("ecartes"), now)
    entry = {**entry, "gestures": dict(entry.get("gestures") or {}), "ecartes": skipped}
    report = {"piece": spec.name, "jours": round(days, 1), "appris": days >= MIN_DAYS, "notes": {}}
    if days <= 0:
        return entry, report
    data = samples(history, spec, outdoor, sun, start, now, location, zone, house_heaters, house_idle)
    split, recent = now - HELD_OUT, max(start, now - timedelta(days=SEARCH_DAYS))
    searched = [s for s in data if s.when >= recent]

    heat = Params(**entry["heat"])
    if heat.share < 0:
        # Learned before the bound: a room receives no less than nothing of the house's heat.
        heat = replace(heat, share=0.0)
        entry["heat"] = asdict(heat)
    if share_max is not None and heat.share > share_max:
        # More than the other rooms leave of the stove's heat: brought back within it before being judged.
        report["part_maison"] = {"avant": round(heat.share, 3), "plafond": round(share_max, 3)}
        heat = replace(heat, share=max(0.0, share_max))
        entry["heat"] = asdict(heat)
    if days >= MIN_DAYS:
        before = score(heat, searched, since=split)
        found = fit(heat, searched, until=split, iterations=HEAT_SEARCH, held=spec.declared, share_max=share_max)
        after = score(found, searched, since=split)
        kept, verdict = judged(before.hour + before.three, after.hour + after.three)
        report["chaleur"] = {"avant": [_rounded(before.hour), _rounded(before.three)],
                             "apres": [_rounded(after.hour), _rounded(after.three)], "garde": kept, "verdict": verdict}
        if kept:
            heat = found
            entry["heat"] = asdict(found)
        # Then the windows' effect, from the openings' notes (CAHIER-MOTEUR.md § 15.1): the day-long fit hardly weighs a few
        # minutes of opening. Kept when the last day is forecast no worse than 5 % off.
        tuned, _, windows = fit_windows(heat, data, now, skipped)
        if tuned != heat:
            now_score, tuned_score = score(heat, searched, since=split), score(tuned, searched, since=split)
            windows["garde"] = tuned_score.hour + tuned_score.three <= NOTES_TOLERANCE * (now_score.hour + now_score.three)
            windows["fenetre"] = [round(heat.window, 3), round(tuned.window, 3)]
            if windows["garde"]:
                heat = tuned
                entry["heat"] = asdict(tuned)
        report["notes"]["heat"] = windows
    # What became of each gesture: noted, or why it was left out (advisor/notes.py `left_out`), in the night's report.
    why = report["notes"].setdefault("heat", {}).setdefault("gestes_vus", {})
    entry["gestures"]["heat"] = _merge(entry["gestures"].get("heat"), heat_notes(heat, data, skipped, why), start, now, now)

    for key, kind, subject in TWINS:
        if key not in entry or not getattr(spec, "humidity" if key == "water" else SENSORS[key][0]):
            continue
        plain = _air_rows(key, history, spec, data, outdoor, outdoor_humidity)
        shares = {"boost": entry.get("boost_scale", 1.0), "purify": entry.get("purifier_scale", 1.0)}

        def rows_at(**changed):
            both = {**shares, **changed}
            return _scaled(plain, both["boost"], both["purify"])

        rows = rows_at()
        last = [r for r in rows if r[0].when >= recent]
        volume = entry[key]["volume"]
        x = vector(kind, entry[key], entry[f"{key}_flow"])
        if days >= MIN_DAYS:
            before = air_score(kind, x, volume, last, split, now)
            found = _nelder_mead(lambda y: air_score(kind, y, volume, last, recent, split), x,
                                 [m * WARM for m in MOVES[kind]], AIR_SEARCH)
            after = air_score(kind, found, volume, last, split, now)
            kept, verdict = judged(before, after)
            report[subject] = {"avant": _rounded(before), "apres": _rounded(after), "garde": kept, "verdict": verdict}
            if kept:
                x = found
                entry[key], entry[f"{key}_flow"] = values(kind, x, volume)
            # Then the windows' effect on this subject, from the openings' notes (CAHIER-MOTEUR.md § 15.1).
            reference = air_score(kind, x, volume, last, split, now)

            def with_window(w):
                return [x[0], math.log(w), *x[2:]]
            window, report["notes"][subject] = _corrected(
                lambda w: air_notes(kind, subject, with_window(w), volume, rows, "window", skipped), math.exp(x[1]),
                lambda w: air_score(kind, with_window(w), volume, last, split, now) <= NOTES_TOLERANCE * reference, now)
            if window != math.exp(x[1]):
                x = with_window(window)
                entry[key], entry[f"{key}_flow"] = values(kind, x, volume)
            # The share of its declared flow the VMC gives the room, from its runs on the humidity; the purifier's, on the
            # particles.
            for device, own, key_scale, present in (("boost", "water", "boost_scale", spec.boost),
                                                     ("purify", "particles", "purifier_scale", spec.purifier)):
                if not present or key != own:
                    continue
                share, report["notes"][f"{device}:{subject}"] = _corrected(
                    lambda v: air_notes(kind, subject, x, volume, rows_at(**{device: v}), device, skipped), shares[device],
                    lambda v: air_score(kind, x, volume, [r for r in rows_at(**{device: v}) if r[0].when >= recent], split,
                                        now) <= NOTES_TOLERANCE * reference, now)
                shares[device] = entry[key_scale] = share
            rows = rows_at()
        why = report["notes"].setdefault(subject, {}).setdefault("gestes_vus", {})
        entry["gestures"][subject] = _merge(entry["gestures"].get(subject),
                                            air_notes(kind, subject, x, volume, rows, "window", skipped, why), start, now, now)
        # Each device's runs: their effect on this subject (« boost:humidity », « purify:particles »).
        for device, present in (("boost", spec.boost), ("purify", spec.purifier)):
            if present or f"{device}:{subject}" in entry["gestures"]:
                why = report["notes"].setdefault(f"{device}:{subject}", {}).setdefault("gestes_vus", {})
                found = air_notes(kind, subject, x, volume, rows, device, skipped, why) if present else []
                entry["gestures"][f"{device}:{subject}"] = _merge(entry["gestures"].get(f"{device}:{subject}"), found,
                                                                   start, now, now)

    report["gestes"] = {s: len(g) for s, g in entry["gestures"].items()}
    report["preuves"] = {s: level([(f, m) for _, f, m in g]) for s, g in entry["gestures"].items()}
    return entry, report
