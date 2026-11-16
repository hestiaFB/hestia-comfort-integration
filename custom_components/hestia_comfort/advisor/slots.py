"""The day's slots (niak-comfort/docs/ETAT-DES-LIEUX-MOTEUR.md § 4.2): one gesture per room and per slot, fixed when
the slot begins, at the best moment within it.

Frank, 16 November: « dans la vie de tous les jours on ne regarde pas l'application pour savoir si à un instant T il
faut ouvrir ou pas ». The household aired each room two to five times in ten days, near 9 h, 15-16 h or 19 h, while the
advisor, deciding anew every five minutes, asked 47 airings at any hour and took 39 of them back unfollowed.

Four slots, set on the household's hours: the morning from its waking to noon, the afternoon to the evening, the
evening to its bedtime, the night to its waking. The night's gesture is said in the evening (« Cette nuit, pensez à… »).
"""
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta

from .decide import Gesture, candidates
from .household import Habits

SLOTS = ("matin", "apres_midi", "soir", "nuit")
# The airings a slot's plan compares (minutes), and how far apart its moments are: a slot is planned once, its moment
# is said to the half hour (« vers 14 h 30 »), never to the five minutes that changed at every step.
PLAN_AIRINGS = (10, 20, 30, 45, 60)
PLAN_EVERY = 30
# What the plan's forecast covers beyond the slot's end: an airing is judged on what stays once the walls gave back
# their water (advisor/opening.py SETTLE).
PLAN_AFTER = 120
# Mild outside: no more than this under the room's minimum (°C) over the slot. Then an airing may last up to the
# household's `plan_max` (1 h), as it does with a mild outside; otherwise its usual longest (`airing_max`, 30 min): at
# 9 °C outside, the plan for the Chambre A said « Aérez 60 min » (rejeu of 16 November at 7 h 02).
MILD_GAP = 8.0


@dataclass(frozen=True)
class Slot:
    name: str
    start: datetime
    end: datetime

    @property
    def key(self) -> str:
        """The slot's own name, the same at every step within it: « 2026-11-16/apres_midi »."""
        return f"{self.start:%Y-%m-%d}/{self.name}"

    def minutes_left(self, local: datetime) -> float:
        return max(0.0, (self.end - local).total_seconds() / 60)


def _at(day: date, hour: time, tz) -> datetime:
    return datetime.combine(day, hour, tzinfo=tz)


def slot_at(local: datetime, habits: Habits = Habits()) -> Slot:
    """The slot `local` (an aware local time) falls in, on the household's hours."""
    sleep, tz = habits.sleep, local.tzinfo
    if sleep.asleep(local):
        start = _at(local.date(), sleep.start, tz)
        if start > local:
            start -= timedelta(days=1)
        return Slot("nuit", start, sleep.wake(local))
    day = local.date()
    wake = _at(day, sleep.end_on(day), tz)
    bed = sleep.bedtime(local)
    noon = min(bed, max(wake, _at(day, time(habits.noon), tz)))
    evening = min(bed, max(noon, _at(day, time(habits.evening), tz)))
    if local < noon:
        return Slot("matin", min(wake, local), noon)
    if local < evening:
        return Slot("apres_midi", noon, evening)
    return Slot("soir", evening, bed)


def slot_name(local: datetime, habits: Habits = Habits()) -> str:
    return slot_at(local, habits).name


def plan_pool(now, twins, habits: Habits, comfort, minutes_left: float, outdoor: float | None = None) -> list[Gesture]:
    """The gestures a slot's plan weighs: the room's own (its devices, its shutter, its heating), and the airings of
    PLAN_AIRINGS now or at a moment of the slot, every PLAN_EVERY minutes, that ends before the slot does. `outdoor`: the
    slot's mean outdoor temperature; mild (MILD_GAP), the airings may last up to `plan_max`."""
    mild = outdoor is not None and comfort is not None and outdoor >= comfort.minimum - MILD_GAP
    longest = max(habits.plan_max if mild else habits.airing_max, PLAN_AIRINGS[0])
    airings = [m for m in PLAN_AIRINGS if m <= longest]
    pool = [g for g in candidates(now, twins, habits, comfort) if g.kind != "open"]
    pool += [Gesture("open", m) for m in airings]
    pool += [Gesture("open", m, after=a) for m in airings for a in range(PLAN_EVERY, int(minutes_left) - m + 1, PLAN_EVERY)]
    return pool


def plan_habits(habits: Habits, minutes_left: float) -> Habits:
    """The habits a plan is decided with: its later moments up to the slot's end."""
    return replace(habits, later_max=max(0, int(minutes_left)))
