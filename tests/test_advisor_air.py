"""The 3.0 advisor's twins of the water, the CO₂ and the fine particles: they go where physics says, and settle."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.physics.air import OUTDOOR, AirParams, BREATH, ParticleParams, air_step, particles_step
from advisor.physics.water import WaterParams, absolute, relative, water_step

ROOM = 110.0                    # m³, the salon of Frank's house
WATER = WaterParams(ROOM, exchange=0.5, reserve=5.0, sources=30.0)


def hours(step, value, n):
    for _ in range(int(n * 12)):
        value = step(value)
    return value


class WaterTest(unittest.TestCase):
    def test_humidity_and_water_read_back(self):
        self.assertAlmostEqual(relative(20.6, absolute(20.6, 66.0)), 66.0, places=6)

    def test_an_open_window_dries_toward_a_drier_outside(self):
        inside, outside = absolute(20.6, 66.0), absolute(12.8, 88.0)
        shut, open_ = (inside, inside), (inside, inside)
        for _ in range(12):
            shut = water_step(WATER, *shut, outside, 10.0, 22.0)
            open_ = water_step(WATER, *open_, outside, 300.0, 22.0)
        self.assertLess(open_[0], shut[0])
        self.assertGreater(open_[0], outside)

    def test_the_walls_give_their_water_back_once_shut(self):
        inside, outside = absolute(20.0, 70.0), absolute(10.0, 60.0)
        water, reserve = inside, inside
        for _ in range(3):
            water, reserve = water_step(WATER, water, reserve, outside, 400.0, 14.0)
        dried = water
        for _ in range(12):
            water, reserve = water_step(WATER, water, reserve, outside, 10.0, 14.0)
        self.assertGreater(water, dried)

    def test_the_household_makes_water(self):
        dry = WaterParams(ROOM, 0.5, 5.0, 0.0)
        start = absolute(20.0, 50.0)
        self.assertGreater(water_step(WATER, start, start, start, 10.0, 8.0)[0], water_step(dry, start, start, start, 10.0, 8.0)[0])


class AirTest(unittest.TestCase):
    def test_people_raise_the_co2_and_a_window_brings_it_back(self):
        p = AirParams(ROOM, sources=2 * BREATH)
        shut = hours(lambda c: air_step(p, c, 10.0, 20.0), 600.0, 3)
        self.assertGreater(shut, 600.0)
        aired = hours(lambda c: air_step(p, c, 400.0, 20.0), shut, 1)
        self.assertLess(aired, shut)
        self.assertGreater(aired, OUTDOOR)

    def test_an_empty_room_settles_at_the_outdoor_level(self):
        p = AirParams(ROOM, sources=0.0)
        self.assertAlmostEqual(hours(lambda c: air_step(p, c, 50.0, 3.0), 1200.0, 48), OUTDOOR, delta=1.0)


class ParticlesTest(unittest.TestCase):
    p = ParticleParams(ROOM, settling=0.5, outdoor=8.0, sources=0.0)

    def test_after_cooking_the_air_clears_faster_with_a_window_or_the_purifier(self):
        alone = hours(lambda v: particles_step(self.p, v, 10.0, 20.0), 80.0, 1)
        aired = hours(lambda v: particles_step(self.p, v, 400.0, 20.0), 80.0, 1)
        purified = hours(lambda v: particles_step(self.p, v, 10.0, 20.0, purifier=200.0), 80.0, 1)
        self.assertLess(alone, 80.0)
        self.assertLess(aired, alone)
        self.assertLess(purified, alone)

    def test_a_window_cannot_take_the_air_below_the_outdoor_level(self):
        aired = hours(lambda v: particles_step(self.p, v, 2000.0, 20.0), 30.0, 6)
        self.assertGreater(aired, 0.0)
        self.assertLessEqual(aired, 8.0 + 0.5)


if __name__ == "__main__":
    unittest.main()
