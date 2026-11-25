"""Forum, 25 November: a home without an outdoor sensor (a Hestia Weather place without a station) learned nothing.
Open-Meteo's past hours now stand in for the outdoor measures (forecast_past.py, engine 3.23.0): the twins learn,
less finely than with a sensor at the house, and the room says so."""
import asyncio
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from custom_components.hestia_comfort import forecast_past, learning_check  # noqa: E402
from custom_components.hestia_comfort.room.learning import LearningMixin  # noqa: E402
from advisor.nightly import MIN_DAYS, learn_room  # noqa: E402
from advisor.observe import Series  # noqa: E402
from test_advisor_nightly import PARIS, SPEC, TRUTH, recorded  # noqa: E402

UTC = timezone.utc


def hourly(start, hours, temperature=lambda t: 10.0, humidity=lambda t: 80.0):
    return [(start + timedelta(hours=h), (temperature(start + timedelta(hours=h)), humidity(start + timedelta(hours=h))))
            for h in range(hours)]


class Points(unittest.TestCase):
    def test_every_quarter_of_an_hour_between_the_hours(self):
        start = datetime(2026, 11, 20, tzinfo=UTC)
        hours = hourly(start, 3, temperature=lambda t: 10.0 + (t - start).total_seconds() / 3600)
        found = forecast_past.points(hours, 0, start, start + timedelta(hours=2))
        self.assertEqual(len(found), 9)
        self.assertEqual(found[1], (start + timedelta(minutes=15), 10.25))
        self.assertEqual(found[-1], (start + timedelta(hours=2), 12.0))

    def test_a_missing_hour_cuts_the_series(self):
        start = datetime(2026, 11, 20, tzinfo=UTC)
        hours = hourly(start, 4)
        hours[2] = (hours[2][0], (None, 80.0))
        times = [t for t, _ in forecast_past.points(hours, 0, start, start + timedelta(hours=4))]
        self.assertNotIn(start + timedelta(hours=1, minutes=30), times)
        self.assertIn(start + timedelta(minutes=30), times)

    def test_the_two_histories_read_them_alike(self):
        start = datetime(2026, 11, 20, tzinfo=UTC)
        hours = hourly(start, 2, humidity=lambda t: 70.0)
        row = forecast_past.recorder_rows(hours, "outdoor_humidity", start, start + timedelta(hours=1))[0]
        self.assertEqual((row.state, row.last_changed, row.last_updated), ("70.00", start, start))
        night = forecast_past.night_rows(hours, "outdoor_temperature", start, start + timedelta(hours=1))[0]
        self.assertEqual((night["entity_id"], night["state"], night["last_changed"]),
                         (forecast_past.TEMPERATURE, "10.00", start.isoformat()))


class Download(unittest.TestCase):
    def hass(self):
        return SimpleNamespace(config=SimpleNamespace(latitude=43.456, longitude=5.512), data={})

    def run_with(self, hass, answer, now):
        calls = []

        class Response:
            async def __aenter__(self):
                if isinstance(answer, Exception):
                    raise answer
                return self

            async def __aexit__(self, *_):
                return False

            async def json(self):
                return answer

        session = SimpleNamespace(get=lambda url, timeout: calls.append(url) or Response())
        with patch.object(forecast_past, "async_get_clientsession", lambda _h: session):
            return asyncio.run(forecast_past.async_hours(hass, now)), calls

    def test_one_download_an_hour_with_the_location_rounded(self):
        hass, now = self.hass(), datetime(2026, 11, 25, 12, tzinfo=UTC)
        answer = {"hourly": {"time": ["2026-11-25T10:00", "2026-11-25T11:00", "2026-11-25T13:00"],
                             "temperature_2m": [9.0, 10.0, 12.0], "relative_humidity_2m": [80, 78, 70]}}
        hours, calls = self.run_with(hass, answer, now)
        self.assertEqual([h for h, _ in hours], [datetime(2026, 11, 25, 10, tzinfo=UTC), datetime(2026, 11, 25, 11, tzinfo=UTC)])
        self.assertIn("latitude=43.5&longitude=5.5", calls[0])
        self.assertIn("past_days=61", calls[0])
        again, calls = self.run_with(hass, answer, now + timedelta(minutes=30))
        self.assertEqual((again, calls), (hours, []))
        self.assertFalse(forecast_past.unavailable(hass))

    def test_without_an_answer_the_learning_says_it_waits(self):
        hass = self.hass()
        hours, _ = self.run_with(hass, OSError("down"), datetime(2026, 11, 25, 12, tzinfo=UTC))
        self.assertIsNone(hours)
        self.assertTrue(forecast_past.unavailable(hass))


class Room(LearningMixin):
    """Only what `_learning_sources` reads of a coordinator."""
    def __init__(self, chosen):
        self.hass = SimpleNamespace(config=SimpleNamespace(components={"recorder"}))
        self.chosen, self._history_pass = chosen, {}

    def _source_entity(self, key):
        return self.chosen.get(key)


class Sources(unittest.TestCase):
    def sources(self, chosen, hours):
        room, now = Room(chosen), datetime(2026, 11, 25, 12, tzinfo=UTC)

        async def download(_hass, _now):
            return hours
        with patch.object(forecast_past, "async_hours", download):
            found = asyncio.run(room._learning_sources(now, timedelta(days=10)))
        return room, found

    def test_a_missing_outdoor_sensor_is_read_from_the_forecast(self):
        hours = hourly(datetime(2026, 11, 14, tzinfo=UTC), 24 * 12)
        room, found = self.sources({"indoor_temperature": "sensor.t", "indoor_humidity": "sensor.h"}, hours)
        self.assertEqual((found["outdoor_temperature"], found["outdoor_humidity"]), (forecast_past.TEMPERATURE, forecast_past.HUMIDITY))
        rows = room._history_pass[(forecast_past.TEMPERATURE, None)]
        self.assertEqual(rows[0].last_changed, datetime(2026, 11, 15, 12, tzinfo=UTC))
        self.assertEqual(room._from_forecast, ("outdoor_temperature", "outdoor_humidity"))

    def test_a_sensor_chosen_is_always_read_first(self):
        chosen = {"indoor_temperature": "sensor.t", "indoor_humidity": "sensor.h", "outdoor_temperature": "sensor.dehors"}
        room, found = self.sources(chosen, hourly(datetime(2026, 11, 14, tzinfo=UTC), 24))
        self.assertEqual((found["outdoor_temperature"], found["outdoor_humidity"]), ("sensor.dehors", forecast_past.HUMIDITY))
        self.assertNotIn((forecast_past.TEMPERATURE, None), room._history_pass)

    def test_without_the_forecast_nothing_stands_in(self):
        room, found = self.sources({"indoor_temperature": "sensor.t"}, None)
        self.assertIsNone(found["outdoor_temperature"])
        self.assertEqual(room._history_pass, {})


class Said(unittest.TestCase):
    def blocks(self, sources, forecast):
        h = SimpleNamespace(config=SimpleNamespace(components={"recorder"}), states=SimpleNamespace(get=lambda e: None))
        with patch("homeassistant.components.recorder.is_entity_recorded", lambda _h, e: True), \
                patch("homeassistant.components.recorder.get_instance", lambda _h: SimpleNamespace(keep_days=10)):
            return learning_check.blocks(h, sources, weather_linked=True, forecast=forecast)

    def test_learning_with_the_forecast_is_a_tip_not_a_stop(self):
        found = self.blocks({"indoor_temperature": "sensor.t", "indoor_humidity": "sensor.h"}, forecast=True)
        self.assertEqual(found, [{"cause": "forecast", "scope": "part", "key": "outdoor_temperature"}])
        self.assertIn("pris des prévisions", learning_check.text(found[0]))

    def test_without_the_forecast_the_place_without_station_stops_it(self):
        found = self.blocks({"indoor_temperature": "sensor.t", "indoor_humidity": "sensor.h"}, forecast=False)
        self.assertEqual([(b["cause"], b["scope"]) for b in found], [("no_station", "all")])

    def test_only_the_outdoor_humidity_from_the_forecast(self):
        found = self.blocks({"indoor_temperature": "sensor.t", "indoor_humidity": "sensor.h", "outdoor_temperature": "sensor.d"}, True)
        self.assertEqual([(b["cause"], b["key"]) for b in found], [("forecast", "outdoor_humidity")])


class Nightly(unittest.TestCase):
    """The same room as test_advisor_nightly, learned from Open-Meteo's hours instead of the house's own sensor: the hours
    only, half a degree too warm (the model's point)."""

    def learn(self, history, now, outdoor):
        wrong = replace(TRUTH, h_env=60.0, window=2.0)
        return learn_room(SPEC, {"heat": asdict(wrong)}, history, Series([]), now, outdoor, None, (43.4, 5.5), PARIS)

    def test_the_forecast_teaches_the_twin_as_the_sensor_does(self):
        history, now = recorded(MIN_DAYS + 1)
        measured = {datetime.fromisoformat(r["last_changed"]): float(r["state"]) for r in history["sensor.dehors"]}
        hours = [(t, (v + 0.5, 80.0)) for t, v in sorted(measured.items()) if t.minute == 0]
        start = min(measured)
        forecasted = {k: v for k, v in history.items() if k != "sensor.dehors"}
        forecasted[forecast_past.TEMPERATURE] = forecast_past.night_rows(hours, "outdoor_temperature", start, now)
        by_sensor, _ = self.learn(history, now, "sensor.dehors")
        by_forecast, report = self.learn(forecasted, now, forecast_past.TEMPERATURE)
        # One night nudges the twin it starts from (advisor/nightly.py WARM): with the sensor, 60 → 55.9 W/K; with the
        # forecast, as far or further, and the new twin kept because it replays the last day better.
        self.assertTrue(report["appris"])
        self.assertTrue(report["chaleur"]["garde"])
        error = lambda entry: abs(entry["heat"]["h_env"] - TRUTH.h_env)
        self.assertLess(error(by_forecast), abs(60.0 - TRUTH.h_env))
        self.assertLessEqual(error(by_forecast), error(by_sensor) + 1.0)
        self.assertLess(max(report["chaleur"]["apres"]), 0.05)


if __name__ == "__main__":
    unittest.main()
