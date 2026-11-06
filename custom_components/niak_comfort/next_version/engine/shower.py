"""A shower going on now, in a room that has one in its « Équipements »: a fast rise of humidity.

Read from the samples the room received in this session, never guessed in a room without a shower. During the
episode the peak is expected: it calls for the usual drying gesture, never for a mould risk.
"""
from datetime import datetime

# Humidity points gained, in at most this many minutes, for a rise to be a shower.
RISE, WITHIN = 8, 20
# An episode lasts an hour from its start, or until the humidity is back near where it started.
LASTS, BACK = 60, 2


def episode(history, now, equipped):
    """{"since", "minutes", "base", "peak"} of the shower going on, or None."""
    if not equipped or not history or now is None:
        return None
    points = []
    for stamp, value in history:
        try:
            when = datetime.fromisoformat(stamp)
        except (TypeError, ValueError):
            continue
        if isinstance(value, (int, float)) and 0 <= (now - when).total_seconds() <= (LASTS + WITHIN) * 60:
            points.append((when, float(value)))
    for i, (start, base) in enumerate(points):
        for when, value in points[i + 1:]:
            if (when - start).total_seconds() > WITHIN * 60:
                break
            if value - base >= RISE:
                minutes = (now - start).total_seconds() / 60
                if minutes <= LASTS and points[-1][1] > base + BACK:
                    return {"since": start.isoformat(), "minutes": round(minutes), "base": round(base),
                            "peak": round(max(v for w, v in points if w >= start))}
                return None
    return None
