"""How the twins of the water, the CO₂ and the particles learn their room: forecasts of one and three hours from every
half hour, scored against what was then measured, and what each window opening did against what was forecast.

Shared by the bench (advisor/bench/air_check.py, with SciPy's search) and the nightly learning (advisor/nightly.py, with
the twin's own search, advisor/physics/fit.py): Home Assistant has no SciPy. A twin is a vector `x`: the logarithms of
its learned leaks and window multipliers, then its own values (`vector`, `values`).
"""
from dataclasses import replace
import math

from ..notes import SETTLE_STEPS, SHORTEST_STEPS, case, episodes, left_out, put_aside
from .air import AirParams, ParticleParams, air_step, particles_step
from .vents import leak_flow, window_flow
from .water import WaterParams, bounded, water_step

HOUR, THREE = 12, 36
# Eight hours ahead, from every sixth hour, without the last hour's correction (it fades within two): a twin good at one
# and three hours may still drift over a night (bilan of 11 November: Chambre P, 89 % foreseen at 7 h, 82 % measured,
# sources of 186 g/h at midnight balanced by leaks ×3.7). Weighed NIGHT_WEIGHT in the score.
NIGHT, NIGHT_EVERY, NIGHT_WEIGHT = 96, 6, 0.5


# Logarithms are kept within this, the search's first moves are these: a search started with the default tiny moves on a
# value at zero never leaves it (first run of 31 October, every room stuck at ×1.00).
BOUND = 4.0
MOVES = {"water": [0.7, 0.7, 0.7, 0.7, 20.0, 15.0, 15.0], "air": [0.7, 0.7, 0.02, 0.015, 0.015],
         "particles": [0.7, 0.7, 0.7, 5.0, 50.0, 40.0, 40.0]}
START = {"particles": [0.0, 0.0, math.log(0.5), 10.0, 50.0, 0.0, 0.0]}


def _e(v):
    return math.exp(min(BOUND, max(-BOUND, v)))


def _flow(x, volume, sample):
    """Outdoor air coming in, m³/h: the leaks and the open windows, each scaled by what was learned."""
    u = sample.inputs
    leaks = _e(x[0]) * leak_flow(volume)
    windows = _e(x[1]) * u.cross * sum(window_flow(a, h, sample.measured, u.outdoor, u.wind) for a, h in u.windows)
    return leaks + windows + u.vent


def _stepper(kind, x, volume, rows):
    """The twin's five-minute step at row `i`: (value, hidden) → (value, hidden) five minutes on; `sample` stands for the
    row's own (what acted on the room), to forecast without a gesture."""
    def model(value, hidden, i, sample=None):
        s, _, outdoor = rows[i]
        s = sample or s
        flow = _flow(x, volume, s)
        if kind == "water":
            p = WaterParams(volume, *bounded(_e(x[2]), _e(x[3]), x[4], x[5], x[6]))
            return water_step(p, value, hidden, outdoor, flow, s.inputs.hour)
        if kind == "particles":
            p = ParticleParams(volume, _e(x[2]), x[3], x[4], x[5], x[6])
            return particles_step(p, value, flow, s.inputs.hour, purifier=s.inputs.purifier), hidden
        p = AirParams(volume, x[2], x[3], x[4])
        return air_step(p, value, flow, s.inputs.hour), hidden
    return model


def _ok(rows):
    def ok(i):
        return 0 <= i < len(rows) and rows[i][0].inputs is not None and rows[i][0].measured is not None \
            and rows[i][1] is not None and rows[i][2] is not None
    return ok


def _run(kind, x, volume, rows, since, until):
    """Forecasts of one and three hours from every half hour in [since, until), with the last hour's error added (as the
    heat's twin does); and each window opening. rows: (sample, measured value, outdoor value) every five minutes."""
    out = {"hour": [], "three": [], "night": [], "still_hour": [], "still_three": [], "gestures": [], "devices": []}

    model, ok = _stepper(kind, x, volume, rows), _ok(rows)

    # The one-hour forecast from each start, before its correction: it is what the start an hour later missed.
    hidden, track, raw = None, {}, {}
    for i, (s, value, outdoor) in enumerate(rows):
        if not ok(i):
            hidden = None
            continue
        hidden = value if hidden is None else hidden
        track[i] = hidden
        inside = since <= s.when < until
        if inside and s.when.minute % 30 == 0 and ok(i + THREE):
            missed = 0.0
            if i - HOUR in raw:
                missed = value - raw[i - HOUR]
            elif i - HOUR in track and all(ok(j) for j in range(i - HOUR, i)):
                v, h = rows[i - HOUR][1], track[i - HOUR]
                for j in range(i - HOUR, i):
                    v, h = model(v, h, j)
                missed = value - v
            v, h, at_hour, good = value, hidden, None, True
            for k in range(THREE):
                if not ok(i + k):
                    good = False
                    break
                v, h = model(v, h, i + k)
                if k == HOUR - 1:
                    raw[i] = v
                    at_hour = v + missed * math.exp(-k / 24)
            if good:
                out["hour"].append(at_hour - rows[i + HOUR][1])
                out["still_hour"].append(value - rows[i + HOUR][1])
                out["three"].append(v + missed * math.exp(-(THREE - 1) / 24) - rows[i + THREE][1])
                out["still_three"].append(value - rows[i + THREE][1])
        if inside and s.when.minute == 0 and s.when.hour % NIGHT_EVERY == 0 and all(ok(i + k) for k in range(NIGHT + 1)):
            v, h = value, hidden
            for k in range(NIGHT):
                v, h = model(v, h, i + k)
            out["night"].append(v - rows[i + NIGHT][1])
        before = rows[i - 1][0].inputs if i else None
        if inside and before is not None and s.inputs.windows and not before.windows and all(ok(i + k) for k in range(HOUR + 1)):
            v, h = value, hidden
            for k in range(HOUR):
                v, h = model(v, h, i + k)
            out["gestures"].append((rows[i + HOUR][1] - value, v - value, s.when))
        # A device started: the VMC's fast speed, the purifier (what it did, against what the twin forecast).
        started = before is not None and ("boost" if s.inputs.vent > before.vent else
                                          "purify" if s.inputs.purifier > before.purifier else None)
        if inside and started and all(ok(i + k) for k in range(HOUR + 1)):
            v, h = value, hidden
            for k in range(HOUR):
                v, h = model(v, h, i + k)
            out["devices"].append((rows[i + HOUR][1] - value, v - value, s.when, started))
        _, hidden = model(value, hidden, i)
    return out


# What a gesture stops, to forecast the room without it: the windows, the VMC's fast speed, the purifier.
WITHOUT = {"window": lambda u: replace(u, windows=(), cross=1.0), "boost": lambda u: replace(u, vent=0.0),
           "purify": lambda u: replace(u, purifier=0.0)}
RUNNING = {"window": lambda u: bool(u.windows), "boost": lambda u: u.vent > 0, "purify": lambda u: u.purifier > 0}


def notes(kind, subject, x, volume, rows, gesture="window", skipped=(), why: dict | None = None) -> list[list]:
    """Each gesture — a window opening, a run of the VMC's fast speed or of the purifier — judged an hour after it ended
    against the twin without it (advisor/notes.py). Left out when anything else that the gesture's own forecast holds
    still moved while it ran or while the room settled: the windows, the VMC, the purifier; and those put aside during
    the day (`skipped`). rows: (sample, measured value, outdoor value) every five minutes; `why` counts the gestures left
    out, by reason (advisor/notes.py `left_out`)."""
    model, ok = _stepper(kind, x, volume, rows), _ok(rows)
    hidden_at, hidden = {}, None
    for i, (s, value, _) in enumerate(rows):
        if not ok(i):
            hidden = None
            continue
        hidden = value if hidden is None else hidden
        hidden_at[i] = hidden
        _, hidden = model(value, hidden, i)
    running, without = RUNNING[gesture], WITHOUT[gesture]
    others = [g for g in RUNNING if g != gesture]
    flags = [running(s.inputs) if ok(i) else None for i, (s, _, _) in enumerate(rows)]
    out = []
    for i, j in episodes(flags):
        end = j + SETTLE_STEPS
        reason = ("trop_court" if j - i < SHORTEST_STEPS
                  else "pas_encore" if end >= len(rows)
                  else "ecarte_le_jour" if put_aside(skipped, rows[i][0].when)
                  else "trou" if i not in hidden_at or not all(ok(k) for k in range(i - 1, end + 1))
                  else "rouverte" if any(flags[k] for k in range(j, end + 1))
                  else "appareil" if any(RUNNING[g](rows[k][0].inputs) != RUNNING[g](rows[i - 1][0].inputs)
                                         for g in others for k in range(i, end + 1))
                  else None)
        if reason:
            left_out(why, reason)
            continue
        start = rows[i][1]
        v, h = start, hidden_at[i]
        w, hw = start, hidden_at[i]
        for k in range(i, end):
            v, h = model(v, h, k)
            s = rows[k][0]
            w, hw = model(w, hw, k, replace(s, inputs=without(s.inputs)) if k < j else None)
        noted = case(subject, rows[i][0].when, v, w, rows[end][1])
        if noted:
            out.append(noted)
        left_out(why, None if noted else "illisible")
    return out


KINDS = {"water": "humidity", "air": "co2", "particles": "particles"}
# Each twin of the air as kept (jumeaux.json): (its key, the law it follows, its subject). The VOC index follows the
# particles' law.
TWINS = (("water", "water", "humidity"), ("air", "air", "co2"), ("particles", "particles", "particles"),
         ("voc", "particles", "voc"))


def first(kind: str) -> list[float]:
    """Where a twin's search starts before anything is learned."""
    if kind in START:
        return list(START[kind])
    return [0.0, 0.0, math.log(0.5), math.log(5.0), 30.0, 0.0, 0.0] if kind == "water" else [0.0, 0.0, 0.036, 0.0, 0.0]


def untrained(learned: dict) -> set[str]:
    """The subjects whose twin of the air is still the one it started from: no night has fitted it to the room's measures
    (no history of its sensor, or never better). Its forecast is ordinary values only, and backs no gesture (Salon ·
    Cuisine, 4-5 November: « Aérez 5 min, le COV retombe en 5 min », the VOC twin never compared with a measure)."""
    out = set()
    for key, kind, subject in TWINS:
        twin = learned.get(key)
        if not isinstance(twin, dict):
            continue
        start, _ = values(kind, first(kind), twin.get("volume") or 1.0)
        if all(k in twin and abs(twin[k] - v) <= 1e-9 * max(1.0, abs(v)) for k, v in start.items() if k != "volume"):
            out.add(subject)
    return out


def vector(kind: str, values: dict, flow) -> list[float]:
    """A learned twin back as the search's vector: `values`, its parameters as kept; `flow`, its leaks and windows."""
    x = [math.log(flow[0]), math.log(flow[1])]
    if kind == "water":
        return x + [math.log(values["exchange"]), math.log(values["reserve"]), values["sources"], values["rhythm_cos"],
                    values["rhythm_sin"]]
    if kind == "air":
        return x + [values["sources"], values["rhythm_cos"], values["rhythm_sin"]]
    return x + [math.log(values["settling"]), values["outdoor"], values["sources"], values["rhythm_cos"], values["rhythm_sin"]]


def values(kind: str, x, volume: float) -> tuple[dict, list[float]]:
    """The search's vector as a twin's parameters to keep, and its leaks and windows multipliers."""
    flow = [_e(x[0]), _e(x[1])]
    if kind == "water":
        exchange, reserve, steady, cos_, sin_ = bounded(_e(x[2]), _e(x[3]), x[4], x[5], x[6])
        return {"volume": volume, "exchange": exchange, "reserve": reserve, "sources": steady, "rhythm_cos": cos_,
                "rhythm_sin": sin_}, flow
    if kind == "air":
        return {"volume": volume, "sources": x[2], "rhythm_cos": x[3], "rhythm_sin": x[4]}, flow
    return {"volume": volume, "settling": _e(x[2]), "outdoor": x[3], "sources": x[4], "rhythm_cos": x[5],
            "rhythm_sin": x[6]}, flow


def score(kind, x, volume, rows, since, until) -> float:
    """Mean error at one hour plus at three hours, and half the one at eight (NIGHT): what the search lowers. Infinite
    without a forecast."""
    e = _run(kind, x, volume, rows, since, until)
    if not e["three"]:
        return float("inf")
    found = sum(abs(v) for v in e["hour"]) / len(e["hour"]) + sum(abs(v) for v in e["three"]) / len(e["three"])
    if e["night"]:
        found += NIGHT_WEIGHT * sum(abs(v) for v in e["night"]) / len(e["night"])
    return found
