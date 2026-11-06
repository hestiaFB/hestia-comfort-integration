"""What a room learns: its stores, ten days of history read compacted, its twin, and the hourly statistics."""
from datetime import timedelta
from functools import partial
import asyncio

from homeassistant.util import dt as dt_util

from .. import recorder_history
from ..const import DOMAIN, SEASON_REFRESH_SECONDS
from ..engine import airflow, habits, learning, sunlight, twin, voc as vocs
from ..engine.sources import indicator_state
from .constants import FULL_SPAN, TWIN_FORMAT


def _contacts(states, windows):
    """{window: [(time, open or not, None while it does not answer)]} from a recorder answer."""
    return {e: [(row.last_changed, {"on": True, "off": False}.get(row.state)) for row in states.get(e, [])] for e in windows}


class LearningMixin:
    """Part of ComfortCoordinator: its methods use the coordinator's own state (self)."""

    async def _restore_learning(self):
        """What the room learned before a restart, from its stores: known at once, while the history is read again later."""
        try:
            stored = await self._learning_store.async_load() or {}
            listed = lambda key: stored.get(key) if isinstance(stored.get(key), list) else []
            self.drying_model = {**learning.fit(listed("episodes")), **learning.settling(listed("peaks"))}
            self.flow_model = airflow.fit(listed("flows"))
            stored = await self._twin_store.async_load() or {}
            if isinstance(stored.get("samples"), list) and stored.get("format") == TWIN_FORMAT and stored["samples"]:
                rows, now = stored["samples"], dt_util.utcnow()
                self.twin = await self.hass.async_add_executor_job(twin.summary, rows, now)
                self.habits = await self.hass.async_add_executor_job(habits.detect, rows, dt_util.get_default_time_zone())
        except Exception:  # the history read a few minutes later rebuilds it all
            self.logger.warning("What %s learned could not be restored", self.config.get("name"), exc_info=True)

    async def _history(self, entity_ids, start, end, attribute=None):
        """Compact recorder rows of these entities (recorder_history.py), read once per learning pass."""
        from homeassistant.components.recorder import get_instance
        wanted = [e for e in dict.fromkeys(entity_ids) if e]
        if missing := [e for e in wanted if (e, attribute) not in self._history_pass]:
            rows = await get_instance(self.hass).async_add_executor_job(
                partial(recorder_history.read, self.hass, start, end, missing, attribute=attribute))
            self._history_pass.update({(e, attribute): rows.get(e, []) for e in missing})
        return {e: self._history_pass[(e, attribute)] for e in wanted}

    async def _learn(self, now, span=FULL_SPAN):
        """Refit the room's airing model, one room at a time: each pass holds a share of ten days of history."""
        lock = self.hass.data.setdefault(f"{DOMAIN}_learning_lock", asyncio.Lock())
        async with lock:
            try:
                await self._learn_pass(now, span)
            finally:
                self._history_pass = {}

    async def _learn_pass(self, now, span=FULL_SPAN):
        """Refit the room's airing model from the stored openings plus the recorder's recent history."""
        stored = await self._learning_store.async_load() or {}
        episodes = stored.get("episodes") if isinstance(stored.get("episodes"), list) else []
        flows = stored.get("flows") if isinstance(stored.get("flows"), list) else []
        shed = stored.get("peaks") if isinstance(stored.get("peaks"), list) else []
        keys = ("indoor_temperature", "indoor_humidity", "outdoor_temperature", "outdoor_humidity")
        sources = {k: self._source_entity(k) for k in keys}
        co2 = self.sources.get("co2")
        # The partner rooms' windows air this room too: their openings teach it as well.
        windows = self.windows
        humidity = all(sources.values())
        if windows and (humidity or co2) and "recorder" in self.hass.config.components:
            try:
                states = await self._history([*windows, *sources.values(), co2], now - span, now)
                fahrenheit = self._fahrenheit([*sources.values(), co2])

                def prepare():
                    """In the executor (PLAN-OPTIMISATION.md, point 2): ten days of rows turned into points."""
                    points = lambda entity_id: self._points(states, entity_id, fahrenheit)
                    return (_contacts(states, windows), [points(sources[k]) for k in keys] if humidity else [],
                            points(co2) if co2 else [])

                contacts, measured, co2_points = await self.hass.async_add_executor_job(prepare)
                if humidity:
                    fresh = await self.hass.async_add_executor_job(learning.episodes, contacts, *measured)
                    episodes = learning.merge(episodes, fresh, now)
                    # The peaks of water the room sheds by itself, windows shut: what waiting brings.
                    fresh = await self.hass.async_add_executor_job(learning.peaks, contacts, *measured)
                    shed = learning.merge(shed, fresh, now)[-learning.KEEP_PEAKS:]
                if co2:
                    fresh = await self.hass.async_add_executor_job(airflow.flows, contacts, co2_points)
                    flows = airflow.merge(flows, fresh, now)
                await self._learning_store.async_save({"episodes": episodes, "flows": flows, "peaks": shed})
            except Exception:  # the room then keeps what it learned before, or the default model
                if not self._learning_failed:
                    self._learning_failed = True
                    self.logger.warning("Past openings could not be read for %s", self.config.get("name"), exc_info=True)
        model, flow_model = {**learning.fit(episodes), **learning.settling(shed)}, airflow.fit(flows)
        # The twin only observes: the next periodic refresh shows it, no extra one that would delay a sensor change.
        await self._learn_twin(now, span)
        if model != self.drying_model or flow_model != self.flow_model:
            self.drying_model, self.flow_model = model, flow_model
            await self.async_request_refresh()

    def _fahrenheit(self, entity_ids):
        """The entities reporting in °F, read on the loop: the points are made in the executor, which never reads
        Home Assistant's states."""
        return {e for e in entity_ids if e and (state := self.hass.states.get(e)) and state.attributes.get("unit_of_measurement") == "°F"}

    @staticmethod
    def _points(states, entity_id, fahrenheit=()):
        """Numeric (time, value) points of one entity from a recorder answer, in °C for temperatures (`fahrenheit`: the
        entities reporting in °F)."""
        converted = entity_id in fahrenheit
        out = []
        for row in states.get(entity_id, []):
            try:
                value = float(row.state)
            except (TypeError, ValueError):
                continue
            out.append((row.last_changed, (value - 32) * 5 / 9 if converted else value))
        return out

    async def _learn_twin(self, now, span=FULL_SPAN):
        """Add the days read (ten, or the last one after a window is shut) to the twin's half-hour samples (thirty days kept) and refit it."""
        stored = await self._twin_store.async_load() or {}
        # Samples kept before the sun was counted on the windows and the air was learned are rebuilt from the history.
        rows = stored.get("samples") if isinstance(stored.get("samples"), list) and stored.get("format") == TWIN_FORMAT else []
        keys = ("indoor_temperature", "indoor_humidity", "outdoor_temperature", "outdoor_humidity")
        sources = {k: self._source_entity(k) for k in keys}
        if all(sources.values()) and "recorder" in self.hass.config.components:
            try:
                solar, heating = self._source_entity("solar"), self.sources.get("heating")
                # The air as well: how CO₂ and VOC go down, windows shut and open.
                air = {k: self.sources.get(k) for k in ("co2", "voc")}
                start, full = now - span, span >= FULL_SPAN
                beside = [p["indoor"] for p in self.partners if all(p.get("indoor") or [None])]
                states = await self._history(
                    [*self.windows, *sources.values(), solar, *air.values(), *(e for pair in beside for e in pair)], start, now)
                # The thermostat's running state is an attribute: its own query keeps them.
                # An indicator chosen beside it says it in its state, and is what the room reads now.
                indicator = self.sources.get("heating_indicator") if heating else None
                running = await self._history([indicator or heating], start, now, None if indicator else "hvac_action") if heating else {}
                # What the executor needs from Home Assistant, read here on the loop (PLAN-OPTIMISATION.md, point 2).
                fahrenheit = self._fahrenheit([*sources.values(), solar, *air.values(), *(e for pair in beside for e in pair)])
                location, zone, shade = (self.hass.config.latitude, self.hass.config.longitude), dt_util.get_default_time_zone(), self.sun_shade
                facades, windows = self._facades(), list(self.windows)
                near = set(self.config.get("windows", [])) if self.partners else None
                threshold = self._voc_threshold() if full and air["voc"] else None

                def prepare():
                    """In the executor: the points, the station's sun with its shade learned again (ten days read), the
                    half-hour samples, and what the openings did to the VOC."""
                    points = lambda entity_id: self._points(states, entity_id, fahrenheit)
                    contacts = _contacts(states, windows)
                    heat = [(row.last_changed, indicator_state(row.state) == "heating") for row in running.get(indicator, [])] if indicator else \
                        [(row.last_updated, row.attributes.get("hvac_action") == "heating") for row in running.get(heating, [])
                         if hasattr(row, "attributes")]
                    learned_shade, sun = shade, []
                    if solar:
                        sunshine = points(solar)
                        if full or learned_shade is None:
                            learned_shade = sunlight.learn(sunshine, *location, zone)
                        sun = sunlight.corrected(sunshine, *location, learned_shade)
                    fresh = twin.samples(start, now, *(points(sources[k]) for k in keys), sun, contacts, heat,
                                         facades=facades, location=location,
                                         co2=points(air["co2"]) if air["co2"] else [], voc=points(air["voc"]) if air["voc"] else [],
                                         near=near, beside=[(points(t), points(h)) for t, h in beside])
                    # What the openings did to the VOC in their first minutes (ten days read): the hours when the air outside brings it.
                    airings = vocs.airings(contacts, points(air["voc"]), threshold, zone) if threshold else None
                    return fresh, learned_shade, airings

                fresh, learned_shade, airings = await self.hass.async_add_executor_job(prepare)
                if solar:
                    self.sun_shade = learned_shade
                rows = twin.merge(rows, fresh, now)
                if airings is not None:
                    self.voc_airings = airings
                    self.voc_slots = vocs.outdoor_slots(self.voc_airings)
                await self._twin_store.async_save({"samples": rows, "format": TWIN_FORMAT})
            except Exception:  # the twin then keeps what it learned before
                if not self._twin_failed:
                    self._twin_failed = True
                    self.logger.warning("The twin of %s could not read the history", self.config.get("name"), exc_info=True)
        self.twin = await self.hass.async_add_executor_job(twin.summary, rows, now)
        self.habits = await self.hass.async_add_executor_job(habits.detect, rows, dt_util.get_default_time_zone())

    def learning_progress(self, alone=False):
        """How much of the room is learned: only what it has (a window, a heating, CO₂ or VOC sensors) is asked.

        Rooms sharing one air are learned together: one percentage for all of them, complete once each one is."""
        # The airings are learned for the whole air (the volume reads the model learned from the most openings).
        airings = max([(self.drying_model or {}).get("openings", 0)]
                      + [(getattr(getattr(self.hass.config_entries.async_get_entry(p["entry_id"]), "runtime_data", None), "drying_model", None)
                          or {}).get("openings", 0) for p in self.partners])
        air = tuple(k for k in ("co2", "voc") if self.sources.get(k))
        own = twin.progress(self.twin, airings, windows=bool(self.windows), heating=bool(self.sources.get("heating")), air=air)
        # What the advice can already promise, measure by measure, before the whole room is learned.
        own["ready"] = twin.categories(self.twin, airings, air)
        if alone or not self.partners:
            return own
        others = []
        for partner in self.partners:
            entry = self.hass.config_entries.async_get_entry(partner["entry_id"])
            if (coordinator := getattr(entry, "runtime_data", None)) is not None and hasattr(coordinator, "learning_progress"):
                others.append(coordinator.learning_progress(alone=True))
        return twin.together([own, *others])

    def questions(self):
        return habits.questions(self.config.get("name") or self.config_entry.title, self.config.get("area_id"), self.habits, self._answers(),
                                self.season_name, self.config.get("equipment") or ())

    def _answers(self):
        """The person's answers to this room's questions (Oui / Non / Je ne sais pas), kept with the home settings."""
        home = getattr(self.home_configuration, "home", None) or {}
        return (home.get("answers") or {}).get(self.entry_id, {})

    async def _refresh_season(self, now):
        stamp = self.season[0]
        if stamp and (now - stamp).total_seconds() < SEASON_REFRESH_SECONDS:
            return
        self.season = (now, await self._outdoor_mean(now))
        self.day_range = await self._indoor_range(now)
        self.humidity_floor = await self._humidity_floor(now)

    async def _statistics(self, entity_id, start, end, types):
        """Hourly statistics rows of one entity; None when the recorder cannot answer."""
        try:
            from homeassistant.components.recorder import get_instance
            from homeassistant.components.recorder.statistics import statistics_during_period
            stats = await get_instance(self.hass).async_add_executor_job(
                statistics_during_period, self.hass, start, end, {entity_id}, "hour", None, types)
        except Exception:  # the card then simply shows less
            if not self._season_failed:
                self._season_failed = True
                self.logger.warning("Home Assistant statistics could not be read", exc_info=True)
            return None
        return stats.get(entity_id, [])

    async def _outdoor_mean(self, now):
        """Seven-day mean of the outdoor temperature from hourly statistics; None when not known."""
        entity_id = self._outdoor_entity()
        rows = await self._statistics(entity_id, now - timedelta(days=7), now, {"mean"}) if entity_id else None
        means = [row["mean"] for row in rows or [] if isinstance(row.get("mean"), (int, float))]
        # Three days of hourly means at least: a recent sensor must not set the season alone.
        if len(means) < 72:
            return None
        value = sum(means) / len(means)
        return value if -40 <= value <= 60 else None

    async def _indoor_range(self, now):
        """Lowest and highest hourly indoor temperature over the last 24 hours."""
        entity_id = self.config.get("sources", {}).get("indoor_temperature")
        rows = await self._statistics(entity_id, now - timedelta(hours=24), now, {"min", "max"}) if entity_id else None
        lows = [row["min"] for row in rows or [] if isinstance(row.get("min"), (int, float))]
        highs = [row["max"] for row in rows or [] if isinstance(row.get("max"), (int, float))]
        # Half a day of hours at least, so a fresh sensor does not draw a misleading range.
        if len(lows) < 12 or len(highs) < 12:
            return None
        return {"min": round(min(lows), 1), "max": round(max(highs), 1)}

    async def _humidity_floor(self, now):
        """Lowest indoor humidity of the last three full hours: above the threshold, the excess lasts."""
        entity_id = self.config.get("sources", {}).get("indoor_humidity")
        rows = await self._statistics(entity_id, now - timedelta(hours=4), now, {"min", "max"}) if entity_id else None
        lows = [row["min"] for row in rows or [] if isinstance(row.get("min"), (int, float))][-3:]
        highs = [row["max"] for row in rows or [] if isinstance(row.get("max"), (int, float))][-3:]
        self.humidity_ceiling = max(highs) if len(highs) == 3 else None
        return min(lows) if len(lows) == 3 else None
