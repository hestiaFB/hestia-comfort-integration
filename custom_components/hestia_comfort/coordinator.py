"""Event-driven inputs plus a clock tick for freshness, per configured zone."""
from collections import deque
from dataclasses import asdict, replace
from datetime import timedelta
import logging
import random

from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.core import callback
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN, LEARNING_REFRESH_SECONDS, OPEN_DEBOUNCE_SECONDS, SOURCES, STARTUP_GRACE_SECONDS, VIEW_VERSION
from .engine.assessment import Opening, Settings, assess
from .engine import feedback, habits, horizon, learning, night, twin, voc as vocs
from .engine.sources import Reading
from .engine.verdict import verdict
from .configuration import DATA_CONFIG
from .exterior import exterior_reading
from . import advisor_home, cover_link, weather_link
from .room.advice import verdict as advisor_verdict
from .room.constants import FULL_SPAN, MEASURES, MEASURE_COOLDOWN, SHARED_SOURCES, SHORT_SPAN, STATE_KINDS, SUN_SMOOTHING, TWIN_FORMAT  # noqa: F401 - also read by the tests
from .room.learning import LearningMixin
from .room.volume import VolumeMixin
from .room.presence import PresenceMixin
from .room.sun import SunMixin
from .room.airings import AiringsMixin
from .room.readings import ReadingsMixin


def heating_power(attributes):
    """The heating's power in percent: Versatile Thermostat's own, or 100 while the thermostat heats, 0 otherwise."""
    for key, scale in (("power_percent", 1), ("on_percent", 100)):
        value = attributes.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return max(0.0, min(100.0, float(value) * scale))
    action = attributes.get("hvac_action")
    return None if action is None else 100.0 if action == "heating" else 0.0


def heated_minutes(rows, start, end):
    """Minutes spent « heating » between start and end, from the recorder's rows of the thermostat's « hvac_action »
    (an attribute: it changes at the row's last update, not at its last state change)."""
    total, since = 0.0, None
    for row in rows:
        moment = max(row.last_updated, start)
        if since is not None:
            total += (moment - since).total_seconds()
        since = moment if row.attributes.get("hvac_action") == "heating" else None
    if since is not None:
        total += (end - since).total_seconds()
    return round(total / 60)


# The measures whose last hours are kept for the trends: (history, reading).
HISTORIES = (("temperature_history", "indoor_temperature"), ("outdoor_history", "outdoor_temperature"), ("humidity_history", "indoor_humidity"),
             ("co2_history", "co2"), ("voc_history", "voc"), ("pm25_history", "pm25"),
             # The « Ouvertures » and « Chauffage » modules: the sun outside and the heating's power (30 October).
             ("solar_history", "solar"), ("heating_history", "heating_power"))


class ComfortCoordinator(LearningMixin, VolumeMixin, PresenceMixin, SunMixin, AiringsMixin, ReadingsMixin, DataUpdateCoordinator):
    def __init__(self, hass, entry):
        logger = logging.getLogger(__name__)
        # A contact or a sensor that changes is shown within a second, not after the default 10 s grouping: the
        # minute tick only ages the readings and moves the clock (night, countdowns), all in memory.
        super().__init__(hass, logger, name=DOMAIN, config_entry=entry, update_interval=timedelta(seconds=60),
                         request_refresh_debouncer=Debouncer(hass, logger, cooldown=1.0, immediate=True))
        self._measure_refresh = Debouncer(hass, logger, cooldown=MEASURE_COOLDOWN, immediate=False, function=self.async_refresh)
        self._measure_ids = set()
        self.config = {**entry.data, **entry.options}
        self.settings = Settings(**self.config.get("settings", {}))
        self.home_configuration = hass.data.get(DATA_CONFIG)
        self.previous = None
        self._horizon = None
        self.entry_id = entry.entry_id
        self.stop_listeners = set()
        self.opened_since = {}
        # Windows opened while the advice said « open »: the gesture was followed, no bounce delay to wait for.
        self.followed = set()
        self.started = dt_util.utcnow()
        self.history_reports = {}
        self.histories = {key: deque(maxlen=360) for key, _ in HISTORIES}
        # The heating's last 24 hours, read in the recorder now and then: minutes heated, and when it was read.
        self.heating_day, self._heating_day_due = None, None
        # The VOC index of the last minutes, for its mean (engine/voc.py).
        self.voc_points = deque(maxlen=240)
        # The last airing while the VOC called for air, noted the moment the room is shut: the pause starts there.
        self.voc_aired = None
        # The index when the room was opened, while it stays open: climbing well above it, the air outside brings VOC.
        self.voc_opened_level = None
        self.voc_going = False
        # The last time the rain was measured falling: just after it, the air holds fewer pollens.
        self.rained_at = None
        # What each airing did to the index, read in the history, and the times of day when opening made it climb.
        self.voc_airings, self.voc_slots = [], []
        # The sun of the last quarter of an hour: a passing cloud does not make « Soleil » come and go.
        self._sun_samples = deque(maxlen=120)
        # Where the station's sensor is shaded, learned from its history; the sky's share seen just before the shade.
        self.sun_shade = None
        self._sun_before = self._sky_bias = None
        # (computed at, seven-day outdoor mean or None): the seasonal comfort range follows it.
        self.season = (None, None)
        self.day_range = None
        self.humidity_floor = None
        self.humidity_ceiling = None
        self._season_failed = False
        # What airing really does in this room, learned from its past openings (engine/learning.py).
        self.drying_model = {**learning.fit([]), **learning.settling([])}
        # How fast each combination of openings renews the air, from the CO₂ (engine/airflow.py).
        self.flow_model = {}
        # The next full pass (ten days), and the next short one asked for by a window shut (the last day).
        self._full_due = None
        self._learning_due = None
        self._learning_failed = False
        # The history read during one learning pass, shared by the airing model and the twin: {(entity, attribute): rows}.
        self._history_pass = {}
        self._learning_store = Store(hass, 1, f"{DOMAIN}.learning.{entry.entry_id}")
        # The room's twin (engine/twin.py): it observes and learns, it never decides an advice.
        self._twin_store = Store(hass, 1, f"{DOMAIN}.twin.{entry.entry_id}")
        self.twin = None
        self._twin_failed = False
        # The feedback loop (engine/feedback.py): airings followed and measured, advice left aside.
        self._feedback_store = Store(hass, 1, f"{DOMAIN}.feedback.{entry.entry_id}")
        self.feedback = []
        self._feedback_unsaved = False
        self._experiment = None
        self._advice_since = None
        self._advice_followed = False
        # Habits found in the twin's half hours (engine/habits.py), asked about in the hub.
        self.habits = []
        # The season the home lives in (Hestia Weather's, or a season sensor): hours of airing, answers by season.
        self.season_name = None
        # Rooms open onto this one (no wall between them): their openings are this room's too.
        self.partners = self._partners()
        self.windows = list(dict.fromkeys([*self.config.get("windows", []), *(e for p in self.partners for e in p["windows"])]))
        # The sources read for this room: its own, completed by what belongs to its shared air (engine/volume.py).
        self.sources = self._sources()
        # This room's advice as computed alone, before the volume settles opposite gestures.
        self.own = None
        self._own_gesture = None

    async def async_start(self):
        self.config_entry.async_on_unload(self.async_stopped)
        self.config_entry.async_on_unload(self._save_feedback)
        ids = set(self.sources.values()) | set(self.windows) | set(self.config.get("presence", []))
        for meta in self.config.get("openings", {}).values():
            ids.update(meta[k] for k in ("cover_entity", "auto_entity", "override_entity") if meta.get(k))
        # Covers driven with the sun (Adaptive Cover Pro, CoverAutomatic, Cover Extender): their signals are read without being chosen by hand.
        self.drivers = self._drivers()
        for roles in self.drivers.values():
            ids.update(roles.get("watch") or [v for k, v in roles.items() if k in cover_link.SIGNALS])
        # The sun is read at each refresh: the minute tick follows it, its own changes would only add refreshes.
        shared = self.home_configuration.effective_sources(self.config) if self.home_configuration else {}
        ids |= {s["entity_id"] for s in shared.values()}
        self._measure_ids = ({v for k, v in self.sources.items() if k in MEASURES} |
                             {s["entity_id"] for k, s in shared.items() if k in MEASURES}) - set(self.windows)
        self.config_entry.async_on_unload(self._measure_refresh.async_shutdown)
        # Who is at home: the alarm panels (Alarmo) and the home zone.
        ids |= set(self._occupancy_entities())
        ids.discard("")
        if ids:
            self.config_entry.async_on_unload(async_track_state_change_event(self.hass, sorted(ids), self._changed))
        # Linked to Hestia Weather: recompute when its forecasts or alerts change.
        if weather_link.api(self.hass) and (place := self._weather_place()):
            self.config_entry.async_on_unload(weather_link.listen(self.hass, place, lambda: self.hass.async_create_task(self.async_request_refresh())))
        stored = await self._feedback_store.async_load() or {}
        self.feedback = feedback.keep(stored.get("records"), dt_util.utcnow())
        await self._restore_learning()
        # The 3.0 advisor (advisor_home.py): this room advises its air when it leads it. One that fails to start leaves
        # the room on the 2.1 advice.
        try:
            self.advisor = await advisor_home.async_room(self.hass, self)
        except Exception:  # noqa: BLE001
            logging.getLogger(__name__).exception("Hestia Comfort: advisor 3.0 for %s", self.config.get("name"))
            self.advisor = None
        await self.async_config_entry_first_refresh()

    @callback
    def async_stopped(self):
        for listener in tuple(self.stop_listeners):
            listener()
        self.stop_listeners.clear()

    async def _changed(self, event):
        entity_id = event.data.get("entity_id")
        old, new = event.data.get("old_state"), event.data.get("new_state")
        before, after = old.state if old else None, new.state if new else None
        now = dt_util.utcnow()
        if entity_id in self.windows:
            began = self.opened_since.get(entity_id)
            if after != "on" or before not in ("on", "off"):
                self.opened_since.pop(entity_id, None)
                self.followed.discard(entity_id)
            elif before == "off":
                if not any(e in self.opened_since for e in self.windows):
                    # The reading at the opening, not the mean: a mean still coming down from a peak would hide the climb.
                    self.voc_opened_level = self.voc_points[-1][1] if self.voc_points else None
                    threshold = self._voc_threshold()
                    self.voc_going = bool(threshold) and vocs.is_going(list(self.voc_points), now, threshold)
                self.opened_since[entity_id] = now
                shown = (self.data or {}).get("assessment") or {}
                if shown.get("action") == "ouvrir":
                    self.followed.add(entity_id)
                    self._advice_followed = True
                    # The advice followed becomes an experiment: the measure now, and what was predicted.
                    if self._experiment is None:
                        values = {k: (v or {}).get("value") for k, v in ((self.data or {}).get("observations") or {}).items()}
                        self._experiment = feedback.start(shown, values, now)
            if before == "on" and after == "off":
                self._note_voc_airing(began, now)
                if not any(e in self.opened_since for e in self.windows):
                    self.voc_opened_level = None
                # Learn from this opening once the room has had time to give its water back.
                self._learning_due = now + learning.REBOUND_AFTER + timedelta(minutes=5)
                # Recompute right when the bounce delay ends, not at the next periodic refresh.
                cancel = async_call_later(self.hass, OPEN_DEBOUNCE_SECONDS + 1, self._bounce_over)
                self.stop_listeners.add(cancel)
        if entity_id in self._measure_ids:
            # An attribute that changed alone (a friendly name, an icon) changes nothing in the advice.
            if before != after:
                await self._measure_refresh.async_call()
            return
        await self.async_request_refresh()

    async def _seed_histories(self, readings, now):
        """After a start, the last half hour read in the recorder: the tiles' trends do not wait for new measures."""
        self._seeded = True
        wanted = {key: readings[source].source for key, source in HISTORIES
                  if not self.histories[key] and readings.get(source) and readings[source].source}
        if not wanted:
            return
        try:
            from homeassistant.components.recorder import get_instance
            from . import recorder_history
            start = now - timedelta(minutes=30)
            rows = await get_instance(self.hass).async_add_executor_job(recorder_history.read, self.hass, start, now, set(wanted.values()))
            seeded = {}
            for key, entity_id in wanted.items():
                seeded[key] = []
                for row in rows.get(entity_id, []):
                    try:
                        value = float(row.state)
                    except (TypeError, ValueError):
                        continue
                    # The state at the start of the window was set earlier: it holds from the window's start.
                    seeded[key].append((max(row.last_changed, start).isoformat(), value, row.last_changed))
        except Exception:  # noqa: BLE001 - no recorder, or a failed read: the trends simply start with this session
            logging.getLogger(__name__).debug("Recorder history unavailable for the trends", exc_info=True)
            return
        for key, points in seeded.items():
            for stamp, value, changed in points:
                self.histories[key].append((stamp, value))
                self.history_reports[key] = changed

    async def _read_heating_day(self, entity_id, now):
        """How long the room heated over the last 24 hours (the thermostat's « heating » action), read every ten minutes."""
        if self._heating_day_due is not None and now < self._heating_day_due:
            return
        self._heating_day_due = now + timedelta(minutes=10)
        try:
            from homeassistant.components.recorder import get_instance
            from . import recorder_history
            start = now - timedelta(hours=24)
            rows = (await get_instance(self.hass).async_add_executor_job(
                recorder_history.read, self.hass, start, now, [entity_id], "hvac_action")).get(entity_id, [])
        except Exception:  # noqa: BLE001 - no recorder: the module says nothing about the last day
            logging.getLogger(__name__).debug("Recorder history unavailable for the heating day", exc_info=True)
            return
        self.heating_day = heated_minutes(rows, start, now)

    def _context(self, now, readings):
        for key, source in HISTORIES:
            history = self.histories[key]
            reading = readings.get(source)
            # Keep samples received during this session; repeated clock refreshes do not invent samples.
            if reading and reading.usable and reading.received_at:
                stamp = dt_util.parse_datetime(reading.received_at)
                if stamp and stamp.tzinfo and -60 <= (now - stamp).total_seconds() <= 1800:
                    previous_report = self.history_reports.get(key)
                    if previous_report is None or stamp > previous_report:
                        # Coverage starts when this session observed the source. A sensor
                        # last reported before startup must not fabricate a long history.
                        history.append((now.isoformat(), reading.value))
                        self.history_reports[key] = stamp
            while history and (now - dt_util.parse_datetime(history[0][0])).total_seconds() > 10800:
                history.popleft()
        def minutes(eid, starts, expected):
            state = self.hass.states.get(eid)
            if not state or state.state != expected:
                starts.pop(eid, None)
            start = starts.get(eid)
            return max(0, (now - start).total_seconds() / 60) if start else None
        voc_reading = readings.get("voc")
        if voc_reading and voc_reading.usable and isinstance(voc_reading.value, (int, float)):
            if not self.voc_points or self.voc_points[-1][1] != voc_reading.value or now - self.voc_points[-1][0] > timedelta(minutes=1):
                self.voc_points.append((now, voc_reading.value))
        # Two means apart and the reading before them: whether the index is falling by itself.
        while self.voc_points and now - self.voc_points[0][0] > timedelta(minutes=3 * vocs.MEAN_MINUTES):
            self.voc_points.popleft()
        # The last airing about the VOC: what it left, for the pause that follows. The one noted at the closing counts at
        # once; the measured record only comes a few minutes later, and not for a short or unadvised airing.
        recorded = next((r for r in reversed(self.feedback) if r.get("measure") == "voc" and r.get("end")), None)
        aired = max((a for a in (recorded, self.voc_aired) if a), key=lambda a: a["end"], default=None)
        # The season first: the hours of airing and the answers about a window open at night depend on it.
        self._remember_season(weather_link.season(self.hass, self._weather_place()) or self._season(readings))
        return {**self.config.get("evolution", {}), "occupied": self._occupied(), "people": self._people(), "alarm": self._alarm(),
                "volume": self._volume_air(readings),
                # Today's pollens, only when someone at home said they are allergic (« Réglages généraux »).
                "pollen": self.home_configuration.pollen() if self.home_configuration else None,
                "rained_at": self._rained(readings, now),
                "intended_open": self._intended_open(now), "zone": dt_util.get_default_time_zone(),
                # The season: Hestia Weather's when it is the exterior source, else a season sensor chosen in « Extérieur ».
                "season_name": self.season_name,
                "heated": self.config.get("heated", True), "outdoor_mean_7d": self.season[1],
                # What the room holds that makes its air change: a shower (« Équipements »).
                "equipment": self.config.get("equipment") or [],
                "indoor_day_range": self.day_range, "drying_model": self.drying_model, "flows": self.flow_model,
                "humidity_floor_3h": self.humidity_floor,
                "humidity_ceiling_3h": self.humidity_ceiling,
                "opening_minutes": {e: minutes(e, self.opened_since, "on") for e in self.windows},
                "presence_off_minutes": {e: self._off_minutes(e, now) for e in self.config.get("presence", [])},
                "voc_mean": vocs.mean(list(self.voc_points), now) if voc_reading and voc_reading.usable else None,
                "voc_aired_at": aired["end"] if aired else None, "voc_aired_after": aired.get("after") if aired else None,
                **self._voc_learned(now),
                **{k: list(v) for k, v in self.histories.items()}}

    async def _async_update_data(self):
        now = dt_util.utcnow()
        readings = {}
        selected = self.sources
        for key, kind in SOURCES.items():
            entity_id = selected.get(key)
            # Optional unselected sources do not fabricate a missing measurement.
            # The heating indicator is read with the heating, never alone.
            if not entity_id or key == "heating_indicator":
                continue
            readings[key] = self._reading(entity_id, kind, now)
        if self.home_configuration:
            for key, spec in self.home_configuration.live_sources(self.config).items():
                readings[key] = exterior_reading(self.hass.states.get(spec["entity_id"]), key, spec, now=now, max_age=self.settings.max_age_seconds)
        windows = self.config.get("windows", [])
        declared = self.config.get("openings", {})
        # Older rooms declared rain shelter for the whole room instead of per opening.
        sheltered = self.config.get("rain_exposed") is False
        openings = {e: o for p in self.partners for e, o in p["openings"].items()}
        openings.update({e: Opening(**{"sheltered": sheltered, **declared.get(e, {})}) for e in windows})
        drivers = getattr(self, "drivers", None)
        if drivers is None:
            drivers = self.drivers = self._drivers()
        for e, roles in drivers.items():
            if e in openings:
                o, known = openings[e], cover_link.facts(self.hass, roles)
                # An angle typed by the person wins over the one the driver was given.
                openings[e] = replace(o, driver=roles.get("driver", "adaptive_cover_pro"), auto_entity=o.auto_entity or roles.get("auto"),
                                      # CoverAutomatic says a hand on the cover in its status: read as the override below.
                                      override_entity=o.override_entity or roles.get("override") or roles.get("status"),
                                      azimuth=o.azimuth if o.azimuth is not None else known["azimuth"],
                                      exposure=o.exposure or cover_link.exposure(known["azimuth"]),
                                      width=o.width if o.width is not None else known["width"],
                                      height=o.height if o.height is not None else known["height"])
                reason = known["reason"] or cover_link.values(self.hass, roles).get("reason")
                if reason:
                    readings[f"shutter_reason:{e}"] = Reading(reason, "valid", roles.get("target") or roles.get("status") or roles.get("mode"), now.isoformat())
        for entity_id in self.windows:
            readings[f"window:{entity_id}"] = self._reading(entity_id, "window", now)
        for entity_id in self.config.get("presence", []):
            state = self.hass.states.get(entity_id)
            reading = self._reading(entity_id, "presence", now)
            readings[f"presence:{entity_id}"] = replace(reading, detail=state.attributes.get("device_class") if state else "unavailable")
        for entity_id in windows:
            meta = declared.get(entity_id, {})
            if meta.get("shutter") != "connected":
                continue
            cover = meta.get("cover_entity")
            if cover:
                state = self.hass.states.get(cover)
                # Some covers report only open/closed. Their absent position is an
                # optional capability, while cover_state still tracks availability.
                if state and state.attributes.get("current_position") is not None:
                    readings[f"cover:{entity_id}"] = self._reading(cover, "cover", now)
                readings[f"cover_state:{entity_id}"] = self._reading(cover, "cover_state", now)
            opening = openings[entity_id]
            for field, kind in (("auto_entity", "shutter_auto"), ("override_entity", "shutter_override")):
                if getattr(opening, field):
                    readings[f"{kind}:{getattr(opening, field)}"] = self._reading(getattr(opening, field), kind, now)
            roles = drivers.get(entity_id) or {}
            # A driver's own signals are extras: one it leaves unavailable (a disabled
            # feature) is simply not read, never counted as a sensor that stopped answering.
            live = lambda role: roles.get(role) and (s := self.hass.states.get(roles[role])) and s.state not in ("unknown", "unavailable")
            for role, kind in (("sun", "shutter_sun"), ("target", "shutter_target")):
                if live(role):
                    readings[f"{kind}:{entity_id}"] = self._reading(roles[role], kind, now)
            # Its own switches: on, following the sun, watching for a hand on the cover, closing against heat.
            for role in ("enabled", "tracking", "detection", "climate"):
                if live(role):
                    readings[f"shutter_{role}:{entity_id}"] = self._reading(roles[role], "shutter_auto", now)
            for role in ("sun_start", "sun_end", "override_end"):
                state = self.hass.states.get(roles[role]) if roles.get(role) else None
                moment = dt_util.parse_datetime(state.state) if state else None
                # In local time, so that « 13 h 50 » reads as the person's clock.
                if moment:
                    readings[f"shutter_{role}:{entity_id}"] = Reading(dt_util.as_local(moment).isoformat(), "valid", roles[role], state.last_reported.isoformat())
            # The signals a driver says in its own words (CoverAutomatic's status, Cover Extender's attribute on the cover).
            derived = cover_link.values(self.hass, roles) if roles else {}
            source = roles.get("status") or roles.get("cover") or roles.get("mode")
            for role, kind in (("override", "shutter_override"), ("sun", "shutter_sun"), ("target", "shutter_target"), ("sun_start", "shutter_sun_start"), ("sun_end", "shutter_sun_end")):
                if derived.get(role) is not None:
                    key = f"shutter_override:{opening.override_entity or source}" if role == "override" else f"{kind}:{entity_id}"
                    readings[key] = Reading(derived[role], "valid", source, now.isoformat())
        if selected.get("purifier"):
            state = self.hass.states.get(selected["purifier"])
            # A purifier's on/off state is useful even without speed reporting.
            if state and state.attributes.get("percentage") is not None:
                readings["purifier_speed"] = self._reading(selected["purifier"], "purifier_speed", now)
        if selected.get("heating"):
            # The thermostat's mode (frost protection, eco, comfort…), shown on the card; the advice does not use it.
            state = self.hass.states.get(selected["heating"])
            if state and state.state not in ("unknown", "unavailable"):
                preset = state.attributes.get("preset_mode")
                mode, detail = (preset, "preset") if preset and preset != "none" else (state.state, "hvac")
                readings["heating_mode"] = Reading(mode, "valid", selected["heating"], state.last_reported.isoformat(), detail)
                # Its power: Versatile Thermostat says it in percent; any other thermostat heats fully or not at all.
                power = heating_power(state.attributes)
                if power is not None:
                    # A state that lasts: a thermostat heating for an hour reports nothing new, yet its curve goes on.
                    readings["heating_power"] = Reading(power, "valid", selected["heating"], now.isoformat(), "percent")
                target = state.attributes.get("temperature")
                if isinstance(target, (int, float)) and not isinstance(target, bool):
                    readings["heating_target"] = Reading(float(target), "valid", selected["heating"], state.last_reported.isoformat())
            await self._read_heating_day(selected["heating"], now)
        outlook = weather_link.outlook(self.hass, self._weather_place())
        # The sun: estimated where the station is shaded (engine/sunlight.py), then averaged over a quarter of an hour.
        if (solar := readings.get("solar")) is not None:
            readings["solar"] = self._steady_sun(self._unshaded_sun(solar, now, outlook), now)
        await self._refresh_season(now)
        if self._full_due is None:
            # Spread over the first minutes: rooms started together do not all read ten days of history at once.
            self._full_due = now + timedelta(seconds=random.uniform(30, 300))
        span = None
        if now >= self._full_due:
            span, self._full_due = FULL_SPAN, now + timedelta(seconds=LEARNING_REFRESH_SECONDS)
        elif self._learning_due is not None and now >= self._learning_due:
            span = SHORT_SPAN
        if span is not None:
            self._learning_due = None
            self.config_entry.async_create_background_task(self.hass, self._learn(now, span), f"{DOMAIN} learning {self.entry_id}")
        # The card shows a contact as it is; the advice ignores an opening younger than the bounce delay.
        advice_readings = {k: (replace(r, value=False, detail="debounce") if k.startswith("window:") and self._bouncing(k[7:], r, now) else r)
                           for k, r in readings.items()}
        def now_value(key):
            reading = readings.get(key)
            return reading.value if reading and reading.usable and isinstance(reading.value, (int, float)) and not isinstance(reading.value, bool) else None
        current = {"ti": now_value("indoor_temperature"), "hi": now_value("indoor_humidity"), "te": now_value("outdoor_temperature"),
                   "he": now_value("outdoor_humidity"), "sun": self._sun_now(now_value("solar")),
                   "opened": 1.0 if any(r.usable and r.value is True for k, r in advice_readings.items() if k.startswith("window:")) else 0.0,
                   "heated": 1.0 if readings.get("heating") and readings["heating"].value == "heating" else 0.0,
                   "holding": bool(readings.get("heating") and readings["heating"].value in ("heating", "idle")),
                   "co2": now_value("co2"), "voc": now_value("voc")}
        # Only the windows of the room sharing this air open: the twin weighs them as it learned.
        mine = set(self.config.get("windows", []))
        open_now = {k[7:] for k, r in advice_readings.items() if k.startswith("window:") and r.usable and r.value is True}
        current["far"] = 1.0 if self.partners and open_now and not open_now & mine else 0.0
        current["beside"] = self._beside_now()
        if not getattr(self, "_seeded", False):
            await self._seed_histories(readings, now)
        context = self._context(now, readings)
        context["thermostat"] = self._thermostat()
        context["thermostat_reference"] = self.config.get("thermostat_reference", True)
        # The room in an hour, as its twin sees it: a cold room already warming by itself is not told to heat.
        context["next_hour_temperature"] = (twin.next_hour(self.twin, current) or {}).get("temperature")
        self.previous = assess(advice_readings, self.settings, self.previous, openings, self._sun(), outlook, now, context=context)
        own = self.previous.to_dict()
        # The room's own learning, once optimal, gives the advised gesture its predicted result.
        summary = feedback.summarize(self.feedback, now)
        if self.heating_day is not None:
            own.setdefault("features", {})["heating_day"] = {"minutes": self.heating_day}
        own.setdefault("features", {})["learned"] = twin.learned_advice(own, self.twin, current, (self.drying_model or {}).get("openings", 0), summary)
        # Tonight, simulated on the room's own twin (engine/night.py): when opening cools, what it leaves for tomorrow.
        learned_twin = self.twin or {}
        own["features"]["night"] = night.plan(learned_twin.get("model") if learned_twin.get("status") == "ready" else None,
                                              current, outlook.get("hours") or [], now, minimum=self.settings.minimum,
                                              mass=learned_twin.get("mass"), sun=self._sun_ahead())
        # « Prochaines heures »: the room without the advised gesture and with it, for the card's graph (engine/horizon.py).
        own["features"]["horizon"] = horizon.build(own, learned_twin.get("model") if learned_twin.get("status") == "ready" else None,
                                                   current, outlook.get("hours") or [], now, minimum=self.settings.minimum,
                                                   mass=learned_twin.get("mass"), sun=self._sun_ahead(),
                                                   previous=self._horizon)
        self._horizon = own["features"]["horizon"]
        assessment = self._settle(own)
        self._track(assessment, current, now)
        learned = self.twin or {}
        precision = learned.get("precision") or {}
        twin_view = {"status": learned.get("status", "learning"), "days": learned.get("days", 0), "samples": learned.get("samples", 0),
                     "next_hour": twin.next_hour(learned, current),
                     "precision": {k: precision[k] for k in ("hours", "temperature", "humidity")} if precision else None,
                     "progress": self.learning_progress()}
        view = {"version": VIEW_VERSION, "entry_id": self.entry_id,
                "area_id": self.config.get("area_id"), "title": self.config.get("name"),
                "comfort_minimum": self.settings.minimum, "comfort_maximum": self.settings.maximum,
                "computed_at": now.isoformat(), "assessment": assessment,
                "volume": [{"entry_id": p["entry_id"], "title": p["title"]} for p in self.partners], "volume_name": self.volume_name,
                # Measures read from the room sharing this air: the card shows them once, under the room that has them.
                "inherited": self.inherited(),
                "twin": twin_view,
                "feedback": {"last": summary["last"], "week": summary["week"]},
                "habit": habits.now_habit(self.habits, self._answers(), dt_util.as_local(now), self.config.get("name") or "", self.config.get("area_id"),
                                          self.config.get("equipment") or ()),
                "observations": {k: asdict(v) for k, v in readings.items()},
                "names": {e: (state.name if (state := self.hass.states.get(e)) else e) for e in self.windows},
                "starting": (now - self.started).total_seconds() < STARTUP_GRACE_SECONDS}
        # What the card's banner says, as states for the entities (engine/verdict.py, kept word for word with the card).
        # A verdict that fails leaves the room's advice standing: its entities only go unknown.
        try:
            view["verdict"] = verdict(view, dt_util.as_local)
        except (KeyError, TypeError, ValueError):
            logging.getLogger(__name__).exception("Hestia Comfort: verdict for %s", view["title"])
            view["verdict"] = None
        # The 3.0 advisor's decision for this room's air (room/advice.py), shown by the card in place of the 2.1 advice.
        view["advice3"] = advisor_home.result(self.hass, self.entry_id)
        # The entities and the lights then say the 3.0 decision too, never the 2.1 one beside it.
        if view["advice3"]:
            view["verdict"] = advisor_verdict(view["advice3"], view)
        return view

    def outdoor_entity(self):
        """The outdoor temperature sensor this room reads, for the home's review (review_source.py)."""
        return self._outdoor_entity()

    def _outdoor_entity(self):
        return self._source_entity("outdoor_temperature")

    def _source_entity(self, key):
        """The entity behind a room source, chosen in the room or shared by the home (outdoor ones)."""
        if self.home_configuration and (spec := self.home_configuration.effective_sources(self.config).get(key)):
            return spec["entity_id"]
        return self.sources.get(key)

    async def _bounce_over(self, _now):
        # A coroutine, so Home Assistant runs it in its own loop (a plain function would run in a worker thread).
        await self.async_refresh()

    def _remember_season(self, name):
        self.season_name = name
        return name

    @staticmethod
    def _season(readings):
        reading = readings.get("season")
        return reading.value if reading and reading.quality == "valid" else None

    def _rained(self, readings, now):
        """When the rain was last measured falling, ISO time, or None."""
        rain = readings.get("rain")
        if rain is not None and rain.usable and rain.value is True:
            self.rained_at = now
        return self.rained_at.isoformat() if self.rained_at else None

    def _weather_place(self):
        home = self.home_configuration.home if self.home_configuration else {}
        return home.get("weather") if home.get("configured") else None


















