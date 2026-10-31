"""The 2.1 engine and the 3.0 advisor on the same days of the real house, every half hour: where they disagree.

The 2.1 engine is run as it runs at home (engine/assessment.py, its banner reduced to the gesture); the 3.0 advisor with
the twins of jumeaux.json and, for the coming hours, what really came (a perfect forecast: what the advisor would say
with a forecast that never errs). The report groups the disagreements into episodes, to be read together.

    cd custom_components/hestia_comfort
    ../../../niak-comfort/banc/.venv/bin/python -m advisor.bench.compare history.json open-meteo.json co2.json pm25.json jumeaux.json report.md
"""
from collections import Counter
from datetime import datetime, timedelta
import json
import sys
from zoneinfo import ZoneInfo

from dataclasses import replace

from ..decide import Now, Thermostat, Twins, decide, for_season
from ..physics.fit import HOUR
from ..physics.sunlight import sun_position as sun_at, through_windows
from ..proof import level, window_reinforced
from ..physics.air import AirParams, ParticleParams
from ..physics.thermal import STEP, Params, step
from ..physics.water import WaterParams, absolute
from ..words import phrase
from . import twin_check as T
from .air_check import CO2, CO2_FLOOR, PM25, PM25_CEILING
from .history import attribute, contacts, load, numbers

try:
    from ...engine.assessment import Settings, Sun, assess
    from ...engine.sources import Reading
    from ...engine.twin import sun_position
except ImportError:  # run from custom_components/hestia_comfort, where the engine is a top-level package
    from engine.assessment import Settings, Sun, assess
    from engine.sources import Reading
    from engine.twin import sun_position

ZONE = ZoneInfo("Europe/Paris")
WAKE = 7
LOCATION = (43.4, 5.5)
# The ranges Frank set in Confort (its diagnostics, 31 October): °C, winter's upper limit, summer's.
RANGES = {"Salon": 19, "Chambre P": 18, "Chambre A": 19, "Chambre AL": 19, "Chambre M": 19}
MAXIMUM, SUMMER = 24, 26


def old_title(action: str) -> str:
    """The 2.1 banner, reduced to its gesture: the banner only ever carries a gesture or « Rien à faire »."""
    return {"fermer": "Refermez", "ouvrir": "Aérez"}.get(action, "Rien à faire")


def gesture_of(title: str) -> str:
    return "close" if title.startswith("Refermez") else "open" if title.startswith(("Aérez", "Ouvrez")) else "nothing"


def _twins(entry, windows, thermostat):
    return Twins(heat=Params(**entry["heat"]), windows=windows,
                 water=WaterParams(**entry["water"]) if "water" in entry else None, water_flow=tuple(entry.get("water_flow", (1, 1))),
                 air=AirParams(**entry["air"]) if "air" in entry else None, air_flow=tuple(entry.get("air_flow", (1, 1))),
                 particles=ParticleParams(**entry["particles"]) if "particles" in entry else None,
                 particles_flow=tuple(entry.get("particles_flow", (1, 1))), thermostat=thermostat)


def compare(history_path, sun_path, co2_path, pm_path, learned_path, report_path):
    history = load(history_path, co2_path, pm_path)
    sun = T.open_meteo_sun(sun_path)
    learned = json.load(open(learned_path, encoding="utf-8"))["rooms"]
    start = max(datetime.fromisoformat(s[0]["last_changed"]) for s in history.values())
    start = start.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    end = max(datetime.fromisoformat(s[-1]["last_changed"]) for s in history.values()) - timedelta(hours=10)
    ot, oh = numbers(history, T.STATION["temperature"]), numbers(history, T.STATION["humidity"])
    lines = [f"# Rejeu : moteur 2.1 et moteur 3.0, du {start:%d/%m} au {end:%d/%m}\n",
             "Toutes les demi-heures, les deux moteurs sur les mêmes mesures. Le 3.0 voit la météo qui est vraiment venue "
             "(prévision parfaite) et ses jumeaux appris sur ces mêmes jours : c'est son meilleur cas, pas encore la vie réelle.\n"]
    for name, room in T.HOUSE.items():
        known = T.room_of(name)
        samples = T.samples(history, room, sun, start, end + timedelta(hours=10), known.openings, cover=T.COVERS.get(name))
        humidity = numbers(history, room[1])
        co2 = numbers(history, CO2[name]) if name in CO2 else None
        pm = numbers(history, PM25[name]) if name in PM25 else None
        target = attribute(history, room[2], "temperature")
        modes = [(datetime.fromisoformat(e["last_changed"]), e["state"]) for e in history.get(room[2], [])]
        entry, windows = learned[name], tuple(o.size for o in known.openings)
        heat = Params(**entry["heat"])
        contact = {o.entity_id: contacts(history, o.entity_id) for o in known.openings}
        comfort = for_season(RANGES[name], MAXIMUM, SUMMER)
        glazing = [(o.glazing, o.exposure, o.sheltered) for o in known.openings if o.exposure is not None]
        everything = range(len(glazing))
        seen = entry.get("gestures") or {}
        trail = {}
        tally, episodes, current, walls, previous_old, previous_new = Counter(), [], None, None, None, None
        for i, s in enumerate(samples):
            if s.inputs is None or s.measured is None:
                walls = None
                continue
            walls = s.measured if walls is None else walls
            trail[i] = walls
            if s.when.minute % 30 == 0 and s.when < end:
                local = s.when.astimezone(ZONE)
                night = local.hour >= 22 or local.hour < WAKE
                wake = local.replace(hour=WAKE, minute=0, second=0, microsecond=0) + (timedelta(days=1) if local.hour >= 22 else timedelta())
                steps = max(12, int((wake - local).total_seconds() // STEP)) if night else 36
                coming = []
                for k in range(steps):
                    later = samples[i + k] if i + k < len(samples) else None
                    if later is None or later.inputs is None:
                        break
                    te, he = ot.at(later.when), oh.at(later.when)
                    u = later.inputs
                    if glazing:
                        # The sun of each scenario's windows: all shut, all open (as the test Home Assistant gives it).
                        light, position = u.sun, sun_at(later.when, *T.LOCATION)
                        u = replace(u, facade_shut=through_windows(light, *position, glazing, ()),
                                    facade_all=through_windows(light, *position, glazing, everything))
                    coming.append((u, absolute(te, he) if te is not None and he is not None else None))
                hvac = next((v for t, v in reversed(modes) if t <= s.when), None)
                aim = target.at(s.when)
                twins = _twins(entry, windows, Thermostat(aim) if hvac == "heat" and aim is not None else None)
                c = co2.at(s.when) if co2 else None
                p = pm.at(s.when) if pm else None
                # The trend the twin missed over the last hour (decide.Now.missed).
                missed = None
                if i - HOUR in trail and all(samples[j].inputs is not None for j in range(i - HOUR, i)):
                    guess, mass = samples[i - HOUR].measured, trail[i - HOUR]
                    for j in range(i - HOUR, i):
                        guess, mass = step(heat, guess, mass, samples[j].inputs)
                    missed = s.measured - guess
                now = Now(air=s.measured, walls=walls, opened=s.inputs.windows, humidity=humidity.at(s.when),
                          co2=c if c is not None and c >= CO2_FLOOR else None, particles=p if p is not None and p <= PM25_CEILING else None,
                          night=night, missed=missed)
                # The proof: only the gestures seen before this moment count.
                stamp = s.when.isoformat()
                water = absolute(s.measured, now.humidity) if now.humidity is not None else None
                outside_water = coming[0][1] if coming else None
                measured = {"co2": now.co2 is not None, "particles": now.particles is not None}
                proof = {subject: level([(f, m) for w, f, m in seen.get(subject, ()) if w < stamp],
                                        window_reinforced(subject, s.measured, s.inputs.outdoor, water, outside_water,
                                                          measured.get(subject, True)))
                         for subject in ("heat", "humidity", "co2", "particles")}
                decision = decide(twins, now, coming, comfort, previous=previous_new, proof=proof)
                previous_new = decision.gesture
                words = phrase(decision, wake.hour if night else (local + timedelta(hours=3)).hour,
                               marks={"minimum": comfort.minimum, "maximum": comfort.maximum, "co2": 1000.0, "particles": 15.0})
                if words["try"]:
                    tally["à essayer"] += 1
                # The 2.1 engine, with the same measures.
                readings = {"indoor_temperature": Reading(s.measured, "valid", "t", stamp),
                            "outdoor_temperature": Reading(s.inputs.outdoor, "valid", "t", stamp)}
                if now.humidity is not None:
                    readings["indoor_humidity"] = Reading(now.humidity, "valid", "h", stamp)
                if oh.at(s.when) is not None:
                    readings["outdoor_humidity"] = Reading(oh.at(s.when), "valid", "h", stamp)
                if now.co2 is not None:
                    readings["co2"] = Reading(now.co2, "valid", "c", stamp)
                for entity, series in contact.items():
                    state = series.at(s.when)
                    if state is not None:
                        readings[f"window:{entity}"] = Reading(state, "valid", entity, stamp)
                elevation, azimuth = sun_position(s.when, *LOCATION)
                old = assess(readings, Settings(minimum=RANGES[name], maximum=MAXIMUM, humidity_high=60), previous_old, sun=Sun(elevation, azimuth), now=s.when,
                             context={"season_name": "autumn", "zone": ZONE})
                previous_old = old
                old_text, new_text = old_title(old.action), words["title"]
                agree = gesture_of(old_text) == gesture_of(new_text)
                tally["accord" if agree else "désaccord"] += 1
                if not agree:
                    key = (old_text, gesture_of(new_text))
                    if current and current["key"] == key and s.when - current["end"] <= timedelta(minutes=30):
                        current["end"] = s.when
                    else:
                        current = {"key": key, "start": s.when, "end": s.when, "old": f"{old_text} ({old.reason})",
                                   "new": f"{new_text} — {words['line']}" + (f" ({words['try']})" if words["try"] else ""),
                                   "why": words["why"],
                                   "at": f"{s.measured:.1f} °C dedans, {s.inputs.outdoor:.1f} °C dehors, "
                                         f"{len(s.inputs.windows)} fenêtre(s) ouverte(s)"
                                         + (f", humidité {now.humidity:.0f} %" if now.humidity is not None else "")
                                         + (f", CO₂ {now.co2:.0f} ppm" if now.co2 is not None else "")}
                        episodes.append(current)
            _, walls = step(heat, s.measured, walls, s.inputs)
        total = tally["accord"] + tally["désaccord"]
        lines.append(f"\n## {name} : {tally['accord']} accords sur {total} demi-heures ({tally['accord'] / total:.0%}), "
                     f"{len(episodes)} épisodes de désaccord, {tally['à essayer']} demi-heures avec « À essayer »\n")
        for e in sorted(episodes, key=lambda e: e["end"] - e["start"], reverse=True)[:8]:
            span = (e["end"] - e["start"]).total_seconds() / 3600 + 0.5
            lines.append(f"- **{e['start'].astimezone(ZONE):%d/%m %H:%M}**, {span:.1f} h — {e['at']}  \n"
                         f"  2.1 : {e['old']}  \n  3.0 : {e['new']}  \n  Pourquoi : {' · '.join(e['why'])}")
        print(f"{name} : {tally['accord']}/{total} accords, {len(episodes)} épisodes de désaccord, "
              f"{tally['à essayer']} « À essayer »", flush=True)
    open(report_path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    compare(*sys.argv[1:7])
