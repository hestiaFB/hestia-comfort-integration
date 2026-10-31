"""Is the physical twin good enough to compare gestures? The check of CONCEPTION-MOTEUR.md, step 2.

The physical twin is fitted on the first days (advisor/physics/fit.py), the 2.1 twin on the same days; over the last days,
from every half hour, both forecast one and three hours with the real weather, heating and windows, and are compared with
« nothing changes », overall and while a window is open.

    cd custom_components/hestia_comfort && python -m advisor.bench.twin_check history.json [days_learned] [open-meteo.json]

With an Open-Meteo download (hourly `shortwave_radiation`, UTC), its sun stands in for the station's: the check of a
station shaded by the house (CAHIER-MOTEUR.md § 7.3).
"""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import sys
from zoneinfo import ZoneInfo

from ..house import Opening, Room
from ..observe import Series
from ..physics.fit import Sample, fit, score
from ..physics.sunlight import sun_position, through_windows
from ..physics.thermal import STEP, Inputs, ordinary, shutter_insulation, time_constant
from .history import attribute, contacts, load, numbers

try:
    from ...engine import twin as old_twin
except ImportError:  # run from custom_components/hestia_comfort, where the engine is a top-level package
    from engine import twin as old_twin

DT = timedelta(seconds=STEP)
ZONE = ZoneInfo("Europe/Paris")

# Frank's house, as Hestia would know it before anything is declared: sensors, windows and their kind only.
STATION = {"temperature": "sensor.gw2000a_outdoor_temperature", "humidity": "sensor.gw2000a_outdoor_humidity",
           "sun": "sensor.gw2000a_solar_radiation"}
HOUSE = {
    "Chambre P": ("sensor.temperature_p_temperature", "sensor.temperature_p_humidity", "climate.thermostat_p", ("fenetre_p",)),
    "Chambre A": ("sensor.temperature_a_temperature", "sensor.temperature_a_humidity", "climate.thermostat_a", ("fenetre_a",)),
    "Chambre M": ("sensor.temperature_m_temperature", "sensor.temperature_m_humidity", "climate.thermostat_m", ("fenetre_m",)),
    "Chambre AL": ("sensor.temperature_al_temperature", "sensor.temperature_al_humidity", "climate.thermostat_al", ("fenetre_al",)),
    "Salon": ("sensor.gw2000a_indoor_temperature", "sensor.gw2000a_indoor_humidity", "climate.thermostat_salon",
              ("fenetre_ouest", "porte_fenetre_sd:french", "porte_fenetre_sg:french", "fenetre_c")),
}
# Connected shutters, read on their position (CAHIER-MOTEUR.md § 6.7 ter); the bedrooms' wooden shutters are manual.
COVERS = {"Chambre P": "cover.volet_roulant_p"}
# A shut roller shutter still lets a little light through its slats.
SHUT = 0.05
# The house heaters: the stove stands in the salon and heats the whole house. (thermostat, W, the room it stands in)
HOUSE_HEATERS = (("climate.thermostat_poele", 8500, "Salon"),)
# Where a house heater's heat goes before anything is learned: half where it stands, a little in every other room.
HOME_SHARE, AWAY_SHARE = 0.5, 0.1


# What Frank declared on 31 October, from the plan of the house: floor area (m²) and window sizes (width × height, m);
# the heating power is the one declared in Versatile Thermostat (`power_manager.device_power`), which Hestia can read.
# The salon's air reaches the kitchen, the larder and the hall with its staircase: one volume, heated by the stove.
DECLARED = {
    "Chambre P": (17.06, 1500, {"fenetre_p": (1.40, 0.95)}),
    "Chambre A": (10.86 + 2.24, 1000, {"fenetre_a": (0.97, 1.21)}),
    "Chambre M": (10.88, 1000, {"fenetre_m": (0.97, 1.21)}),
    "Chambre AL": (9.32, 1000, {"fenetre_al": (0.97, 1.21)}),
    "Salon": (36.46 + 1.74 + 5.83, 3000, {"fenetre_ouest": (1.18, 1.21), "porte_fenetre_sd": (1.18, 2.10),
                                          "porte_fenetre_sg": (1.18, 2.10)}),
}


# The orientations Frank declared in Hestia Comfort (its diagnostics, `room.config.openings`): bearing, sheltered.
ORIENTED = {"fenetre_ouest": (270, False), "porte_fenetre_sd": (180, True), "porte_fenetre_sg": (180, True),
            "fenetre_c": (90, False), "fenetre_p": (270, False), "fenetre_a": (180, False), "fenetre_m": (180, False),
            "fenetre_al": (90, False)}
LOCATION = (43.45, 5.47)


def _openings(names, sizes=None):
    out = []
    for name in names:
        entity, _, kind = name.partition(":")
        width, height = (sizes or {}).get(entity, (None, None))
        bearing, sheltered = ORIENTED.get(entity, (None, False))
        out.append(Opening(f"binary_sensor.{entity}_contact", kind or "window",
                           area=width * height if width else None, height=height, exposure=bearing, sheltered=sheltered))
    return tuple(out)


def room_of(name, declared=True) -> Room:
    """The room as Hestia knows it: only its windows and their kind, or everything Frank declared."""
    names = HOUSE[name][3]
    if not declared or name not in DECLARED:
        return Room(name, name, openings=_openings(names))
    surface, power, sizes = DECLARED[name]
    return Room(name, name, volume=surface * 2.5, heating_power=power, openings=_openings(names, sizes))


def _facade(solar, when, windows):
    """W of sun through the room's windows at `when`, each by its orientation, open or shut."""
    elevation, azimuth = sun_position(when, *LOCATION)
    glazing = [(o.glazing, o.exposure, o.sheltered) for o, _ in windows]
    opened = {i for i, (_, s) in enumerate(windows) if s.at(when) is True}
    return through_windows(solar, elevation, azimuth, glazing, opened)


def _points(series):
    return [(t, v) for t, v in zip(series.times, series.values) if v is not None]


def _mean(values):
    return sum(abs(v) for v in values) / len(values) if values else float("nan")


def open_meteo_sun(path) -> Series:
    """Open-Meteo's hourly sun, each value the mean of the hour that ends at its time."""
    hourly = json.load(open(path, encoding="utf-8"))["hourly"]
    return Series([(datetime.fromisoformat(t).replace(tzinfo=timezone.utc) - timedelta(hours=1), v)
                   for t, v in zip(hourly["time"], hourly["shortwave_radiation"])])


def samples(history, room, sun, start, end, openings, shared=True, cover=None) -> list[Sample]:
    """The room every five minutes: its measured air and what acted on it; `cover`: its connected shutter."""
    temperature, _, thermostat, _ = room
    indoor, outdoor = numbers(history, temperature), numbers(history, STATION["temperature"])
    power = attribute(history, thermostat, "power_percent", 0.01)
    position = attribute(history, cover, "current_position", 0.01) if cover and cover in history else None
    house = [(attribute(history, entity, "power_percent", 0.01), watts) for entity, watts, _ in HOUSE_HEATERS] if shared else []
    windows = [(o, contacts(history, o.entity_id)) for o in openings]
    oriented = any(o.exposure is not None for o in openings)
    out, when = [], start
    while when <= end:
        te, local = outdoor.at(when), when.astimezone(ZONE)
        inputs = None if te is None else Inputs(
            outdoor=te, sun=sun.at(when) or 0.0, heating=power.at(when) or 0.0,
            windows=tuple(o.size for o, s in windows if s.at(when) is True), hour=local.hour + local.minute / 60,
            house_heat=sum((series.at(when) or 0.0) * watts for series, watts in house),
            shade=1.0 if position is None or position.at(when) is None else max(SHUT, position.at(when)),
            shutter=0.0 if position is None or position.at(when) is None
            else shutter_insulation(sum(o.size[0] for o in openings), 1 - position.at(when)),
            facade=_facade(sun.at(when) or 0.0, when, windows) if oriented else None)
        out.append(Sample(when, indoor.at(when), inputs))
        when += DT
    return out


def old_errors(history, room, split, start, end):
    """The 2.1 twin, fitted on the days before `split`: its errors at one and three hours, by half hour."""
    temperature, humidity, thermostat, names = room
    power = attribute(history, thermostat, "power_percent")
    heating = [(t, v is not None and v > 0) for t, v in zip(power.times, power.values)]
    windows = {o.entity_id: list(zip(contacts(history, o.entity_id).times, contacts(history, o.entity_id).values))
               for o in _openings(names)}
    rows = old_twin.samples(start, end, _points(numbers(history, temperature)), _points(numbers(history, humidity)),
                            _points(numbers(history, STATION["temperature"])), _points(numbers(history, STATION["humidity"])),
                            _points(numbers(history, STATION["sun"])), windows, heating)
    model = old_twin.fit([r for r in rows if datetime.fromisoformat(r[0]) < split])
    masses = dict(zip((r[0] for r in rows), old_twin._masses(rows)))
    index = {r[0]: r for r in rows}
    hour, three, opened = [], [], []
    for r in rows:
        when = datetime.fromisoformat(r[0])
        if when < split:
            continue
        ti, hi, mass, cur = r[1], r[2], masses[r[0]], r
        for k in range(1, 7):
            before = ti
            ti, hi = old_twin.step(model, ti, hi, cur[3], cur[4], cur[5], cur[6], cur[7], 0, None, mass)
            mass = old_twin.mass_after(mass, before)
            cur = index.get((when + k * old_twin.STEP).isoformat())
            if cur is None:
                break
            if k == 2:
                hour.append(ti - cur[1])
                if r[6] > 0 or index.get((when + old_twin.STEP).isoformat(), r)[6] > 0:
                    opened.append(ti - cur[1])
            if k == 6:
                three.append(ti - cur[1])
    return hour, three, opened


def check(path, learned_days=7.0, sun_path=None, declared=True):
    history = load(path)
    sun = open_meteo_sun(sun_path) if sun_path else numbers(history, STATION["sun"])
    # From the hour after the latest first record: every series is known from there on.
    start = max(datetime.fromisoformat(s[0]["last_changed"]) for s in history.values())
    start = start.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    end = max(datetime.fromisoformat(s[-1]["last_changed"]) for s in history.values())
    split = start + timedelta(days=learned_days)
    print(f"Ajusté du {start:%d/%m %H:%M} au {split:%d/%m %H:%M} UTC, testé jusqu'au {end:%d/%m %H:%M}"
          f" ; soleil {'Open-Meteo' if sun_path else 'de la station'} ; {'avec' if declared else 'sans'} déclarations\n")
    print(f"{'Pièce':11} | {'1 h : physique':>14} {'2.1':>5} {'immobile':>8} | {'3 h : physique':>14} {'2.1':>5} {'immobile':>8}"
          f" | {'gain':>5} | fenêtre ouverte, 1 h")
    for name, room in HOUSE.items():
        known = room_of(name, declared)
        data = samples(history, room, sun, start, end, known.openings, shared=declared)
        base = ordinary(known)
        if declared:
            base = replace(base, share=HOME_SHARE if any(where == name for *_, where in HOUSE_HEATERS) else AWAY_SHARE)
        p = fit(base, data, until=split, held=frozenset({"heat"} if known.heating_power else ()))
        s = score(p, data, since=split)
        old_hour, old_three, old_opened = old_errors(history, room, split, start, end)
        gain = 1 - s.three / s.still_three
        window = (f"{s.opened_cases} cas : physique {s.opened:.2f}° (biais {s.opened_bias:+.2f}), 2.1 {_mean(old_opened):.2f}°"
                  f" ({sum(old_opened) / len(old_opened) if old_opened else float('nan'):+.2f})" if s.opened_cases else "aucun cas")
        print(f"{name:11} | {s.hour:>13.2f}° {_mean(old_hour):>4.2f}° {s.still_hour:>7.2f}° | {s.three:>13.2f}° {_mean(old_three):>4.2f}°"
              f" {s.still_three:>7.2f}° | {gain:>4.0%} | {window}")
        print(f"{'':11}   ajusté : constante {time_constant(p):.0f} h, pertes {p.h_env:.0f} W/K, murs {p.cm / 1e6:.1f} MJ/K,"
              f" chauffage {p.heat:.0f} W, fenêtre ×{p.window:.2f}, soleil {p.sun:.2f} m², apports {p.gains:.0f} W"
              f" (rythme {p.rhythm_cos:+.0f}/{p.rhythm_sin:+.0f}), part du poêle {min(1.0, max(0.0, p.share)):.0%}")


if __name__ == "__main__":
    check(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 7.0, sys.argv[3] if len(sys.argv) > 3 else None,
          declared="--sans-declarations" not in sys.argv)
