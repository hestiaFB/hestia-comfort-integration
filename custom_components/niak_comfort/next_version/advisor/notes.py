"""A note for each gesture (CAHIER-MOTEUR.md § 15.1, proposed by Frank on 3 November).

A gesture — a window opened then shut, the VMC's fast speed, the purifier — is judged an hour after it ended, once the
walls and the furnishings gave back what the air lost, against what the twin forecasts without it: the effect announced
(with − without) against the effect measured (measured − without). A room that takes on water all evening and stays
where it was after an airing was dried by it. Nothing is noted when something else acted meanwhile.

Its note says it in a word (+, 0, −); its ratio corrects the twin by category — the room's (one twin each) × the gesture ×
the subject — a night at a time, from the middle of the recent ones. A note is kept as [when, announced, measured]: the
gesture's start, its effect announced and its effect measured, both against « without ».

Everything here is plain values: the twins simulate « with » and « without » (advisor/physics/fit.py, airfit.py,
advisor/opening.py); this module only says what counts and what it tells.
"""
from datetime import datetime, timedelta
import math

# A gesture is judged this many five-minute steps after it ended: an hour (Frank: « met le à 1 h, je pense que c'est
# mieux pour l'inertie »).
SETTLE_STEPS = 12
# Shorter than this (steps), a gesture says nothing: a sensor's step is all one sees (advisor/opening.py OBSERVE_MINUTES).
SHORTEST_STEPS = 2
# An effect announced smaller than this cannot be read against the sensors' noise: °C; g/m³ of water; ppm; µg/m³; VOC
# index points (about twice each sensor's noise, advisor/decide.py SOURCE_GAP).
READ = {"heat": 0.3, "humidity": 0.5, "co2": 60.0, "particles": 4.0, "voc": 20.0}
# The note: + when the gesture did between half and twice what was announced (or more: the twin underrates it), 0 when
# less than half, − when the other way (advisor/proof.py LOW, HIGH).
LOW, HIGH = 0.5, 2.0
GOOD, LITTLE, WORSE = "+", "0", "−"
# A night corrects a category from this many notes at least; a note weighs half as much every HALF_LIFE (a seal changed,
# a piece of furniture moved: the room is no longer the same); the effect moves by MOVE at most either way in a night,
# in a few rounds (it is not exactly proportional to the twin's parameter).
LEAST = 3
HALF_LIFE = timedelta(days=15)
MOVE, ROUNDS = 2.0, 3
# Notes kept, and the gestures put aside during the day (« ecartes »: something else acted), this long.
KEEP = timedelta(days=60)
# Two starts this close are the same gesture: the day's note and the night's reading of it.
SAME = timedelta(minutes=30)


def readable(subject: str, announced: float | None) -> bool:
    return announced is not None and abs(announced) >= READ.get(subject, 0.0)


def ratio(announced: float, measured: float) -> float | None:
    return None if not announced else measured / announced


def grade(r: float | None) -> str | None:
    if r is None:
        return None
    return GOOD if r >= LOW else LITTLE if r >= 0 else WORSE


def case(subject: str, when: datetime, with_it: float, without: float, measured: float) -> list | None:
    """The note of a gesture started at `when`: the twin's value with and without it, and the measured value, an hour
    after it ended. None when the effect announced is too small to be read."""
    announced = with_it - without
    if not readable(subject, announced):
        return None
    return [when.isoformat(), round(announced, 3), round(measured - without, 3)]


def grades(notes, last: int = 5) -> str:
    """The last notes in a word each, oldest first: « 0 0 − »."""
    return " ".join(g for n in notes[-last:] if (g := grade(ratio(n[-2], n[-1]))))


def episodes(flags) -> list[tuple[int, int]]:
    """(first step on, first step off again) of each run of `flags`, one a step (True, False, or None for unknown); a run
    whose start or end is unknown is left out."""
    out, start = [], None
    for i, flag in enumerate(flags):
        if flag is None:
            start = None
        elif flag and start is None and i and flags[i - 1] is False:
            start = i
        elif not flag and start is not None:
            out.append((start, i))
            start = None
    return out


def left_out(why: dict | None, reason: str | None) -> None:
    """Counts a gesture in `why` by what became of it: « notee », or why it was left out — « trop_court », « pas_encore »
    (its hour not over), « ecarte_le_jour », « trou » (a gap in the history), « rouverte », « appareil » (the VMC or the
    purifier switched), « derive » (the room's own drift hides it), « illisible » (an effect too small to be read)."""
    if why is not None:
        key = reason or "notee"
        why[key] = why.get(key, 0) + 1


def put_aside(skipped, when: datetime) -> bool:
    """Whether the gesture started at `when` was put aside during the day (something else acted while it settled)."""
    return any(abs(datetime.fromisoformat(s) - when) < SAME for s in skipped or ())


def middle(notes, now: datetime) -> tuple[float | None, int]:
    """The middle ratio of the notes, the recent ones weighing more, and how many count. A few odd notes never move it."""
    weighted = []
    for n in notes:
        r = ratio(n[-2], n[-1])
        if r is not None:
            age = (now - datetime.fromisoformat(n[0])).total_seconds()
            weighted.append((r, 0.5 ** (max(0.0, age) / HALF_LIFE.total_seconds())))
    if not weighted:
        return None, 0
    weighted.sort()
    half, total = sum(w for _, w in weighted) / 2, 0.0
    for r, w in weighted:
        total += w
        if total >= half:
            return r, len(weighted)
    return weighted[-1][0], len(weighted)


def factor(notes, now: datetime) -> tuple[float | None, float | None, int]:
    """By how much the category's effect is to be multiplied: (factor within MOVE, the middle ratio, the notes counted);
    no factor with fewer than LEAST notes."""
    m, n = middle(notes, now)
    if m is None or n < LEAST:
        return None, m, n
    return min(MOVE, max(1 / MOVE, m)), m, n


def settle(fit_notes, value: float, now: datetime) -> tuple[float, list, dict]:
    """The category's parameter corrected in a few rounds, never further than MOVE either way from where the night
    started it: `fit_notes(value)` gives the notes with the parameter at `value`. (the value, its notes, the report)."""
    start = value
    notes = fit_notes(value)
    f, m, n = factor(notes, now)
    report = {"notes": grades(notes), "nombre": n, "rapport": None if m is None else round(m, 2)}
    if f is None or not start:
        return value, notes, report
    for _ in range(ROUNDS):
        if f is None or abs(math.log(f)) < 0.05:
            break
        value = start * min(MOVE, max(1 / MOVE, value * f / start))
        notes = fit_notes(value)
        f, m, n = factor(notes, now)
    report["facteur"] = round(value / start, 2)
    report["apres"] = None if m is None else round(m, 2)
    return value, notes, report


def prune(skipped, now: datetime) -> list:
    limit = (now - KEEP).isoformat()
    return [s for s in skipped or () if s >= limit]
