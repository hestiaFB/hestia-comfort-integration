"""The sun through each window: its position, the share a facade faces, and the watts that reach the room.

The same formulas as Hestia Comfort 2.1 (engine/twin.py `sun_position`, engine/assessment.py `facade_share`,
`facade_irradiance`), copied so that the advisor stays free of the 2.1 engine: what already works is taken as it is
(CAHIER-MOTEUR.md § 21). At home the position comes from Home Assistant's `sun.sun`; for the coming hours and on the
bench it is computed here.

An overhang above a window (eaves, a balcony, a canopy) is drawn by its shadow, not by a fixed share: in summer the high
sun stays above the window, in winter the low sun passes under it (Frank, 5 November: the Salon's French windows, under
a 1 m overhang, full of sun on a November noon — the former « a third of the sun » hid it).
"""
from dataclasses import dataclass
from datetime import timedelta
import math

EXPOSURES = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SO": 225, "O": 270, "NO": 315}
# Under an overhang, the window sees this share of the sky's diffuse light.
SKY_UNDER = 0.7


@dataclass(frozen=True)
class Overhang:
    """An overhang above a window (REGLAGES-3.md § 4.4), in metres: A its depth from the wall, B the gap from its underside
    down to the window's top, and the window's height. Not declared, the ordinary ones of the panel's examples."""
    depth: float = 0.6
    gap: float = 0.3
    height: float = 2.1


def lit_share(overhang: Overhang, bearing: float | None, elevation: float, azimuth: float) -> float:
    """Share of the window's height the direct sun reaches under its overhang: the shadow falls the depth × the tangent
    of the sun's height seen square to the wall (its profile angle) down the wall, from the overhang's edge."""
    if bearing is None or elevation <= 0:
        return 0.0
    square = math.cos(math.radians(((azimuth - bearing + 540) % 360) - 180))
    if square <= 0.01:
        return 0.0
    shadow = overhang.depth * math.tan(math.radians(min(elevation, 89.0))) / square
    return 1.0 - max(0.0, min(1.0, (shadow - overhang.gap) / max(overhang.height, 0.1)))
# A shut pane lets this share of the sun through; an open sash, all of it.
GLASS = 0.6


def sun_position(when, latitude, longitude):
    """Elevation and azimuth of the sun in degrees (NOAA's simplified formulas, within a degree)."""
    day = when.timetuple().tm_yday
    hour = when.hour + when.minute / 60 + when.second / 3600 - (when.utcoffset().total_seconds() / 3600 if when.utcoffset() else 0)
    gamma = 2 * math.pi / 365 * (day - 1 + (hour - 12) / 24)
    equation = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma) - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))
    declination = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma) - 0.006758 * math.cos(2 * gamma)
                   + 0.000907 * math.sin(2 * gamma) - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))
    angle = math.radians((hour * 60 + equation + 4 * longitude) / 4 - 180)
    lat = math.radians(latitude)
    cos_zenith = math.sin(lat) * math.sin(declination) + math.cos(lat) * math.cos(declination) * math.cos(angle)
    zenith = math.acos(max(-1.0, min(1.0, cos_zenith)))
    azimuth = math.degrees(math.atan2(math.sin(angle), math.cos(angle) * math.sin(lat) - math.tan(declination) * math.cos(lat))) + 180
    return 90 - math.degrees(zenith), azimuth % 360


def facade_share(bearing: float | None, elevation: float, azimuth: float) -> float:
    """Share of the sun facing a facade: cos(elevation)·cos(azimuth gap)."""
    if bearing is None or elevation <= 0:
        return 0.0
    gap = ((azimuth - bearing + 540) % 360) - 180
    return max(math.cos(math.radians(elevation)) * math.cos(math.radians(gap)), 0.0)


def facade_irradiance(share: float, elevation: float, solar: float, lit: float = 1.0, sky: float = 1.0) -> float:
    """W/m² on a vertical facade from the horizontal sun: the direct part it faces, never less than the diffuse light.
    `lit`: the share of the window the direct sun reaches; `sky`: the share of the sky it sees (an overhang)."""
    diffuse = solar * 0.15 * sky
    direct = 0.0
    if elevation > 5 and solar > 40:
        direct = min(solar / max(math.sin(math.radians(elevation)), 0.09) * share, 850) * lit
    return max(direct, diffuse)


def through_windows(solar: float, elevation: float, azimuth: float, windows, opened=()) -> float:
    """Watts of sun entering the room: each window's glazing × the sun on its facade, through glass or an open sash.
    `windows`: (glazed area, bearing or None, sheltered[, solar factor]) of each, sheltered being False, an Overhang, or
    True for an ordinary one; `opened`: the indexes of those open."""
    if solar <= 0 or elevation <= 0:
        return 0.0
    total = 0.0
    for i, (area, bearing, sheltered, *pane) in enumerate(windows):
        share = facade_share(bearing, elevation, azimuth)
        if sheltered:
            roof = sheltered if isinstance(sheltered, Overhang) else Overhang()
            watts = facade_irradiance(share, elevation, solar, lit_share(roof, bearing, elevation, azimuth), SKY_UNDER)
        else:
            watts = facade_irradiance(share, elevation, solar)
        # A shut pane lets its solar factor through (a double glazing's, GLASS, when not given); an open sash, all of it.
        total += area * watts * (1.0 if i in opened else (pane[0] if pane else GLASS))
    return total


# The sun is on a facade when it faces it within this angle and stands this high: lower or more sideways, it grazes the
# wall and hardly enters (Adaptive Cover Pro, on Chambre P's window: 60 to 86° each side, 8° high).
FACING, LOW_SUN = 75.0, 5.0
BEARINGS = ((0, "north"), (45, "north_east"), (90, "east"), (135, "south_east"), (180, "south"), (225, "south_west"),
            (270, "west"), (315, "north_west"))


def facing(bearing: float | None, elevation: float, azimuth: float) -> bool:
    """Whether the sun shines on a facade of this bearing."""
    if bearing is None or elevation < LOW_SUN:
        return False
    return abs(((azimuth - bearing + 540) % 360) - 180) <= FACING


def sun_hours(day, latitude: float, longitude: float, bearing: float | None, step_minutes: int = 5):
    """When the sun is on a facade on `day` (an aware datetime at local midnight): (start, end) of each stretch."""
    stretches, start, when = [], None, day
    end = day + timedelta(days=1)
    while when <= end:
        on = when < end and facing(bearing, *sun_position(when, latitude, longitude))
        if on and start is None:
            start = when
        elif not on and start is not None:
            stretches.append((start, when))
            start = None
        when += timedelta(minutes=step_minutes)
    return stretches


def bearing_name(bearing: float) -> str:
    """The nearest of the eight directions, as a key of the words (« west », « south_east »…)."""
    return min(BEARINGS, key=lambda b: abs(((bearing - b[0] + 540) % 360) - 180))[1]
