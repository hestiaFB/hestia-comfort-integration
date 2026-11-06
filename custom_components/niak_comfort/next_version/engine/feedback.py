"""The feedback loop: every advice followed becomes a measured experiment.

When a window opens on an « open » advice, the measure the advice is about (humidity, temperature, CO₂, VOC) is noted,
with what was predicted. When the room is shut again, the measure is read once more. An advice shown for half an hour
without a window opening is noted as left aside. From these records come the last airing shown on the card, the week's
summary shown in the hub, and the bias that corrects the next predictions of the room.
"""
from datetime import datetime, timedelta

# How close the result must come to the prediction to count as held.
TOLERANCE = {"humidity": 3.0, "temperature": 0.5, "co2": 100.0, "voc": 30.0}
# An advice left on screen this long without a window opening counts as left aside.
IGNORED_AFTER = timedelta(minutes=30)
# An airing longer than this is not an experiment any more, only a window left open.
LONGEST = timedelta(hours=3)
# Shorter than this, an opening is someone going through a door, not an airing: it is neither followed nor measured.
SHORTEST = timedelta(minutes=5)
# The result is read this long after closing: a VOC or CO₂ sensor speaks every minute or two.
SETTLE = timedelta(minutes=4)
KEEP_DAYS = 60
SENSORS = {"humidity": "indoor_humidity", "temperature": "indoor_temperature", "co2": "co2", "voc": "voc"}


def _shown(assessment):
    """The advice as shown: a room that follows its shared air shows the leading room's reason and features."""
    if assessment.get("reason") != "shared_volume":
        return assessment.get("reason"), assessment.get("features") or {}
    volume = (assessment.get("features") or {}).get("volume") or {}
    lead = volume.get("assessment") or {}
    return volume.get("reason"), {**(assessment.get("features") or {}), **(lead.get("features") or {})}


def measure(assessment):
    """The measure an airing advice is about, or None."""
    reason, features = _shown(assessment)
    air = features.get("air") or {}
    if reason in ("drying_possible", "ventilation_possible"):
        return "humidity"
    if reason in ("cooling_possible", "precool_possible", "warming_possible"):
        return "temperature"
    if reason in ("air_needed", "short_air_change", "optional_air_change"):
        return "co2" if air.get("co2_status") == "high" else "voc" if air.get("voc_status") == "high" else None
    return None


def start(assessment, values, now):
    """An experiment from the advice followed and the measures at the opening; None when nothing is measured."""
    name = measure(assessment)
    before = values.get(SENSORS.get(name)) if name else None
    if not isinstance(before, (int, float)) or isinstance(before, bool):
        return None
    _, features = _shown(assessment)
    learned, drying = features.get("learned"), features.get("drying") or {}
    predicted = None
    if learned and learned.get("measure") == name:
        predicted = learned.get("after")
    elif name == "humidity" and drying.get("after") is not None:
        predicted = drying["after"]
    return {"start": now.isoformat(), "measure": name, "before": round(before, 1),
            "predicted": None if predicted is None else round(predicted, 1), "learned": bool(learned)}


def finish(experiment, values, now):
    """The experiment once the room is shut again; None when it lasted too long or the measure is gone."""
    begun = datetime.fromisoformat(experiment["start"])
    closed = datetime.fromisoformat(experiment.get("closed") or now.isoformat())
    after = values.get(SENSORS[experiment["measure"]])
    if not SHORTEST <= closed - begun <= LONGEST or not isinstance(after, (int, float)) or isinstance(after, bool):
        return None
    record = {k: v for k, v in experiment.items() if k != "closed"}
    return {**record, "end": closed.isoformat(), "minutes": round((closed - begun).total_seconds() / 60), "after": round(after, 1)}


def ignored(since, now):
    return {"start": since.isoformat(), "end": now.isoformat(), "ignored": True}


def keep(records, now):
    limit = now - timedelta(days=KEEP_DAYS)
    # Openings too short to be airings, measured before 1.2.7, are dropped: they would bend the room's predictions.
    return [r for r in records or [] if isinstance(r, dict) and isinstance(r.get("start"), str) and datetime.fromisoformat(r["start"]) >= limit
            and not (isinstance(r.get("end"), str) and not r.get("ignored")
                     and datetime.fromisoformat(r["end"]) - datetime.fromisoformat(r["start"]) < SHORTEST)]


def held(record):
    """Did the result come within the tolerance of the prediction? None without a prediction."""
    if record.get("predicted") is None or record.get("after") is None:
        return None
    return abs(record["after"] - record["predicted"]) <= TOLERANCE[record["measure"]]


def bias(records, name, last=10):
    """Mean gap between result and prediction over the last airings of this measure; None under three."""
    gaps = [r["after"] - r["predicted"] for r in records if r.get("measure") == name and held(r) is not None][-last:]
    return round(sum(gaps) / len(gaps), 1) if len(gaps) >= 3 else None


def summarize(records, now):
    """What the card and the hub show: the last airing of the day, the week, and the corrections."""
    done = [r for r in records or [] if r.get("after") is not None]
    last = done[-1] if done and now - datetime.fromisoformat(done[-1]["end"]) <= timedelta(hours=24) else None
    week = [r for r in records or [] if now - datetime.fromisoformat(r["start"]) <= timedelta(days=7)]
    followed = [r for r in week if r.get("after") is not None]
    evaluated = [r for r in followed if held(r) is not None]
    gains = {}
    for name in TOLERANCE:
        values = [r["after"] - r["before"] for r in followed if r["measure"] == name]
        if values:
            gains[name] = round(sum(values) / len(values), 1)
    recent = [held(r) for r in done if held(r) is not None][-6:]
    return {"last": last, "week": {"followed": len(followed), "ignored": sum(1 for r in week if r.get("ignored")),
                                   "evaluated": len(evaluated), "held": sum(1 for r in evaluated if held(r)), "gains": gains},
            "bias": {name: bias(done, name) for name in TOLERANCE},
            # Predictions that stopped holding take a room back to estimated advice.
            "trusted": len(recent) < 3 or sum(recent) * 2 >= len(recent)}
