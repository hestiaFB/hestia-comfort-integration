"""How much outdoor air comes in: through the leaks of a shut room, and through an open window.

The window follows the usual laws of natural ventilation (CIBSE AM10): the stack effect of the temperature gap across
its height, and the wind on its area, added in quadrature. Each window then learns its own multiplier (a curtain, a
half-open sash, a tilted pane): the law gives the order of magnitude, the room gives the rest.
"""
import math

GRAVITY = 9.81
# Discharge coefficient of a sharp-edged opening.
DISCHARGE = 0.6
# Wind-driven single-sided ventilation: 0.025 × area × wind speed (m/s).
WIND = 0.025
# Air changes per hour of an ordinary shut room.
LEAKS = 0.3


def window_flow(area: float, height: float, indoor: float, outdoor: float, wind: float | None = None) -> float:
    """Outdoor air (m³/h) through one window open wide, from its area (m²) and height (m), the indoor and outdoor
    temperatures (°C) and the wind (m/s) when known."""
    gap = abs(indoor - outdoor)
    mean = 273.15 + (indoor + outdoor) / 2
    stack = DISCHARGE * area / 3 * math.sqrt(GRAVITY * height * gap / mean)
    breeze = WIND * area * wind if wind else 0.0
    return 3600 * math.hypot(stack, breeze)


def leak_flow(volume: float) -> float:
    """Outdoor air (m³/h) that comes in through the leaks of a shut room."""
    return LEAKS * volume


def conductance(flow: float) -> float:
    """W/K carried by an air flow (m³/h): ρ·c of air, 0.34 Wh/m³K."""
    return 0.34 * flow
