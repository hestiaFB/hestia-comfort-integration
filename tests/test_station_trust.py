"""Hestia Weather's trust in its station (its docs/STATION-EMPLACEMENT.md § 4, § 5), read by the 3.0 advisor: the
temperature it retains when a wall or a roof in the sun warms the station, the stronger gust from a sheltered side, the
announced rain still believed under a sheltered gauge — and nothing changed by a Hestia Weather that does not share it."""
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.hestia_comfort import advisor_home, weather_link  # noqa: E402
from custom_components.hestia_comfort.advisor.physics.water import absolute  # noqa: E402
from custom_components.hestia_comfort.advisor.safety import rain_believed  # noqa: E402

STATION = {"temperature": "sensor.station_t", "humidity": "sensor.station_h", "wind_gust": "sensor.station_rafale",
           "rain_rate": "sensor.station_pluie"}
WALL = {"temperature": {"level": "handled", "now": "forecast", "value": 12.4, "why": "la station est au soleil contre le mur"},
        "wind": {"level": "ok", "now": "station"},
        "rain": {"level": "ok", "now": "station"}}


def state(value, **attributes):
    return SimpleNamespace(state=value, attributes=attributes)


def weather(trust=WALL, broken=False):
    """Hestia Weather's interface, version 1; `trust` None: a Hestia Weather older than api.station_trust()."""
    api = SimpleNamespace(version=1, station=lambda entry_id: {"entry_id": entry_id, "title": "Maison", "sensors": dict(STATION)})
    if broken:
        api.station_trust = mock.Mock(side_effect=RuntimeError("not yet computed"))
    elif trust is not None:
        api.station_trust = lambda entry_id: trust
    return api


def home(api, states, sources=None):
    """The house's advisor with only what reading the outside needs."""
    h = SimpleNamespace(data={weather_link.API_KEY: api} if api else {}, states=SimpleNamespace(get=states.get),
                        config=SimpleNamespace(latitude=46.0, longitude=4.0))
    advisor = advisor_home.AdvisorHome.__new__(advisor_home.AdvisorHome)
    advisor.hass = h
    advisor.outdoor, advisor.outdoor_measured, advisor.trust, advisor.retained = (None, None), (None, None), None, None
    advisor.rain_soon_since, advisor.forecast, advisor.sun_missed = None, {}, None
    found = sources or {"outdoor_temperature": {"entity_id": "sensor.station_t"}, "outdoor_humidity": {"entity_id": "sensor.station_h"},
                        "wind_gust": {"entity_id": "sensor.station_rafale"},
                        "rain": {"entity_id": "sensor.station_pluie", "adapter": "rain_rate"}}
    advisor._sources = lambda: found
    advisor._place = lambda: "lieu"
    return advisor


SUNNY_WALL = {"sensor.station_t": state("19.0"), "sensor.station_h": state("48"),
              "sensor.station_rafale": state("8", unit_of_measurement="km/h"), "sensor.station_pluie": state("0.0")}


class WhatWeatherRetains(unittest.TestCase):
    def test_a_value_only_when_it_is_not_the_stations(self):
        self.assertEqual(weather_link.retained(WALL, "temperature"), (12.4, "forecast", "la station est au soleil contre le mur"))
        self.assertIsNone(weather_link.retained(WALL, "wind"))
        self.assertEqual(weather_link.retained({"temperature": {"now": "corrected", "value": 16}}, "temperature")[:2], (16.0, "corrected"))
        # No value, or not a number: the station's reading is kept.
        self.assertIsNone(weather_link.retained({"temperature": {"now": "forecast"}}, "temperature"))
        self.assertIsNone(weather_link.retained({"temperature": {"now": "forecast", "value": "12"}}, "temperature"))
        self.assertIsNone(weather_link.retained({"temperature": {"now": "forecast", "value": float("nan")}}, "temperature"))
        self.assertIsNone(weather_link.retained(None, "temperature"))

    def test_the_gauge_sheltered_only_when_weather_handles_it(self):
        self.assertTrue(weather_link.gauge_sheltered({"rain": {"level": "handled", "now": "station"}}))
        self.assertFalse(weather_link.gauge_sheltered({"rain": {"level": "watch"}}))
        self.assertFalse(weather_link.gauge_sheltered(WALL))
        self.assertFalse(weather_link.gauge_sheltered(None))

    def test_an_older_or_failing_weather_shares_nothing(self):
        self.assertIsNone(weather_link.station_trust(SimpleNamespace(data={}), "lieu"))
        self.assertIsNone(weather_link.station_trust(SimpleNamespace(data={weather_link.API_KEY: weather(trust=None)}), "lieu"))
        with self.assertLogs(weather_link.__name__, "WARNING"):
            self.assertIsNone(weather_link.station_trust(SimpleNamespace(data={weather_link.API_KEY: weather(broken=True)}), "lieu"))
        self.assertEqual(weather_link.station_trust(SimpleNamespace(data={weather_link.API_KEY: weather()}), "lieu"), WALL)


class TheOutsideTemperature(unittest.TestCase):
    def test_the_wall_in_the_sun_gives_way_to_the_retained_temperature(self):
        advisor = home(weather(), SUNNY_WALL)
        temperature, humidity = advisor._read_outdoor()
        self.assertEqual(temperature, 12.4)
        self.assertEqual(advisor.outdoor_measured, (19.0, 48.0))
        self.assertEqual(advisor.retained["now"], "forecast")
        # The same water in the air: cooler, the humidity rises.
        self.assertAlmostEqual(absolute(12.4, humidity), absolute(19.0, 48.0), places=1)
        self.assertGreater(humidity, 48.0)

    def test_the_station_kept_when_weather_trusts_it_or_does_not_say(self):
        for api in (weather(trust={"temperature": {"level": "ok", "now": "station"}}), weather(trust=None), None):
            with self.subTest(api=api):
                advisor = home(api, SUNNY_WALL)
                self.assertEqual(advisor._read_outdoor(), (19.0, 48.0))
                self.assertIsNone(advisor.retained)
        advisor = home(weather(broken=True), SUNNY_WALL)
        with self.assertLogs(weather_link.__name__, "WARNING"):
            self.assertEqual(advisor._read_outdoor(), (19.0, 48.0))

    def test_a_sensor_chosen_in_confort_keeps_its_own_reading(self):
        sources = {"outdoor_temperature": {"entity_id": "sensor.jardin_t"}, "outdoor_humidity": {"entity_id": "sensor.jardin_h"}}
        advisor = home(weather(), {"sensor.jardin_t": state("17.0"), "sensor.jardin_h": state("55")}, sources)
        with mock.patch.object(weather_link, "entity", return_value=None):
            self.assertEqual(advisor._read_outdoor(), (17.0, 55.0))

    def test_the_coming_hours_carry_no_wall_gap(self):
        now = datetime(2026, 11, 5, 14, 0, tzinfo=timezone.utc)
        advisor = home(weather(), SUNNY_WALL)
        advisor.forecast = {now: (12.0, 70.0, 300.0)}
        outdoor, rh = advisor._read_outdoor()
        first = advisor.coming(now, 1, outdoor, rh, 0.0, 0.0)[0][0]
        # Only the forecast's own small gap (0.4 °C), never the wall's seven degrees.
        self.assertAlmostEqual(first.outdoor, 12.4, places=1)
        raw = advisor.coming(now, 1, 19.0, 48.0, 0.0, 0.0)[0][0]
        self.assertAlmostEqual(raw.outdoor, 19.0, places=1)


class TheSafetySignals(unittest.TestCase):
    def safety(self, trust, states=SUNNY_WALL, rain_in=10.0):
        advisor = home(weather(trust=trust), states)
        advisor._read_outdoor()
        with mock.patch.object(weather_link, "outlook", return_value={"rain": {"minutes": rain_in}}), \
                mock.patch.object(weather_link, "entity", return_value=None), \
                mock.patch.object(advisor_home.dt_util, "utcnow", return_value=datetime(2026, 11, 5, 14, tzinfo=timezone.utc)):
            return advisor, advisor.safety()

    def test_the_stronger_gust_from_a_sheltered_side(self):
        sheltered = {**WALL, "wind": {"level": "handled", "now": "forecast", "value": 52.0, "why": "station abritée à l’ouest"}}
        _, (_, gust, _, _, _) = self.safety(sheltered)
        self.assertEqual(gust, 52.0)
        # The station's own gust when it is the stronger.
        _, (_, gust, _, _, _) = self.safety(sheltered, {**SUNNY_WALL, "sensor.station_rafale": state("70", unit_of_measurement="km/h")})
        self.assertEqual(gust, 70.0)
        _, (_, gust, _, _, _) = self.safety(WALL)
        self.assertEqual(gust, 8.0)

    def test_a_sheltered_gauge_does_not_unbelieve_the_rain(self):
        under_tree = {**WALL, "rain": {"level": "handled", "now": "station"}}
        advisor, (_, _, rain_in, _, _) = self.safety(under_tree)
        self.assertEqual(rain_in, 10.0)
        self.assertIsNone(advisor.rain_soon_since)
        # An open gauge starts the wait: 45 minutes without a drop and the rain is no longer believed.
        advisor, _ = self.safety(WALL)
        self.assertIsNotNone(advisor.rain_soon_since)

    def test_rain_believed_under_a_sheltered_gauge(self):
        self.assertEqual(rain_believed(6, 0.0, 0, 3 * 3600), (None, 0))
        self.assertEqual(rain_believed(6, 0.0, 0, 3 * 3600, sheltered=True), (6, None))


if __name__ == "__main__":
    unittest.main()
