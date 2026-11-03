"""The window open now, seen at work: what the twin said it would do since it was opened, against what was measured.

A window barely open, or tilted, lets through a fraction of the air the twin gives it (Chambre P, 3 November: one leaf
ajar, 0.1 °C lost in twenty minutes with 10 °C outside, the humidity up from 67 to 69 % where the twin forecast −13
points). After a few minutes the measures say how much of the forecast the window really does; the rest of the airing
is judged with that share (CAHIER-MOTEUR.md § 4.1, the gesture under way).
"""
from dataclasses import dataclass, replace
from datetime import datetime

from .physics.thermal import STEP
from .physics.water import absolute

# The window's work is read from this long after it was first seen open: sooner, a sensor's step is all one sees.
OBSERVE_MINUTES = 10
# The forecast change is read from this much at least (°C; g/m³ of water): smaller, the ratio is noise. The air first,
# its heat free of the room's own sources of water; the water when the air hardly changes (a mild evening).
HEAT_READ, WATER_READ = 0.3, 0.5
# The share is kept within these: a window does nothing at worst, half as much again as forecast at best.
LOWEST, HIGHEST = 0.0, 1.5
# Under this share, the window renews little of the air: said in « Bon à savoir ».
WEAK = 0.5


@dataclass(frozen=True)
class Opened:
    """The opening as first seen, with the twin's forecast for it: the windows left as they are, every step from then."""
    since: datetime
    air: float
    humidity: float | None
    forecast_air: tuple[float, ...]
    forecast_humidity: tuple[float, ...] = ()


def seen_share(opened: Opened, now: datetime, air: float, humidity: float | None) -> float | None:
    """The share of the forecast the open window shows since it was opened: 1 as forecast, 0 nothing at all; None when
    too soon, or when the forecast changes too little to be read."""
    minutes = (now - opened.since).total_seconds() / 60
    k = int(round(minutes * 60 / STEP)) - 1
    if minutes < OBSERVE_MINUTES or k < 0 or not opened.forecast_air:
        return None
    k = min(k, len(opened.forecast_air) - 1)
    told = opened.forecast_air[k] - opened.air
    if abs(told) >= HEAT_READ:
        share = (air - opened.air) / told
    elif humidity is not None and opened.humidity is not None and len(opened.forecast_humidity) > k:
        then = absolute(opened.air, opened.humidity)
        told = absolute(opened.forecast_air[k], opened.forecast_humidity[k]) - then
        if abs(told) < WATER_READ:
            return None
        share = (absolute(air, humidity) - then) / told
    else:
        return None
    return min(HIGHEST, max(LOWEST, share))


def scaled(twins, share: float):
    """The twins with the windows doing this share of what they learned: the heat's, and each air's."""
    def flow(pair):
        return (pair[0], pair[1] * share)
    return replace(twins, heat=replace(twins.heat, window=twins.heat.window * share), water_flow=flow(twins.water_flow),
                   air_flow=flow(twins.air_flow), particles_flow=flow(twins.particles_flow), voc_flow=flow(twins.voc_flow))
