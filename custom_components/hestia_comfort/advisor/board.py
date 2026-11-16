"""The card's memory (niak-comfort/docs/ETAT-DES-LIEUX-MOTEUR.md § 4-5): what is shown changes on an event, never because
a timer ran out.

Ten days of the house (6 to 16 November): 43 advices came and went within the hour with no window touched; of 47
airings asked, 39 were taken back unfollowed, most of them half an hour after they were shown, when the banner's hold
(HOLD_MINUTES) ran out, to come back five minutes later. The calculation started afresh every five minutes; some thirty
holds, eleven of them timers, each added by a day's fix, tried to keep what had been said.

Here, four families, one memory:
- a slot's gesture (advisor/slots.py): planned once when the slot begins, shown until it is followed or its moment is
  past, never asked again within the slot;
- an urgency, at any hour, on a measure: it enters above its threshold two steps in a row, leaves under a lower one
  (a band), and once left unfollowed PATIENCE minutes is put aside ASIDE minutes, unless its measure gets clearly worse;
- an answer to a gesture: a window open for more than OPEN_LEAST is the household there — said only when it helps;
- the safety (the rain, the gusts, the alarm, the stove): at once, as before.
The humidity is judged on the room's own normal (advisor/identity.py): the Chambre P lives at 75-80 %.
"""
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timedelta

from .decide import Decision, Gesture, effect
from .proof import PROVEN, SUPPOSED

# Urgencies measured: (enter, leave). A band, never on and off around one value.
URGENT = {"co2": (1400.0, 1100.0), "particles": (25.0, 15.0), "voc": (250.0, 150.0)}
# The humidity: HUMID_ENTER points above the room's own normal to enter, never under HUMID_FLOOR; back within
# HUMID_LEAVE of it to leave; and the outside drier by DRIER g/m³ at least, or an airing does not dry the room.
HUMID_ENTER, HUMID_LEAVE, HUMID_FLOOR, DRIER = 8.0, 3.0, 70.0, 2.0
# Steps in a row above its threshold for an urgency to be shown: a measure alone shows nothing.
ENTER_STEPS = 2
# Minutes an urgency waits to be followed, then minutes it is put aside; it comes back before if its measure gets
# worse by WORSE.
PATIENCE, ASIDE = 45, 120
WORSE = {"co2": 300.0, "particles": 10.0, "voc": 100.0, "humidity": 5.0}
# The order urgencies are said in when several are on.
ORDER = ("co2", "particles", "voc", "humidity")
# A window open less than this (seconds) does not count for comfort: someone going through. The safety acts at once.
OPEN_LEAST = 60
# Minutes a slot's gesture stays once its moment has come, for the household to do it.
PLAN_GRACE = 45
# The gestures an urgency may ask: open the windows now, or run a device.
URGENT_KINDS = ("open", "open_more", "boost", "purify")


def thresholds(subject: str, normal: float | None) -> tuple[float, float] | None:
    """(enter, leave) for `subject`; for the humidity, on the room's own normal, None while it is not known."""
    if subject in URGENT:
        return URGENT[subject]
    if subject == "humidity":
        if normal is None:
            return None
        return max(HUMID_FLOOR, normal + HUMID_ENTER), normal + HUMID_LEAVE
    return None


@dataclass
class Urgent:
    since: datetime | None = None        # shown since then; None while not shown
    above: int = 0                       # steps in a row above its threshold, not shown yet
    aside_until: datetime | None = None
    aside_value: float | None = None


@dataclass
class Plan:
    """A slot's gesture, as planned when the slot began (advisor/slots.py)."""
    slot: str                            # the slot's key, « 2026-11-16/apres_midi »
    at: datetime                         # when it was planned
    until: datetime                      # shown until then, unless followed
    gesture: Gesture                     # its moment (`after`) counted from `at`; Gesture("nothing"): nothing this slot
    words: dict = field(default_factory=dict)   # title, line, why, try, subject: said as planned
    trial: bool = False                  # only to try (« À essayer »)
    done: bool = False                   # followed: a window opened for it

    def moment(self) -> datetime:
        return self.at + timedelta(minutes=self.gesture.after or 0)

    def left(self, now: datetime) -> Gesture:
        """The gesture as it stands now: its moment counted down."""
        after = max(0.0, (self.moment() - now).total_seconds() / 60)
        return replace(self.gesture, after=round(after) if after >= 5 else None)


def _plain(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _when(value):
    return datetime.fromisoformat(value) if value else None


class Board:
    """One room's card memory: its urgencies, its slot's plan, the subject said while calm."""

    def __init__(self):
        self.urgent: dict[str, Urgent] = {}
        self.plan: Plan | None = None
        self.calm: str | None = None

    # The urgencies.
    def urgent_now(self, measures: dict, normal_humidity: float | None, drier: float | None, opened: bool,
                   now: datetime) -> tuple[str, float] | None:
        """The urgency shown now, (subject, measure), or None. `measures`: {subject: value}; `drier`: g/m³ the outside
        air holds less than the room's; `opened`: the household airing the room now (an urgency followed)."""
        for subject in ORDER:
            value = measures.get(subject)
            limits = thresholds(subject, normal_humidity)
            u = self.urgent.setdefault(subject, Urgent())
            if value is None or limits is None:
                u.since, u.above = None, 0
                continue
            enter, leave = limits
            if u.since is not None:
                if value < leave:
                    u.since, u.above = None, 0
                elif opened:
                    # Being followed: its patience starts again once the window is shut.
                    u.since = now
                elif now - u.since >= timedelta(minutes=PATIENCE):
                    u.since, u.above = None, 0
                    u.aside_until, u.aside_value = now + timedelta(minutes=ASIDE), value
                continue
            useful = subject != "humidity" or (drier is not None and drier >= DRIER)
            u.above = u.above + 1 if value >= enter and useful else 0
            aside = u.aside_until is not None and now < u.aside_until and value < (u.aside_value or 0) + WORSE[subject]
            if u.above >= ENTER_STEPS and not aside:
                u.since, u.aside_until, u.aside_value = now, None, None
        shown = [(s, measures[s]) for s in ORDER if (u := self.urgent.get(s)) and u.since is not None]
        return shown[0] if shown else None

    def aside(self, now: datetime) -> dict:
        """The urgencies put aside now: {subject: until}."""
        return {s: u.aside_until for s, u in self.urgent.items() if u.aside_until is not None and now < u.aside_until}

    def put_aside(self, subject: str, until: datetime, value: float | None):
        """« Pas maintenant » on an urgency."""
        u = self.urgent.setdefault(subject, Urgent())
        u.since, u.above, u.aside_until, u.aside_value = None, 0, until, value

    # The slot's plan.
    def needs_plan(self, slot_key: str) -> bool:
        return self.plan is None or self.plan.slot != slot_key

    def set_plan(self, slot_key: str, now: datetime, slot_end: datetime, gesture: Gesture, words: dict, trial: bool):
        moment = now + timedelta(minutes=gesture.after or 0)
        until = min(slot_end, moment + timedelta(minutes=PLAN_GRACE)) if gesture.kind != "nothing" else slot_end
        self.plan = Plan(slot_key, now, until, gesture, dict(words), trial)

    def plan_shown(self, now: datetime) -> Plan | None:
        """The slot's gesture to show now: planned, not followed, its moment not past."""
        p = self.plan
        if p is None or p.done or p.gesture.kind == "nothing" or now >= p.until:
            return None
        return p

    def followed(self):
        """The household did the slot's gesture (a window opened while it was shown)."""
        if self.plan is not None:
            self.plan.done = True

    # Kept across a restart.
    def state(self) -> dict:
        plan = None
        if self.plan is not None:
            p = self.plan
            plan = {"slot": p.slot, "at": p.at.isoformat(), "until": p.until.isoformat(), "gesture": asdict(p.gesture),
                    "words": p.words, "trial": p.trial, "done": p.done}
        return {"urgent": {s: {k: _plain(v) for k, v in asdict(u).items()} for s, u in self.urgent.items()},
                "plan": plan, "calm": self.calm}

    def load(self, state: dict | None):
        state = state or {}
        self.urgent = {s: Urgent(_when(u.get("since")), u.get("above", 0), _when(u.get("aside_until")), u.get("aside_value"))
                       for s, u in (state.get("urgent") or {}).items()}
        if p := state.get("plan"):
            self.plan = Plan(p["slot"], _when(p["at"]), _when(p["until"]), Gesture(**p["gesture"]), p.get("words") or {},
                             p.get("trial", False), p.get("done", False))
        self.calm = state.get("calm")


# The rules that speak at once, whatever else is on: a fact measured or a safety (advisor/decide.py).
SAFE_RULES = ("safety", "ineffective", "overheat", "pollen")


def choose(decision: Decision, airing_now: bool, asked: Decision | None, plan: Plan | None, put_aside, air: float,
           minimum: float) -> str:
    """The family of what the card shows: the safety first; the household airing now (an answer, urgent when the airing
    takes the room under its range); an urgency measured (`asked`, `urgent_decision`); the slot's gesture, unless it was
    answered « Pas maintenant »; otherwise « Rien à faire » (« calme »)."""
    if decision.rule in SAFE_RULES:
        return "securite"
    if airing_now:
        return "urgence" if decision.gesture.kind == "close" and air < minimum else "reponse"
    if asked is not None:
        return "urgence"
    if plan is not None and plan.gesture.kind not in put_aside:
        return "creneau"
    return "calme"


def urgent_decision(decision: Decision, subject: str, value: float, proof: dict | None) -> Decision | None:
    """The gesture an urgency asks, from the scenarios simulated this step: of the airings now and the devices, the
    cheapest that lowers `subject`, the shortest of those that do nearly as much. None when none lowers it (the outside
    is no better)."""
    scenarios = decision.scenarios
    nothing = scenarios.get(Gesture("nothing"))
    if not nothing:
        return None
    term = "humidity" if subject == "humidity" else subject
    helping = [g for g, c in scenarios.items() if g.kind in URGENT_KINDS and not g.after
               and c.get(term, 0.0) < nothing.get(term, 0.0)]
    if not helping:
        return None
    best = min(helping, key=lambda g: scenarios[g]["total"])
    most = nothing[term] - scenarios[best][term]
    near = [g for g in helping if g.kind == best.kind and nothing[term] - scenarios[g][term] >= 0.8 * most]
    chosen = min(near, key=lambda g: (g.minutes or 10_000, scenarios[g]["total"]))
    found = (proof or {}).get(effect(chosen, term), SUPPOSED) if proof is not None else PROVEN
    return Decision(chosen, nothing["total"] - scenarios[chosen]["total"], "urgent", scenarios, decision.paths,
                    level=found, measured={subject: value})
