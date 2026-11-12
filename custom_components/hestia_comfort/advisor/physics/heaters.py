"""What each kind of heating does once its thermostat stops or starts it (CAHIER-MOTEUR.md § 6.7 bis, Frank, 5 November).

A convector gives off its heat as it is fed and stops at once; a radiator with a core (oil, stone, cast iron, central
heating's water) or a heated floor keeps giving it off after it is stopped, and is slow to warm again. The heat given
off follows the heat asked with a delay of the first order, one constant per kind: ordinary values, the household only
declares the kind (« Type » in the room's heating, convector when it says nothing). A wood stove is not put out by an
open window, whatever its thermostat asks; a heat pump gives about three times the electricity it spends.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Heater:
    lag: float = 0.0            # minutes for the heat given off to cover two thirds of the way to the heat asked
    window_cut: bool = True     # an open window stops it (its thermostat's « window_turn_off »)
    efficiency: float = 1.0     # kWh of heat per kWh paid
    # Share of its full power it still gives off while it burns and its thermostat asks 0 %: a pellet stove does not go
    # out, it idles (Frank, 12 November: « il tourne au ralenti mais il chauffe quand même ou maintient »).
    idle: float = 0.0


# Ordinary values per kind. A radiant panel heats the walls and the people more than a convector does (the ressenti,
# engine/feel.py) but holds no more heat: the same delay. A heat pump's seasonal COP (SCOP) is about 3 in France.
HEATERS = {
    "radiator": Heater(),                                   # convector, fan heater: the default
    "radiant": Heater(),
    "inertia": Heater(lag=30.0),                            # oil, stone, cast iron, central heating's water
    "floor": Heater(lag=180.0),
    "stove": Heater(lag=60.0, window_cut=False),            # wood stove, insert, fireplace
    "pellet": Heater(lag=20.0, idle=0.3),                  # its lowest flame: about a third of its power
    "ac": Heater(efficiency=3.0),                           # reversible air conditioning, heat pump
}
KINDS = tuple(HEATERS)


def heater(kind: str | None) -> Heater:
    """A kind's behaviour; a convector's when the kind is not declared or unknown."""
    return HEATERS.get(kind or "radiator", HEATERS["radiator"])


def given_off(given: float, asked: float, lag: float, dt: float) -> float:
    """The share of the full power given off `dt` seconds later, `given` now, `asked` by the thermostat (0 to 1)."""
    if lag <= 0:
        return asked
    return given + (asked - given) * (1 - math.exp(-dt / (lag * 60)))
