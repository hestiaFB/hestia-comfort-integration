"""How fast each combination of openings renews the air, learned from the CO₂ it takes away.

While the same openings stay open, the CO₂ above the outdoor air falls about exponentially: its rate
(per hour) is the air change of that combination. The people inside keep breathing, so the rate is
underestimated alike for every combination, which is enough to compare them. Each airing is kept as a
small summary, so that a combination is known after a few of them (engine/wind.py, MIN_FLOWS).
"""
from bisect import bisect_right
from datetime import datetime, timedelta
import math

OUTDOOR_CO2 = 420.0      # ppm, the outdoor air
MIN_EXCESS = 150.0       # ppm above it at the start: below, the sensor's noise outweighs the fall
FLOOR_EXCESS = 20.0      # ppm: a fall stops being readable this close to the outdoor air
MIN_SPAN = timedelta(minutes=10)
WINDOW = timedelta(minutes=30)  # the first half hour: the fall flattens afterwards, the people weigh more
BLIP = timedelta(minutes=10)
KEEP_DAYS = 90
KEEP_FLOWS = 120


def _segments(contacts):
    """Periods during which the same openings stay open: [(start, end, frozenset of entities)]."""
    changes = []
    for entity, points in contacts.items():
        points = sorted(points)
        for i, (when, value) in enumerate(points):
            # A radio contact silent for a minute has not moved.
            if value is None and i + 1 < len(points) and points[i + 1][0] - when < BLIP:
                continue
            changes.append((when, entity, value))
    changes.sort()
    state, result, start, current = {}, [], None, None
    for when, entity, value in changes:
        state[entity] = value
        known = all(v is not None for v in state.values())
        opened = frozenset(e for e, v in state.items() if v) if known else None
        if opened == current:
            continue
        if current and start is not None:
            result.append((start, when, current))
        start, current = when, opened
    return result


def flows(contacts, co2):
    """One summary per stretch of at least ten minutes with the same openings open and a readable CO₂ fall."""
    points = sorted((t, v) for t, v in co2 if v is not None and math.isfinite(v))
    times = [t for t, _ in points]
    at = lambda when: points[i - 1] if (i := bisect_right(times, when)) else None
    result = []
    for start, end, combo in _segments(contacts):
        if end - start < MIN_SPAN:
            continue
        first, last = at(start), at(min(end, start + WINDOW))
        # The last value must have been reported during the airing, not held from before it.
        if not first or not last or last[0] <= start + timedelta(minutes=5):
            continue
        before, after = first[1] - OUTDOOR_CO2, max(last[1] - OUTDOOR_CO2, FLOOR_EXCESS)
        hours = (last[0] - start).total_seconds() / 3600
        if before < MIN_EXCESS or hours <= 0:
            continue
        rate = math.log(before / after) / hours
        if rate <= 0:
            continue  # the CO₂ rose: someone came in, the airing says nothing of the openings
        result.append({"start": start.isoformat(), "combo": sorted(combo), "minutes": round((end - start).total_seconds() / 60),
                       "co2": round(first[1]), "rate": round(rate, 3)})
    return result


def merge(stored, fresh, now):
    """Stored summaries plus the fresh ones (same start: the fresh one wins), recent ones only."""
    by_start = {f["start"]: f for f in stored or [] if isinstance(f, dict) and isinstance(f.get("start"), str)}
    by_start.update({f["start"]: f for f in fresh})
    limit = now - timedelta(days=KEEP_DAYS)
    kept = []
    for start, item in by_start.items():
        try:
            if datetime.fromisoformat(start) >= limit:
                kept.append(item)
        except ValueError:
            continue
    return sorted(kept, key=lambda f: f["start"])[-KEEP_FLOWS:]


def fit(items):
    """{"a|b": {"rate": median air change per hour, "count": airings}} per combination."""
    groups = {}
    for item in items or []:
        if isinstance(item, dict) and isinstance(item.get("combo"), list) and item["combo"] and isinstance(item.get("rate"), (int, float)):
            groups.setdefault("|".join(sorted(item["combo"])), []).append(item["rate"])
    result = {}
    for combo, rates in groups.items():
        rates.sort()
        middle = len(rates) // 2
        median = rates[middle] if len(rates) % 2 else (rates[middle - 1] + rates[middle]) / 2
        result[combo] = {"rate": round(median, 3), "count": len(rates)}
    return result
