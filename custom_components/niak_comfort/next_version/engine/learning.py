"""What airing really does in each room, learned from its past openings.

The theoretical promise (« the outdoor air, warmed inside, would bring the room to 52 % ») assumes the
whole air is replaced. Real rooms never get there: a tilted window renews little air, walls and fabrics
give their water back, a bathroom next door keeps feeding moisture. So each room learns, from its own
history, three numbers:

- `tau`: minutes for the indoor water content to cover about two thirds of its way toward its floor;
- `residual`: g/m³ the room keeps above the outdoor air even after a long airing (its moisture sources);
- `rebound`: share of the water removed that comes back within 45 minutes once the window is closed.

Each room also learns what it does with its windows shut, from the peaks of water it sheds by itself (a shower
next door, a night's sleep): `settle`, minutes for such a surplus to lose about two thirds of its way back to
`usual`, the g/m³ the room keeps above the outdoor air on an ordinary day. An airing is then judged against
waiting, not against now.

Each opening is summarised by a few sums (a least-squares fit of the 5-minute change of the indoor water
content against its gap to the outdoor air), so episodes can be stored, merged and refitted cheaply.
"""
from bisect import bisect_right
from datetime import datetime, timedelta
import math

STEP = timedelta(minutes=5)
REBOUND_AFTER = timedelta(minutes=45)
MIN_OPENING = timedelta(minutes=10)
# Only the first hour of an opening teaches the drying speed: the longest airing ever asked. A window forgotten
# all day, near its floor for hours, would otherwise outweigh every real airing.
FIT_SPAN = timedelta(hours=1)
BLIP = timedelta(minutes=10)
# Before any opening is learned: a modest, ordinary room rather than a full air replacement.
DEFAULT = {"tau": 45.0, "residual": 1.0, "rebound": 0.4}
# Open-window time weighing as much as the default: two hours of 5-minute steps move the model halfway.
PRIOR_STEPS = 24
# Closings weighing as much as the default rebound.
PRIOR_CLOSINGS = 2
# A lasting gain under this (humidity points) is not worth asking to open.
MIN_GAIN = 5.0
# g/m³ between the station and the forecast beyond which the forecast is not trusted for timing.
MAX_FORECAST_BIAS = 2.5
KEEP_DAYS = 90
KEEP_EPISODES = 60
# A peak of water, windows shut: risen this much (g/m³) within the hour, then followed two hours shut.
PEAK_RISE = 1.5
SETTLE_AFTER = timedelta(hours=2)
# Peaks known before the room's own shedding is trusted: until then, an airing is judged against now, as before.
SETTLE_PEAKS = 3
KEEP_PEAKS = 30
# Five more minutes open bringing less than this (humidity points): the airing stops there.
KNEE = 0.5


def absolute(temperature: float, relative: float) -> float:
    """Water content of the air in g/m³ (Magnus formula)."""
    return 6.112 * math.exp(17.67 * temperature / (temperature + 243.5)) * relative * 2.1674 / (273.15 + temperature)


class _Series:
    """A sample-and-hold series: the value at a time is the last one reported before it."""
    def __init__(self, points):
        points = sorted(p for p in points if p[1] is not None and math.isfinite(p[1]))
        self.times = [t for t, _ in points]
        self.values = [v for _, v in points]

    def at(self, when):
        i = bisect_right(self.times, when)
        return self.values[i - 1] if i else None


def _intervals(contacts):
    """Periods when at least one opening of the room was open. `contacts`: {entity: [(time, bool|None)]}.

    Each period says whether it ended on a real closing (False when a contact stopped answering).
    """
    changes = []
    for entity, points in contacts.items():
        points = sorted(points)
        for i, (when, value) in enumerate(points):
            # Radio contacts drop out for a minute and come back: a short silence is not a closing.
            if value is None and i + 1 < len(points) and points[i + 1][0] - when < BLIP:
                continue
            changes.append((when, entity, value))
    changes.sort()
    state, intervals, start = {}, [], None
    for when, entity, value in changes:
        state[entity] = value
        if value is None:
            if start is not None:
                intervals.append((start, when, False))
                start = None
            continue
        if any(v is None for v in state.values()):
            continue
        opened = any(state.values())
        if opened and start is None:
            start = when
        elif not opened and start is not None:
            intervals.append((start, when, True))
            start = None
    return intervals


def episodes(contacts, indoor_temperature, indoor_humidity, outdoor_temperature, outdoor_humidity):
    """One summary per opening of at least ten minutes, from raw (time, value) points.

    Water contents come from both temperature and humidity, so the cooling of an aired room is not
    taken for drying.
    """
    ti, hi, te, he = (_Series(p) for p in (indoor_temperature, indoor_humidity, outdoor_temperature, outdoor_humidity))

    def water(when):
        a, b, c, d = ti.at(when), hi.at(when), te.at(when), he.at(when)
        if None in (a, b, c, d) or not (0 < b <= 100 and 0 < d <= 100):
            return None
        return absolute(a, b), absolute(c, d)

    spans = _intervals(contacts)
    result = []
    for index, (start, end, closed) in enumerate(spans):
        if end - start < MIN_OPENING:
            continue
        n = sx = sy = sxx = sxy = 0.0
        when, before = start, water(start)
        while when + STEP <= min(end, start + FIT_SPAN):
            after = water(when + STEP)
            if before and after:
                gap, change = before[0] - before[1], after[0] - before[0]
                n, sx, sy, sxx, sxy = n + 1, sx + gap, sy + change, sxx + gap * gap, sxy + gap * change
            when, before = when + STEP, after
        if n < 2:
            continue
        rebound = None
        first, last, later = water(start), water(end), water(end + REBOUND_AFTER)
        reopened = index + 1 < len(spans) and spans[index + 1][0] < end + REBOUND_AFTER
        if closed and not reopened and first and last and later and first[0] - last[0] >= 0.5:
            rebound = min(1.0, max(0.0, (later[0] - last[0]) / (first[0] - last[0])))
        result.append({"start": start.isoformat(), "minutes": round((end - start).total_seconds() / 60),
                       "n": int(n), "sx": round(sx, 4), "sy": round(sy, 4), "sxx": round(sxx, 4), "sxy": round(sxy, 4),
                       "rebound": None if rebound is None else round(rebound, 3)})
    return result


def merge(stored, fresh, now):
    """Stored episodes plus the fresh ones (same start: the fresh summary wins), recent ones only."""
    by_start = {e["start"]: e for e in stored or [] if isinstance(e, dict) and isinstance(e.get("start"), str)}
    by_start.update({e["start"]: e for e in fresh})
    limit = now - timedelta(days=KEEP_DAYS)
    kept = []
    for start, episode in by_start.items():
        try:
            if datetime.fromisoformat(start) >= limit:
                kept.append(episode)
        except ValueError:
            continue
    return sorted(kept, key=lambda e: e["start"])[-KEEP_EPISODES:]


def fit(records):
    """The room's model: the learned numbers, pulled toward the default while few openings are known."""
    records = [e for e in records or [] if all(isinstance(e.get(k), (int, float)) for k in ("n", "sx", "sy", "sxx", "sxy"))]
    count, n = len(records), sum(e["n"] for e in records)
    tau, residual = DEFAULT["tau"], DEFAULT["residual"]
    if count and n >= 6:
        sx, sy, sxx, sxy = (sum(e[k] for e in records) for k in ("sx", "sy", "sxx", "sxy"))
        spread = sxx - sx * sx / n
        if spread > 0.02 * n:
            # Water lost per 5 minutes for each g/m³ of gap; none at all means the window barely renews the air.
            k = min(1.0, max(5 / 600, -(sxy - sx * sy / n) / spread))
            tau = 5 / k
            residual = min(5.0, max(-1.0, (sy + k * sx) / n / k))
    weight = n / (n + PRIOR_STEPS)
    rebounds = sorted(e["rebound"] for e in records if isinstance(e.get("rebound"), (int, float)))
    rebound = rebounds[len(rebounds) // 2] if rebounds else DEFAULT["rebound"]
    rebound_weight = len(rebounds) / (len(rebounds) + PRIOR_CLOSINGS)
    return {"tau": round(math.exp(weight * math.log(tau) + (1 - weight) * math.log(DEFAULT["tau"])), 1),
            "residual": round(weight * residual + (1 - weight) * DEFAULT["residual"], 2),
            "rebound": round(min(0.8, rebound_weight * rebound + (1 - rebound_weight) * DEFAULT["rebound"]), 2),
            "openings": count}


def peaks(contacts, indoor_temperature, indoor_humidity, outdoor_temperature, outdoor_humidity):
    """The peaks of water the room shed by itself, windows shut: what was left of each surplus two hours later.

    The surplus is measured above the room's usual gap to the outdoor air, the median of the previous day shut."""
    ti, hi, te, he = (_Series(p) for p in (indoor_temperature, indoor_humidity, outdoor_temperature, outdoor_humidity))
    spans = _intervals(contacts)
    if not ti.times or not hi.times:
        return []

    def gap(when):
        a, b, c, d = ti.at(when), hi.at(when), te.at(when), he.at(when)
        if None in (a, b, c, d) or not (0 < b <= 100 and 0 < d <= 100):
            return None
        return absolute(a, b) - absolute(c, d)

    def shut(when, until=None):
        return not any(start < (until or when) and end > when for start, end, _ in spans)

    quarter = timedelta(minutes=15)
    start = hi.times[0].replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    series, when = [], start
    while when <= hi.times[-1]:
        series.append((when, gap(when), shut(when)))
        when += quarter
    found, i, day, ahead = [], 4, 96, int(SETTLE_AFTER / quarter)
    while i < len(series) - ahead:
        when, value, closed = series[i]
        before = series[i - 4][1]
        window = [g for _, g, c in series[max(0, i - day):i] if c and g is not None]
        if (value is None or before is None or not closed or len(window) < day // 2 or value - before < PEAK_RISE
                or any(g is not None and g > value for _, g, _ in series[i + 1:i + 3])
                or not shut(when, when + SETTLE_AFTER) or series[i + ahead][1] is None):
            i += 1
            continue
        usual = sorted(window)[len(window) // 2]
        surplus = value - usual
        if surplus >= 1.0:
            found.append({"start": when.isoformat(), "usual": round(usual, 2), "surplus": round(surplus, 2),
                          "left": round((series[i + ahead][1] - usual) / surplus, 3)})
        i += ahead
    return found


def settling(records):
    """How the room sheds a surplus of water by itself: {"settle" minutes, "usual" g/m³, "peaks"}; no time constant
    until SETTLE_PEAKS peaks are known. The median peak, so one shower with the door open does not decide."""
    records = [e for e in records or [] if all(isinstance(e.get(k), (int, float)) for k in ("usual", "left"))]
    if len(records) < SETTLE_PEAKS:
        return {"settle": None, "usual": None, "peaks": len(records)}
    lefts = sorted(min(0.95, max(0.05, e["left"])) for e in records)
    usuals = sorted(e["usual"] for e in records)
    return {"settle": round(-SETTLE_AFTER.total_seconds() / 60 / math.log(lefts[len(lefts) // 2]), 1),
            "usual": round(usuals[len(usuals) // 2], 2), "peaks": len(records)}


def minutes(model):
    """How long to air: about one time constant, between 10 minutes and one hour, by steps of five."""
    return int(min(60, max(10, 5 * round(model["tau"] / 5))))


def _gain(model, indoor_temperature, indoor_water, outdoor_water, duration):
    floor = outdoor_water + model["residual"]
    removed = max(0.0, indoor_water - floor) * (1 - math.exp(-duration / model["tau"]))
    return removed * (1 - model["rebound"]) / absolute(indoor_temperature, 100) * 100


def alone(model, indoor_temperature, indoor_water, outdoor_water, duration):
    """Humidity points the room loses by itself, windows shut, in `duration` minutes; 0 until it is learned."""
    settle, usual = model.get("settle"), model.get("usual")
    if not isinstance(settle, (int, float)) or not isinstance(usual, (int, float)) or settle <= 0:
        return 0.0
    surplus = max(0.0, indoor_water - outdoor_water - usual)
    return surplus * (1 - math.exp(-duration / settle)) / absolute(indoor_temperature, 100) * 100


def airing_minutes(model, indoor_temperature, indoor_water, outdoor_water, target=None):
    """How long to air: until the room is back under `target` (% humidity), or until five more minutes would bring
    less than KNEE points; between 10 minutes and one hour, by steps of five."""
    now = indoor_water / absolute(indoor_temperature, 100) * 100
    for length in range(10, 60, 5):
        gain = _gain(model, indoor_temperature, indoor_water, outdoor_water, length)
        if target is not None and now - gain <= target:
            return length
        if _gain(model, indoor_temperature, indoor_water, outdoor_water, length + 5) - gain < KNEE:
            return length
    return 60


def outcome(model, indoor_temperature, indoor_water, outdoor_water, duration=None, target=None):
    """Humidity after airing for `duration` minutes (chosen by `airing_minutes` when not given), once the room has given
    part of its water back; `alone`: what waiting as long would bring, `net`: what the airing adds to it."""
    duration = duration or airing_minutes(model, indoor_temperature, indoor_water, outdoor_water, target)
    now = indoor_water / absolute(indoor_temperature, 100) * 100
    gain = _gain(model, indoor_temperature, indoor_water, outdoor_water, duration)
    shed = min(gain, alone(model, indoor_temperature, indoor_water, outdoor_water, duration))
    return {"minutes": duration, "now": round(now, 1), "after": round(now - gain, 1), "gain": round(gain, 1),
            "alone": round(now - shed, 1), "net": round(gain - shed, 1)}


# Hours an airing can be asked for, local time, by season (0 winter … 1 summer, engine/assessment.py seasonal):
# the summer evening until bedtime, the in-between seasons by day, the winter in its least cold hours.
AWAKE = {"summer": (7, 23), "between": (8, 21), "winter": (10, 18)}


def awake(name=None):
    """The (from, until) local hours an airing can be asked for in this season: Hestia Weather's, or the season sensor
    chosen in « Extérieur ». Spring, autumn, or no season known: the in-between hours, nothing guessed."""
    return AWAKE[name] if name in ("summer", "winter") else AWAKE["between"]


def best_moment(model, indoor_temperature, indoor_water, outdoor_water, hours, now, horizon=12, zone=None, season=None, duration=None):
    """A later hour that would dry clearly better than now, from the Hestia Weather forecast.

    The forecast is set on the local station: its error at the current hour is carried over. Only waking hours are
    proposed (`awake`, for the `season` name, in the home's time zone `zone`): « Aérez vers 3 h » asks for nothing anyone would do.
    """
    forecast = []
    for hour in hours or []:
        try:
            when = datetime.fromisoformat(hour["time"])
            water = absolute(float(hour["temperature"]), float(hour["humidity"]))
        except (KeyError, TypeError, ValueError):
            continue
        if when.tzinfo is None:
            continue
        rainy = isinstance(hour.get("precipitation"), (int, float)) and hour["precipitation"] >= 0.2
        forecast.append((when, None if rainy else water))
    if not forecast:
        return None
    current = min(forecast, key=lambda f: abs((f[0] - now).total_seconds()))
    if current[1] is None or abs((current[0] - now).total_seconds()) > 5400:
        return None
    bias = outdoor_water - current[1]
    if abs(bias) > MAX_FORECAST_BIAS:
        # The forecast does not describe this place well enough right now to promise a better hour.
        return None
    present = outcome(model, indoor_temperature, indoor_water, outdoor_water, duration)["gain"]
    best = None
    for when, water in forecast:
        if water is None or not now + timedelta(hours=1) <= when <= now + timedelta(hours=horizon):
            continue
        start, until = awake(season)
        if not start <= (when.astimezone(zone) if zone else when).hour < until:
            continue
        later = outcome(model, indoor_temperature, indoor_water, max(0.5, water + bias), duration)
        if later["gain"] >= MIN_GAIN and later["gain"] >= present + 4 and (best is None or later["gain"] > best["gain"]):
            best = {**later, "time": when.isoformat()}
    return best
