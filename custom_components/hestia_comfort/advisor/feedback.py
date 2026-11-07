"""What the household says of an advice, and what it does with it (CAHIER-MOTEUR.md § 15).

« Ce conseil ne va pas » on the card: « faux » (the advice is wrong), « inutile » (right, but not worth the gesture),
« pas maintenant » (not now: the gesture is put aside for a while, a household setting). The situation is kept with its
trace, without limit, to be replayed (§ 16 bis.2).

The engine also follows each gesture shown: done while it was shown, or replaced before. An advice never followed is a
failure, not a success. (The 2.1 engine's own loop is engine/feedback.py; this one belongs to the 3.0 advisor.)
"""
from dataclasses import dataclass
from datetime import datetime, timedelta

from .decide import SHUTTER_OPEN, SHUTTER_SHUT, Gesture, Now

OPINIONS = ("faux", "inutile", "pas_maintenant")
# The free note sent with an opinion, at most this many characters.
NOTE = 500


@dataclass(frozen=True)
class Asked:
    """A gesture shown on the card, since when, and whether it was only one to try (« À essayer »)."""
    kind: str
    since: datetime
    title: str
    trial: bool = False
    target: float | None = None     # the set point « Remettez le chauffage à 19 °C » asks for
    kwh: float | None = None        # what it costs against « do nothing », as simulated when first asked (decide.gesture_energy)
    heated: bool = False            # those kWh are the simulated thermostat's, not only the heat let out


def done(kind: str, now: Now, target: float | None = None) -> bool:
    """Whether the room shows the gesture done: a window open, all shut, the device started or stopped, the heating on
    again or set to `target`."""
    if kind == "open":
        return bool(now.opened)
    if kind == "close":
        return not now.opened
    if kind == "keep":
        # Left open: nothing more to do, the « Ouvrez » it follows was the gesture.
        return True
    if kind in ("boost", "purify"):
        return now.boosting if kind == "boost" else now.purifying
    if kind in ("boost_off", "purify_off"):
        return not (now.boosting if kind == "boost_off" else now.purifying)
    if kind == "heat_on":
        return now.heating is True
    if kind == "heat_to":
        return now.heating is True and None not in (now.heating_target, target) and now.heating_target >= target - 0.25
    if kind == "open_more":
        # Both sides open: more than one window.
        return len(now.opened) > 1
    if kind == "heat_stop":
        return not now.house_running
    if kind in ("shutter_close", "shutter_open") and now.cover is not None:
        return now.cover <= SHUTTER_SHUT if kind == "shutter_close" else now.cover >= SHUTTER_OPEN
    return False


def follow(asked: Asked | None, shown: Gesture | None, title: str, trial: bool, now: Now,
           when: datetime, energy: tuple[float, bool] | None = None) -> tuple[Asked | None, list[dict]]:
    """The gesture followed from one decision to the next: what is asked now, and what was learned — a gesture done
    while it was asked, or replaced by another before. `shown`: the gesture on the card now, None or « nothing » if none;
    `energy`: its (kWh, heated) against « do nothing » (decide.gesture_energy), kept with it for Hestia Énergie."""
    out = []
    if asked is not None:
        if done(asked.kind, now, asked.target):
            out.append(_record(asked, when, True))
            asked = None
        elif shown is None or shown.kind != asked.kind:
            out.append(_record(asked, when, False))
            asked = None
    if asked is None and shown is not None and shown.kind != "nothing" and not done(shown.kind, now, shown.target):
        kwh, heated = energy if energy else (None, False)
        asked = Asked(shown.kind, when, title, trial, shown.target, None if kwh is None else round(kwh, 2), heated)
    return asked, out


def _record(asked: Asked, when: datetime, followed: bool) -> dict:
    return {"geste": asked.kind, "conseil": asked.title, "essai": asked.trial, "suivi": followed,
            "depuis": asked.since.isoformat(), "minutes": round((when - asked.since).total_seconds() / 60),
            "kwh": asked.kwh, "chauffage": asked.heated}


def declined(paused: dict[str, datetime], now: Now, when: datetime) -> frozenset[str]:
    """The gestures put aside (« pas maintenant ») still in their pause. An opening put aside never makes the windows
    already open look forbidden: `decide` would read it as the rain's « Fermez »."""
    return frozenset(kind for kind, until in paused.items() if until > when and not (kind == "open" and now.opened))


def pause_until(when: datetime, minutes: int) -> datetime:
    return when + timedelta(minutes=minutes)


def followed_share(records: list[dict]) -> dict:
    """Of the gestures asked, how many were followed; the ones only to try, apart."""
    asked = [r for r in records if not r.get("essai")]
    tried = [r for r in records if r.get("essai")]
    return {"suivis": sum(r["suivi"] for r in asked), "demandes": len(asked),
            "essais_faits": sum(r["suivi"] for r in tried), "essais": len(tried)}
