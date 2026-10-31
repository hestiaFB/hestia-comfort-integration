"""The sun through each window: its position, the share a facade faces, and the watts that reach the room.

The same formulas as Hestia Comfort 2.1 (engine/twin.py `sun_position`, engine/assessment.py `facade_share`,
`facade_irradiance`, `SHELTER_ATTENUATION`), copied so that the advisor stays free of the 2.1 engine: what already works
is taken as it is (CAHIER-MOTEUR.md § 21). At home the position comes from Home Assistant's `sun.sun`; for the coming
hours and on the bench it is computed here.
"""
import math

EXPOSURES = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SO": 225, "O": 270, "NO": 315}
SHELTER_ATTENUATION = 3.0
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


def facade_irradiance(share: float, elevation: float, solar: float) -> float:
    """W/m² on a vertical facade from the horizontal sun: the direct part it faces, never less than the diffuse light."""
    diffuse = solar * 0.15
    direct = 0.0
    if elevation > 5 and solar > 40:
        direct = min(solar / max(math.sin(math.radians(elevation)), 0.09) * share, 850)
    return max(direct, diffuse)


def through_windows(solar: float, elevation: float, azimuth: float, windows, opened=()) -> float:
    """Watts of sun entering the room: each window's glazing × the sun on its facade, through glass or an open sash.
    `windows`: (glazed area, bearing or None, sheltered) of each; `opened`: the indexes of those open."""
    if solar <= 0 or elevation <= 0:
        return 0.0
    total = 0.0
    for i, (area, bearing, sheltered) in enumerate(windows):
        watts = facade_irradiance(facade_share(bearing, elevation, azimuth), elevation, solar)
        if sheltered:
            watts /= SHELTER_ATTENUATION
        total += area * watts * (1.0 if i in opened else GLASS)
    return total
