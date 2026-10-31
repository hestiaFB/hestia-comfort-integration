"""The rooms' sensors checked before the engine uses them (CAHIER-MOTEUR.md § 7.3): out of range, an impossible jump,
frozen. A doubtful measure is never advised on: the engine leaves it aside and says so (« Mesure douteuse »), the
Fiabilité page shows why. The outdoor's checks are Hestia Weather's (§ 7.4).

Seen in the house: a CO₂ sensor at 0 ppm, a PM2.5 sensor at 999 µg/m³ (31 October).
"""
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class Limits:
    low: float              # under this, the sensor is wrong
    high: float             # above this too
    jump: float | None      # more than this in five minutes is impossible; None: anything can happen (cooking smoke)
    frozen: timedelta       # the same value this long, from a sensor that always moves a little


KINDS = {
    # Indoors, a window open in winter moves the air 2 to 3 °C in five minutes at most.
    "temperature": Limits(-10.0, 45.0, 4.0, timedelta(hours=12)),
    # A shower lifts a bathroom 20 points in five minutes.
    "humidity": Limits(1.0, 100.0, 30.0, timedelta(hours=12)),
    # Outdoor air is 420 ppm: a room never goes under 350.
    "co2": Limits(350.0, 10000.0, 2000.0, timedelta(hours=12)),
    # Clean air can stay at 0 or 1 µg/m³ for a day; cooking jumps by hundreds.
    "particles": Limits(0.0, 500.0, None, timedelta(hours=48)),
    # Sensirion VOC index: 1 to 500, 100 the room's usual air.
    "voc": Limits(1.0, 500.0, None, timedelta(hours=48)),
}


@dataclass(frozen=True)
class Verdict:
    ok: bool
    reason: str | None = None       # range · jump · frozen
    since: datetime | None = None   # frozen since then
    value: float | None = None      # what the sensor said


GOOD = Verdict(True)


class Checker:
    """Remembers, sensor by sensor, the last value kept: a jump is doubtful until the next reading confirms it."""

    def __init__(self):
        self.kept: dict[str, float] = {}
        self.pending: dict[str, float] = {}

    def check(self, entity_id: str, kind: str, value: float | None, changed: datetime | None, now: datetime) -> Verdict:
        """`changed`: when the sensor's value last changed (Home Assistant's `last_changed`)."""
        limits = KINDS.get(kind)
        if value is None or limits is None:
            return GOOD
        if not limits.low <= value <= limits.high:
            return Verdict(False, "range", value=value)
        if changed is not None and now - changed >= limits.frozen:
            return Verdict(False, "frozen", changed, value)
        kept = self.kept.get(entity_id)
        if limits.jump is not None and kept is not None and abs(value - kept) > limits.jump:
            pending = self.pending.get(entity_id)
            if pending is None or abs(value - pending) > limits.jump:
                # A jump not confirmed yet: the next reading tells a real change from a glitch.
                self.pending[entity_id] = value
                return Verdict(False, "jump", value=value)
        self.pending.pop(entity_id, None)
        self.kept[entity_id] = value
        return GOOD
