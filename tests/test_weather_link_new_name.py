"""Hestia Weather 3 (new name) updated before this version: its sensors are still found, under their new platform, and its
interface is still read where this version looks for it (Hestia Weather 3 keeps answering there)."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.niak_comfort import discovery, weather_link  # noqa: E402


class Registry:
    def __init__(self, platform):
        self.platform = platform

    def async_get_entity_id(self, domain, platform, unique_id):
        if platform == self.platform and unique_id == "new-id_pluie_en_cours" and domain == "binary_sensor":
            return "binary_sensor.niak_weather_pluie_en_cours"  # the entity id is kept by the carrying over
        return None


class NewNameTests(unittest.TestCase):
    def test_sensors_found_under_either_platform(self):
        for platform in ("niak_weather", "hestia_weather"):
            with patch.object(weather_link.er, "async_get", return_value=Registry(platform)):
                self.assertEqual(weather_link.entity(object(), "new-id", "pluie_en_cours"), "binary_sensor.niak_weather_pluie_en_cours")
        with patch.object(weather_link.er, "async_get", return_value=Registry("other")):
            self.assertIsNone(weather_link.entity(object(), "new-id", "pluie_en_cours"))

    def test_discovery_recognises_both_platforms(self):
        for platform in ("niak_weather", "hestia_weather"):
            self.assertTrue(discovery.niak_weather(SimpleNamespace(platform=platform, unique_id="x_qualite_air"), "qualite_air"))
        self.assertFalse(discovery.niak_weather(SimpleNamespace(platform="met", unique_id="x_qualite_air"), "qualite_air"))

    def test_interface_read_with_version_1(self):
        link = SimpleNamespace(version=1)
        hass = SimpleNamespace(data={weather_link.API_KEY: link})
        self.assertIs(weather_link.api(hass), link)


if __name__ == "__main__":
    unittest.main()
