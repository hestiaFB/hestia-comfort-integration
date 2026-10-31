"""The forecast sun checked against the weather station's (CAHIER-MOTEUR.md § 6.2 bis).

Open-Meteo forecasts the sun hour by hour, clouds included; the station measures it, but from where it stands: a house,
a tree hide the low sun from it. So the station first learns its own shade, by the sun's position: under a clear sky,
the share of the forecast it receives (« ombre de la station »). Then, where it sees the sun, the last two hours tell
the clouds the forecast missed: measured over what it should have received. That gap holds for the next hours and fades.

Bench of 31 October (a year of the house's GW2000A against Open-Meteo's forecasts, judged on September–October, not
learned): the forecast sun missed the station by 64 W/m² on average one hour ahead, 46 corrected; 70 → 57 two hours
ahead, 74 → 64 three hours ahead; nothing gained at six hours. Under 25° of sun the station is in the shade most of the
year: in winter it rarely sees the sun and the forecast is kept as it is.
"""
import math
from datetime import timedelta

from .sunlight import sun_position

# The sun's position in cells of this many degrees of azimuth and of elevation.
AZIMUTH_STEP, ELEVATION_STEP = 10, 5
# Under this elevation the sun is too low to be read (°).
LOW = 5.0
# A clear hour: the forecast sun above this (W/m²) and its cloud cover under that (%).
CLEAR_SUN, CLEAR_CLOUDS = 100.0, 20.0
# A cell is learned from this many clear hours; its share is a high quantile of them (clear skies, not the hazy ones).
CELL_HOURS, QUANTILE = 4, 0.8
# The station sees the sun where its share is this much at least; under it, it is in its own shade.
SEES = 0.6
# The gap of the last hours, measured over forecast, held within these bounds, and faded over this many hours.
LEAST, MOST = 0.1, 1.5
FADE_HOURS = 4.0
# Hours of forecast sun too faint to tell the clouds by (W/m²).
FAINT = 50.0


def cell(when, latitude, longitude):
    """The sun's cell in the middle of the hour that starts at `when`, None when it is too low."""
    elevation, azimuth = sun_position(when + timedelta(minutes=30), latitude, longitude)
    if elevation < LOW:
        return None
    return f"{int(azimuth // AZIMUTH_STEP) * AZIMUTH_STEP}/{int(elevation // ELEVATION_STEP) * ELEVATION_STEP}"


def learn_shade(hours, latitude, longitude, known=None) -> dict:
    """The station's share of the forecast sun under a clear sky, by cell: {"170/25": 0.38, …}.

    `hours`: (start of the hour, forecast sun of that hour, measured mean, cloud cover or None). The cells learned before
    and not seen again are kept: winter's low sun is learned in winter and still known in spring."""
    shares = {}
    for start, forecast, measured, clouds in hours:
        if forecast is None or measured is None or forecast < CLEAR_SUN or (clouds is not None and clouds >= CLEAR_CLOUDS):
            continue
        where = cell(start, latitude, longitude)
        if where is not None:
            shares.setdefault(where, []).append(measured / forecast)
    out = dict(known or {})
    for where, values in shares.items():
        if len(values) >= CELL_HOURS:
            values.sort()
            out[where] = round(min(1.2, values[min(len(values) - 1, int(QUANTILE * len(values)))]), 2)
    return out


def share(shade: dict, where: str | None) -> float | None:
    """The station's share in that cell, or the mean of its learned neighbours; None when unknown."""
    if where is None:
        return None
    if where in shade:
        return shade[where]
    azimuth, elevation = (int(v) for v in where.split("/"))
    near = [shade[k] for da in (-AZIMUTH_STEP, 0, AZIMUTH_STEP) for de in (-ELEVATION_STEP, 0, ELEVATION_STEP)
            if (k := f"{azimuth + da}/{elevation + de}") in shade]
    return sum(near) / len(near) if near else None


def clouds_missed(recent, shade, latitude, longitude) -> float | None:
    """Measured over forecast sun in the last hours where the station saw it: under 1, more clouds than forecast; above,
    fewer. None when the station was in its shade, the sun too low or too faint: then nothing is corrected.

    `recent`: (start of the hour, forecast sun, measured mean) of the last full hours."""
    measured = expected = 0.0
    for start, forecast, mean in recent:
        seen = share(shade, cell(start, latitude, longitude))
        if forecast is None or mean is None or seen is None or seen < SEES or forecast < FAINT:
            continue
        measured += mean
        expected += forecast * seen
    if expected <= 0:
        return None
    return min(MOST, max(LEAST, measured / expected))


def corrected(forecast: float, hours_ahead: float, missed: float | None) -> float:
    """The forecast sun of an hour that many hours ahead, corrected by the gap of the last hours, which fades."""
    if missed is None or forecast is None:
        return forecast
    return forecast * (1 + (missed - 1) * math.exp(-max(0.0, hours_ahead) / FADE_HOURS))
