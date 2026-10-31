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
