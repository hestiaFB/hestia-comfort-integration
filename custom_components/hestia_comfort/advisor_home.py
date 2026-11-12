"""The 3.0 advisor's house part (niak-comfort/docs/PASSAGE-CONFORT-3.md § 2.1, § 2.2): created once, for every room.

It holds what the rooms share — the forecast (Hestia Weather's air, Open-Meteo's sun), the station's own shade and the
clouds the forecast missed, the house's heaters, the safety signals — and the rooms' clock: a decision every five
minutes, again ten seconds after a window moved, retried shortly after a restart while the measures arrive. Each night
at 3:30 every room relearns its twins from the recorder's days, one after the other, in the executor.
Taken over from the test Home Assistant's `hestia_advisor_dev` (Engine).
"""
import asyncio
from datetime import timedelta
from functools import partial
import logging
import math
from pathlib import Path
import pickle
import sys

from homeassistant.components.recorder import get_instance, history as recorder_history
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import (async_call_later, async_track_state_change_event, async_track_time_change,
                                         async_track_time_interval)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import schedule_link, weather_link
from .advisor import VERSION as ADVISOR_VERSION
from .advisor.decide import Thermostat
from .advisor.household import Habits
from .advisor.nightly import learn_room
from .advisor.observe import Series
from .advisor.physics.heaters import heater
from .advisor.physics.station_sun import cell, clouds_missed, corrected, learn_shade, share
from .advisor.physics.sunlight import sun_position, through_windows
from .advisor.physics.thermal import STEP, Inputs
from .advisor.physics.water import absolute, relative
from .advisor.safety import minutes, rain_believed, rain_held
from .advisor_store import AdvisorFiles
from .const import DOMAIN, VERSION
from .engine import schedule
from .room.advice import RoomAdvisor, heater_kinds, house_given_now, house_heaters, house_power_now, leads, room_spec

_LOGGER = logging.getLogger(__name__)
DATA = f"{DOMAIN}_advisor"
EVERY = timedelta(minutes=5)
# Seconds a window must stay as it is before its room is advised again (a sash pushed to, then opened wide).
WINDOW_SETTLE = 10
# Seconds between tries of the first advice after a restart, while the measures arrive.
START_RETRY = 15
# Versatile Thermostat's reason when it turned itself off for an open window.
WINDOW_OFF = "hvac_off_window_detection"
FORECAST = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&hourly=temperature_2m,relative_humidity_2m,shortwave_radiation&past_days=1&forecast_days=2&timezone=UTC")
PAST_SUN = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=shortwave_radiation,cloud_cover"
            "&past_days={days}&forecast_days=1&timezone=UTC")
OFFSET_STEPS = 144      # twelve hours of five-minute steps
STOVE_PATH_KEPT = timedelta(minutes=15)  # a stove's simulated power is followed this long by the other rooms
# The nightly learning (advisor/nightly.py): at 3:30, and ten minutes after a start when the last one is a day old; from
# the recorder's days (60 at most), with Open-Meteo's sun of those days.
LEARN_AT, LEARN_AFTER_START, LEARN_DAYS = (3, 30), 600, 60
WIND_UNITS = {"km/h": 1.0, "m/s": 3.6, "mph": 1.609344, "kn": 1.852}
# The only attributes the nightly learning reads (advisor/bench/history.py `attribute`): the heating's power, the cover's
# position. The history is read one entity and one day at a time (PLAN-OPTIMISATION.md, point 1): never sixty days of
# every state with all its attributes in memory at once, and never converted on Home Assistant's loop.
NIGHT_ATTRIBUTES = ("power_percent", "current_position")
NIGHT_SLICE = timedelta(days=1)


def night_rows(entity_id, states, attributes, last=None):
    """The states as the nightly learning reads them (dicts, advisor/bench/history.py), with `last` the key of the row kept
    before them: (rows, last). A state repeated as it was (only an attribute the learning does not read changed) is
    kept once: every series holds its value until the next row, and a repeated state keeps its `last_changed`, so
    nothing the learning reads changes."""
    rows = []
    for state in states:
        kept = {k: state.attributes[k] for k in NIGHT_ATTRIBUTES if k in state.attributes} if attributes else {}
        if (state.state, kept) == last:
            continue
        last = (state.state, kept)
        rows.append({"entity_id": entity_id, "state": state.state, "attributes": kept,
                     "last_changed": state.last_changed.isoformat(), "last_updated": state.last_updated.isoformat()})
    return rows, last


# One room's nightly learning, in a process of its own (PLAN-OPTIMISATION.md, point 10): night_worker.py.
NIGHT_WORKER = Path(__file__).with_name("night_worker.py")


def room_history(history, spec, outdoor, outdoor_rh, houses):
    """Only what one room's learning reads (advisor/nightly.py): sent to its process, not the whole home's."""
    wanted = {outdoor, outdoor_rh, spec.alarm, spec.temperature, spec.humidity, spec.thermostat, spec.cover, spec.co2,
              spec.particles, spec.voc, *spec.windows, *(houses or {}), *(d[0] for d in (spec.boost, spec.purifier) if d)}
    return {e: rows for e, rows in history.items() if e in wanted}


def night_history(hass, start, end, entity_ids, with_attributes):
    """{entity: [state as a dict]} for the nightly learning, read and converted in the recorder's executor."""
    out = {}
    for entity_id in entity_ids:
        rows, last, begin = [], None, start
        attributes = entity_id in with_attributes
        while begin < end:
            stop = min(begin + NIGHT_SLICE, end)
            # The state at `start` opens the window; later slices only add what changed within them.
            found = recorder_history.get_significant_states(hass, begin, stop, [entity_id], None, begin == start, False, False,
                                                            not attributes)
            more, last = night_rows(entity_id, found.get(entity_id, ()), attributes, last)
            rows.extend(more)
            del found
            begin = stop
        if rows:
            out[entity_id] = rows
    return out


def share_caps(shares: dict) -> dict:
    """{room: the most of the stove's heat it may receive tonight}: all the rooms together never more than all of it.
    Over it (10 November: 128 %), each keeps its part of the whole; under it, each may grow by what is left."""
    known = {room: max(0.0, share) if isinstance(share, (int, float)) else 0.0 for room, share in shares.items()}
    total = sum(known.values())
    if total > 1.0:
        return {room: share / total for room, share in known.items()}
    return {room: share + (1.0 - total) for room, share in known.items()}


def _number(hass, entity_id, attribute=None):
    state = hass.states.get(entity_id) if entity_id else None
    if state is None:
        return None
    try:
        return float(state.attributes.get(attribute) if attribute else state.state)
    except (TypeError, ValueError):
        return None


async def async_room(hass, coordinator):
    """The room's advisor when it advises its air (it leads its shared air), registered with the house's; else None."""
    if not coordinator.sources.get("indoor_temperature") or not leads(coordinator):
        return None
    home = hass.data.get(DATA)
    if home is None:
        home = hass.data[DATA] = AdvisorHome(hass)
        await home.async_load()
    advisor = RoomAdvisor(coordinator, home)
    await advisor.async_load()
    home.add(advisor)
    coordinator.config_entry.async_on_unload(partial(home.remove, advisor))
    return advisor


# Shown while a room's advisor has not decided yet (just after a restart): never the 2.1 advice in its place, which
# flashed « Aérez » for twenty seconds after each restart of the test Home Assistant (3 November, Chambre P).
WAITING = {"title": "Conseil en attente", "regle": "waiting", "geste": "nothing",
           "phrase": "Le moteur redémarre : le conseil revient dans une minute."}


def result(hass, entry_id):
    """The decision shown for this room: its own, or the one of the room advising its shared air; None when no 3.0
    advisor reads this room (no temperature sensor)."""
    home = hass.data.get(DATA)
    advisor = home.advisor_of(entry_id) if home else None
    if advisor is None:
        return None
    return advisor.result or WAITING


def gestures(hass, entry_id, start, end):
    """The gestures asked in this room's air between `start` and `end`, with their kWh (room/advice.py `gestures_between`);
    None when no 3.0 advisor reads this room."""
    home = hass.data.get(DATA)
    advisor = home.advisor_of(entry_id) if home else None
    return advisor.gestures_between(start, end) if advisor else None


def knowing(hass, entry_id):
    """What the hub's « Apprentissage » shows of this room's air (room/advice.py `knowing`); None without a 3.0 advisor."""
    home = hass.data.get(DATA)
    advisor = home.advisor_of(entry_id) if home else None
    return advisor.knowing() if advisor and advisor.learned else None


def outside(hass):
    """How reliable the outside is (« Fiabilité »): the forecast against the station now, the sun's position checked against
    Home Assistant's, the station's shade learned. None before the house's advisor has started."""
    home = hass.data.get(DATA)
    if home is None:
        return None
    now = dt_util.utcnow()
    start = home.forecast.get(now.replace(minute=0, second=0, microsecond=0))
    outdoor = home.outdoor[0]
    return {"moteur": home.version, "source": home.forecast_source, "station": outdoor, "prevision": start[0] if start else None,
            # The station's own reading when Hestia Weather retains another temperature now, and why.
            "station_mesuree": home.outdoor_measured[0], "retenue": home.retained,
            "ecart": round(outdoor - start[0], 1) if start and start[0] is not None and outdoor is not None else None,
            "soleil": home.sun, **_shade_counts(home),
            "nuages_manques": None if home.sun_missed is None else round(home.sun_missed, 2)}


def _shade_counts(home):
    """How much of the station's shade is known: learned positions of the sun out of those it crosses here, and by whom."""
    shared = home._weather_shade()
    if shared:
        return {"ombre_cases": shared.get("learned", 0), "ombre_positions": shared.get("reachable"),
                "ombre_connues": len(shared.get("cells") or {}), "ombre_declaree": shared.get("declared"),
                "ombre_source": "Hestia Weather"}
    return {"ombre_cases": len(home.station_shade), "ombre_positions": None, "ombre_connues": len(home.station_shade),
            "ombre_declaree": None, "ombre_source": "Hestia Confort"}


class AdvisorHome:
    def __init__(self, hass):
        self.hass = hass
        # The engine's version, apart from the integration's: in the snapshots, the journal and the nightly report.
        self.version, self.integration = ADVISOR_VERSION, VERSION
        self.store = Store(hass, 1, f"{DOMAIN}.advisor_home")
        self.files = AdvisorFiles(hass.config.path())
        self.rooms = {}             # entry_id of the room advising → RoomAdvisor
        self.listeners = {}         # entry_id → its windows' listener
        self.pending = {}           # entry_id → the decision waiting for its window to settle
        self.unsubscribe = []
        # One step at a time: the rooms registered together at a start share one first step, never one each.
        self.lock, self.soon = asyncio.Lock(), None
        self.started = False
        self.boot = dt_util.utcnow()
        self.houses = {}
        # {stove's thermostat: (when, its share given off at each step)}: simulated in the room it stands in, followed by
        # the other rooms it warms (`house_heat_steps`).
        self.stove_paths = {}
        self.outdoor = (None, None)
        # The station's own reading, and how far Hestia Weather trusts it now (weather_link.station_trust): the
        # temperature it retains replaces a station warmed by its wall or its roof in the sun.
        self.outdoor_measured, self.trust, self.retained = (None, None), None, None
        # Since when the rain has been said due without a drop at the station (advisor/safety.py `rain_believed`).
        self.rain_soon_since = None
        # The last rain announced: {gauge, intensity, chance} (`safety`).
        self.rain_hint = {}
        self.learning = False
        # The nightly learning's own process failed once (night_worker.py): said once in the log, then in the threads.
        self.worker_failed = False
        self.forecast, self.forecast_at, self.forecast_source = {}, None, "Open-Meteo"
        # The station's own shade by the sun's position, and the clouds the forecast missed in the last two hours, read
        # where it sees the sun (advisor/physics/station_sun.py); None: the forecast sun is kept as it is.
        self.station_shade, self.sun_missed, self.sun_missed_hour, self.sun_recent = {}, None, None, []
        self.past_sky = {}
        self.sun = {}

    async def async_load(self):
        kept = await self.store.async_load() or {}
        self.station_shade = dict(kept.get("station_shade") or {})

    async def _save(self):
        await self.store.async_save({"station_shade": self.station_shade})

    # The rooms.

    def add(self, advisor):
        self.rooms[advisor.entry_id] = advisor
        self.houses = house_heaters(self.hass)
        self._listen(advisor)
        if not self.unsubscribe:
            self.unsubscribe = [async_track_time_interval(self.hass, self.tick, EVERY),
                                async_track_time_change(self.hass, self.learn, hour=LEARN_AT[0], minute=LEARN_AT[1], second=0),
                                async_call_later(self.hass, LEARN_AFTER_START, self._learn_if_stale)]
        # Its first decision now, not in five minutes: one step for all the rooms registering together.
        if self.soon is None:
            self.soon = async_call_later(self.hass, 2, self._first)

    async def _first(self, _now):
        self.soon = None
        await self.tick(None)

    def remove(self, advisor):
        if self.rooms.get(advisor.entry_id) is advisor:
            del self.rooms[advisor.entry_id]
        if listener := self.listeners.pop(advisor.entry_id, None):
            listener()
        if pending := self.pending.pop(advisor.entry_id, None):
            pending()
        if not self.rooms:
            for unsubscribe in self.unsubscribe:
                unsubscribe()
            self.unsubscribe = []

    def advisor_of(self, entry_id):
        return next((a for a in self.rooms.values() if a.room and entry_id in a.room["members"]), None)

    def _listen(self, advisor):
        """A window opened or shut: its room is advised again once it has settled, not at the next step."""
        windows = sorted(advisor.room["windows"])
        if getattr(advisor, "listened", None) == windows:
            return
        if listener := self.listeners.pop(advisor.entry_id, None):
            listener()
        advisor.listened = windows
        if windows:
            self.listeners[advisor.entry_id] = async_track_state_change_event(self.hass, windows, partial(self._window_moved, advisor))

    def _window_moved(self, advisor, event):
        old, new = event.data.get("old_state"), event.data.get("new_state")
        if not old or not new or old.state == new.state:
            return
        if pending := self.pending.pop(advisor.entry_id, None):
            pending()
        self.pending[advisor.entry_id] = async_call_later(self.hass, WINDOW_SETTLE, partial(self._advise_now, advisor))

    async def _advise_now(self, advisor, _now):
        self.pending.pop(advisor.entry_id, None)
        try:
            if await advisor.advise(dt_util.utcnow(), stepping=False):
                self._publish(advisor)
        except Exception:  # noqa: BLE001 - the next step advises it anyway
            _LOGGER.exception("Hestia Comfort: advice 3.0 for %s", advisor.room["name"])

    def _publish(self, advisor):
        """The rooms sharing this air show the new decision."""
        for entry_id in advisor.room["members"]:
            entry = self.hass.config_entries.async_get_entry(entry_id)
            coordinator = getattr(entry, "runtime_data", None) if entry else None
            if coordinator is not None and hasattr(coordinator, "async_request_refresh"):
                self.hass.async_create_task(coordinator.async_request_refresh())

    # What the rooms share.

    def _anchor(self):
        return next(iter(self.rooms.values())).coordinator if self.rooms else None

    def _sources(self):
        coordinator = self._anchor()
        configuration = coordinator.home_configuration if coordinator else None
        return configuration.effective_sources(coordinator.config) if configuration else {}

    def _place(self):
        coordinator = self._anchor()
        return coordinator._weather_place() if coordinator else None

    def analysis(self):
        """Our analysis tools on (configuration.py `set_analysis`): the files the Atelier reads are written. Off by default."""
        coordinator = self._anchor()
        configuration = coordinator.home_configuration if coordinator else None
        return bool(configuration and configuration.home.get("analysis"))

    def foyer(self):
        """The household's settings of the house (« Réglages du foyer »)."""
        coordinator = self._anchor()
        configuration = coordinator.home_configuration if coordinator else None
        return (configuration.home.get("foyer") if configuration else None) or {}

    def _read_outdoor(self):
        """The outside's temperature and humidity now. Where Hestia Weather does not trust its station at this moment (a
        wall or a roof in the sun, docs/STATION-EMPLACEMENT.md § 4.1 of Hestia Weather), its retained temperature is
        taken — the forecast, or the measure less the excess learned — and the humidity follows: the wall heats the air,
        it adds no water. `coming()` then carries no wall's gap into the evening. A Hestia Weather that does not share
        its trust, or a sensor chosen in Confort that is not its station's, keeps the raw reading."""
        sources = self._sources()
        temperature_entity = (sources.get("outdoor_temperature") or {}).get("entity_id")
        temperature, humidity = (_number(self.hass, (sources.get(k) or {}).get("entity_id")) for k in ("outdoor_temperature", "outdoor_humidity"))
        self.outdoor_measured = (temperature, humidity)
        place = self._place()
        self.trust = weather_link.station_trust(self.hass, place)
        kept = weather_link.retained(self.trust, "temperature")
        self.retained = None
        if kept is not None and temperature is not None and weather_link.from_station(self.hass, place, temperature_entity):
            if humidity is not None:
                humidity = round(relative(kept[0], absolute(temperature, humidity)), 1)
            temperature, self.retained = kept[0], {"temperature": kept[0], "now": kept[1], "why": kept[2]}
        self.outdoor = (temperature, humidity)
        return self.outdoor

    def house_heat(self):
        """W the house's heaters give off now, wherever they stand: none from a stove waiting to be lit."""
        kinds = heater_kinds(self.hass)
        return sum(house_given_now(self.hass, e, kinds) * w for e, w in self.houses.items())

    def house_heat_steps(self, now, steps):
        """W the house's heaters give off at each coming step: a stove as its own room simulates it (5 min old at most,
        STOVE_PATH_KEPT), the others as they are now. Kept at its power of the moment, a stove just lit at 100 % warmed
        the other rooms two hours at full power (bilan of 11 November: Chambre M 24,8 °C foreseen, 21,8 °C measured)."""
        out = [0.0] * steps
        kinds = heater_kinds(self.hass)
        for entity, watts in self.houses.items():
            found = self.stove_paths.get(entity)
            power = house_given_now(self.hass, entity, kinds)
            shares = None
            if found is not None and power > 0 and timedelta(0) <= now - found[0] <= STOVE_PATH_KEPT and found[1]:
                shift = int((now - found[0]).total_seconds() // STEP)
                shares = found[1][shift:] or found[1][-1:]
            for k in range(steps):
                share = shares[min(k, len(shares) - 1)] if shares else power
                out[k] += share * watts
        return out

    def safety(self):
        """(rain mm/h, gusts km/h, minutes before the rain, vigilance, where the wind comes from in degrees): from the home's
        sources and Hestia Weather's interface, never from an entity's name. A value not known forbids nothing
        (advisor/safety.py)."""
        sources = self._sources()
        rain = sources.get("rain") or {}
        state = self.hass.states.get(rain.get("entity_id") or "")
        rate = None
        if state is not None:
            if rain.get("adapter") == "rain_rate":
                rate = _number(self.hass, rain["entity_id"])
            elif state.state in ("on", "off"):
                rate = 1.0 if state.state == "on" else 0.0
        rate, self.rain_last = rain_held(rate, getattr(self, "rain_last", None), dt_util.utcnow().timestamp())
        gust_entity = (sources.get("wind_gust") or {}).get("entity_id")
        gust = _number(self.hass, gust_entity)
        if gust is not None:
            unit = (s.attributes.get("unit_of_measurement") if (s := self.hass.states.get(gust_entity)) else None) or "km/h"
            gust = gust * WIND_UNITS[unit] if unit in WIND_UNITS else None
        place = self._place()
        # From a side where the station is sheltered, Hestia Weather retains the stronger gust, the station's or the
        # forecast's (km/h): a calm read behind the hedge does not open a window wide to a west wind.
        stronger = weather_link.retained(self.trust, "wind")
        if stronger is not None and weather_link.from_station(self.hass, place, gust_entity):
            gust = stronger[0] if gust is None else max(gust, stronger[0])
        outlook = weather_link.outlook(self.hass, place)
        ahead = outlook.get("rain") or {}
        rain_in = ahead.get("minutes") if isinstance(ahead.get("minutes"), (int, float)) else None
        if rain_in is None and outlook.get("rain_in_hours") is not None:
            rain_in = minutes(outlook["rain_in_hours"], "h")
        # A rain gauge under a tree or an overhang: its zero does not make the rain announced unbelieved.
        sheltered = weather_link.gauge_sheltered(self.trust) and weather_link.from_station(self.hass, place, rain.get("entity_id"))
        rain_in, self.rain_soon_since = rain_believed(rain_in, rate, self.rain_soon_since, dt_util.utcnow().timestamp(), sheltered)
        # How sure the rain announced is, and whether a gauge in the open has the last word (advisor/safety.py).
        self.rain_hint = {"gauge": rate is not None and not sheltered,
                          "intensity": ahead.get("intensity") if isinstance(ahead.get("intensity"), int) else None,
                          "chance": ahead.get("chance") if isinstance(ahead.get("chance"), (int, float)) else None}
        wind_from = _number(self.hass, (sources.get("wind_bearing") or {}).get("entity_id"))
        return rate, gust, rain_in, outlook.get("vigilance"), wind_from

    def thermostat(self, entity_id, mode="heat"):
        """The room's Versatile Thermostat as it runs (`mode` « heat »), or as it would run once turned on again (« off »,
        unless the system turned it off: window, safety, central mode — CAHIER-MOTEUR.md § 9.1 bis).
        Frost protection is a safeguard: turned on again, it would aim at its comfort temperature."""
        state = self.hass.states.get(entity_id) if entity_id else None
        reason = (state.attributes.get("specific_states") or {}).get("hvac_off_reason") if state else None
        # Turned off by its window, it is still the room's thermostat: it heats again once the window is shut, in the
        # scenarios too (Chambre AL, 1 November: three hours open, « Ouverte ou fermée » as the room left its range).
        by_window = mode == "heat" and state is not None and state.state == "off" and reason == WINDOW_OFF
        if state is None or (state.state != mode and not by_window):
            return None
        # A thermostat turned off by hand may be turned on again (a passive advice); one the system turned off may not.
        if mode == "off" and reason and reason != "hvac_off_manual":
            return None
        aimed = state.attributes.get("current_state") or {}
        target = aimed.get("target_temperature") or state.attributes.get("temperature")
        if mode == "off" and "frost" in (aimed.get("preset") or ""):
            target = (state.attributes.get("preset_temperatures") or {}).get("comfort_temp") or target
        tpi = state.attributes.get("vtherm_over_switch") or {}
        window = (state.attributes.get("window_manager") or {}).get("window_action")
        if not isinstance(target, (int, float)):
            return None
        # Its schedule's next set point (ha-chauffage, Scheduler): eco now, comfort at 17 h, followed in every scenario.
        then = at = None
        configuration = getattr(self._anchor(), "home_configuration", None)
        change = schedule_link.next_change(self.hass, entity_id, (configuration.home.get("disabled") if configuration else None) or ())
        if change and change.get("temperature") is not None:
            then = change["temperature"]
            at = (dt_util.parse_datetime(change["at"]) - dt_util.now()).total_seconds() / 60
        return Thermostat(float(target), tpi.get("tpi_coef_int") or 0.6, tpi.get("tpi_coef_ext") or 0.01,
                          by_window or window == "window_turn_off", then, at)

    async def mean_air(self, entity_id, start, end):
        """The mean of a sensor over the recorder's states: where the walls start after a long stop."""
        try:
            states = await get_instance(self.hass).async_add_executor_job(partial(
                recorder_history.get_significant_states, self.hass, start, end, [entity_id],
                significant_changes_only=False, minimal_response=True))
        except Exception:  # noqa: BLE001 - without history, the walls start at the air
            _LOGGER.warning("Hestia Comfort: no history for the walls of %s", entity_id)
            return None
        found = []
        for row in states.get(entity_id) or ():
            try:
                found.append(float(row.state if hasattr(row, "state") else row["state"]))
            except (TypeError, ValueError, KeyError):
                pass
        return sum(found) / len(found) if found else None

    # The forecast and the sun.

    async def _refresh_forecast(self, now):
        if self.forecast_at and now - self.forecast_at < timedelta(hours=1):
            # Hestia Weather may load after this integration: tried again at each step until it answers.
            if self.forecast_source != "Hestia Weather":
                self._from_weather()
            return
        # Only the location rounded to a tenth leaves the house (PASSAGE-CONFORT-3.md § 2.4).
        url = FORECAST.format(lat=round(self.hass.config.latitude, 1), lon=round(self.hass.config.longitude, 1))
        try:
            async with async_get_clientsession(self.hass).get(url, timeout=30) as response:
                hourly = (await response.json())["hourly"]
            # Open-Meteo's sun at a time is the mean of the hour that ends then: kept under the hour it covers.
            times = [dt_util.parse_datetime(t + "+00:00") for t in hourly["time"]]
            suns = {t - timedelta(hours=1): v for t, v in zip(times, hourly["shortwave_radiation"])}
            self.forecast = {t: (te, rh, suns.get(t)) for t, te, rh in zip(times, hourly["temperature_2m"], hourly["relative_humidity_2m"])}
            self.forecast_at = now
        except Exception:  # noqa: BLE001 - without a forecast the outdoor air is held as it is now
            _LOGGER.warning("Hestia Comfort: Open-Meteo's forecast unavailable, the outdoor air is held as measured")
        self._from_weather()

    def _from_weather(self):
        """The outside's temperature and humidity to come from Hestia Weather (CAHIER-MOTEUR.md § 6.2), Open-Meteo's
        sun kept: Weather gives no sun hour by hour. Open-Meteo's own point may stand far higher than the house."""
        api = weather_link.api(self.hass)
        self.forecast_source = "Open-Meteo"
        if api is None:
            return
        try:
            hours = api.hourly(self._place())
        except Exception:  # noqa: BLE001 - Weather's forecast is a plus over Open-Meteo's
            _LOGGER.warning("Hestia Comfort: Hestia Weather's forecast unreadable, Open-Meteo kept")
            return
        merged = dict(self.forecast)
        for h in hours:
            when = dt_util.as_utc(dt_util.parse_datetime(h["time"])).replace(minute=0, second=0, microsecond=0)
            sun = (self.forecast.get(when) or (None, None, None))[2]
            merged[when] = (h.get("temperature"), h.get("humidity"), sun)
        if hours:
            self.forecast, self.forecast_source = merged, "Hestia Weather"

    def _station_sun(self):
        """The sun sensor of the station chosen in Hestia Weather (CAHIER-MOTEUR.md § 6.2 bis): no station, no check."""
        api = weather_link.api(self.hass)
        station = (api.station(self._place()) if api else None) or {}
        return (station.get("sensors") or {}).get("solar_radiation")

    def _weather_shade(self):
        """The station's shade as Hestia Weather shares it (CAHIER-MOTEUR.md § 7.4): learned on 92 days of its statistics,
        filled from the neighbours and the household's declaration. None from a Hestia Weather that does not share it yet:
        the shade learned here is then used."""
        api = weather_link.api(self.hass)
        shared = getattr(api, "station_shade", None) if api else None
        return shared(self._place()) if shared else None

    def shade(self):
        """The station's shade by the sun's position, {cell: share}: Hestia Weather's, else the one learned here."""
        shared = self._weather_shade()
        return shared["cells"] if shared else self.station_shade

    async def _hourly_means(self, entity_id, start, end, period):
        """The recorder's mean of a sensor for each hour from `start` to `end`: {start of the hour (UTC): W/m²}."""
        rows = (await get_instance(self.hass).async_add_executor_job(
            statistics_during_period, self.hass, start, end, {entity_id}, period, None, {"mean"})).get(entity_id, [])
        hours = {}
        for row in rows:
            if row.get("mean") is None:
                continue
            at = dt_util.utc_from_timestamp(row["start"]).replace(minute=0, second=0, microsecond=0)
            hours.setdefault(at, []).append(row["mean"])
        return {at: sum(v) / len(v) for at, v in hours.items()}

    async def _station_clouds(self, now):
        """The clouds the forecast missed in the last two full hours, where the station saw the sun; read once an hour."""
        hour = now.replace(minute=0, second=0, microsecond=0)
        if self.sun_missed_hour == hour:
            return
        entity, shade = self._station_sun(), self.shade()
        if entity is None or not shade:
            self.sun_missed, self.sun_recent = None, []
            return
        means = await self._hourly_means(entity, hour - timedelta(hours=2), hour, "5minute")
        recent = [(start, (self.forecast.get(start) or (None, None, None))[2], means.get(start))
                  for start in (hour - timedelta(hours=2), hour - timedelta(hours=1))]
        latitude, longitude = self.hass.config.latitude, self.hass.config.longitude
        self.sun_missed = clouds_missed(recent, shade, latitude, longitude)
        self.sun_recent = [{"heure": dt_util.as_local(start).strftime("%H h"), "prevu": forecast, "mesure": mean,
                            "part_station": share(shade, cell(start, latitude, longitude)),
                            "soleil_bas": cell(start, latitude, longitude) is None}
                           for start, forecast, mean in recent]
        # Read again within the hour while the past hours are not all in the recorder yet.
        if all(mean is not None for _, _, mean in recent):
            self.sun_missed_hour = hour

    def coming(self, now, steps, outdoor, outdoor_rh, house_heat, shade, glazing=None, opened=(), shutter=0.0):
        """The coming steps: the forecast, pulled toward the station's measure for the first hours."""
        start = self.forecast.get(now.replace(minute=0, second=0, microsecond=0))
        offset = outdoor - start[0] if start and start[0] is not None else 0.0
        # The water too (bilan of 11 Nov.: 91 % forecast outside, 78 % at the station → « Refermez » for nothing): the
        # forecast's own water, from its own temperature and humidity, pulled toward the station's like the temperature.
        water_offset = 0.0
        if start and start[0] is not None and start[1] is not None and outdoor_rh is not None:
            water_offset = absolute(outdoor, outdoor_rh) - absolute(start[0], start[1])
        out = []
        hour = now.replace(minute=0, second=0, microsecond=0)
        for k in range(steps):
            when = now + k * timedelta(seconds=STEP)
            fc = self.forecast.get(when.replace(minute=0, second=0, microsecond=0))
            # The sun checked against the station's: the clouds missed in the last two hours, fading over the next ones.
            if fc and fc[2] is not None and self.sun_missed is not None:
                ahead = (when.replace(minute=0, second=0, microsecond=0) - hour).total_seconds() / 3600
                fc = (fc[0], fc[1], corrected(fc[2], ahead, self.sun_missed))
            # The gap between the station and the forecast holds for hours: it fades over twelve hours, not two.
            te = (fc[0] + offset * math.exp(-k / OFFSET_STEPS)) if fc and fc[0] is not None else outdoor
            fade = math.exp(-k / OFFSET_STEPS)
            if fc and fc[0] is not None and fc[1] is not None:
                water = absolute(fc[0], fc[1]) + water_offset * fade
                water = min(max(water, 0.0), absolute(te, 100.0))
            else:
                water = absolute(te, outdoor_rh) if outdoor_rh is not None else None
            sun = fc[2] if fc and fc[2] is not None else 0.0
            local = dt_util.as_local(when)
            # The sun on each window by its orientation, when declared (an optional plus, CAHIER-MOTEUR.md § 6.7).
            facades = (None, None, None)
            if glazing:
                elevation, azimuth = sun_position(when, self.hass.config.latitude, self.hass.config.longitude)
                # As the windows are now, all shut, all open: an open sash lets in more sun than its glass.
                facades = tuple(through_windows(sun, elevation, azimuth, glazing, which) for which in (opened, (), range(len(glazing))))
            out.append((Inputs(te, sun=sun, hour=local.hour + local.minute / 60, house_heat=house_heat, shade=shade, shutter=shutter,
                               facade=facades[0], facade_shut=facades[1], facade_all=facades[2]),
                        water))
        return out

    def _sun_check(self, now):
        """The Sun integration, found by the integration and not by name: its hours, and its position against the
        advisor's own — a gap means the home's location is wrong in Home Assistant (CAHIER-MOTEUR.md § 6.2 bis)."""
        found = {}
        for entry in er.async_get(self.hass).entities.values():
            if entry.platform == "sun" and entry.domain == "sensor":
                for key in ("solar_elevation", "solar_azimuth", "next_rising", "next_setting", "next_dawn", "next_dusk"):
                    if (entry.unique_id or "").endswith(key):
                        state = self.hass.states.get(entry.entity_id)
                        found[key] = state.state if state else None
                        if key == "solar_elevation" and state:
                            found["at"] = state.last_updated
        elevation, azimuth = sun_position(found.get("at", now), self.hass.config.latitude, self.hass.config.longitude)
        try:
            gap = max(abs(float(found["solar_elevation"]) - elevation), abs(((float(found["solar_azimuth"]) - azimuth + 540) % 360) - 180))
        except (KeyError, TypeError, ValueError):
            gap = None
        hours = {k: dt_util.as_local(t).strftime("%H:%M") if (t := dt_util.parse_datetime(found.get(k) or "")) else None
                 for k in ("next_dawn", "next_rising", "next_setting", "next_dusk")}
        self.sun = {"ecart": None if gap is None else round(gap, 2), "elevation_calculee": round(elevation, 2),
                    "azimut_calcule": round(azimuth, 2), "elevation_soleil": found.get("solar_elevation"),
                    "azimut_soleil": found.get("solar_azimuth"), "aube": hours["next_dawn"], "lever": hours["next_rising"],
                    "coucher": hours["next_setting"], "crepuscule": hours["next_dusk"]}

    # The rooms' clock.

    async def tick(self, _now):
        if not self.rooms or self.lock.locked():
            return
        async with self.lock:
            await self._tick()

    async def _tick(self):
        now = dt_util.utcnow()
        self.houses = house_heaters(self.hass)
        await self._refresh_forecast(now)
        try:
            await self._station_clouds(now)
        except Exception:  # noqa: BLE001 - without the station, the forecast sun is kept as it is
            _LOGGER.exception("Hestia Comfort: station sun")
            self.sun_missed = None
        outdoor, _ = self._read_outdoor()
        rooms = list(self.rooms.values())
        for advisor in rooms:
            advisor.refresh_spec()
        # Just after a restart the measures are not there yet: tried again shortly, not in five minutes, and never
        # advised on before every room's temperature has come (else it would be called doubtful), for five minutes at
        # most: a sensor still silent then is the checks' business.
        if not self.started and now - self.boot < EVERY and (
                outdoor is None or any(_number(self.hass, a.room["temperature"]) is None for a in rooms)):
            async_call_later(self.hass, START_RETRY, self.tick)
            return
        if outdoor is None:
            return
        self.started = True
        try:
            self._sun_check(now)
        except Exception:  # noqa: BLE001 - the check is a plus
            _LOGGER.exception("Hestia Comfort: sun check")
        for advisor in rooms:
            self._listen(advisor)
            try:
                if await advisor.advise(now):
                    self._publish(advisor)
                await advisor.async_save(now)
            except Exception:  # noqa: BLE001 - one room that fails never stops the others
                _LOGGER.exception("Hestia Comfort: advice 3.0 for %s", advisor.room["name"])

    # The nightly learning.

    async def _learn_if_stale(self, _now):
        stale = [a for a in self.rooms.values() if not a.learned_at
                 or dt_util.utcnow() - dt_util.parse_datetime(a.learned_at) > timedelta(days=1)]
        if stale:
            await self.learn()

    async def learn(self, _now=None):
        """Relearn every room's twins from the recorded days (advisor/nightly.py), keep them, note what was learned."""
        if self.learning or not self.rooms:
            return
        self.learning = True
        try:
            now = dt_util.utcnow()
            sources = self._sources()
            outdoor, outdoor_rh = ((sources.get(k) or {}).get("entity_id") for k in ("outdoor_temperature", "outdoor_humidity"))
            if not outdoor:
                return
            self.houses = house_heaters(self.hass)
            specs = {}
            wanted = {outdoor, outdoor_rh, *self.houses} - {None}
            for advisor in self.rooms.values():
                # The household's habits say when its manual shutters are shut (HABITUDES-FOYER.md): the alarm's
                # history gives its absences.
                room = advisor.refresh_spec()
                alarm = advisor.coordinator._alarm_entity()
                spec = room_spec(room, Habits.of(self.foyer(), room["foyer"]), alarm,
                                 advisor.coordinator.season_name == "summer")
                if not spec.temperature:
                    continue
                specs[advisor.entry_id] = spec
                wanted |= {alarm} if alarm and spec.manual else set()
                wanted |= {spec.temperature, *spec.windows} | {e for e in (spec.humidity, spec.thermostat, spec.cover, spec.co2,
                                                                         spec.particles, spec.voc) if e} \
                    | {d[0] for d in (spec.boost, spec.purifier) if d}
            # The heating's power and the cover's position are attributes: only their entities are read with them.
            with_attributes = {e for spec in specs.values() for e in (spec.thermostat, spec.cover) if e} | set(self.houses)
            history = await get_instance(self.hass).async_add_executor_job(
                night_history, self.hass, now - timedelta(days=LEARN_DAYS), now, sorted(wanted), with_attributes)
            first = min((dt_util.parse_datetime(v[0]["last_changed"]) for v in history.values()), default=now)
            sun = await self._past_sun(max(1, min(92, (now - first).days + 1)))
            zone = dt_util.get_time_zone(self.hass.config.time_zone)
            location = (self.hass.config.latitude, self.hass.config.longitude)
            reports = []
            kinds = heater_kinds(self.hass)
            house_idle = {e: heater(kinds.get(e)).idle for e in self.houses}
            caps = share_caps({e: (a.learned or {}).get("heat", {}).get("share") for e, a in self.rooms.items() if e in specs}) \
                if self.houses else {}
            for entry_id, spec in specs.items():
                advisor = self.rooms.get(entry_id)
                if advisor is None:
                    continue
                arguments = (spec, advisor.learned, room_history(history, spec, outdoor, outdoor_rh, self.houses), sun, now,
                             outdoor, outdoor_rh, location, zone, self.houses, None, caps.get(entry_id), house_idle)
                try:
                    entry, report = await self._learn_room(arguments)
                except Exception:  # noqa: BLE001 - one room that fails keeps its twins
                    _LOGGER.exception("Hestia Comfort: nightly learning of %s", spec.name)
                    continue
                await advisor.learned_now(entry, now, report)
                reports.append(report)
            try:
                # Hestia Weather learns the shade on its long statistics when it shares it; here only for an older one.
                if self._weather_shade() is None:
                    await self._learn_station_shade(now, (now - first).days + 1)
            except Exception:  # noqa: BLE001 - the shade learned before is kept
                _LOGGER.exception("Hestia Comfort: station shade")
            await self._save()
            if self.analysis():
                await self.hass.async_add_executor_job(self.files.learned, {"heure": now.isoformat(), "moteur": self.version, "pieces": reports})
            await self.hass.async_add_executor_job(self.files.prune, now)
        finally:
            self.learning = False

    async def _learn_room(self, arguments):
        """One room's nightly learning in its own process (night_worker.py, PLAN-OPTIMISATION.md point 10): a minute or
        more of pure calculation that, in one of Home Assistant's threads, slowed the whole of it down. Where a process
        cannot be started or fails, in Home Assistant's threads as before, its reason in the log."""
        payload = await self.hass.async_add_executor_job(partial(pickle.dumps, arguments, protocol=pickle.HIGHEST_PROTOCOL))
        try:
            process = await asyncio.create_subprocess_exec(sys.executable, "-I", str(NIGHT_WORKER), stdin=asyncio.subprocess.PIPE,
                                                           stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            out, err = await process.communicate(payload)
            if process.returncode == 0 and out:
                return await self.hass.async_add_executor_job(pickle.loads, out)
            reason = err.decode(errors="replace").strip().splitlines()[-1:] or [f"code {process.returncode}"]
        except OSError as error:
            reason = [str(error)]
        if not self.worker_failed:
            self.worker_failed = True
            _LOGGER.warning("Hestia Comfort: the nightly learning runs in Home Assistant's own threads (%s)", reason[0])
        return await self.hass.async_add_executor_job(learn_room, *arguments)

    async def _past_sun(self, days):
        """Open-Meteo's sun of the past days, each value the mean of the hour that ends at its time."""
        url = PAST_SUN.format(lat=round(self.hass.config.latitude, 1), lon=round(self.hass.config.longitude, 1), days=days)
        try:
            async with async_get_clientsession(self.hass).get(url, timeout=60) as response:
                hourly = (await response.json())["hourly"]
        except Exception:  # noqa: BLE001 - without the sun, the twins still learn the rest
            _LOGGER.warning("Hestia Comfort: Open-Meteo's past sun unavailable for the nightly learning")
            return Series([])
        hours = [(dt_util.parse_datetime(t + "+00:00") - timedelta(hours=1), v) for t, v in zip(hourly["time"], hourly["shortwave_radiation"])]
        # The same hours' sun and clouds, for the station's shade.
        self.past_sky = {at: (v, c) for (at, v), c in zip(hours, hourly.get("cloud_cover") or [None] * len(hours))}
        return Series(hours)

    async def _learn_station_shade(self, now, days):
        """The station's shade, learned again from the recorder's hours and Open-Meteo's of the same days; the cells not
        seen again are kept (advisor/physics/station_sun.py)."""
        entity = self._station_sun()
        if entity is None or not self.past_sky:
            return
        start = now.replace(minute=0, second=0, microsecond=0) - timedelta(days=min(days, 92))
        means = await self._hourly_means(entity, start, now, "hour")
        hours = [(at, sky[0], means.get(at), sky[1]) for at, sky in self.past_sky.items() if at in means]
        self.station_shade = learn_shade(hours, self.hass.config.latitude, self.hass.config.longitude, self.station_shade)
