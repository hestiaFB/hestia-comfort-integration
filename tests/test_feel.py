"""The room's ressenti (engine/feel.py): the air, half of what the surfaces add, a draught, damp warm air."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from engine.feel import feel

WINDOW = {"entity_id": "binary_sensor.baie", "open": False, "kind": "window", "sun_wm2": None}


class Feel(unittest.TestCase):
    def test_without_the_air_nothing(self):
        self.assertIsNone(feel(None, 10))

    def test_evening_in_november_the_walls_cool(self):
        # The Salon on 3 November: 21.3 °C inside, 10.1 °C outside, night, the stove off.
        f = feel(21.3, 10.1, 52, openings=[WINDOW], heating={"on": False, "kind": "stove"}, night=True)
        self.assertEqual(f["feels"], 20.9)
        self.assertEqual(f["factors"]["walls"]["delta"], -0.4)
        self.assertEqual(f["factors"]["sun"]["delta"], 0.0)
        self.assertEqual(f["factors"]["heating"], {"delta": 0.0, "kind": "stove", "on": False})

    def test_insulation_and_glazing_are_settings(self):
        poor = feel(20, 0, walls="peu", glazing="simple")["feels"]
        good = feel(20, 0, walls="bien", glazing="triple")["feels"]
        self.assertLess(poor, good)
        self.assertLess(good, 20)

    def test_a_closed_shutter_keeps_the_pane_warmer(self):
        open_ = feel(20, 0, openings=[WINDOW])["factors"]["walls"]["delta"]
        shut = feel(20, 0, openings=[WINDOW], covers={"binary_sensor.baie": 0})["factors"]["walls"]
        self.assertGreater(shut["delta"], open_)
        self.assertTrue(shut["shutters"])

    def test_the_sun_warms_unless_hidden_or_night(self):
        sunny = {**WINDOW, "sun_wm2": 420}
        self.assertEqual(feel(22.6, 14, openings=[sunny])["factors"]["sun"]["delta"], 0.8)
        # Strong sun on the facade: one and a half degrees at most.
        self.assertEqual(feel(22.6, 14, openings=[{**WINDOW, "sun_wm2": 900}])["factors"]["sun"]["delta"], 1.5)
        self.assertEqual(feel(22.6, 14, openings=[sunny], night=True)["factors"]["sun"]["delta"], 0.0)
        hidden = feel(22.6, 14, openings=[sunny], covers={"binary_sensor.baie": 5})["factors"]["sun"]
        self.assertEqual(hidden["delta"], 0.0)
        self.assertTrue(hidden["hidden"])

    def test_a_running_stove_radiates_more_than_a_radiator(self):
        stove = feel(19.4, 2, heating={"on": True, "kind": "stove"})["factors"]["heating"]["delta"]
        radiator = feel(19.4, 2, heating={"on": True, "kind": "radiator"})["factors"]["heating"]["delta"]
        half = feel(19.4, 2, heating={"on": True, "kind": "radiator", "power": 50})["factors"]["heating"]["delta"]
        self.assertEqual(stove, 1.2)
        self.assertEqual(radiator, 0.3)
        self.assertEqual(half, 0.1)
        # A stove's thermostat at 0 % while it heats only switches it: it runs fully. A kind not set counts as a radiator.
        self.assertEqual(feel(19.4, 2, heating={"on": True, "kind": "stove", "power": 0})["factors"]["heating"]["delta"], 1.2)
        unknown = feel(19.4, 2, heating={"on": True, "kind": None})["factors"]["heating"]
        self.assertEqual((unknown["delta"], unknown["kind"]), (0.3, None))

    def test_an_open_window_on_colder_air_is_a_draught(self):
        f = feel(20.4, 8, gust=25, openings=[{**WINDOW, "open": True}])
        self.assertEqual(f["factors"]["draught"]["delta"], -1.3)
        # Outside as warm as inside: no draught felt.
        self.assertEqual(feel(20, 20, gust=25, openings=[{**WINDOW, "open": True}])["factors"]["draught"]["delta"], 0.0)

    def test_damp_air_weighs_only_when_warm(self):
        self.assertEqual(feel(21, 15, 70)["factors"]["humidity"]["delta"], 0.0)
        summer = feel(27.2, 32, 68)["factors"]["humidity"]
        self.assertEqual(summer["delta"], 0.4)
        self.assertGreater(summer["dew"], 20)

    def test_summer_walls_warm(self):
        self.assertGreater(feel(27, 32)["factors"]["walls"]["delta"], 0)


if __name__ == "__main__":
    unittest.main()
