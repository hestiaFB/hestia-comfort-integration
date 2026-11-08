"""What the VMC should do now, for automations: its slow speed (« VMC conseillée ») and its fast one (« Turbo conseillé »).

Two ways a ventilation runs, set for each room (« Fonctionnement », Frank, 7 November):
- « En continu »: a classic VMC. Its slow speed never stops; only its fast speed comes and goes.
- « À la demande »: an extractor, run when it helps: the air too humid while the outdoor air is drier, or too much CO₂.
  Never during the room's night (its sleeping hours, or the alarm armed for the night), and stopped when an hour of
  running did not lower the humidity: it then rests two hours before being advised again.
The fast speed (Turbo), when the room has one: a shower going on (in a room that declares one, engine/shower.py), or the
advisor's « Lancez la VMC rapide » for the minutes it says. With the fast speed, the slow one is advised too: a two-speed
VMC runs both contactors.
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
# An hour of running must lower the humidity by this many points, else the extractor rests.
JUDGE, GAIN, REST = timedelta(minutes=60), 1.0, timedelta(minutes=120)
OFF_DELAY = timedelta(minutes=3)
# The advisor's run of the fast speed when it does not say how long (minutes).
BOOST_MINUTES = 20


@dataclass
class Memory:
    """What one room's VMC remembers between two readings: lost at a restart, which only starts a run afresh."""
    run_since: datetime | None = None
    checkpoint: tuple | None = None            # (when, humidity) the current hour of running is judged from
    rest_until: datetime | None = None
    boost_until: datetime | None = None
    slow: bool = False
    fast: bool = False
    slow_no_since: datetime | None = None
    fast_no_since: datetime | None = None


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
    # The room's night as the advisor reads it (its sleeping hours, or the alarm armed for the night); the alarm alone
    # when the advisor has not said (just started, « Conseil en attente »); None when nothing says it.
    night = (advice["nuit"] if isinstance(advice.get("nuit"), bool)
             else True if (features.get("household") or {}).get("sleeping") is True else None)
    return {
        "humidity": verdict.get("humidity"),
        "measured": measured if isinstance(measured, (int, float)) and not isinstance(measured, bool) else None,
        # Unknown outdoor water: the VMC is not kept from drying on a guess.
        "drier_outside": inside is None or outside is None or inside - outside >= DRIER_OUTSIDE,
        "co2_high": air.get("co2_status") == "high",
        "night": night,
        "shower": bool(humidity.get("shower")),
        # The 2.1 engine's « Lancez la VMC » (no 3.0 advice): the slow speed.
        "asked": not advice and verdict.get("gesture") == "ventilation",
        "advisor": advice.get("geste"),
        "advisor_minutes": advice.get("minutes"),
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


def _fast(r, memory, now, has_boost):
    if not has_boost:
        memory.boost_until = None
        return False
    if r["advisor"] == "boost":
        minutes = r["advisor_minutes"] if isinstance(r["advisor_minutes"], (int, float)) and r["advisor_minutes"] > 0 else BOOST_MINUTES
        memory.boost_until = max(memory.boost_until or now, now + timedelta(minutes=minutes))
    elif r["advisor"] == "boost_off":
        memory.boost_until = None
    return r["shower"] or (memory.boost_until is not None and now < memory.boost_until)


def _on_demand(r, memory, now):
    """The extractor's slow speed: when it helps, never at night, rested after an hour that did nothing."""
    if r["night"]:
        memory.run_since = memory.checkpoint = None
        return False
    if memory.rest_until is not None and now < memory.rest_until:
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
            memory.run_since = memory.checkpoint = None
            memory.rest_until = now + REST
            return False
        memory.checkpoint = (now, r["measured"])
    return True


def advise(view, config, memory: Memory, now: datetime) -> dict:
    """{"slow": bool, "fast": bool|None, "mode": str} for a room's VMC; slow False and fast None without one."""
    sources = (config or {}).get("sources") or {}
    mode = mode_of(config)
    has_vmc, has_boost = bool(sources.get("ventilation")), bool(sources.get("ventilation_boost"))
    if not has_vmc and not has_boost:
        return {"slow": False, "fast": None, "mode": mode}
    r = reading(view)
    fast = _settled(memory, "fast", _fast(r, memory, now, has_boost), now)
    slow = True if mode == "continuous" else _on_demand(r, memory, now)
    slow = _settled(memory, "slow", slow or fast, now)
    return {"slow": slow, "fast": fast if has_boost else None, "mode": mode}
