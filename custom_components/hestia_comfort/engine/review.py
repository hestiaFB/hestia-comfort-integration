"""The comfort review: months of hourly measures graded on the categories of EN 16798-1.

Each hour of a room falls in a category of the European standard on indoor environment, for its warmth, its
humidity and its air; it earns 100 points in category I (high expectation), 75 in II (normal), 50 in III
(moderate), none beyond. A theme's score is the mean of its hours, 0 to 100, and a letter from A to E. A room is
graded on the themes it measures, the home on the mean of its rooms. The categories come from the standard; the
points and the letter thresholds are Hestia-FB's own.

- warmth, heating season (November to April): fixed ranges for dwellings, 21-25 °C (I), 20-25 (II), 18-25 (III);
- warmth, otherwise: the adaptive model for rooms without cooling, around 0.33·Trm + 18.8 °C, Trm being the running
  mean of the outdoor daily means; it is used while Trm lies between 10 and 30 °C, the fixed ranges outside;
- humidity: 30-50 % (I), 25-60 (II), 20-70 (III);
- air: CO₂ above the outdoor air (taken as 400 ppm), up to 550 ppm (I), 800 (II), 1 350 (III).

An unheated room (a laundry) is not graded on its warmth. A theme with less than two weeks of measures is not graded.

Advice (`advice`) speaks only of a lasting problem the measures show, never of a cause they cannot prove: the standard's
normal range is missed half the winter in most homes heated to the legal 19 °C, so a room is told to heat only when it
falls out of every category (under 18 °C) for a sixth of the heating season, and to dry only above the 70 % that
Confort already calls a mould risk. A room whose minimum was set lower (a bedroom kept at 16 °C) is told to heat only
under that minimum: the grade keeps the standard, the advice follows the person's choice.
"""
from collections import defaultdict
from datetime import timedelta
from statistics import mean

POINTS = {1: 100, 2: 75, 3: 50, 4: 0}
LETTERS = ((85, "A"), (70, "B"), (55, "C"), (40, "D"))
HEATING_MONTHS = (11, 12, 1, 2, 3, 4)
WINTER, SUMMER = (12, 1, 2), (6, 7, 8)
HEAT_FIXED = ((1, 21.0, 25.0), (2, 20.0, 25.0), (3, 18.0, 25.0))
# Degrees below and above the adaptive comfort temperature, by category.
HEAT_ADAPTIVE = ((1, 3.0, 2.0), (2, 4.0, 3.0), (3, 5.0, 4.0))
ADAPTIVE_RANGE = (10.0, 30.0)
RUNNING_ALPHA = 0.8
HUMIDITY = ((1, 30.0, 50.0), (2, 25.0, 60.0), (3, 20.0, 70.0))
OUTDOOR_CO2 = 400.0
CO2_ABOVE = ((1, 550.0), (2, 800.0), (3, 1350.0))
MIN_HOURS = 14 * 24
THEMES = ("warmth", "humidity", "air")
# Share of the hours (%) beyond which a lasting problem is worth one piece of advice.
CHILLY_SHARE, DAMP_SHARE, STALE_SHARE = 15, 15, 5
# Above this the air gives water back to cold walls: Confort's own mould threshold.
DAMP = 70.0
# A summer worth cooling at night: its mean indoor temperature, and the outdoor air this much cooler at dawn.
WARM_SUMMER, DAWN_GAP = 25.0, 3.0


def letter(score):
    """A to E from a score out of 100; None for no score."""
    if score is None:
        return None
    return next((name for floor, name in LETTERS if round(score) >= floor), "E")


def running_means(outdoor):
    """The running mean of the outdoor daily means before each day, {date: °C} (EN 16798-1, α 0.8)."""
    daily = defaultdict(list)
    for when, value in outdoor:
        daily[when.date()].append(value)
    result, previous = {}, None
    for day in sorted(daily):
        today = mean(daily[day])
        result[day] = today if previous is None else RUNNING_ALPHA * previous[0] + (1 - RUNNING_ALPHA) * previous[1]
        previous = (result[day], today)
    return result


def warmth_bands(when, running):
    """The (category, low, high) ranges that apply at a local time, given the running means of the days."""
    trm = running.get(when.date()) if running else None
    if when.month in HEATING_MONTHS or trm is None or not ADAPTIVE_RANGE[0] <= trm <= ADAPTIVE_RANGE[1]:
        return HEAT_FIXED
    comfort = 0.33 * trm + 18.8
    return tuple((category, comfort - below, comfort + above) for category, below, above in HEAT_ADAPTIVE)


def _category(value, bands):
    return next((category for category, low, high in bands if low <= value <= high), 4)


def humidity_category(value):
    return _category(value, HUMIDITY)


def air_category(value):
    above = value - OUTDOOR_CO2
    return next((category for category, limit in CO2_ABOVE if above <= limit), 4)


def _grade(categories, minimum=MIN_HOURS):
    """Score, letter and share of hours in categories I and II; no grade under `minimum` hours (two weeks)."""
    if not categories or len(categories) < minimum:
        return {"score": None, "letter": None, "comfortable": None, "hours": len(categories)}
    score = mean(POINTS[c] for c in categories)
    return {"score": round(score), "letter": letter(score), "hours": len(categories),
            "comfortable": round(100 * sum(c <= 2 for c in categories) / len(categories))}


def _month(when):
    return when.strftime("%Y-%m")


def _profile(points, months):
    """Mean by hour of the day over the given months, 24 values (None for an hour never seen)."""
    hours = defaultdict(list)
    for when, value in points:
        if when.month in months:
            hours[when.hour].append(value)
    return [round(mean(hours[h]), 1) if hours[h] else None for h in range(24)]


def warmth(points, outdoor, running, floor=HEAT_FIXED[2][1]):
    """The warmth of a room: grade, month by month against the normal range (II), and a typical day by season."""
    rows, months = [], defaultdict(lambda: {"values": [], "cold": 0, "hot": 0, "low": [], "high": []})
    heating = chilly = 0
    for when, value in points:
        bands = warmth_bands(when, running)
        rows.append(_category(value, bands))
        if when.month in HEATING_MONTHS:
            heating += 1
            chilly += value < floor
        _, low, high = bands[1]
        month = months[_month(when)]
        month["values"].append(value)
        month["low"].append(low)
        month["high"].append(high)
        month["cold"] += value < low
        month["hot"] += value > high
    monthly = []
    for key in sorted(months):
        m = months[key]
        n = len(m["values"])
        monthly.append({"month": key, "min": round(min(m["values"]), 1), "mean": round(mean(m["values"]), 1),
                        "max": round(max(m["values"]), 1), "cold": round(100 * m["cold"] / n), "hot": round(100 * m["hot"] / n),
                        "comfortable": round(100 * (n - m["cold"] - m["hot"]) / n),
                        "low": round(mean(m["low"]), 1), "high": round(mean(m["high"]), 1)})
    coldest = min(points, key=lambda p: p[1]) if points else None
    hottest = max(points, key=lambda p: p[1]) if points else None
    return {**_grade(rows), "monthly": monthly, "chilly": round(100 * chilly / heating) if heating else None, "chilly_below": floor,
            "coldest": {"value": round(coldest[1], 1), "month": _month(coldest[0])} if coldest else None,
            "hottest": {"value": round(hottest[1], 1), "month": _month(hottest[0])} if hottest else None,
            "day": {"winter": _profile(points, WINTER), "summer": _profile(points, SUMMER),
                    "outdoor_winter": _profile(outdoor, WINTER), "outdoor_summer": _profile(outdoor, SUMMER)}}


def humidity(points):
    """The humidity of a room: grade, share of hours under and over the normal range (II), month by month."""
    low, high = HUMIDITY[1][1], HUMIDITY[1][2]
    months = defaultdict(list)
    for when, value in points:
        months[_month(when)].append(value)
    total = len(points) or 1
    return {**_grade([humidity_category(v) for _, v in points]),
            "dry": round(100 * sum(v < low for _, v in points) / total, 1),
            "humid": round(100 * sum(v > high for _, v in points) / total, 1),
            "damp": round(100 * sum(v > DAMP for _, v in points) / total, 1),
            "monthly": [{"month": k, "mean": round(mean(v)), "humid": round(100 * sum(x > high for x in v) / len(v))}
                        for k, v in sorted(months.items())]}


def air(points):
    """The air of a room from its CO₂: grade, share of hours very good (I), correct (II), to renew (beyond), by hour."""
    rows = [air_category(v) for _, v in points]
    total = len(rows) or 1
    months = defaultdict(list)
    for when, value in points:
        months[_month(when)].append(value)
    return {**_grade(rows), "split": [round(100 * sum(c == 1 for c in rows) / total, 1), round(100 * sum(c == 2 for c in rows) / total, 1),
                                      round(100 * sum(c >= 3 for c in rows) / total, 1)],
            "day": _profile(points, range(1, 13)),
            "monthly": [{"month": k, "median": round(sorted(v)[len(v) // 2])} for k, v in sorted(months.items())]}


def room(series, outdoor, zone=None, heated=True, minimum=None):
    """A room's review from hourly means: `series` {"temperature"|"humidity"|"co2": [(time, value)]}, `outdoor` the
    outdoor temperature's. Times are aware and read in the home's time zone `zone`. `minimum` is the room's own, when set:
    under 18 °C, it is the one the advice to heat is measured against."""
    def local(points):
        return [(t.astimezone(zone) if zone else t, float(v)) for t, v in points or ()
                if isinstance(v, (int, float)) and not isinstance(v, bool)]
    outside = local(outdoor)
    themes = {}
    if heated and series.get("temperature"):
        floor = min(HEAT_FIXED[2][1], minimum) if isinstance(minimum, (int, float)) and not isinstance(minimum, bool) else HEAT_FIXED[2][1]
        themes["warmth"] = warmth(local(series["temperature"]), outside, running_means(outside), floor)
    if series.get("humidity"):
        themes["humidity"] = humidity(local(series["humidity"]))
    if series.get("co2"):
        themes["air"] = air(local(series["co2"]))
    scores = [t["score"] for t in themes.values() if t["score"] is not None]
    score = mean(scores) if scores else None
    return {"score": round(score) if score is not None else None, "letter": letter(score), "themes": themes}


def advice(review, ventilation=False):
    """A room's advice, one per theme at most, most pressing first: {"key", "theme", "level", "share", …}.
    `ventilation`: the room has a ventilation it can run longer."""
    found, themes = [], review["themes"]
    warm = themes.get("warmth") or {}
    if warm.get("score") is not None and (warm.get("chilly") or 0) >= CHILLY_SHARE:
        found.append({"key": "heat_more", "theme": "warmth", "level": "action", "share": warm["chilly"], "below": warm.get("chilly_below", HEAT_FIXED[2][1])})
    wet = themes.get("humidity") or {}
    if wet.get("score") is not None and (wet.get("damp") or 0) >= DAMP_SHARE:
        found.append({"key": "run_ventilation" if ventilation else "air_daily", "theme": "humidity", "level": "action", "share": wet["damp"]})
    air = themes.get("air") or {}
    day = [v for v in air.get("day") or () if v is not None]
    if air.get("score") is not None and air["split"][2] >= STALE_SHARE and day:
        found.append({"key": "air_at", "theme": "air", "level": "action", "share": air["split"][2], "hour": air["day"].index(max(day))})
    return sorted(found, key=lambda a: -a["share"])


def home_advice(rooms):
    """The home's advice: the rooms' most pressing ones, then what concerns the whole house. `rooms` carry "title" and
    "advice" beside their review."""
    found = [{**a, "room": r["title"], "entry_id": r.get("entry_id")} for r in rooms for a in r.get("advice", ())]
    found.sort(key=lambda a: -a["share"])
    # The summer night: a house warm all summer while dawn is clearly cooler outside, in most of its rooms.
    summers = []
    for r in rooms:
        day = ((r["themes"].get("warmth") or {}).get("day") or {})
        inside, outside = day.get("summer") or [], day.get("outdoor_summer") or []
        pairs = [(i, o) for i, o in zip(inside, outside) if i is not None and o is not None]
        if pairs:
            dawn = min(pairs, key=lambda p: p[1])
            summers.append((mean(i for i, _ in pairs), dawn[0] - dawn[1]))
    warm = [s for s in summers if s[0] >= WARM_SUMMER and s[1] >= DAWN_GAP]
    if summers and len(warm) * 2 > len(summers):
        found.append({"key": "open_at_night", "theme": "warmth", "level": "benefit", "share": None,
                      "gap": round(mean(g for _, g in warm), 1)})
    # The air measured in fewer than half the rooms: a CO₂ sensor where people sleep says more than any rule.
    # Counted by sensor, graded or not yet: a CO₂ sensor too new for a grade is already there.
    measured = sum(1 for r in rooms if r["themes"].get("air"))
    if rooms and measured * 2 < len(rooms):
        found.append({"key": "add_co2", "theme": "air", "level": "neutral", "share": None, "rooms": measured})
    return found


def home(rooms):
    """The home's review from its rooms' ones: each theme and the whole, as the mean of the rooms graded on them."""
    themes = {}
    for name in THEMES:
        scores = [r["themes"][name]["score"] for r in rooms if (r["themes"].get(name) or {}).get("score") is not None]
        value = mean(scores) if scores else None
        themes[name] = {"score": round(value) if value is not None else None, "letter": letter(value), "rooms": len(scores)}
    scores = [r["score"] for r in rooms if r["score"] is not None]
    value = mean(scores) if scores else None
    return {"score": round(value) if value is not None else None, "letter": letter(value), "themes": themes}


# The home card's periods: their length in days, the hours a theme needs to be graded, the curve's step in hours.
PERIODS = {"day": (1, 12, 1), "week": (7, 3 * 24, 2), "month": (30, 10 * 24, 6)}


def _share(flags):
    return round(100 * sum(flags) / len(flags)) if flags else None


def period(rooms, outdoor, now, name, zone=None):
    """The home over its last day, week or month, for the home card: the four themes of the review, each room's range,
    and the curves inside and outside. `rooms`: [{"entry_id", "title", "series", "heated"}], series and `outdoor` as for room()."""
    days, minimum, step = PERIODS[name]
    since = now - timedelta(days=days)

    def local(points):
        return [(t.astimezone(zone) if zone else t, float(v)) for t, v in points or ()
                if isinstance(v, (int, float)) and not isinstance(v, bool)]
    outside_all = local(outdoor)
    running = running_means(outside_all)
    outside = [(t, v) for t, v in outside_all if t >= since]
    out, pooled, buckets = [], {"warmth": [], "humidity": [], "air": []}, defaultdict(list)
    for room in rooms:
        series = {k: [(t, v) for t, v in local(room["series"].get(k)) if t >= since] for k in ("temperature", "humidity", "co2")}
        temps = series["temperature"]
        themes = {}
        if room.get("heated", True) and temps:
            categories = [_category(v, warmth_bands(t, running)) for t, v in temps]
            pooled["warmth"] += categories
            themes["warmth"] = _grade(categories, minimum)
            for t, v in temps:
                buckets[int((t - since).total_seconds() // (step * 3600))].append(v)
        if series["humidity"]:
            categories = [humidity_category(v) for _, v in series["humidity"]]
            pooled["humidity"] += [v > HUMIDITY[1][2] for _, v in series["humidity"]]
            themes["humidity"] = _grade(categories, minimum)
        if series["co2"]:
            categories = [air_category(v) for _, v in series["co2"]]
            pooled["air"] += categories
            themes["air"] = _grade(categories, minimum)
        scores = [t["score"] for t in themes.values() if t["score"] is not None]
        values = [v for _, v in temps]
        out.append({"entry_id": room["entry_id"], "title": room["title"], "heated": room.get("heated", True),
                    "score": round(mean(scores)) if scores else None,
                    "themes": {k: {"score": v["score"], "letter": v["letter"]} for k, v in themes.items()},
                    "min": round(min(values), 1) if values else None, "max": round(max(values), 1) if values else None,
                    "mean": round(mean(values), 1) if values else None})
    themes = {}
    for key in THEMES:
        scores = [r["themes"][key]["score"] for r in out if (r["themes"].get(key) or {}).get("score") is not None]
        value = mean(scores) if scores else None
        # The figure under each letter: hours comfortable (warmth, air) or too humid (humidity), all rooms together.
        share = _share(pooled[key]) if key == "humidity" else _share([c <= 2 for c in pooled[key]])
        themes[key] = {"score": round(value) if value is not None else None, "letter": letter(value), "share": share}
    scores = [r["score"] for r in out if r["score"] is not None]
    value = mean(scores) if scores else None
    themes["comfort"] = {"score": round(value) if value is not None else None, "letter": letter(value)}
    values = [v for _, v in outside]
    outdoor_buckets = defaultdict(list)
    for t, v in outside:
        outdoor_buckets[int((t - since).total_seconds() // (step * 3600))].append(v)
    count = days * 24 // step

    def curve(source):
        return [round(mean(source[i]), 1) if source.get(i) else None for i in range(count)]
    return {"period": name, "start": since.isoformat(), "step_hours": step, "themes": themes, "rooms": out,
            "outdoor": {"min": round(min(values), 1), "max": round(max(values), 1), "mean": round(mean(values), 1)} if values else None,
            "curve": {"inside": curve(buckets), "outside": curve(outdoor_buckets)}}
