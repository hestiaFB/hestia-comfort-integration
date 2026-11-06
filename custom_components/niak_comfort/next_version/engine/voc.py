"""VOC that call for air: steady enough to be worth an airing, not every passing peak.

A Sensirion VOC index (IKEA VINDSTYRKA and others) is relative: 100 is the home's own mean of the last 24 hours,
500 its ceiling. It moves a lot: cooking, a cleaning product, a candle, someone coming in. Compared moment by moment
with a threshold, it crosses it again and again and the advice comes and goes. So:

- the index is judged on its mean over the last MEAN_MINUTES, not on one reading;
- a margin: it calls for air above the threshold, and stops below the threshold minus MARGIN of it (like the CO₂);
- a delay: only once above for `delay` minutes (10 by default), except a strong peak (twice the threshold) at once;
- a pause after an airing: for `pause` minutes (45 by default) no new call, unless the index climbs well above what the
  airing left (by RISE of the threshold): while the pan is still on the stove, opening ten times does not help;
- judged against waiting: an index already falling by itself, windows shut, calls for nothing (`falling`);
- learned from the airings themselves: where opening has made the index climb at this time of day (the air outside
  carries VOC, a neighbour's wood fire in the evening), it no longer calls for air then (`slots`, `outdoor`);
- and while a window is open, an index climbing well above what it was at the opening says « close » (`rising`).
"""
from datetime import datetime, timedelta

MEAN_MINUTES = 10
MARGIN = 0.2
STRONG = 2.0
RISE = 1 / 3
DELAY_MINUTES = 10
PAUSE_MINUTES = 45
# Open this long at least, a window shut is an airing that starts the pause; shorter, someone went through.
AIRING = timedelta(minutes=2)
# Seconds the newest reading counts at least in the mean: one update of the room.
LATEST = 30
# Falling by itself: the mean of the last MEAN_MINUTES under the one before by this share of the threshold.
FALL = 0.15
# An opening that makes the index climb this much (share of the threshold) over its first minutes brings VOC in.
CLIMB = 0.25
# The first minutes of an opening that tell what the air outside brings; shorter openings teach nothing.
FIRST = timedelta(minutes=6)
# While open, the climb is watched this long: later, a meal cooked with the window open would be blamed on the outside.
WATCH = 2 * FIRST
SHORTEST = timedelta(minutes=4)
# Already climbing this much (share of the threshold) over the minutes before the opening: the source inside is still
# going, the climb that follows is not the outside's.
GOING = 0.15
# The times of day learned apart, by local hour: a neighbour's fire burns in the evening, not at noon.
SLOTS = (("night", 0, 7), ("morning", 7, 12), ("afternoon", 12, 19), ("evening", 19, 24))
# The last airings of a slot weighed, and how many of them must have made the index climb: the index jumps a lot,
# and a pan left on the stove makes an opening look bad; two airings out of three taught noon wrongly at home.
LAST, WORSE = 4, 3


def _since(value):
    try:
        return datetime.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def judge(value, threshold, now, *, mean=None, was_high=False, above_since=None, delay=DELAY_MINUTES,
          pause=PAUSE_MINUTES, aired_at=None, aired_after=None, falling=False, outdoor=False, opened_at_level=None,
          going=False, shut=None):
    """{"high", "above_since", "minutes", "mean", "paused", "falling", "outdoor", "rising"} for one reading of the index;
    `mean` is the recent mean. `falling`: the windows shut and the index going down by itself; `outdoor`: opening has
    made it climb at this time of day; `opened_at_level`: the index when the windows open now were opened, `going`: it
    was already climbing then (a source inside, the climb that follows is not the outside's). `shut`: no window open,
    told apart when an open window is no longer watched (after WATCH); by default, no `opened_at_level` means shut.
    Each flag is True only when it is what holds the call back."""
    level = mean if isinstance(mean, (int, float)) else value
    limit = threshold * (1 - MARGIN) if was_high else threshold
    above = level >= limit
    since = (_since(above_since) or now) if above and now else None
    minutes = (now - since).total_seconds() / 60 if since and now else 0.0
    strong = value >= threshold * STRONG
    # Without a clock (a single reading judged alone), no delay can be counted: judged at once.
    high = above and (now is None or was_high or strong or minutes >= delay)
    # Right after an airing, the source is often still there: no new call unless the index climbs well above, even while
    # it was already high or a strong peak: the airing just done is the answer to it.
    aired = _since(aired_at)
    paused = (high and aired is not None and now is not None
              and now - aired < timedelta(minutes=pause) and isinstance(aired_after, (int, float))
              and level < aired_after + threshold * RISE)
    held = high and not paused
    # Open: the index climbing well above what it was at the opening, steady then, the air outside brings VOC in. The
    # reading itself is watched here, twice the climb, the mean following: ten minutes of mean would say it too late.
    # Only an airing begun on a high index, for the VOC: one begun low and climbing is a meal cooked window open.
    rising = (above and not going and isinstance(opened_at_level, (int, float)) and opened_at_level >= threshold
              and level >= opened_at_level
              and (level >= opened_at_level + threshold * CLIMB or value >= opened_at_level + 2 * threshold * CLIMB))
    # Shut: what waiting already brings, or what opening has brought at this hour, is no reason to open.
    closed = shut if isinstance(shut, bool) else not isinstance(opened_at_level, (int, float))
    # Judged on its own, not only when the call would come: the clock it holds back must stay held back.
    falling = above and not paused and closed and falling is True
    outdoor = held and closed and not falling and outdoor is True
    # Falling, the clock starts again: should it stop falling while still above, the delay is waited anew.
    if falling and now:
        since, minutes = now, 0.0
    return {"high": held and not (rising or falling or outdoor), "above_since": since.isoformat() if since else None,
            "minutes": round(minutes), "mean": round(level), "paused": paused, "falling": falling, "outdoor": outdoor,
            "rising": rising}


def mean(points, now, minutes=MEAN_MINUTES):
    """The index's mean over the last `minutes`, each reading weighed by how long it stood; None without one.

    `points`: [(datetime, value)] in time order. A reading taken before the window counts from its start; the newest
    counts at least LATEST seconds, so that a reading just received is not left out."""
    start = now - timedelta(minutes=minutes)
    total = weight = 0.0
    for i, (when, value) in enumerate(points):
        until = points[i + 1][0] if i + 1 < len(points) else now
        span = (min(until, now) - max(when, start)).total_seconds()
        if i + 1 == len(points):
            span = max(span, LATEST)
        if span > 0:
            total += value * span
            weight += span
    return total / weight if weight else (points[-1][1] if points else None)


def is_falling(points, now, threshold, minutes=MEAN_MINUTES, was=False):
    """Is the index going down by itself: its mean over the last `minutes` under the one before by FALL of the threshold,
    and on its way under the threshold within as many minutes?

    Once said (`was`), it holds while the index does not climb back: a falling index flattens before it is down, and
    « it falls by itself » coming and going would bring « Aérez » back each time."""
    if not points or now - points[0][0] < timedelta(minutes=2 * minutes):
        return False
    recent, before = mean(points, now, minutes), mean([p for p in points if p[0] <= now - timedelta(minutes=minutes)],
                                                      now - timedelta(minutes=minutes), minutes)
    if recent is None or before is None:
        return False
    if was:
        return before - recent >= -threshold * FALL / 2
    # Going down, and fast enough to be under the threshold by the next ten minutes: a dip that stays high is no fall.
    return before - recent >= threshold * FALL and recent - (before - recent) < threshold


def is_going(points, now, threshold):
    """Was the index already climbing over the last minutes: a source inside still at work?"""
    earlier = [v for t, v in points if t <= now - timedelta(minutes=4)]
    return bool(points and earlier) and points[-1][1] - earlier[-1] >= threshold * GOING


def slot(hour):
    return next(name for name, start, until in SLOTS if start <= hour < until)


def airings(contacts, points, threshold, zone=None):
    """What each opening of the room did to the index in its first minutes, from the history.

    `contacts`: {entity: [(datetime, bool|None)]}, `points`: [(datetime, value)] in time order. Openings of several
    windows at once are one airing. [{"start", "slot", "before", "climb", "worse"}]; an airing that began while a source
    inside was still sending the index up is left out: its climb tells nothing of the air outside."""
    events = sorted((t, e, v) for e, rows in contacts.items() for t, v in rows if v is not None)
    opened, spans, start = set(), [], None
    for t, e, v in events:
        was = bool(opened)
        (opened.add if v else opened.discard)(e)
        if not was and opened:
            start = t
        elif was and not opened and start is not None:
            spans.append((start, t))
            start = None

    def at(t):
        value = None
        for when, x in points:
            if when > t:
                break
            value = x
        return value
    out = []
    for begin, end in spans:
        if end - begin < SHORTEST:
            continue
        before, earlier = at(begin), at(begin - timedelta(minutes=4))
        seen = [x for when, x in points if begin < when <= min(end, begin + FIRST)]
        if before is None or not seen or (earlier is not None and before - earlier >= threshold * GOING):
            continue
        climb = max(seen) - before
        local = begin.astimezone(zone) if zone else begin
        out.append({"start": begin.isoformat(), "slot": slot(local.hour), "before": round(before), "climb": round(climb),
                    "worse": climb >= threshold * CLIMB})
    return out


def outdoor_slots(records):
    """The times of day when opening has made the index climb: WORSE of the LAST airings of the slot at least."""
    out = []
    for name, _, _ in SLOTS:
        last = [r for r in records if r.get("slot") == name][-LAST:]
        if len(last) >= WORSE and sum(1 for r in last if r.get("worse")) >= WORSE:
            out.append(name)
    return out
