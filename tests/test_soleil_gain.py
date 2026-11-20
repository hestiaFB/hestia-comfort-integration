"""The sun counted as a gain (spec « Ce qui joue sur chaque pièce », 19 November; moteur 3.21.0).

The Chambre A, south, on 19 November: no word of the sun all day, its morning warming under 0,5 °C. In the heating season
« Bon à savoir » now judges the sun on what it spares until bedtime: the heating's kWh with a thermostat, the °C kept
without one. A line only: the banner's gestures do not change.
"""
from dataclasses import replace
from datetime import datetime
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.decide import Now, Thermostat, sun_saved  # noqa: E402
from advisor.knowing import RoomView, Window, sun_on_windows  # noqa: E402
from advisor.physics.thermal import Inputs  # noqa: E402
from advisor.physics.water import absolute  # noqa: E402
from advisor.words import tip_text  # noqa: E402
from test_advisor_decide import TWINS  # noqa: E402

PARIS = ZoneInfo("Europe/Paris")
HOME = (43.447, 5.470)
NOW = datetime(2026, 11, 19, 11, 0, tzinfo=PARIS)
SOUTH = [Window("binary_sensor.fenetre_a_contact", 180)]


def view(saved, manual=False, gain=0.2):
    return RoomView(NOW, *HOME, windows=SOUTH, sun_gain=gain, sun_saved=saved, shutters_manual=manual)


def said(saved, manual=False):
    tips = sun_on_windows(view(saved, manual))
    return tip_text(tips[0], now=NOW) if tips else None


class TheLine(unittest.TestCase):
    def test_heating_spared(self):
        line = said({"energy": 0.6, "heated": True, "kept": 0.0, "closed": False})
        self.assertEqual(line, "Soleil sur la fenêtre sud jusqu'à 16 h 35 : environ 0,6 kWh de chauffage en moins ce soir")

    def test_said_even_when_it_warms_less_than_half_a_degree(self):
        # 19 November: the old rule (SUN_COUNTS, 0,5 °C now) kept it silent.
        self.assertIsNotNone(said({"energy": 0.3, "heated": True, "kept": 0.0, "closed": False}))

    def test_not_said_when_it_spares_little(self):
        self.assertIsNone(said({"energy": 0.1, "heated": True, "kept": 0.0, "closed": False}))

    def test_a_room_warming_in_the_sun_still_says_so(self):
        # Labo, 20 November at 11 h 16: the Chambres A and M rising 1,5 °C an hour in the sun, the heating spared little
        # and nothing kept by bedtime (the thermostat holds it): the warming now is said, as before 3.21.
        tips = sun_on_windows(view({"energy": 0.1, "heated": True, "kept": 0.1, "closed": False}, gain=0.8))
        self.assertEqual(tip_text(tips[0], now=NOW), "Soleil sur la fenêtre sud jusqu'à 16 h 35 : +0,8 °C dans la pièce")

    def test_above_its_set_point_the_heat_kept_is_said(self):
        # Labo, 20 November at 9 h 43: the Chambre A at 18,6 °C for 18 °C asked spares no heating, yet the sun keeps it
        # warmer by bedtime; no sun line anywhere that morning.
        line = said({"energy": 0.0, "heated": True, "kept": 0.6, "closed": False})
        self.assertTrue(line.endswith(": environ +0,6 °C au coucher"))

    def test_shutters_without_a_sensor_say_if(self):
        line = said({"energy": 0.6, "heated": True, "kept": 0.0, "closed": False}, manual=True)
        self.assertTrue(line.endswith("en moins ce soir, si les volets sont ouverts"))

    def test_a_connected_shutter_shut_says_open_it(self):
        line = said({"energy": 0.6, "heated": True, "kept": 0.0, "closed": True})
        self.assertTrue(line.endswith(": ouvrez le volet pour en profiter (environ 0,6 kWh)"))

    def test_without_a_thermostat_the_heat_kept_at_bedtime(self):
        line = said({"energy": 0.0, "heated": False, "kept": 0.4, "closed": False})
        self.assertTrue(line.endswith(": environ +0,4 °C au coucher"))
        self.assertIsNone(said({"energy": 0.0, "heated": False, "kept": 0.2, "closed": False}))

    def test_out_of_the_heating_season_the_old_rule(self):
        # No `sun_saved` (summer, a room already too warm): the warming now, from 0,5 °C.
        self.assertEqual(sun_on_windows(view(None, gain=0.2)), [])
        self.assertEqual(len(sun_on_windows(view(None, gain=0.8))), 1)

    def test_in_english(self):
        tips = sun_on_windows(view({"energy": 0.6, "heated": True, "kept": 0.0, "closed": False}))
        self.assertTrue(tip_text(tips[0], "en", now=NOW).endswith("about 0.6 kWh less heating this evening"))


def sunny_day(hours=8, start=10.0, sun=450.0):
    return [(Inputs(8.0, hour=start + k / 12, sun=sun), absolute(8.0, 80.0)) for k in range(int(hours * 12))]


class TheFigures(unittest.TestCase):
    def test_with_a_thermostat_the_sun_spares_heating(self):
        heated = replace(TWINS, thermostat=Thermostat(target=20.0))
        now = Now(air=19.8, walls=19.5, opened=(), humidity=60.0)
        saved = sun_saved(heated, now, sunny_day())
        self.assertTrue(saved["heated"])
        self.assertGreater(saved["energy"], 0.0)
        self.assertFalse(saved["closed"])

    def test_without_one_the_room_keeps_some_heat(self):
        now = Now(air=19.0, walls=19.0, opened=(), humidity=60.0)
        saved = sun_saved(TWINS, now, sunny_day())
        self.assertFalse(saved["heated"])
        self.assertGreater(saved["kept"], 0.0)

    def test_no_sun_no_gain(self):
        now = Now(air=19.0, walls=19.0, opened=(), humidity=60.0)
        saved = sun_saved(TWINS, now, sunny_day(sun=0.0))
        self.assertAlmostEqual(saved["kept"], 0.0, places=6)

    def test_nothing_ahead(self):
        self.assertIsNone(sun_saved(TWINS, Now(air=19.0, walls=19.0, opened=()), []))


if __name__ == "__main__":
    unittest.main()
