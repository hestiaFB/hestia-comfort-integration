"""Forum, 19 November (Confort 3.1.0b16, coming from 2.1.0b8): five rooms on « Conseil en attente — Le moteur redémarre »
for a day, no error in the log, the panel saying « rien à régler ». His Hestia Weather place has no station: no outdoor
sensor at all, and the 3.0 advisor stopped without a word at each step. The forecast now stands for the outside; and a
room still not advised says why."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.hestia_comfort import advisor_home  # noqa: E402

NOW = datetime(2026, 11, 19, 8, 30, tzinfo=timezone.utc)


def home(sources, states=None, forecast=None, boot=NOW - timedelta(hours=1)):
    h = SimpleNamespace(data={}, states=SimpleNamespace(get=(states or {}).get),
                        config=SimpleNamespace(latitude=43.6, longitude=4.8))
    advisor = advisor_home.AdvisorHome.__new__(advisor_home.AdvisorHome)
    advisor.hass = h
    advisor.outdoor, advisor.outdoor_measured, advisor.trust, advisor.retained = (None, None), (None, None), None, None
    advisor.forecast, advisor.boot = forecast or {}, boot
    advisor._sources = lambda: sources
    advisor._place = lambda: None
    return advisor


HOUR = NOW.replace(minute=0)
FORECAST = {HOUR: (9.0, 80.0, 0.0), HOUR + timedelta(hours=1): (11.0, 70.0, 50.0)}


class NoOutdoorSensor(unittest.TestCase):
    def read(self, advisor):
        with mock.patch.object(advisor_home.dt_util, "utcnow", return_value=NOW):
            return advisor._read_outdoor()

    def test_the_forecast_stands_for_the_outside(self):
        advisor = home({}, forecast=FORECAST)
        temperature, humidity = self.read(advisor)
        # Half way between 8 h (9 °C, 80 %) and 9 h (11 °C, 70 %).
        self.assertAlmostEqual(temperature, 10.0)
        self.assertAlmostEqual(humidity, 75.0)
        self.assertEqual(advisor.retained["now"], "forecast")
        self.assertEqual(advisor.outdoor_measured, (None, None))

    def test_a_sensor_chosen_but_silent_is_not_replaced(self):
        # A chosen sensor that does not answer is the checks' business: never hidden behind the forecast.
        advisor = home({"outdoor_temperature": {"entity_id": "sensor.jardin_t"}}, forecast=FORECAST)
        self.assertEqual(self.read(advisor), (None, None))

    def test_a_sensor_answering_is_kept(self):
        advisor = home({"outdoor_temperature": {"entity_id": "sensor.jardin_t"}},
                       {"sensor.jardin_t": SimpleNamespace(state="7.5", attributes={})}, FORECAST)
        self.assertEqual(self.read(advisor)[0], 7.5)
        self.assertIsNone(advisor.retained)

    def test_no_forecast_either(self):
        self.assertEqual(self.read(home({})), (None, None))


class WaitingSaysWhy(unittest.TestCase):
    def waiting(self, advisor, room_states=None, now=NOW):
        advisor.hass.states = SimpleNamespace(get=(room_states or {}).get)
        room = SimpleNamespace(room={"temperature": "sensor.salon_t"})
        with mock.patch.object(advisor_home.dt_util, "utcnow", return_value=now):
            return advisor.waiting(room)

    def test_starting(self):
        advisor = home({}, boot=NOW - timedelta(minutes=2))
        self.assertEqual(self.waiting(advisor), advisor_home.WAITING)

    def test_no_outside_once_started(self):
        found = self.waiting(home({}))
        self.assertEqual(found["manque"], "dehors")
        self.assertEqual(found["regle"], "waiting")
        self.assertIn("Réglages généraux", found["phrase"])

    def test_no_room_temperature(self):
        advisor = home({})
        advisor.outdoor = (10.0, 70.0)
        found = self.waiting(advisor, {"sensor.salon_t": SimpleNamespace(state="unavailable", attributes={})})
        self.assertEqual(found["manque"], "temperature")

    def test_everything_there_still_waiting(self):
        advisor = home({})
        advisor.outdoor = (10.0, 70.0)
        found = self.waiting(advisor, {"sensor.salon_t": SimpleNamespace(state="20.5", attributes={})})
        self.assertEqual(found, advisor_home.WAITING)


if __name__ == "__main__":
    unittest.main()
