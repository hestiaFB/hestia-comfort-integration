"""The outside of the past days from Open-Meteo, for the learning of a home without an outdoor sensor (forum, 25 November).

A Hestia Weather place without a station gives the advice its forecast, but the learning reads the recorder's history
of an outdoor sensor: without one, nothing was learned. Open-Meteo gives the past hours too (`past_days`): their
temperature and humidity stand in for the missing outdoor measures, as two series no Home Assistant entity has. Less
precise than a sensor at the house (the model's point, a grid of a few kilometres), so the room says it learns « avec
les prévisions », and a real sensor chosen in « Extérieur » is always read first.

One download an hour for the whole home, the location rounded to a tenth as for the forecast (PASSAGE-CONFORT-3.md
§ 2.4); points every quarter of an hour, interpolated between the hours, so that a half-hour sample never reads a
step."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

URL = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m"
       "&past_days={days}&forecast_days=1&timezone=UTC")
# Names of the two series: never Home Assistant entities, only keys of the history the learning reads.
TEMPERATURE = f"{DOMAIN}.prevision_temperature_dehors"
HUMIDITY = f"{DOMAIN}.prevision_humidite_dehors"
SERIES = {"outdoor_temperature": TEMPERATURE, "outdoor_humidity": HUMIDITY}
# The nightly learning reads up to 60 days (advisor_home.LEARN_DAYS); Open-Meteo gives 92 at most.
DAYS = 61
KEPT = timedelta(hours=1)
STEP = timedelta(minutes=15)
DATA = f"{DOMAIN}_forecast_past"


@dataclass(frozen=True)
class Row:
    """A point as the recorder's compact rows give it (recorder_history.py): what the twin's learning reads."""
    state: str
    last_changed: datetime

    @property
    def last_updated(self):
        return self.last_changed


def points(hours, index, start, end):
    """[(time, value)] every STEP between `start` and `end`, interpolated between the hours (`index` 0 the temperature,
    1 the humidity). An hour without its value cuts the series there."""
    out = []
    known = [(at, values[index]) for at, values in hours if isinstance(values[index], (int, float))]
    for (a, va), (b, vb) in zip(known, known[1:]):
        if b - a > timedelta(hours=1) or b < start or a > end:
            continue
        t = a
        while t < b:
            if start <= t <= end:
                out.append((t, va + (vb - va) * ((t - a) / (b - a))))
            t += STEP
    if known and start <= known[-1][0] <= end:
        out.append(known[-1])
    return out


def recorder_rows(hours, key, start, end):
    """The series as the twin's history (rows with `state`, `last_changed`)."""
    return [Row(f"{v:.2f}", t) for t, v in points(hours, 0 if key == "outdoor_temperature" else 1, start, end)]


def night_rows(hours, key, start, end):
    """The series as the nightly learning's history (dicts, advisor/bench/history.py)."""
    entity_id = SERIES[key]
    return [{"entity_id": entity_id, "state": f"{v:.2f}", "attributes": {}, "last_changed": t.isoformat(), "last_updated": t.isoformat()}
            for t, v in points(hours, 0 if key == "outdoor_temperature" else 1, start, end)]


async def async_hours(hass, now=None):
    """[(hour, (°C, %))] of the past days, oldest first; the last download kept an hour. None when Open-Meteo does not
    answer (the learning then waits for the next pass)."""
    now = now or dt_util.utcnow()
    kept = hass.data.get(DATA)
    if kept and now - kept[0] < KEPT:
        return kept[1]
    url = URL.format(lat=round(hass.config.latitude, 1), lon=round(hass.config.longitude, 1), days=DAYS)
    try:
        async with async_get_clientsession(hass).get(url, timeout=60) as response:
            hourly = (await response.json())["hourly"]
        hours = [(dt_util.parse_datetime(t + "+00:00"), (te, rh))
                 for t, te, rh in zip(hourly["time"], hourly["temperature_2m"], hourly["relative_humidity_2m"])]
        hours = [(at, values) for at, values in hours if at is not None and at <= now]
    except Exception:  # noqa: BLE001 - said in the room's learning, tried again at its next pass
        if not hass.data.get(DATA + "_failed"):
            hass.data[DATA + "_failed"] = True
            _LOGGER.warning("Hestia Comfort: Open-Meteo's past outside unavailable, the learning waits for it")
        hass.data[DATA + "_down"] = True
        return kept[1] if kept else None
    hass.data[DATA] = (now, hours)
    hass.data[DATA + "_down"] = False
    return hours


def unavailable(hass):
    """Open-Meteo did not answer at the last try, and nothing was downloaded before."""
    return bool(hass.data.get(DATA + "_down")) and not hass.data.get(DATA)
