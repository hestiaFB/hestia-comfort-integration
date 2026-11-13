"""Water: the vapour of a room's air, and the reserve its walls, fabrics and furniture hold and give back.

    V · dW/dt = Q·(We − W) + sources + k·V·(Wb − W)
    r·V · dWb/dt = k·V·(W − Wb)

W is in g/m³ (the humidity a sensor gives in % depends on the temperature, the water does not). Q is the outdoor air coming
in (advisor/physics/vents.py: leaks and open windows), the sources the household's water (sleep, showers, cooking), and the
reserve explains why the air dries fast while a window is open and the humidity comes back once it is shut. Stepped
implicitly, like the heat.
"""
from dataclasses import dataclass
import math

STEP = 300.0


def absolute(temperature: float, relative_humidity: float) -> float:
    """Water in the air, g/m³ (Magnus)."""
    return 6.112 * math.exp(17.67 * temperature / (temperature + 243.5)) * relative_humidity * 2.1674 / (273.15 + temperature)


def relative(temperature: float, water: float) -> float:
    """The humidity a sensor would read, %."""
    return min(100.0, water / absolute(temperature, 100.0) * 100.0)


@dataclass(frozen=True)
class WaterParams:
    volume: float           # m³
    exchange: float         # h⁻¹: how fast the reserve trades water with the air
    reserve: float          # the reserve's size, in volumes of air
    sources: float          # g/h, steady
    rhythm_cos: float = 0.0
    rhythm_sin: float = 0.0


# What a room's water can physically be (bilan of 13 November: Chambre AL learned −150 g/h of sources, the air renewed
# 55 times an hour against a reserve of 0.02 volumes; the Buanderie −8 g/h; the Chambre P 147 g/h swinging by 185). The
# household and the walls only add water: the steady sources are never negative and their daily rhythm never takes them
# below zero; the walls trade it within hours, not minutes, and hold at least two rooms of air (the realistic twins: 2 to 6).
EXCHANGE = (0.05, 5.0)      # h⁻¹
RESERVE = (2.0, 50.0)       # volumes of the room's air: the walls and the furniture of a lived-in room hold some
SOURCES_MAX = 150.0         # g/h, steady


def bounded(exchange: float, reserve: float, steady: float, rhythm_cos: float, rhythm_sin: float) -> tuple:
    """A twin's values within what a room can do: (exchange, reserve, sources, rhythm_cos, rhythm_sin)."""
    exchange = min(EXCHANGE[1], max(EXCHANGE[0], exchange))
    reserve = min(RESERVE[1], max(RESERVE[0], reserve))
    steady = min(SOURCES_MAX, max(0.0, steady))
    swing = math.hypot(rhythm_cos, rhythm_sin)
    if swing > steady:
        scale = steady / swing if swing else 0.0
        rhythm_cos, rhythm_sin = rhythm_cos * scale, rhythm_sin * scale
    return exchange, reserve, steady, rhythm_cos, rhythm_sin


def within(p: WaterParams) -> WaterParams:
    """A learned twin brought within what a room can do (`bounded`)."""
    return WaterParams(p.volume, *bounded(p.exchange, p.reserve, p.sources, p.rhythm_cos, p.rhythm_sin))


def sources(p: WaterParams, hour: float | None) -> float:
    if hour is None:
        return p.sources
    angle = 2 * math.pi * hour / 24
    return max(0.0, p.sources + p.rhythm_cos * math.cos(angle) + p.rhythm_sin * math.sin(angle))


def water_step(p: WaterParams, water: float, reserve: float, outdoor: float, flow: float, hour: float | None,
               dt: float = STEP) -> tuple[float, float]:
    """The air's water and the reserve's `dt` seconds later; `flow` in m³/h, `outdoor` in g/m³."""
    h = dt / 3600
    q, k, v, r = flow, p.exchange, p.volume, p.reserve
    a11, a12 = v / h + q + k * v, -k * v
    a21, a22 = -k * v, r * v / h + k * v
    b1 = v / h * water + q * outdoor + sources(p, hour)
    b2 = r * v / h * reserve
    det = a11 * a22 - a12 * a21
    return (b1 * a22 - a12 * b2) / det, (a11 * b2 - a21 * b1) / det
