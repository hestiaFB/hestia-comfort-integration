"""A room's identity card (docs/ETAT-DES-LIEUX-MOTEUR.md § 4.3 bis), made again every night with its
twins: what the room is, as measured, learned and declared — its normal, its insulation, its inertia, its heating, what
an airing does to it, its sources, its household's habits, what is still badly understood, what is chronic.

Frank, 16 November: « apprendre la globalité de la pièce sur tous les capteurs qu'on connaît […] une sorte de carte
d'identité de la pièce, qui nous permet de comprendre cette pièce et donner les meilleurs conseils possibles ». Each room
is judged on its own normal, never on the others': the Chambre P, an old garage turned bedroom, lives at 75-80 % of
humidity; what is chronic becomes an advice for the dwelling, not a daily one.

Plain values in, plain values out, as advisor/nightly.py: it runs in the nightly worker.
"""
from dataclasses import replace
from datetime import datetime, timedelta
import math
from statistics import median

from .bench.history import contacts, numbers
from .household import Habits
from .physics.thermal import Inputs, Params, step, time_constant
from .physics.water import EXCHANGE, RESERVE, SOURCES_MAX, WaterParams
from .slots import SLOTS, slot_name

# The room's normal is read on its last two weeks, its habits on four.
NORMAL_DAYS, HABIT_DAYS = 14, 28
# Hours a slot needs to say its normal.
NORMAL_LEAST = 24
# A window open for less is someone going through, not an airing.
OPENED_LEAST = timedelta(minutes=3)
# Chronic: half the time above this humidity (%), a tenth of the time above this CO₂ (ppm).
CHRONIC_HUMIDITY, CHRONIC_CO2 = 70.0, 1400.0
# The outdoor temperature's lags compared (hours), and the pairs of hours one needs.
LAGS, LAG_LEAST = 24, 72
# Twin parameters at their bounds (advisor/physics/water.py): this many, and the room's humidity is badly understood.
BOUNDS_BADLY = 2


def _quantiles(values) -> list[float] | None:
    """[low (10 %), median, high (90 %)], one decimal."""
    if len(values) < NORMAL_LEAST:
        return None
    s = sorted(values)
    n = len(s)
    return [round(s[min(n - 1, int(round(p * (n - 1))))], 1) for p in (0.1, 0.5, 0.9)]


def _hours(start: datetime, end: datetime):
    t = start.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    while t <= end:
        yield t
        t += timedelta(hours=1)


def normals(history, spec, now: datetime, zone, habits: Habits) -> dict:
    """Each slot's normal and the day's, as measured hour by hour over NORMAL_DAYS: {slot: {measure: [low, median,
    high]}}, for « air » (°C), « humidite » (%), « co2 » (ppm)."""
    series = {"air": numbers(history, spec.temperature)}
    if spec.humidity:
        series["humidite"] = numbers(history, spec.humidity)
    if spec.co2:
        series["co2"] = numbers(history, spec.co2)
    by = {name: {k: [] for k in series} for name in (*SLOTS, "jour")}
    for t in _hours(now - timedelta(days=NORMAL_DAYS), now):
        name = slot_name(t.astimezone(zone), habits)
        for k, s in series.items():
            value = s.at(t)
            if value is not None:
                by[name][k].append(value)
                by["jour"][k].append(value)
    out = {}
    for name, values in by.items():
        found = {k: q for k, v in values.items() if (q := _quantiles(v)) is not None}
        if found:
            out[name] = found
    return out


def _correlation(pairs) -> float | None:
    n = len(pairs)
    ma, mb = sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n
    va = sum((a - ma) ** 2 for a, _ in pairs)
    vb = sum((b - mb) ** 2 for _, b in pairs)
    if va <= 0 or vb <= 0:
        return None
    return sum((a - ma) * (b - mb) for a, b in pairs) / math.sqrt(va * vb)


def outdoor_lag(history, spec, outdoor: str, now: datetime) -> dict | None:
    """How late the room follows the outdoor temperature, measured: the lag (hours) at which they go together best, and
    how closely (« lien », 0 to 1). A room its heating holds hardly follows it (a low « lien »)."""
    inside, outside = numbers(history, spec.temperature), numbers(history, outdoor)
    hours = list(_hours(now - timedelta(days=NORMAL_DAYS), now))
    a, b = [inside.at(t) for t in hours], [outside.at(t) for t in hours]
    best = None
    for lag in range(LAGS + 1):
        pairs = [(a[i], b[i - lag]) for i in range(lag, len(hours)) if a[i] is not None and b[i - lag] is not None]
        if len(pairs) < LAG_LEAST:
            continue
        r = _correlation(pairs)
        if r is not None and (best is None or r > best[1]):
            best = (lag, r)
    return {"retard_h": best[0], "lien": round(best[1], 2)} if best else None


def heat_card(p: Params, windows) -> dict:
    """What the heat twin says of the room, in plain figures: °C lost in an hour, shut and unheated, with 10 °C less
    outside; hours to cover two thirds of the way to the outside (inertia); °C its own heater adds in an hour; °C an
    airing of 20 min takes, and what is still missing an hour after it is shut."""
    still = replace(p, gains=0.0, rhythm_cos=0.0, rhythm_sin=0.0, share=0.0)

    def run(steps, inputs, air=20.0, walls=20.0):
        for _ in range(steps):
            air, walls = step(still, air, walls, inputs)
        return air, walls

    shut = Inputs(outdoor=10.0)
    out = {"perte_h": round(20.0 - run(12, shut)[0], 2), "inertie_h": round(time_constant(p), 1)}
    if p.heat > 0:
        out["chauffage_h"] = round(run(12, Inputs(outdoor=10.0, heating=1.0), 19.0, 19.0)[0] - run(12, shut, 19.0, 19.0)[0], 2)
    if windows:
        opened = Inputs(outdoor=10.0, windows=tuple((w * h, h) for w, h in windows))
        air, walls = run(4, opened)
        out["aeration_20"] = round(run(4, shut)[0] - air, 2)
        later_air, _ = run(12, shut, air, walls)
        out["aeration_20_1h"] = round(run(16, shut)[0] - later_air, 2)
    if p.share > 0:
        out["part_maison"] = round(p.share, 2)
    return out


def water_card(entry: dict) -> dict | None:
    """The water twin: its steady sources (g/h), and which of its values sit at the bounds of what a room can do — a
    twin pushed against them does not understand its room yet (bilan of 16 November: six rooms out of seven)."""
    learned = entry.get("water")
    if not learned:
        return None
    p = WaterParams(**learned)
    at = [name for name, value, (low, high) in (("echange", p.exchange, EXCHANGE), ("reserve", p.reserve, RESERVE))
          if value <= low * 1.01 or value >= high * 0.99]
    if p.sources >= SOURCES_MAX * 0.99:
        at.append("sources")
    return {"sources_g_h": round(p.sources, 1), "aux_bornes": at}


def airing_card(entry: dict, zone, habits: Habits) -> dict:
    """What the windows really did, gesture after gesture (the nightly notes: [when, forecast, measured]): how many,
    the effect measured, and the share of the forecast it was (« rapport »), for the day and slot by slot."""
    out = {}
    for subject, key in (("humidity", "humidite"), ("heat", "chaleur"), ("co2", "co2")):
        rows = [(g[0], g[1], g[2]) for g in (entry.get("gestures") or {}).get(subject) or ()
                if len(g) >= 3 and g[1] and g[2] is not None]
        if not rows:
            continue

        def summed(found):
            return {"cas": len(found), "mesure": round(median(m for _, _, m in found), 2),
                    "rapport": round(median(m / f for _, f, m in found), 2)}
        card = {"jour": summed(rows)}
        for name in SLOTS:
            found = [r for r in rows if slot_name(datetime.fromisoformat(r[0]).astimezone(zone), habits) == name]
            if found:
                card[name] = summed(found)
        out[key] = card
    return out


def opening_habits(history, spec, now: datetime, zone, habits: Habits) -> dict:
    """When the household really opens the room (its windows' contacts, HABIT_DAYS): per slot, the openings of
    OPENED_LEAST or more a week and their median length (min)."""
    series = [contacts(history, e) for e in spec.windows]
    since = now - timedelta(days=HABIT_DAYS)
    times = sorted({t for s in series for t in s.times if since <= t <= now})
    if not times:
        return {}
    openings, opened_at = [], None
    for t in times:
        is_open = any(s.at(t) is True for s in series)
        if is_open and opened_at is None:
            opened_at = t
        elif not is_open and opened_at is not None:
            if t - opened_at >= OPENED_LEAST:
                openings.append((opened_at, t))
            opened_at = None
    first = min((s.times[0] for s in series if s.times), default=since)
    days = max(1.0, (now - max(first, since)).total_seconds() / 86400)
    per = {name: [] for name in SLOTS}
    for a, b in openings:
        per[slot_name(a.astimezone(zone), habits)].append((b - a).total_seconds() / 60)
    return {name: {"par_semaine": round(len(v) * 7 / days, 1), "duree_min": round(median(v))}
            for name, v in per.items() if v}


def chronic(normal: dict) -> list[dict]:
    """What the room is as a rule, not on a bad day: an advice for the dwelling (ETAT-DES-LIEUX-MOTEUR.md § 4.3)."""
    day = normal.get("jour") or {}
    out = []
    if (h := day.get("humidite")) and h[1] >= CHRONIC_HUMIDITY:
        out.append({"sujet": "humidite", "mediane": h[1], "bas": h[0]})
    if (c := day.get("co2")) and c[2] >= CHRONIC_CO2:
        out.append({"sujet": "co2", "haut": c[2]})
    return out


def identity(spec, entry: dict, history, now: datetime, zone, outdoor: str, report: dict | None = None) -> dict:
    """The room's identity card, as kept with its twins (`entry["identite"]`)."""
    habits = spec.habits if isinstance(spec.habits, Habits) else Habits()
    normal = normals(history, spec, now, zone, habits)
    card = {"fait_le": now.isoformat(), "normale": normal, "dehors": outdoor_lag(history, spec, outdoor, now),
            "chaleur": heat_card(Params(**entry["heat"]), list(spec.windows.values())) if entry.get("heat") else None,
            "eau": water_card(entry), "aeration": airing_card(entry, zone, habits),
            "habitudes": opening_habits(history, spec, now, zone, habits), "chronique": chronic(normal)}
    badly = []
    if card["eau"] and len(card["eau"]["aux_bornes"]) >= BOUNDS_BADLY:
        badly.append("humidite")
    if ((report or {}).get("chaleur") or {}).get("verdict") == "pire":
        badly.append("chaleur")
    card["mal_compris"] = badly
    return card


def normal_of(card: dict | None, measure: str, slot: str | None = None) -> float | None:
    """The room's median for `measure` in `slot` (the day's when the slot has none), None while unknown."""
    normal = (card or {}).get("normale") or {}
    for name in (slot, "jour"):
        if name and (q := (normal.get(name) or {}).get(measure)):
            return q[1]
    return None
