"""A Hestia Weather update recomputes a room only when what the room reads there changed (PLAN-OPTIMISATION.md, point 3):
Weather updates every minute, mostly for its wind and pressure."""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.hestia_comfort import weather_link
from custom_components.hestia_comfort.coordinator import ComfortCoordinator


class WeatherListen(unittest.TestCase):
    def room(self):
        return SimpleNamespace(hass=Mock(), _weather_seen=("hours", "autumn", None, None), _measure_refresh=Mock())

    def test_an_update_that_changes_nothing_read_does_not_recompute(self):
        room = self.room()
        with patch.object(weather_link, "fingerprint", return_value=("hours", "autumn", None, None)):
            ComfortCoordinator._weather_updated(room, "place")
        room.hass.async_create_task.assert_not_called()

    def test_a_new_forecast_recomputes_once_with_the_measures(self):
        room = self.room()
        with patch.object(weather_link, "fingerprint", return_value=("other hours", "autumn", None, None)):
            ComfortCoordinator._weather_updated(room, "place")
            ComfortCoordinator._weather_updated(room, "place")
        self.assertEqual(room.hass.async_create_task.call_count, 1)
        room._measure_refresh.async_call.assert_called_once()

    def test_the_air_s_time_of_calculation_is_not_read(self):
        hass = Mock()
        link = SimpleNamespace(air=lambda e: {"index": 2, "at": "12:01"}, pollen=lambda e: None, season=lambda e: {"season": "autumn"},
                               station=lambda e: None, rain=lambda e: None, hourly=lambda e: [])
        with patch.object(weather_link, "api", return_value=link), patch.object(weather_link, "entity", return_value=None):
            hass.states.get.return_value = None
            first = weather_link.fingerprint(hass, "place")
            link.air = lambda e: {"index": 2, "at": "12:02"}
            self.assertEqual(weather_link.fingerprint(hass, "place"), first)

    def test_the_time_of_calculation_of_rain_and_pollens_is_not_read(self):
        """Hestia Weather's rain, air and pollens all carry `at`, which changes at every update: with real values (not
        None), an update that changes nothing else must leave the room's fingerprint the same."""
        hass = Mock()
        hass.states.get.return_value = None

        def link_at(at, minutes=None, level=2):
            return SimpleNamespace(
                air=lambda e: {"entry_id": e, "source": "atmo", "index": 2, "at": at},
                pollen=lambda e: {"entry_id": e, "source": "atmo", "level": level, "high": False, "main": "graminées", "at": at},
                rain=lambda e: {"entry_id": e, "minutes": minutes, "precision": "minute" if minutes is not None else None,
                                "dry_until": None, "at": at},
                season=lambda e: {"season": "autumn"}, station=lambda e: None, hourly=lambda e: [])

        def seen(link):
            with patch.object(weather_link, "api", return_value=link), patch.object(weather_link, "entity", return_value=None):
                return weather_link.fingerprint(hass, "place")

        first = seen(link_at("2026-11-17T12:01:00+00:00"))
        self.assertEqual(seen(link_at("2026-11-17T12:02:00+00:00")), first)
        # What the room does read still counts.
        self.assertNotEqual(seen(link_at("2026-11-17T12:02:00+00:00", minutes=20)), first)
        self.assertNotEqual(seen(link_at("2026-11-17T12:02:00+00:00", level=3)), first)

    def test_the_same_readings_at_a_new_time_do_not_recompute_the_room(self):
        hass = Mock()
        hass.states.get.return_value = None
        at = {"value": "12:01"}
        link = SimpleNamespace(air=lambda e: {"index": 2, "at": at["value"]}, pollen=lambda e: {"level": 1, "at": at["value"]},
                               rain=lambda e: {"minutes": None, "at": at["value"]}, season=lambda e: {"season": "autumn"},
                               station=lambda e: None, hourly=lambda e: [])
        with patch.object(weather_link, "api", return_value=link), patch.object(weather_link, "entity", return_value=None):
            room = SimpleNamespace(hass=hass, _weather_seen=weather_link.fingerprint(hass, "place"), _measure_refresh=Mock())
            at["value"] = "12:02"
            ComfortCoordinator._weather_updated(room, "place")
        hass.async_create_task.assert_not_called()


if __name__ == "__main__":
    unittest.main()
