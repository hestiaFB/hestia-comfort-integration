"""The house's days of 14 and 15 November (moteur 3.17.0), read with Frank.

- « Refermez : il pleut » at 16 h 21 in three rooms whose windows were opened after the rain had stopped (16 h 03).
- « Coupez le poêle : 19,5 °C pour 14 °C visés » at 19 h 55, the Salon under its range, the stove lit for a boost.
- « Gardez fermé : le gel est annoncé » every half hour all night; airings asked in the evening for 4 points.
"""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.decide import Comfort, Gesture, Now, Thermostat, Twins, decide  # noqa: E402
from advisor.house import Opening, Room  # noqa: E402
from advisor.physics.thermal import Inputs, ordinary  # noqa: E402
from advisor.safety import rain_for  # noqa: E402

WEST = Opening("binary_sensor.fenetre_ouest_contact", "window", area=1.2, height=1.2)
SALON = Room("salon", "Salon", volume=90.0, openings=(WEST,), heating_power=0)
T = 1_763_130_000.0


class RainForTests(unittest.TestCase):
    def test_a_window_opened_after_the_rain_is_not_told_it_rains(self):
        last = (T, 1.8)
        self.assertEqual(rain_for(1.8, 0.0, last, T + 18 * 60), 0.0)

    def test_a_room_shut_or_open_under_the_rain_keeps_it(self):
        last = (T, 1.8)
        self.assertEqual(rain_for(1.8, 0.0, last, None), 1.8)
        self.assertEqual(rain_for(1.8, 0.0, last, T - 10 * 60), 1.8)
        self.assertEqual(rain_for(2.4, 2.4, (T, 2.4), T + 60), 2.4)


class StoveStopTests(unittest.TestCase):
    def setUp(self):
        self.twins = Twins(heat=replace(ordinary(SALON), share=0.4), windows=(WEST.size,),
                           house_thermostat=Thermostat(target=14.0, inside=0.7, kind="pellet"), house_power=8500.0,
                           house_now=0.0, house_idle=0.3, house_idle_for=10.0)
        self.coming = [(Inputs(13.0, hour=19.9 + k / 12, house_heat=0.3 * 8500.0), None) for k in range(36)]

    def test_never_to_a_room_under_its_range(self):
        now = Now(air=19.5, walls=19.0, opened=(), house_running=True, overheated=31.0)
        self.assertNotEqual(decide(self.twins, now, self.coming, Comfort(minimum=20.0, maximum=25.0)).rule, "overheat")

    def test_still_to_a_room_too_warm(self):
        twins = replace(self.twins, house_thermostat=replace(self.twins.house_thermostat, target=21.5))
        now = Now(air=24.1, walls=23.0, opened=(), house_running=True, overheated=30.0)
        found = decide(twins, now, self.coming, Comfort(minimum=20.0, maximum=25.0))
        self.assertEqual((found.rule, found.gesture), ("overheat", Gesture("heat_stop")))


if __name__ == "__main__":
    unittest.main()
