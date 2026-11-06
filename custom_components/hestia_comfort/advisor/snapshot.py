"""A decision kept as one file, replayed exactly, and its trace layer by layer (CAHIER-MOTEUR.md § 16 bis).

The snapshot holds everything the decision was made from — the twins, the room now, the coming hours, the preferences,
the safety rule, the proof — and nothing else: the advisor reads no clock and draws no chance, so replaying it gives the
same decision. Change one input or one weight in the file, replay it, and see what the advice would have been.
"""
from dataclasses import fields, is_dataclass, replace
import json

from .household import Habits
from .decide import (SIGNIFICANT, Comfort, Decision, Gesture, Now, Thermostat, Twins, Weights, candidates, decide,
                     main_subject, significant)
from .physics.air import AirParams, ParticleParams
from .physics.thermal import Inputs, Params
from .physics.water import WaterParams
from .words import phrase

FORMAT = 1


def _plain(value):
    if is_dataclass(value):
        return {f.name: _plain(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    if isinstance(value, frozenset):
        return sorted(value)
    return value


def _pairs(value):
    """(area, height) pairs back as tuples: the advisor compares them."""
    return tuple(tuple(v) for v in value or ())


def capture(twins: Twins, now: Now, coming, comfort: Comfort = Comfort(), weights: Weights = Weights(),
            previous: Gesture | None = None, forbidden=frozenset(), proof: dict | None = None, holidays: bool = False,
            habits: Habits = Habits(), *,
            reason: str | None = None, held: float | None = None, tried: Gesture | None = None, aired: float | None = None,
            end_hour: int, hour: float | None = None, language: str = "fr", room: str = "", when: str = "",
            version: str = "") -> dict:
    """The decision's inputs, as plain JSON."""
    return {"format": FORMAT, "version": version, "room": room, "when": when, "twins": _plain(twins), "now": _plain(now),
            "coming": [[_plain(u), water] for u, water in coming], "comfort": _plain(comfort), "weights": _plain(weights),
            "previous": _plain(previous), "forbidden": sorted(forbidden), "reason": reason, "proof": proof, "holidays": holidays,
            "habits": habits.setting(), "held": held, "tried": _plain(tried), "aired": aired,
            "end_hour": end_hour, "hour": hour, "language": language}


def restore(snap: dict) -> dict:
    """The arguments of `decide`, back from a snapshot."""
    t = snap["twins"]
    twins = Twins(heat=Params(**t["heat"]), windows=_pairs(t["windows"]),
                  water=WaterParams(**t["water"]) if t.get("water") else None, water_flow=tuple(t["water_flow"]),
                  air=AirParams(**t["air"]) if t.get("air") else None, air_flow=tuple(t["air_flow"]),
                  particles=ParticleParams(**t["particles"]) if t.get("particles") else None,
                  particles_flow=tuple(t["particles_flow"]),
                  voc=ParticleParams(**t["voc"]) if t.get("voc") else None, voc_flow=tuple(t.get("voc_flow", (1, 1))),
                  boost=t.get("boost", 0.0), purifier=t.get("purifier", 0.0),
                  thermostat=Thermostat(**t["thermostat"]) if t.get("thermostat") else None,
                  shutter_area=t.get("shutter_area", 0.0),
                  idle_thermostat=Thermostat(**t["idle_thermostat"]) if t.get("idle_thermostat") else None,
                  house_thermostat=Thermostat(**t["house_thermostat"]) if t.get("house_thermostat") else None,
                  house_power=t.get("house_power", 0.0), house_now=t.get("house_now", 0.0),
                  bearings=tuple(t.get("bearings", ())), cross=t.get("cross", 2.0))
    now = Now(**{**snap["now"], "opened": _pairs(snap["now"]["opened"])})
    coming = [(Inputs(**{**u, "windows": _pairs(u["windows"])}), water) for u, water in snap["coming"]]
    return {"twins": twins, "now": now, "coming": coming, "comfort": Comfort(**snap["comfort"]),
            "weights": Weights(**snap["weights"]), "previous": Gesture(**snap["previous"]) if snap.get("previous") else None,
            "forbidden": frozenset(snap["forbidden"]), "proof": snap.get("proof"), "holidays": snap.get("holidays", False),
            "habits": Habits.of(snap.get("habits")), "held": snap.get("held"),
            "tried": Gesture(**snap["tried"]) if snap.get("tried") else None, "aired": snap.get("aired")}


def replay(snap: dict, **changes) -> tuple[Decision, dict]:
    """The decision and its words, from a snapshot; `changes` replace arguments of `decide` (« Et si… ? »)."""
    args = {**restore(snap), **changes}
    decision = decide(**args)
    c = args["comfort"]
    marks = {"minimum": c.minimum, "maximum": c.maximum, "humidity": c.humidity, "co2": c.co2, "particles": c.particles,
             "voc": c.voc}
    return decision, phrase(decision, snap["end_hour"], snap.get("language", "fr"), hour=snap.get("hour"),
                            reason=snap.get("reason"), marks=marks)


def warmer(coming, degrees: float):
    """The same coming hours, the outside this many degrees warmer."""
    return [(replace(u, outdoor=u.outdoor + degrees), water) for u, water in coming]


# « Ce qui ferait changer d'avis » tries the outside warmer or colder by these steps (°C).
SHIFTS = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)


def turning_point(snap: dict, decision: Decision) -> dict | None:
    """The smallest change of the outside temperature that would turn the advice: {"outdoor": +1.5, "gesture": …}."""
    args = restore(snap)
    for shift in SHIFTS:
        for sign in (1, -1):
            other = decide(**{**args, "coming": warmer(args["coming"], sign * shift), "previous": None})
            if other.gesture != decision.gesture or other.passive != decision.passive:
                return {"outdoor": sign * shift, "gesture": _plain(other.gesture), "passive": _plain(other.passive),
                        "rule": other.rule}
    return None


def _round(value, digits=2):
    if isinstance(value, float):
        return round(value, digits)
    if isinstance(value, dict):
        return {k: _round(v, digits) for k, v in value.items()}
    if isinstance(value, list):
        return [_round(v, digits) for v in value]
    return value


def trace(snap: dict, decision: Decision, words: dict) -> dict:
    """The decision layer by layer (CAHIER-MOTEUR.md § 16 bis.1): in which layer an error lies."""
    args = restore(snap)
    first = args["coming"][0][0] if args["coming"] else None
    allowed = [g for g in candidates(args["now"], args["twins"], args["habits"], args["comfort"]) if g.kind not in args["forbidden"]]
    taken = [g for g in candidates(args["now"], args["twins"], args["habits"], args["comfort"]) if g.kind in args["forbidden"]]
    idle = decision.paths.get(Gesture("nothing"))
    scenarios = []
    for g, terms in decision.scenarios.items():
        path = decision.paths.get(g)
        scenarios.append({"geste": _plain(g), "cout": _round(terms),
                          "fin": _round({"air": path.air[-1] if path and path.air else None,
                                         "humidite": path.humidity[-1] if path and path.humidity else None,
                                         "co2": path.co2[-1] if path and path.co2 else None,
                                         "particules": path.particles[-1] if path and path.particles else None,
                                         "cov": path.voc[-1] if path and path.voc else None,
                                         "kwh": path.spent if path else None}),
                          "significatif": (significant(idle, path, args["comfort"], args["now"].night)
                                           if idle and path and g.kind != "nothing" else [])})
    chosen = decision.passive or decision.gesture
    return {
        "1_mesures": _round({**snap["now"], "dehors": first.outdoor if first else None,
                             "soleil": first.sun if first else None, "facade": first.facade if first else None}),
        "2_jumeau": _round(snap["twins"]),
        "3_gestes": {"envisages": [_plain(g) for g in allowed], "retires": [_plain(g) for g in taken],
                     "interdit": snap.get("reason")},
        "4_scenarios": sorted(scenarios, key=lambda s: s["cout"]["total"]),
        "5_regle": {"regle": decision.rule, "gain": round(decision.gain, 2), "sujet": main_subject(decision.scenarios, chosen),
                    "preuve": decision.level, "preuves": snap.get("proof"), "seuils": SIGNIFICANT},
        "6_changerait": turning_point(snap, decision) if decision.rule != "safety" else None,
        "7_phrase": {k: words.get(k) for k in ("title", "line", "try", "why")},
    }


def dump(snap: dict, path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False)


def load(path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
