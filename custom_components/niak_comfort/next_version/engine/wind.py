"""Wind against the openings: which side the wind hits, where the air goes through, what to open."""
import math

EXPOSURES = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SO": 225, "O": 270, "NO": 315}
WINDWARD_ANGLE = 60      # wind coming from within 60° of the facade's direction
DRIVEN_RAIN_GUST = 25    # km/h: from there, rain is pushed under a roof overhang
GUSTY = 40               # km/h: from there, an opening facing the wind slams doors and blows papers away


def gap(a: float, b: float) -> float:
    return abs(((a - b + 540) % 360) - 180)


def side(exposure: str | None, bearing: float | None) -> str | None:
    """Bearing is where the wind comes from (meteorological convention)."""
    if exposure not in EXPOSURES or bearing is None:
        return None
    facing = EXPOSURES[exposure]
    if gap(bearing, facing) < WINDWARD_ANGLE:
        return "windward"
    if gap(bearing, (facing + 180) % 360) < WINDWARD_ANGLE:
        return "leeward"
    return "side"


def crossing(openings: list[dict]) -> str | None:
    """How the air crosses the room through the open openings."""
    opened = [o for o in openings if o.get("open")]
    if not opened:
        return None
    sides = {o.get("wind_side") for o in opened}
    if {"windward", "leeward"} <= sides:
        return "wind"
    exposures = {o.get("exposure") for o in opened if o.get("exposure")}
    if any(gap(EXPOSURES[a], EXPOSURES[b]) >= 135 for a in exposures for b in exposures):
        return "opposite"
    return "two_sides" if len(exposures) > 1 else "one_side"


# How much air an opening lets through, before its size is known: a French window more than a window.
SIZE = {"french": 1.0, "door": 0.8, "window": 0.7, "skylight": 0.5}
# The way the air goes through: into the wind and out of it, two opposite facades, a corner, one facade.
PATH = {"wind": 4.0, "opposite": 3.0, "two_sides": 2.0, "one_side": 1.0}
# Airings of one combination needed before its learned speed replaces the rule.
MIN_FLOWS = 3
# One more opening must renew the air this much faster to be worth asking for.
WORTH = 1.3


def key(entities) -> str:
    return "|".join(sorted(entities))


def score(combo: list[dict]) -> float:
    """What the rule expects of a set of openings: the way the air crosses, then how wide they are."""
    path = crossing([dict(o, open=True) for o in combo]) or "one_side"
    if len(combo) > 1 and path == "one_side" and not all(o.get("exposure") for o in combo):
        path = "two_sides"  # facades not given: two openings still do better than one
    return PATH[path] * (1 + sum(SIZE.get(o.get("kind"), 0.7) for o in combo) / 4)


def plan(openings: list[dict], flows: dict | None = None) -> dict | None:
    """The best openings for the air to cross the room, and what to add to those already open.

    `openings` are the assessment's details (`avoid` says why one should stay shut: rain, gust, sun);
    `flows` the speeds learned per combination (engine/airflow.py), which outweigh the rule once known.
    Only one opening is added to what is open: the person already chose, the plan completes it.
    """
    usable = [o for o in openings if o.get("open") is not None]
    opened = [o for o in usable if o["open"] and not o.get("avoid")]
    free = [o for o in usable if not o["open"] and not o.get("avoid")]
    if opened:
        combos = [opened] + [opened + [o] for o in free]
    else:
        combos = [[o] for o in free] + [[a, b] for i, a in enumerate(free) for b in free[i + 1:]]
    if not combos:
        return None
    flows = flows or {}
    name = lambda c: key(o["entity_id"] for o in c)
    learned = {name(c): flows[name(c)] for c in combos if (flows.get(name(c)) or {}).get("count", 0) >= MIN_FLOWS}
    # The rule's scores are put on the scale of the learned speeds (their geometric mean), so that both compare.
    ratios = [math.log(learned[name(c)]["rate"] / score(c)) for c in combos if name(c) in learned and learned[name(c)]["rate"] > 0]
    scale = math.exp(sum(ratios) / len(ratios)) if ratios else 1.0
    speed = lambda c: learned[name(c)]["rate"] if name(c) in learned else score(c) * scale
    order = {o["entity_id"]: i for i, o in enumerate(openings)}
    best = max(combos, key=lambda c: (speed(c) / WORTH ** len(c), [-order[o["entity_id"]] for o in c]))
    base = opened or max(([o] for o in free), key=speed)
    into = [o for o in best if o.get("wind_side") == "windward"]
    add = sorted((o for o in best if not o["open"]), key=lambda o: (o.get("wind_side") != "windward", order[o["entity_id"]]))
    known = name(best) in learned and name(base) in learned and name(best) != name(base)
    return {"open": [o["entity_id"] for o in add], "keep": [o["entity_id"] for o in best if o["open"]],
            "path": crossing([dict(o, open=True) for o in best]) or "one_side",
            "into": into[0]["exposure"] if into else None,
            # How much faster than what is open, or than the best single opening: said once both are learned.
            "faster": round(speed(best) / speed(base), 1) if known and speed(base) > 0 else None,
            "learned": learned[name(best)]["count"] if name(best) in learned else 0,
            "avoid": [{"entity_id": o["entity_id"], "why": o["avoid"]} for o in usable if o.get("avoid") and not o["open"]]}


def open_first(openings: list[dict], flows: dict | None = None) -> list[str]:
    """The closed openings to open first: the best crossing, the one into the wind first."""
    chosen = plan([o for o in openings if not o.get("open") and not o.get("flags")], flows)
    return chosen["open"] if chosen else []
