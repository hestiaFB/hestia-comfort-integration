"""What the VMC should do now, for automations: its slow speed (« VMC conseillée ») and its fast one (« Turbo conseillé »).

Two ways a ventilation runs, set for each room (« Fonctionnement », Frank, 7 November):
- « En continu »: a classic VMC. Its slow speed never stops; only its fast speed comes and goes.
- « À la demande »: an extractor, run when it helps: the air too humid while the outdoor air is drier, or too much CO₂.
  Never during the room's night (its sleeping hours, or the alarm armed for the night), and stopped when an hour of
  running did not lower the humidity: it then rests two hours, four after a second useless hour, then eight, until an
  hour dries the room or the outdoor air gets clearly drier (Chambre P, 10 November: three useless hours at 80 %).
The fast speed (Turbo), when the room has one: a shower going on (in a room that declares one, engine/shower.py), or the
advisor's « Lancez la VMC rapide » for the minutes it says. During the room's night a shower runs it NIGHT_SHOWER minutes
only (Chambre P, 9 November at 23 h 22: an hour asked for, stopped by hand at 23 h 52). With the fast speed, the slow one
is advised too: a two-speed VMC runs both contactors.
Stopped by hand while advised (seen running, then off): the person is right. Nothing is advised for MANUAL_REST, unless a
new shower starts; a classic VMC keeps its slow speed (Frank, 10 November: « elle ne s'est pas coupée toute seule »).
A « no » is said only once it has lasted OFF_DELAY: a measure that wavers a minute does not stop the VMC.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta

MODES = ("on_demand", "continuous")
# The behaviour before the setting existed: advised when useful. A classic VMC is set « En continu » by the person.
DEFAULT_MODE = "on_demand"
# An extractor starts when the air is humid, and keeps running while it is still a little humid.
START = ("humid", "very_humid")
KEEP = ("slightly_humid", "humid", "very_humid")
# Water (g/m³) the indoor air must hold above the outdoor air for outdoor air to dry it (assessment.VENTILATION_DELTA).
DRIER_OUTSIDE = 0.8
# An hour of running must lower the humidity by this many points, else the extractor rests; each useless hour in a row
# doubles the rest, up to REST_MAX. Outdoor air this much drier (g/m³) than at the last useless hour lifts the rest.
JUDGE, GAIN, REST, REST_MAX = timedelta(minutes=60), 1.0, timedelta(minutes=120), timedelta(hours=8)
CLEARER = 1.0
OFF_DELAY = timedelta(minutes=3)
# The advisor's run of the fast speed when it does not say how long (minutes).
BOOST_MINUTES = 20
# A shower's turbo during the room's night (minutes from the rise): the steam out, the sleepers left alone.
NIGHT_SHOWER = 20
# A VMC stopped by hand is left stopped this long.
MANUAL_REST = timedelta(minutes=120)


@dataclass
class Memory:
    """What one room's VMC remembers between two readings: lost at a restart, which only starts a run afresh."""
    run_since: datetime | None = None
    checkpoint: tuple | None = None            # (when, humidity) the current hour of running is judged from
    rest_until: datetime | None = None
    rests: int = 0                             # useless hours in a row
    rest_outside: float | None = None          # the outdoor water (g/m³) at the last useless hour
    boost_until: datetime | None = None
    slow: bool = False
    fast: bool = False
    slow_no_since: datetime | None = None
    fast_no_since: datetime | None = None
    seen: bool = False                         # the VMC seen running while advised
    manual_until: datetime | None = None
    manual_shower: str | None = None           # the shower going on when it was stopped by hand


def resume(memory: Memory, running: bool, now: datetime) -> None:
    """The VMC as it was before a restart or a reload: running, it goes on, its hour judged afresh from now. Forgotten,
    it stopped a minute until the advisor spoke again (Chambre P, 8 November at 12 h 53)."""
    if running:
        memory.slow = True
        memory.run_since = now
        memory.checkpoint = (now, None)


def mode_of(config) -> str:
    mode = (config or {}).get("ventilation_mode")
    return mode if mode in MODES else DEFAULT_MODE


def reading(view) -> dict:
    """What the VMC's advice reads in a room's view."""
    assessment = view.get("assessment") or {}
    features = assessment.get("features") or {}
    air = features.get("air") or {}
    humidity = features.get("humidity") or {}
    advice = view.get("advice3") or {}
    verdict = view.get("verdict") or {}
    measured = ((view.get("observations") or {}).get("indoor_humidity") or {}).get("value")
    inside, outside = assessment.get("indoor_absolute_humidity"), assessment.get("outdoor_absolute_humidity")
    shower = humidity.get("shower") if isinstance(humidity.get("shower"), dict) else None
    # The room's night as the advisor reads it (its sleeping hours, or the alarm armed for the night); the alarm alone
    # when the advisor has not said (just started, « Conseil en attente »); None when nothing says it.
    night = (advice["nuit"] if isinstance(advice.get("nuit"), bool)
             else True if (features.get("household") or {}).get("sleeping") is True else None)
    return {
        "humidity": verdict.get("humidity"),
        "measured": measured if isinstance(measured, (int, float)) and not isinstance(measured, bool) else None,
        # Unknown outdoor water: the VMC is not kept from drying on a guess.
        "drier_outside": inside is None or outside is None or inside - outside >= DRIER_OUTSIDE,
        "outside": outside if isinstance(outside, (int, float)) else None,
        "co2_high": air.get("co2_status") == "high",
        "night": night,
        "shower": bool(humidity.get("shower")),
        "shower_since": (shower or {}).get("since"),
        "shower_minutes": (shower or {}).get("minutes"),
        "advisor": advice.get("geste"),
        "advisor_minutes": advice.get("minutes"),
        # The 2.1 engine's « Lancez la VMC » (no 3.0 advice): the slow speed.
        "asked": not advice and verdict.get("gesture") == "ventilation",
    }


def _settled(memory, key, wanted, now):
    """`wanted` as said: yes at once, no once it has lasted OFF_DELAY."""
    since_key = f"{key}_no_since"
    if wanted:
        setattr(memory, since_key, None)
        setattr(memory, key, True)
    elif getattr(memory, key):
        since = getattr(memory, since_key) or now
        setattr(memory, since_key, since)
        if now - since >= OFF_DELAY:
            setattr(memory, key, False)
            setattr(memory, since_key, None)
    return getattr(memory, key)


def _shower_counts(r):
    """A shower runs the turbo, at night for its first NIGHT_SHOWER minutes only."""
    if not r["shower"]:
        return False
    minutes = r["shower_minutes"]
    return not (r["night"] and isinstance(minutes, (int, float)) and minutes >= NIGHT_SHOWER)


def _fast(r, memory, now, has_boost):
    if not has_boost:
        memory.boost_until = None
        return False
    if r["advisor"] == "boost":
        minutes = r["advisor_minutes"] if isinstance(r["advisor_minutes"], (int, float)) and r["advisor_minutes"] > 0 else BOOST_MINUTES
        memory.boost_until = max(memory.boost_until or now, now + timedelta(minutes=minutes))
    elif r["advisor"] == "boost_off":
        memory.boost_until = None
    return _shower_counts(r) or (memory.boost_until is not None and now < memory.boost_until)


def _rest(memory, r, now):
    """An hour that did not dry: the rest doubles with each one in a row."""
    memory.run_since = memory.checkpoint = None
    memory.rest_until = now + min(REST * 2 ** memory.rests, REST_MAX)
    memory.rests += 1
    memory.rest_outside = r["outside"]


def _resting(memory, r, now):
    if memory.rest_until is None or now >= memory.rest_until:
        return False
    # Outdoor air clearly drier than at the last useless hour: it may dry now.
    if r["outside"] is not None and memory.rest_outside is not None and memory.rest_outside - r["outside"] >= CLEARER:
        memory.rest_until = None
        memory.rests = 0
        return False
    return True


def _on_demand(r, memory, now):
    """The extractor's slow speed: when it helps, never at night, rested after an hour that did nothing."""
    if r["night"]:
        memory.run_since = memory.checkpoint = None
        return False
    if _resting(memory, r, now):
        return False
    running = memory.run_since is not None
    # The night not known (the advisor not heard yet): no run is started on a guess.
    if r["night"] is None and not running:
        return False
    humid = r["humidity"] in (KEEP if running else START) and r["drier_outside"]
    wanted = humid or r["co2_high"] or r["asked"]
    if not wanted:
        memory.run_since = memory.checkpoint = None
        return False
    if not running:
        memory.run_since = now
        memory.checkpoint = (now, r["measured"])
        return True
    # Judged on the humidity only when it is the reason: CO₂ or an explicit ask keep it running.
    when, before = memory.checkpoint or (now, r["measured"])
    if humid and not r["co2_high"] and not r["asked"] and now - when >= JUDGE:
        if before is not None and r["measured"] is not None and before - r["measured"] < GAIN:
            _rest(memory, r, now)
            return False
        memory.rests = 0
        memory.checkpoint = (now, r["measured"])
    return True


def _stopped_by_hand(memory, r, running, now) -> bool:
    """True while the VMC stopped by hand is left alone. `running`: the speeds' entities on (True), off (False) or unknown
    (None); seen running while advised, then all off while still advised, it was stopped by someone."""
    if memory.manual_until is not None:
        new_shower = r["shower_since"] is not None and r["shower_since"] != memory.manual_shower and _shower_counts(r)
        if now < memory.manual_until and not new_shower:
            return True
        memory.manual_until = memory.manual_shower = None
    known = [on for on in (running or ()) if on is not None]
    advised = memory.slow or memory.fast
    if not advised or not known:
        memory.seen = memory.seen and advised
        return False
    if any(known):
        memory.seen = True
        return False
    if not memory.seen:
        return False
    # Running, advised, now all off: the person stopped it.
    memory.seen = False
    memory.manual_until = now + MANUAL_REST
    memory.manual_shower = r["shower_since"]
    memory.boost_until = memory.run_since = memory.checkpoint = None
    memory.slow = memory.fast = False
    memory.slow_no_since = memory.fast_no_since = None
    return True


def advise(view, config, memory: Memory, now: datetime, running: tuple | None = None) -> dict:
    """{"slow": bool, "fast": bool|None, "mode": str} for a room's VMC; slow False and fast None without one.
    `running`: (slow speed on, fast speed on) as the entities say, None when unknown."""
    sources = (config or {}).get("sources") or {}
    mode = mode_of(config)
    has_vmc, has_boost = bool(sources.get("ventilation")), bool(sources.get("ventilation_boost"))
    if not has_vmc and not has_boost:
        return {"slow": False, "fast": None, "mode": mode}
    r = reading(view)
    if _stopped_by_hand(memory, r, running, now):
        return {"slow": mode == "continuous", "fast": False if has_boost else None, "mode": mode}
    fast = _settled(memory, "fast", _fast(r, memory, now, has_boost), now)
    slow = True if mode == "continuous" else _on_demand(r, memory, now)
    slow = _settled(memory, "slow", slow or fast, now)
    return {"slow": slow, "fast": fast if has_boost else None, "mode": mode}
