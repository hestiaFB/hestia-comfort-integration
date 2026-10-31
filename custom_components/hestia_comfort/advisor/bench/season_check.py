"""The physical twin over seasons, from Home Assistant's hourly statistics (kept for years, windows excepted).

Fitted on last winter (the heating season, stove included), then scored on the spring, the summer and this autumn, at
one and three hours, against « nothing changes ». Hourly means are spread over a quarter-hour grid; the windows are not
known in the statistics, so an airing shows up as an unexplained drop: the twin is judged without them.

    cd custom_components/hestia_comfort
    ../../../niak-comfort/banc/.venv/bin/python -m advisor.bench.season_check statistiques.json open-meteo.json

`statistiques.json`: the result of `recorder/statistics_during_period` (period « hour », type « mean »).
"""
from dataclasses import replace
from datetime import datetime, timezone
import json
import sys
from zoneinfo import ZoneInfo

from scipy.optimize import minimize

from ..physics.fit import FREE, HELD, PULL, params_of
from ..physics.thermal import Inputs, ordinary, step
from .twin_check import AWAY_SHARE, HOME_SHARE, room_of

ZONE = ZoneInfo("Europe/Paris")
DT = 900.0                       # a quarter of an hour
PER_HOUR = 4
HOUR, THREE = PER_HOUR, 3 * PER_HOUR
STRIDE = 3 * PER_HOUR            # a forecast every three hours
OUTDOOR, STOVE = "sensor.gw2000a_outdoor_temperature", ("sensor.thermostat_poele_power_percent", 8500.0)
ROOMS = {   # room: (its temperature, its heater's power in %)
    "Chambre P": ("sensor.temperature_p_temperature", "sensor.thermostat_p_power_percent"),
    "Chambre A": ("sensor.temperature_a_temperature", "sensor.thermostat_a_power_percent"),
    "Chambre M": ("sensor.temperature_m_temperature", "sensor.thermostat_m_power_percent"),
    "Chambre AL": ("sensor.temperature_al_temperature", "sensor.thermostat_al_power_percent"),
    "Salon": ("sensor.gw2000a_indoor_temperature", "sensor.thermostat_salon_power_percent"),
}
PERIODS = (("hiver (appris)", "2025-12-19", "2026-04-01"), ("printemps", "2026-04-01", "2026-06-01"),
           ("été", "2026-06-01", "2026-10-01"), ("automne", "2026-10-01", "2026-10-31"))


def _hourly(stats, entity):
    """{hour start (s): mean} of one statistic."""
    return {int(row["start"]) // 1000: row["mean"] for row in stats.get(entity, ()) if row.get("mean") is not None}


def _between(points: dict, t: int):
    """The value at `t` from hourly means placed at mid-hour, linearly; None across a gap."""
    base = (t - 1800) // 3600 * 3600
    a, b = points.get(base), points.get(base + 3600)
    if a is None or b is None:
        return None
    return a + (b - a) * (t - 1800 - base) / 3600


def timeline(stats, sun_hours, room):
    """The room every quarter of an hour: (time, measured air or None, inputs or None)."""
    temperature, heater = ROOMS[room]
    air, out, heat, stove = (_hourly(stats, e) for e in (temperature, OUTDOOR, heater, STOVE[0]))
    rows, t = [], max(min(air), min(out)) + 1800
    last = min(max(air), max(out))
    while t < last:
        te, ti = _between(out, t), _between(air, t)
        local = datetime.fromtimestamp(t, ZONE)
        hour_start = t // 3600 * 3600
        inputs = None if te is None else Inputs(
            outdoor=te, sun=sun_hours.get(hour_start, 0.0), heating=(heat.get(hour_start) or 0.0) / 100,
            hour=local.hour + local.minute / 60, house_heat=(stove.get(hour_start) or 0.0) / 100 * STOVE[1])
        rows.append((t, ti, inputs))
        t += int(DT)
    return rows


def errors(p, rows, since, until):
    """Signed errors at one and three hours, and those of « nothing changes », for forecasts starting in [since, until)."""
    out = {"hour": [], "three": [], "still_hour": [], "still_three": []}
    walls = None
    for i, (t, ti, u) in enumerate(rows):
        if u is None or ti is None:
            walls = None
            continue
        walls = ti if walls is None else walls
        if since <= t < until and i % STRIDE == 0 and i + THREE < len(rows):
            air, mass = ti, walls
            for k in range(THREE):
                v = rows[i + k][2]
                if v is None:
                    air = None
                    break
                air, mass = step(p, air, mass, v, DT)
                if k == HOUR - 1 and rows[i + HOUR][1] is not None:
                    out["hour"].append(air - rows[i + HOUR][1])
                    out["still_hour"].append(ti - rows[i + HOUR][1])
            if air is not None and rows[i + THREE][1] is not None:
                out["three"].append(air - rows[i + THREE][1])
                out["still_three"].append(ti - rows[i + THREE][1])
        _, walls = step(p, ti, walls, u, DT)
    return out


def _mean(values):
    return sum(abs(v) for v in values) / len(values) if values else float("nan")


def season(stats_path, sun_path):
    stats = json.load(open(stats_path, encoding="utf-8"))
    hourly = json.load(open(sun_path, encoding="utf-8"))["hourly"]
    # Open-Meteo's value is the mean of the hour ending at its time.
    sun_hours = {int(datetime.fromisoformat(t).replace(tzinfo=timezone.utc).timestamp()) - 3600: v
                 for t, v in zip(hourly["time"], hourly["shortwave_radiation"]) if v is not None}

    def stamp(day):
        return int(datetime.fromisoformat(day).replace(tzinfo=ZONE).timestamp())
    learned_from, learned_to = stamp(PERIODS[0][1]), stamp(PERIODS[0][2])
    print("Jumeau physique ajusté sur l'hiver 2025-26 ; erreur moyenne (« rien ne change » entre parenthèses), à 1 h | 3 h\n")
    print(f"{'Pièce':11} " + " ".join(f"| {name:^25}" for name, *_ in PERIODS))
    for room in ROOMS:
        rows = timeline(stats, sun_hours, room)
        base = replace(ordinary(room_of(room)), share=HOME_SHARE if room == "Salon" else AWAY_SHARE)

        def cost(x):
            e = errors(params_of(base, x), rows, learned_from, learned_to)
            if not e["three"]:
                return float("inf")
            pull = sum((HELD if name == "heat" else PULL) * v * v for (name, log, _), v in zip(FREE, x) if log)
            return _mean(e["hour"]) + _mean(e["three"]) + pull
        start = [0.0 if log else getattr(base, name) for name, log, _ in FREE]
        simplex = [start] + [[s + (move if i == j else 0.0) for j, s in enumerate(start)] for i, (_, _, move) in enumerate(FREE)]
        found = minimize(cost, start, method="Nelder-Mead",
                         options={"maxfev": 1500, "xatol": 1e-3, "fatol": 1e-4, "initial_simplex": simplex})
        p = params_of(base, found.x)
        cells = []
        for _, since, until in PERIODS:
            e = errors(p, rows, stamp(since), stamp(until))
            cells.append(f"{_mean(e['hour']):.2f} ({_mean(e['still_hour']):.2f}) | {_mean(e['three']):.2f} ({_mean(e['still_three']):.2f})"
                         if e["three"] else "pas de données")
        print(f"{room:11} " + " ".join(f"| {c:^25}" for c in cells), flush=True)
        tau = (p.cm + p.ca) / (p.h_env + 0.34 * p.leaks) / 3600
        print(f"{'':11}   constante {tau:.0f} h, pertes {p.h_env:.0f} W/K, murs {p.cm / 1e6:.1f} MJ/K, chauffage {p.heat:.0f} W,"
              f" soleil {p.sun:.2f} m², apports {p.gains:.0f} W, part du poêle {min(1.0, max(0.0, p.share)):.0%}", flush=True)


if __name__ == "__main__":
    season(sys.argv[1], sys.argv[2])
