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


class Voc(unittest.TestCase):
    """The kitchen's VOC index, with the twin learned on 10 days (bench of 31 October)."""
    KITCHEN = ParticleParams(110.0, 0.018, 63.7, 3218.0, -997.0, -3003.0)

    def decide(self, sources, voc=450.0):
        from dataclasses import replace
        from advisor.decide import Now, decide
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_advisor_decide import TWINS, day
        twins = replace(TWINS, voc=replace(self.KITCHEN, sources=self.KITCHEN.sources * sources), voc_flow=(5.55, 54.6))
        return decide(twins, Now(air=21.5, walls=21.5, opened=(), voc=voc), day(outdoor=17.0, start=19.0))

    def test_a_cooking_going_on_is_a_source_and_shutting_would_let_it_climb(self):
        # Frank, 1 November: the window open while cooking, the VOC holds; the twin, seeing it should fall, said
        # « Refermez ». The source running now is measured and carried: shut, the VOC would climb.
        from dataclasses import replace
        from advisor.decide import Gesture, Now, recent_sources, simulate
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_advisor_decide import TWINS, day
        twins = replace(TWINS, voc=self.KITCHEN, voc_flow=(5.55, 54.6))
        opened = TWINS.windows
        coming = day(outdoor=12.0, start=19.0)
        before, now = (Now(air=21.0, walls=21.0, opened=opened, voc=300.0) for _ in range(2))
        found = recent_sources(twins, before, coming[:6], now)
        self.assertGreater(found.get("voc", 0.0), 0.0)
        cooking = replace(now, sources=found)
        shut = simulate(twins, cooking, coming, Gesture("close"))
        left = simulate(twins, cooking, coming, Gesture("nothing"))
        self.assertGreater(shut.voc[5], left.voc[5])
        self.assertGreater(shut.voc[5], 300.0)
        # The windows changed meanwhile: the gesture explains the gap, not a source.
        self.assertEqual(recent_sources(twins, replace(before, opened=()), coming[:6], now), {})

    def test_open_on_both_sides_the_air_crosses_the_room(self):
        # « Ouvrez aussi la porte-fenêtre : 5 min au lieu de 15 » (CAHIER-MOTEUR.md § 9.1): supposed, said to try.
        from dataclasses import replace
        from advisor.decide import Gesture, Now, candidates, crossing, decide, simulate
        from advisor.words import phrase
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_advisor_decide import TWINS, day
        west, south = (1.18, 1.21), (1.18, 2.1)
        twins = replace(TWINS, windows=(west, south), bearings=(270.0, 180.0), voc=self.KITCHEN, voc_flow=(5.55, 54.6))
        self.assertEqual(crossing(twins, (west, south)), 2.0)
        self.assertEqual(crossing(twins, (west,)), 1.0)
        now = Now(air=21.0, walls=21.0, opened=(west,), voc=400.0)
        more = [g for g in candidates(now, twins) if g.kind == "open_more"]
        self.assertEqual((more[0].facing, more[0].minutes), ("south", 5))
        coming = day(outdoor=12.0, start=19.0)
        both = simulate(twins, now, coming, Gesture("open_more", 10, facing="south"))
        one = simulate(twins, now, coming, Gesture("nothing"))
        self.assertLess(both.voc[1], one.voc[1])
        decision = decide(twins, now, coming, proof={"voc": "proven"})
        shown = replace(decision, gesture=Gesture("open_more", 5, facing="south"), rule="best")
        self.assertEqual(phrase(shown, 21)["title"], "Ouvrez aussi les fenêtres sud 5 min")
        self.assertEqual(phrase(replace(shown, gesture=Gesture("open_more", 10)), 21)["title"],
                         "Ouvrez aussi les autres fenêtres 10 min")
        # A room with windows on one side only has nothing to cross.
        self.assertFalse(any(g.kind == "open_more" for g in candidates(now, replace(twins, bearings=(270.0, 270.0)))))

    def test_a_moderate_voc_falls_back_by_itself(self):
        # At 300, under 150 within the half-hour without anything done: no gesture (Confort 2.1 had learned it).
        self.assertEqual(self.decide(1, voc=300.0).gesture.kind, "nothing")

    def test_after_cooking_a_short_airing(self):
        # At 450, an hour above 150 if nothing is done: ten minutes of airing on a mild evening.
        # The shortest airing that is enough, five minutes at a time (Frank, 1 November).
        self.assertEqual(self.decide(1).gesture, __import__("advisor.decide", fromlist=["Gesture"]).Gesture("open", 5))

    def test_a_lasting_source_asks_to_open(self):
        from advisor.words import phrase
        decision = self.decide(5)
        self.assertEqual(decision.gesture.kind, "open")
        self.assertEqual(phrase(decision, 22)["subject"], "voc")
        self.assertRegex(phrase(decision, 22)["line"], r"^le COV retombe en \d+ min$")


class Devices(unittest.TestCase):
    """The VMC's fast speed and the purifier, as gestures (CAHIER-MOTEUR.md § 9.1)."""

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))

    def test_a_humid_bedroom_under_the_rain_runs_its_vmc_fast(self):
        from dataclasses import replace
        from advisor.decide import Gesture, Now, decide, effect
        from advisor.proof import PROVEN
        from advisor.words import phrase
        from test_advisor_decide import TWINS, day
        twins = replace(TWINS, boost=60.0)
        # 85 % after a shower, the rain forbids opening: the VMC is the remedy.
        decision = decide(twins, Now(air=21.5, walls=21.5, opened=(), humidity=85.0), day(outdoor=12.0),
                          forbidden=frozenset({"open"}), proof={"boost:humidity": PROVEN})
        self.assertEqual(decision.gesture.kind, "boost")
        self.assertEqual(effect(decision.gesture, "humidity"), "boost:humidity")
        self.assertRegex(phrase(decision, 17)["title"], r"^Lancez la VMC rapide \d+ min$")

    def test_the_purifier_takes_the_particles_not_the_voc(self):
        from dataclasses import replace
        from advisor.decide import Gesture, Now, decide, simulate
        from test_advisor_decide import TWINS, day
        twins = replace(TWINS, particles=ParticleParams(110.0, 0.2, 5.0, 50.0), purifier=150.0,
                        voc=ParticleParams(110.0, 0.018, 63.7, 3218.0), voc_flow=(5.55, 54.6))
        now = Now(air=21.0, walls=21.0, opened=(), particles=60.0, voc=300.0)
        idle, clean = (simulate(twins, now, day(), g) for g in (Gesture("nothing"), Gesture("purify", 60)))
        self.assertLess(clean.particles[11], idle.particles[11] - 10)
        self.assertEqual(clean.voc, idle.voc)
        # Under the rain, the purifier is the remedy (opening would clear the particles too).
        decision = decide(twins, now, day(), forbidden=frozenset({"open"}))
        self.assertEqual(decision.gesture.kind, "purify")
