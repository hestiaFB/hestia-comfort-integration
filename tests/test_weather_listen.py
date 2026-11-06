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


if __name__ == "__main__":
    unittest.main()
