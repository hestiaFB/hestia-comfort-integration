"""The advisor behind the scenes: it records what the physical twin needs and learns it each night, deciding nothing.

Home Assistant keeps the states of windows and heaters for ten days only, too little to judge a twin on gestures that
come once a week. Every five minutes the room's coordinator hands over what it reads; thirty days are kept. Each night
the twin is fitted on all but the last three days and scored on those three (CONCEPTION-MOTEUR.md § 6.5); the result and
the rows themselves go to the diagnostics, for the bench to replay weeks of the real house.

A row: [time (UTC, ISO), air °C, humidity %, outdoor °C, outdoor humidity %, sun W/m², heating W, heater power W,
[open windows], {other heaters: W}]. A value not known is None; nothing is ever filled in.
"""
from dataclasses import replace
from datetime import datetime, timedelta

from .house import Opening, Room
from .physics.fit import Sample, fit, score
from .physics.thermal import STEP, Inputs, ordinary

SLOT = timedelta(seconds=STEP)
KEEP = timedelta(days=30)
# The days the twin is scored on, never fitted on; and how much of the past it learns from, to stay light on a small box.
TESTED, LEARNED = timedelta(days=3), timedelta(days=14)
# A night's fit: fewer steps than the bench's.
ITERATIONS = 200
FORMAT = 1


def _slot(now: datetime) -> datetime:
    return now.replace(minute=now.minute - now.minute % 5, second=0, microsecond=0)


class Recorder:
    """The room's last thirty days, one row every five minutes."""

    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def record(self, now: datetime, air, humidity, outdoor, outdoor_humidity, sun, heating, power, opened, others) -> bool:
        """Notes the room for the current five minutes; the first values of a slot stand for it. True when a row was added."""
        slot = _slot(now).isoformat()
        if self.rows and self.rows[-1][0] >= slot:
            return False
        self.rows.append([slot, air, humidity, outdoor, outdoor_humidity, sun, heating, power, sorted(opened),
                          {k: v for k, v in sorted((others or {}).items()) if v}])
        oldest = (_slot(now) - KEEP).isoformat()
        while self.rows and self.rows[0][0] < oldest:
            self.rows.pop(0)
        return True

    def to_dict(self) -> dict:
        return {"format": FORMAT, "rows": self.rows}

    @classmethod
    def from_dict(cls, data) -> "Recorder":
        return cls(data.get("rows") if isinstance(data, dict) and data.get("format") == FORMAT else None)


def _samples(rows, sizes: dict[str, tuple[float, float]], house: frozenset[str], zone) -> list[Sample]:
    out = []
    for row in rows:
        when = datetime.fromisoformat(row[0])
        air, outdoor, sun, heating, power, opened, others = row[1], row[3], row[5], row[6], row[7], row[8], row[9]
        local = when.astimezone(zone) if zone else when
        inputs = None if outdoor is None else Inputs(
            outdoor=outdoor, sun=sun or 0.0, heating=(heating or 0.0) / power if power else 0.0,
            windows=tuple(sizes[e] for e in opened if e in sizes), hour=local.hour + local.minute / 60,
            house_heat=sum(w for e, w in others.items() if e in house))
        out.append(Sample(when, air, inputs))
    return out


def nightly(name: str, rows, openings: dict[str, dict], now: datetime, zone=None, house: frozenset[str] = frozenset()) -> dict | None:
    """The twin fitted on the recorded days but the last three, and how well it forecast those three; None while fewer
    than four days are recorded. `openings`: the room's declared windows ({entity: {"kind", "width", "height"}});
    `house`: the heaters that warm the whole house (a stove), whose power reaches every room in a learned share."""
    if not rows or datetime.fromisoformat(rows[-1][0]) - datetime.fromisoformat(rows[0][0]) < TESTED + timedelta(days=1):
        return None
    windows = tuple(Opening(e, (m or {}).get("kind") or "window",
                            area=((m or {}).get("width") or 0) * ((m or {}).get("height") or 0) or None,
                            height=(m or {}).get("height")) for e, m in openings.items())
    powers = [r[7] for r in rows if r[7]]
    room = Room(name, name, openings=windows, heating_power=powers[-1] if powers else None)
    samples = _samples([r for r in rows if datetime.fromisoformat(r[0]) >= now - LEARNED - TESTED],
                       {o.entity_id: o.size for o in windows}, house, zone)
    split = now - TESTED
    base = ordinary(room)
    if house:
        base = replace(base, share=0.2)
    learned = fit(base, samples, until=split, iterations=ITERATIONS, held=frozenset({"heat"} if room.heating_power else ()))
    tested = score(learned, samples, since=split)
    return {"computed_at": now.isoformat(), "rows": len(rows), "learned_from": samples[0].when.isoformat() if samples else None,
            "score": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in tested.__dict__.items()},
            "params": {k: round(v, 4) for k, v in learned.__dict__.items()}}
