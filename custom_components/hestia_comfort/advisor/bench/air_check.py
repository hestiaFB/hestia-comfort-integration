"""Are the twins of the water (humidity) and of the air (CO₂) good enough? The check of CAHIER-MOTEUR.md § 18.3.

Fitted on the first seven days, scored on the last three, at one and three hours, against « nothing changes »; and, for
each window that opens, the change it brought in one hour against the change the twin forecast. The outdoor air comes in
through the leaks and the open windows (advisor/physics/vents.py); its flow is learned by each twin.

    cd custom_components/hestia_comfort
    ../../../niak-comfort/banc/.venv/bin/python -m advisor.bench.air_check history.json open-meteo.json co2.json
"""
from datetime import datetime, timedelta
import math
import sys

from scipy.optimize import minimize

from ..physics.air import AirParams, BREATH, ParticleParams, air_step, particles_step
from ..physics.airfit import BOUND, MOVES, START, _e, _flow, _run  # noqa: F401 - the bench's own names
from ..physics.vents import leak_flow
from ..physics.water import WaterParams, absolute, water_step
from . import twin_check as T
from .history import load, numbers

HOUR, THREE = 12, 36
CO2 = {"Salon": "sensor.alpstuga_air_quality_monitor_dioxyde_de_carbone"}
# A CO₂ sensor reading under this is a fault (the ALPSTUGA reports 0 ppm now and then), never a measure.
CO2_FLOOR = 300.0
# Water shown in humidity points: one g/m³ is about this many points at 20 °C.
POINTS = 100 / absolute(20.0, 100.0)


PM25 = {"Salon": "sensor.ikea_sensor_pm25"}
# The IKEA sensor reports 999 µg/m³ when it fails: above this, never a measure.
PM25_CEILING = 500.0


def _mean(values):
    return sum(abs(v) for v in values) / len(values) if values else float("nan")


def check(history_path, sun_path, *extra):
    history = load(history_path, *extra)
    sun = T.open_meteo_sun(sun_path)
    start = max(datetime.fromisoformat(s[0]["last_changed"]) for s in history.values())
    start = start.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    end = max(datetime.fromisoformat(s[-1]["last_changed"]) for s in history.values())
    split = start + timedelta(days=7)
    outdoor_t, outdoor_h = numbers(history, T.STATION["temperature"]), numbers(history, T.STATION["humidity"])
    print("Jumeaux de l'eau et de l'air : appris 7 jours, testés 3 ; erreur moyenne (« rien ne change »)\n")
    for name, room in T.HOUSE.items():
        known = T.room_of(name)
        samples = T.samples(history, room, sun, start, end, known.openings)
        humidity = numbers(history, room[1])

        def water_row(s):
            rh, te, he = humidity.at(s.when), outdoor_t.at(s.when), outdoor_h.at(s.when)
            inside = None if rh is None or s.measured is None else absolute(s.measured, rh)
            return (s, inside, None if te is None or he is None else absolute(te, he))
        subjects = [("water", "humidité", "points", [water_row(s) for s in samples])]
        if name in CO2:
            co2 = numbers(history, CO2[name])
            subjects.append(("air", "CO₂", "ppm", [
                (s, None if co2.at(s.when) is None or co2.at(s.when) < CO2_FLOOR else co2.at(s.when), 420.0) for s in samples]))
        if name in PM25 and PM25[name] in history:
            pm = numbers(history, PM25[name])
            subjects.append(("particles", "PM2.5", "µg/m³", [
                (s, None if pm.at(s.when) is None or pm.at(s.when) > PM25_CEILING else pm.at(s.when), 0.0) for s in samples]))
        for kind, label, unit, rows in subjects:
            start_x = (START[kind] if kind in START else [0.0, 0.0, math.log(0.5), math.log(5.0), 30.0, 0.0, 0.0] if kind == "water"
                       else [0.0, 0.0, 2 * BREATH, 0.0, 0.0])

            def cost(x):
                e = _run(kind, x, known.air, rows, start, split)
                return _mean(e["hour"]) + _mean(e["three"]) if e["three"] else float("inf")
            simplex = [start_x] + [[v + (m if i == j else 0.0) for j, v in enumerate(start_x)] for i, m in enumerate(MOVES[kind])]
            found = minimize(cost, start_x, method="Nelder-Mead",
                             options={"maxfev": 800, "xatol": 1e-3, "fatol": 1e-4, "initial_simplex": simplex})
            e = _run(kind, found.x, known.air, rows, split, end)
            if kind == "water":
                e = {k: ([v * POINTS for v in vals] if k != "gestures" else [(a * POINTS, b * POINTS) for a, b, *_ in vals])
                     for k, vals in e.items()}
            g = e["gestures"]
            gesture = (f"{len(g)} aérations : mesuré {sum(a for a, *_ in g) / len(g):+.1f}, prévu {sum(b for _, b, *_ in g) / len(g):+.1f} {unit} en 1 h"
                       if g else "aucune aération dans les jours de test")
            print(f"{name:11} {label:9} 1 h {_mean(e['hour']):5.1f} ({_mean(e['still_hour']):5.1f}) · 3 h {_mean(e['three']):5.1f}"
                  f" ({_mean(e['still_three']):5.1f}) {unit} · {gesture}", flush=True)
            print(f"{'':21} fuites ×{_e(found.x[0]):.2f}, fenêtres ×{_e(found.x[1]):.2f}", flush=True)


def shared(history_path, sun_path, co2_path, room="Salon"):
    """One flow for the room's air, learned by the CO₂ and lent to the water and the heat: does each twin keep its
    quality with it (CAHIER-MOTEUR.md § 8)?"""
    from dataclasses import replace
    from ..physics.fit import fit, gestures, score
    from ..physics.thermal import ordinary
    history = load(history_path, co2_path)
    sun = T.open_meteo_sun(sun_path)
    start = max(datetime.fromisoformat(s[0]["last_changed"]) for s in history.values())
    start = start.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    end = max(datetime.fromisoformat(s[-1]["last_changed"]) for s in history.values())
    split = start + timedelta(days=7)
    outdoor_t, outdoor_h = numbers(history, T.STATION["temperature"]), numbers(history, T.STATION["humidity"])
    known, spec = T.room_of(room), T.HOUSE[room]
    samples = T.samples(history, spec, sun, start, end, known.openings)
    humidity, co2 = numbers(history, spec[1]), numbers(history, CO2[room])
    air_rows = [(s, None if co2.at(s.when) is None or co2.at(s.when) < CO2_FLOOR else co2.at(s.when), 420.0) for s in samples]
    water_rows = [(s, None if humidity.at(s.when) is None or s.measured is None else absolute(s.measured, humidity.at(s.when)),
                   None if outdoor_t.at(s.when) is None or outdoor_h.at(s.when) is None
                   else absolute(outdoor_t.at(s.when), outdoor_h.at(s.when))) for s in samples]

    def fitted(kind, rows, fixed=None):
        start_x = [0.0, 0.0, math.log(0.5), math.log(5.0), 30.0, 0.0, 0.0] if kind == "water" else [0.0, 0.0, 2 * BREATH, 0.0, 0.0]
        free = list(range(2, len(start_x))) if fixed else list(range(len(start_x)))
        full = lambda y: [*(fixed or ()), *y] if fixed else list(y)
        def cost(y):
            e = _run(kind, full(y), known.air, rows, start, split)
            return _mean(e["hour"]) + _mean(e["three"]) if e["three"] else float("inf")
        y0 = [start_x[i] for i in free]
        simplex = [y0] + [[v + (MOVES[kind][free[i]] if i == j else 0.0) for j, v in enumerate(y0)] for i in range(len(y0))]
        y = minimize(cost, y0, method="Nelder-Mead", options={"maxfev": 800, "xatol": 1e-3, "fatol": 1e-4, "initial_simplex": simplex}).x
        return full(y)

    def line(label, kind, x, rows, unit, factor=1.0):
        e = _run(kind, x, known.air, rows, split, end)
        g = e["gestures"]
        print(f"  {label:34} 1 h {_mean(e['hour']) * factor:5.1f} · 3 h {_mean(e['three']) * factor:5.1f} {unit} ·"
              f" aérations : mesuré {sum(a for a, *_ in g) / len(g) * factor:+.1f}, prévu {sum(b for _, b, *_ in g) / len(g) * factor:+.1f}"
              f" · fenêtres ×{_e(x[1]):.2f}", flush=True)
    air_x = fitted("air", air_rows)
    water_own = fitted("water", water_rows)
    water_shared = fitted("water", water_rows, fixed=air_x[:2])
    print(f"{room} : débit des fenêtres appris par le CO₂, prêté à l'humidité et à la chaleur\n")
    line("CO₂ (apprend le débit)", "air", air_x, air_rows, "ppm")
    line("humidité, son propre débit", "water", water_own, water_rows, "points", POINTS)
    line("humidité, débit du CO₂", "water", water_shared, water_rows, "points", POINTS)
    base = replace(ordinary(known), share=T.HOME_SHARE)
    mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")
    for label, p in (("chaleur, son propre débit", fit(base, samples, until=split, held=frozenset({"heat"}))),
                     ("chaleur, débit du CO₂", fit(replace(base, window=_e(air_x[1]), leaks=_e(air_x[0]) * leak_flow(known.air)),
                                                   samples, until=split, held=frozenset({"heat", "window"})))):
        s, g = score(p, samples, since=split), [x for x in gestures(p, samples, since=split) if x["kind"] == "window"]
        print(f"  {label:34} 1 h {s.hour:5.2f} · 3 h {s.three:5.2f} °C · aérations : mesuré {mean([x['measured'] for x in g]):+.2f},"
              f" prévu {mean([x['forecast'] for x in g]):+.2f} · fenêtres ×{p.window:.2f}", flush=True)


if __name__ == "__main__":
    if "--debit-partage" in sys.argv:
        shared(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        check(*[a for a in sys.argv[1:] if not a.startswith("--")])
