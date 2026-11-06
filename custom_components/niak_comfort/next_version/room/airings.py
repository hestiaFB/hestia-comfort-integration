"""Airings followed and measured: the feedback loop and what the VOC index does when a window opens."""
from datetime import datetime

from homeassistant.util import dt as dt_util

from ..engine import feedback, habits, voc as vocs


class AiringsMixin:
    """Part of ComfortCoordinator: its methods use the coordinator's own state (self)."""

    def _intended_open(self, now):
        """At night, a window the person said is open on purpose is not an oversight."""
        local = dt_util.as_local(now)
        # The answer holds for the season it was given in (an older answer, without one, for the summer).
        answers = self._answers()
        given = answers.get(habits.night_key(self.season_name)) or (answers.get("night_open") if habits.season_group(self.season_name) == "summer" else None)
        # In winter a window open at night is always said: no answer covers it.
        return given == "yes" and habits.season_group(self.season_name) != "winter" and (local.hour >= 21 or local.hour < 8)

    def _track(self, assessment, current, now):
        """The feedback loop: close an airing followed, and note an advice left aside half an hour."""
        opened = current.get("opened", 0.0) > 0
        if self._experiment and opened:
            # Opened again before the result was read: the same airing goes on.
            self._experiment.pop("closed", None)
        elif self._experiment:
            # The result is read a few minutes after closing: a slow sensor has spoken again by then.
            closed = datetime.fromisoformat(self._experiment.setdefault("closed", now.isoformat()))
            if now - closed >= feedback.SETTLE:
                values = {"indoor_humidity": current.get("hi"), "indoor_temperature": current.get("ti"), "co2": current.get("co2"), "voc": current.get("voc")}
                record = feedback.finish(self._experiment, values, now)
                self._experiment = None
                if record:
                    self._remember(record, now)
        if assessment.get("action") == "ouvrir" and not opened:
            self._advice_since = self._advice_since or now
        else:
            since, followed = self._advice_since, self._advice_followed
            self._advice_since, self._advice_followed = None, False
            if since and not followed and not opened and now - since >= feedback.IGNORED_AFTER:
                self._remember(feedback.ignored(since, now), now)

    def _voc_threshold(self):
        threshold = (self.config.get("evolution") or {}).get("voc_threshold") or {}
        value = threshold.get("value") if isinstance(threshold, dict) else None
        return value if isinstance(value, (int, float)) and value > 0 else None

    def _voc_learned(self, now):
        """The VOC against waiting and against what opening brought (engine/voc.py), for the advice."""
        threshold, shut = self._voc_threshold(), not any(e in self.opened_since for e in self.windows)
        if threshold is None:
            return {}
        local = now.astimezone(dt_util.get_default_time_zone())
        air = (self.previous.features.get("air") or {}) if self.previous else {}
        # The climb with a window open is watched over the first minutes of the airing only (engine/voc.py WATCH).
        begun = min((self.opened_since[e] for e in self.windows if e in self.opened_since), default=None)
        watched = begun is not None and now - begun <= vocs.WATCH
        return {"voc_shut": shut,
                "voc_falling": shut and vocs.is_falling(list(self.voc_points), now, threshold, was=air.get("voc_falling") is True),
                "voc_going": self.voc_going,
                "voc_outdoor": vocs.slot(local.hour) in self.voc_slots,
                "voc_opened_level": self.voc_opened_level if watched else None}

    def _note_voc_airing(self, began, now):
        """A window of the room shut after an airing while the VOC called for air: the pause after it starts now."""
        air = (self.previous.features.get("air") or {}) if self.previous else {}
        about_voc = air.get("voc_status") == "high" or (self._experiment or {}).get("measure") == "voc"
        if began is None or now - began < vocs.AIRING or not about_voc:
            return
        if any(e in self.opened_since for e in self.windows):
            return
        level = vocs.mean(list(self.voc_points), now)
        if isinstance(level, (int, float)):
            self.voc_aired = {"end": now.isoformat(), "after": round(level, 1)}

    def _remember(self, record, now):
        self.feedback = feedback.keep([*self.feedback, record], now)
        self._feedback_unsaved = True
        self._feedback_store.async_delay_save(self._feedback_data, 5)

    def _feedback_data(self):
        self._feedback_unsaved = False
        return {"records": self.feedback}

    async def _save_feedback(self):
        """At unload, what is still waiting is written now: the room reloaded reads it back at once."""
        if self._feedback_unsaved:
            await self._feedback_store.async_save(self._feedback_data())
