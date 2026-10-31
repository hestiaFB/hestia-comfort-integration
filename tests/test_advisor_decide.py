"""The 3.0 advisor's decision: the night of 30 October says « close », and a tenth of a degree never turns the advice."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.decide import GAIN, Gesture, Now, Thermostat, Twins, decide
from advisor.house import Opening, Room
from advisor.physics.air import AirParams, BREATH
from advisor.physics.thermal import Inputs, ordinary
from advisor.physics.water import WaterParams, absolute

FRENCH = Opening("binary_sensor.porte_fenetre_sg_contact", "french", area=1.18 * 2.10, height=2.10)
WEST = Opening("binary_sensor.fenetre_ouest_contact", "window", area=1.18 * 1.21, height=1.21)
SALON = Room("salon", "Salon", volume=44.03 * 2.5, openings=(FRENCH, WEST), heating_power=3000)
TWINS = Twins(heat=replace(ordinary(SALON), window=0.6), windows=(FRENCH.size, WEST.size),
              water=WaterParams(SALON.air, 0.5, 5.0, 30.0), water_flow=(0.9, 0.4),
              air=AirParams(SALON.air, 2 * BREATH), air_flow=(0.8, 0.1))


def night(outdoor=12.8, hours=6, start=1.0):
    """The coming steps of a night without sun, the outdoor air at 88 %."""
    return [(Inputs(outdoor, hour=(start + k / 12) % 24), absolute(outdoor, 88.0)) for k in range(int(hours * 12))]


def day(outdoor=15.0, hours=3, start=14.0):
    return [(Inputs(outdoor, hour=start + k / 12), absolute(outdoor, 70.0)) for k in range(int(hours * 12))]


class NightOf30October(unittest.TestCase):
    def test_open_at_one_in_the_morning_with_12_8_outside_says_close(self):
        now = Now(air=20.6, walls=20.6, opened=(FRENCH.size,), humidity=66.0, night=True)
        decision = decide(TWINS, now, night())
        self.assertEqual(decision.gesture, Gesture("close"))
        self.assertGreater(decision.gain, GAIN)

    def test_with_its_thermostat_shut_stays_warm_and_open_costs_heating(self):
        heated = replace(TWINS, thermostat=Thermostat(target=19.0))
        now = Now(air=20.6, walls=20.6, opened=(FRENCH.size,), humidity=66.0, night=True)
        decision = decide(heated, now, night())
        self.assertEqual(decision.gesture, Gesture("close"))
        shut, open_ = decision.paths[Gesture("close")], decision.paths[Gesture("nothing")]
        self.assertGreater(shut.air[-1], 18.8)
        self.assertLess(open_.air[-1], shut.air[-1])
        # The thermostat stops while the window is open: the cold room is the price, not the heating.
        self.assertEqual(open_.heating, 0.0)

    def test_a_tenth_of_a_degree_never_turns_the_advice(self):
        # The 2.1 engine said « Refermez » at 21.0 °C, « cela ne change rien » at 21.1 and « Laissez ouvert » at 21.5.
        for air in (20.9, 21.0, 21.1, 21.2, 21.5):
            now = Now(air=air, walls=air, opened=(FRENCH.size,), humidity=66.0, night=True)
            self.assertEqual(decide(TWINS, now, night()).gesture, Gesture("close"), air)


class Gestures(unittest.TestCase):
    def test_nothing_to_do_in_a_comfortable_shut_room(self):
        now = Now(air=21.5, walls=21.5, opened=(), humidity=50.0, co2=600.0)
        decision = decide(TWINS, now, day(outdoor=21.0))
        self.assertEqual(decision.gesture, Gesture("nothing"))

    def test_stale_air_on_a_mild_afternoon_asks_for_an_airing(self):
        now = Now(air=21.5, walls=21.5, opened=(), humidity=55.0, co2=1600.0)
        decision = decide(TWINS, now, day(outdoor=17.0))
        self.assertEqual(decision.gesture.kind, "open")

    def test_the_rain_shuts_what_is_open_and_never_opens(self):
        opened = Now(air=21.0, walls=21.0, opened=(FRENCH.size,), humidity=55.0)
        self.assertEqual(decide(TWINS, opened, day(), forbidden=frozenset({"open"})).rule, "safety")
        stale = Now(air=21.5, walls=21.5, opened=(), co2=1600.0)
        self.assertNotEqual(decide(TWINS, stale, day(outdoor=17.0), forbidden=frozenset({"open"})).gesture.kind, "open")

    def test_a_colder_outside_never_makes_opening_better_for_a_cool_room(self):
        now = Now(air=19.0, walls=19.0, opened=())
        gains = []
        for outdoor in (16.0, 12.0, 8.0, 4.0):
            costs = decide(TWINS, now, day(outdoor=outdoor)).scenarios
            gains.append(costs[Gesture("nothing")]["total"] - costs[Gesture("open")]["total"])
        self.assertEqual(gains, sorted(gains, reverse=True))

    def test_an_advice_shown_stays_unless_another_clearly_beats_it(self):
        now = Now(air=21.5, walls=21.5, opened=(), humidity=55.0, co2=1600.0)
        first = decide(TWINS, now, day(outdoor=17.0))
        again = decide(TWINS, replace(now, co2=1590.0), day(outdoor=17.0), previous=first.gesture)
        self.assertEqual(again.gesture, first.gesture)


if __name__ == "__main__":
    unittest.main()
