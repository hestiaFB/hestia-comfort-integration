"""The coldest surfaces of a room: the corner of an outer wall and the inside of a window pane (CAHIER-MOTEUR.md § 4, the
dwelling: mould, condensation).

A surface sits between the room's air and the outside, closer to the room the better it is insulated: its temperature is
the outside's plus a share of the gap, the temperature factor of EN ISO 13788. The air's water, the same at the surface,
gives the humidity there: mould grows where it stays at 80 % or more (EN ISO 13788's criterion), water runs down a pane
once it falls under the dew point.
"""
import math

from .water import absolute, relative

# EN ISO 13788 temperature factors: an ordinary outer wall's corner, and a double-glazed pane (U 2.8 W/m²K, Rsi 0.13).
WALL_FACTOR = 0.7
GLASS_FACTOR = 0.64
# The inside of each glazing, its temperature factor 1 − U·Rsi (Rsi 0.13, U of advisor/physics/thermal.py GLAZINGS): a
# single pane is nearly at the outside's temperature and mists early, a triple one hardly ever.
GLASS_FACTORS = {"simple": 0.25, "double": GLASS_FACTOR, "triple": 0.87}
# Mould grows at a surface kept at this humidity or more (EN ISO 13788).
MOULD = 80.0


def surface(air: float, outdoor: float, factor: float = WALL_FACTOR) -> float:
    """°C of a surface between the room's air and the outside."""
    return outdoor + factor * (air - outdoor)


def surface_humidity(air: float, humidity: float, outdoor: float, factor: float = WALL_FACTOR) -> float:
    """% of humidity at that surface: the room's water, at the surface's temperature."""
    return min(100.0, relative(surface(air, outdoor, factor), absolute(air, humidity)))


def mould_risk(air: float, humidity: float, outdoor: float) -> bool:
    return surface_humidity(air, humidity, outdoor) >= MOULD


def mould_excess(air: float, humidity: float, outdoor: float) -> float:
    """Points of humidity above the mould's 80 % at the coldest corner: a measure without a cliff — a corner at 80.5 %
    and one at 79.5 % differ by one point, not by « risk » and « no risk »."""
    return max(0.0, surface_humidity(air, humidity, outdoor) - MOULD)


def dew_point(air: float, humidity: float) -> float:
    """°C under which the room's air leaves water on a surface (Magnus)."""
    a, b = 17.62, 243.12
    gamma = math.log(max(humidity, 1e-3) / 100) + a * air / (b + air)
    return b * gamma / (a - gamma)


def misted(air: float, humidity: float, outdoor: float, glazing: str | None = None) -> bool:
    """Whether the inside of a window pane mists over; `glazing`: the room's coldest, « simple », « double », « triple »."""
    return dew_point(air, humidity) >= surface(air, outdoor, GLASS_FACTORS.get(glazing or "double", GLASS_FACTOR))
