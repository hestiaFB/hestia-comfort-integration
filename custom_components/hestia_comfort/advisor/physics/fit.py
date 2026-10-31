"""How the twin learns its room: its physical parameters fitted on what the advisor needs, forecasts of one and three hours.

From every half hour of the past days, the twin forecasts the next three hours with the weather, heating and windows that
really came, starting from the measured air; the parameters are moved until those forecasts come closest to what was
then measured (a Nelder-Mead search, no library needed). The walls are followed all along from the measured air.

Why not a filter learning step by step: at five minutes a sensor reporting 0.1 °C steps is mostly noise, and parameters
learned on it forecast poorly at three hours (bench of 31 October, CONCEPTION-MOTEUR.md § 1). Each parameter is pulled
gently toward its ordinary value, so that one that the days could not show (a heating that hardly ran, a window never
opened) stays plausible instead of wandering.
"""
from dataclasses import dataclass, replace
from datetime import datetime
import math

from .thermal import Inputs, Params, step

# What is fitted: (name, as a logarithm of its ordinary value, first move of the search).
FREE = (("h_env", True, 0.5), ("heat", True, 0.5), ("sun", True, 0.5), ("window", True, 0.5), ("cm", True, 0.5),
        ("h_am", True, 0.5), ("gains", False, 80.0), ("rhythm_cos", False, 60.0), ("rhythm_sin", False, 60.0),
        ("share", False, 0.1), ("glass", True, 0.5))
# Steps of the two horizons (five minutes each): one hour, three hours.
HOUR, THREE = 12, 36
# How strongly a logarithm is pulled back toward the ordinary value; far more strongly when the value was declared (a
# heater's power read in its thermostat): the days may nudge it, never overrule it.
PULL, HELD = 0.002, 2.0
SEARCH = 400


@dataclass(frozen=True)
class Sample:
    when: datetime
    measured: float | None      # the air, °C
    inputs: Inputs | None


@dataclass(frozen=True)
class Score:
    hour: float         # mean error at one hour (°C)
    three: float        # mean error at three hours
    still_hour: float   # « nothing changes », for comparison
    still_three: float
    opened: float       # mean error at one hour while a window was open
    opened_bias: float  # its mean sign: positive, the twin forecast too warm
    opened_cases: int
    forecasts: int


def _mean(values, signed=False):
    return (sum(values) if signed else sum(abs(v) for v in values)) / len(values) if values else float("nan")


# The twin's error lasts from one hour to the next: what it missed over the last hour is added to its next forecast,
# fading over this many hours. « offset » adds that last error as it was; « rate » takes it as a drift per hour.
# Bench of 31 October (10 days, 5 rooms): « offset » brings the one-hour error from 0.25 to 0.21 °C on average and, with a
# window open, from 0.42 to 0.29 °C (Chambre AL) and 0.26 to 0.18 °C (salon); « rate » does as well at one hour, less well
# with a window open. « offset » is the twin's way.
RECENT_HOURS = 2.0
RECENT = (None, "offset", "rate")
DEFAULT_RECENT = "offset"


def _simulate(p: Params, samples: list[Sample], i: int, air: float, mass: float, steps: int):
    """The air after `steps` steps from sample `i`, with the inputs that really came; None across a gap."""
    for k in range(steps):
        u = samples[i + k].inputs
        if u is None:
            return None
        air, mass = step(p, air, mass, u)
    return air


def correction(kind: str | None, missed: float | None, k: int) -> float:
    """What the error of the last hour adds to the forecast `k` steps ahead."""
    if kind is None or missed is None:
        return 0.0
    fade = math.exp(-k / (RECENT_HOURS * HOUR))
    return missed * fade * (1.0 if kind == "offset" else (k + 1) / HOUR)


def forecasts(p: Params, samples: list[Sample], since: datetime | None = None, until: datetime | None = None,
              recent: str | None = DEFAULT_RECENT):
    """Every half-hour forecast of one and three hours between `since` and `until`, with what was then measured:
    (start, measured at start, forecast at one hour, measured then, forecast at three hours, measured then, window open).
    `recent`: how the error of the last hour corrects the forecast (`RECENT`)."""
    out, walls, walls_at = [], None, {}
    for i, s in enumerate(samples):
        if s.inputs is None or s.measured is None:
            walls = None
            continue
        walls = s.measured if walls is None else walls
        walls_at[i] = walls
        inside = (since is None or s.when >= since) and (until is None or s.when < until)
        if inside and s.when.minute % 30 == 0 and i + THREE < len(samples):
            missed = None
            if recent and (i - HOUR) in walls_at:
                then = samples[i - HOUR]
                guessed = _simulate(p, samples, i - HOUR, then.measured, walls_at[i - HOUR], HOUR)
                missed = None if guessed is None else s.measured - guessed
            air, mass, at_hour, opened = s.measured, walls, None, False
            for k in range(THREE):
                u = samples[i + k].inputs
                if u is None:
                    air = None
                    break
                opened = opened or (k < HOUR and bool(u.windows))
                air, mass = step(p, air, mass, u)
                if k == HOUR - 1:
                    at_hour = air + correction(recent, missed, k)
            if air is not None:
                out.append((s.when, s.measured, at_hour, samples[i + HOUR].measured, air + correction(recent, missed, THREE - 1),
                            samples[i + THREE].measured, opened))
        # The walls follow the measured air.
        _, walls = step(p, s.measured, walls, s.inputs)
    return out


def score(p: Params, samples: list[Sample], since=None, until=None, recent: str | None = DEFAULT_RECENT) -> Score:
    hour, three, still_hour, still_three, opened = [], [], [], [], []
    for _, now, f1, m1, f3, m3, was_open in forecasts(p, samples, since, until, recent):
        if m1 is not None:
            hour.append(f1 - m1)
            still_hour.append(now - m1)
            if was_open:
                opened.append(f1 - m1)
        if m3 is not None:
            three.append(f3 - m3)
            still_three.append(now - m3)
    return Score(_mean(hour), _mean(three), _mean(still_hour), _mean(still_three), _mean(opened), _mean(opened, signed=True),
                 len(opened), len(three))


def gestures(p: Params, samples: list[Sample], since=None, until=None, steps: int = HOUR) -> list[dict]:
    """What each gesture did, against what the twin said it would (CAHIER-MOTEUR.md § 18.3, the main indicator).

    A gesture: a window that opens, or a connected shutter that moves by a third or more. For each, over the next `steps`:
    the measured change of the air, the change the twin forecast with the gesture, and without it. The twin is right on a
    gesture when its forecast change matches the measured one; « without » shows what it thought the gesture itself did."""
    out, walls = [], None
    for i, s in enumerate(samples):
        if s.inputs is None or s.measured is None:
            walls = None
            continue
        walls = s.measured if walls is None else walls
        before = samples[i - 1].inputs if i else None
        inside = (since is None or s.when >= since) and (until is None or s.when < until)
        if inside and before is not None and i + steps < len(samples) and samples[i + steps].measured is not None:
            kind = ("window" if s.inputs.windows and not before.windows
                    else "shutter" if abs(s.inputs.shade - before.shade) >= 1 / 3 else None)
            if kind:
                undone = [replace(x.inputs, windows=before.windows) if kind == "window" else replace(x.inputs, shade=before.shade)
                          for x in samples[i:i + steps] if x.inputs is not None]
                with_it = _simulate(p, samples, i, s.measured, walls, steps)
                if with_it is not None and len(undone) == steps:
                    air, mass = s.measured, walls
                    for u in undone:
                        air, mass = step(p, air, mass, u)
                    out.append({"when": s.when, "kind": kind, "measured": samples[i + steps].measured - s.measured,
                                "forecast": with_it - s.measured, "without": air - s.measured})
        _, walls = step(p, s.measured, walls, s.inputs)
    return out


def params_of(base: Params, x) -> Params:
    return replace(base, **{name: (math.exp(v) * getattr(base, name) if log else v) for (name, log, _), v in zip(FREE, x)})


def _start(base: Params):
    return [0.0 if log else getattr(base, name) for name, log, _ in FREE]


def fit(base: Params, samples: list[Sample], until: datetime | None = None, iterations: int = SEARCH,
        held: frozenset[str] = frozenset(), recent: str | None = DEFAULT_RECENT) -> Params:
    """The parameters that forecast the past days best, from the room's ordinary ones; those in `held` were declared.
    `recent`: fitted with the correction the forecasts will be given (`RECENT`)."""
    def cost(x):
        s = score(params_of(base, x), samples, until=until, recent=recent)
        if not s.forecasts:
            return float("inf")
        pull = sum((HELD if name in held else PULL) * v * v for (name, log, _), v in zip(FREE, x) if log)
        return s.hour + s.three + pull
    best = _nelder_mead(cost, _start(base), [move for _, _, move in FREE], iterations)
    return params_of(base, best)


def _nelder_mead(f, x0, moves, iterations):
    n = len(x0)
    points = [list(x0)] + [[x + (m if i == j else 0.0) for j, x in enumerate(x0)] for i, m in enumerate(moves)]
    values = [f(p) for p in points]
    for _ in range(iterations):
        order = sorted(range(n + 1), key=lambda i: values[i])
        points, values = [points[i] for i in order], [values[i] for i in order]
        centre = [sum(p[j] for p in points[:-1]) / n for j in range(n)]

        def towards(t):
            return [centre[j] + t * (points[-1][j] - centre[j]) for j in range(n)]
        reflected = towards(-1.0)
        fr = f(reflected)
        if fr < values[0]:
            expanded = towards(-2.0)
            fe = f(expanded)
            points[-1], values[-1] = (expanded, fe) if fe < fr else (reflected, fr)
        elif fr < values[-2]:
            points[-1], values[-1] = reflected, fr
        else:
            contracted = towards(0.5)
            fc = f(contracted)
            if fc < values[-1]:
                points[-1], values[-1] = contracted, fc
            else:
                points = [points[0]] + [[points[0][j] + 0.5 * (p[j] - points[0][j]) for j in range(n)] for p in points[1:]]
                values = [values[0]] + [f(p) for p in points[1:]]
    return points[min(range(n + 1), key=lambda i: values[i])]
