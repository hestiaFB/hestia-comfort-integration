"""The house's day of 13 November (moteur 3.16.0, first day of the freeze), read with Frank.

- « Ouvrez » promised 53 % at 11 h for a window supposed open all morning; opened 25 min, the room came back to 65 %.
- The walls' water was taken equal to the air: after an airing or a shower the twin missed the room coming back.
- The stove was supposed to idle until its schedule's lower slot; the household's automation puts it out sooner.
- The snapshots replayed without the stove's idle flame.
- The subject of the line took turns every half hour on a gesture held two hours.
"""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.decide import Gesture, Now, Thermostat, Twins, _open, simulate  # noqa: E402
from advisor.house import Opening, Room  # noqa: E402
from advisor.household import Habits  # noqa: E402
from advisor.physics.thermal import Inputs, ordinary  # noqa: E402
from advisor.physics import airfit  # noqa: E402
from advisor.physics.water import WaterParams, absolute, bounded, relative, sources, within  # noqa: E402
from advisor.snapshot import capture, restore  # noqa: E402

WEST = Opening("binary_sensor.fenetre_a_contact", "window", area=1.2, height=1.2)
ROOM = Room("salon", "Salon", volume=90.0, openings=(WEST,), heating_power=0)


class ClosingTests(unittest.TestCase):
    def test_left_as_it_is_the_window_is_shut_after_the_usual_airing(self):
        twins = Twins(heat=ordinary(ROOM), windows=(WEST.size,))
        now = Now(air=19.3, walls=19.0, opened=(WEST.size,), closing_in=30.0)
        self.assertEqual(_open(Gesture("nothing"), now, twins, 5), (WEST.size,))
        self.assertEqual(_open(Gesture("nothing"), now, twins, 6), ())
        self.assertEqual(_open(Gesture("nothing"), replace(now, closing_in=None), twins, 30), (WEST.size,))


class ReserveTests(unittest.TestCase):
    def test_wet_walls_bring_the_humidity_back_after_an_airing(self):
        twins = Twins(heat=ordinary(ROOM), windows=(WEST.size,),
                      water=WaterParams(volume=40.0, exchange=0.5, reserve=4.7, sources=9.0))
        coming = [(Inputs(9.0, hour=10 + k / 12), absolute(9.0, 80.0)) for k in range(36)]
        dry = Now(air=18.4, walls=18.4, opened=(), humidity=63.0)
        alike = simulate(twins, dry, coming, Gesture("nothing")).humidity[-1]
        wet = simulate(twins, replace(dry, reserve=absolute(19.3, 69.6)), coming, Gesture("nothing")).humidity[-1]
        self.assertGreater(wet, alike + 2.0)


class IdleHoldTests(unittest.TestCase):
    def setUp(self):
        self.twins = Twins(heat=replace(ordinary(ROOM), share=0.4), windows=(WEST.size,),
                           house_thermostat=Thermostat(target=21.5, inside=0.8, kind="pellet"), house_power=8500.0,
                           house_now=0.0, house_idle=0.3)
        self.coming = [(Inputs(12.0, hour=11 + k / 12, house_heat=0.3 * 8500.0), None) for k in range(36)]
        self.now = Now(air=22.0, walls=21.5, opened=(), house_running=True)

    def test_the_idle_flame_is_put_out_after_the_household_hold(self):
        path = simulate(replace(self.twins, house_idle_for=45.0), self.now, self.coming, Gesture("nothing"))
        self.assertGreater(path.stove[5], 0.25)
        # Out within the hour; it may start again later only if the room cools under its set point.
        self.assertLess(path.stove[14], 0.1)
        endless = simulate(self.twins, self.now, self.coming, Gesture("nothing"))
        self.assertGreater(endless.stove[14], 0.25)
        self.assertEqual(Habits().stove_idle_hold, 45)
        self.assertEqual(Habits.KEYS["poele_ralenti_min"], "stove_idle_hold")

    def test_the_snapshot_keeps_the_idle_flame(self):
        twins = replace(self.twins, house_idle_for=20.0)
        back = restore(capture(twins, self.now, self.coming, end_hour=14))["twins"]
        self.assertEqual((back.house_idle, back.house_idle_for), (0.3, 20.0))



class BoundsTests(unittest.TestCase):
    """Chambre AL learned −150 g/h of sources, the air renewed 55 times an hour, a reserve of 0.02 volumes."""

    def test_an_impossible_twin_is_brought_within_a_room(self):
        p = within(WaterParams(volume=40.0, exchange=54.6, reserve=0.02, sources=-150.07, rhythm_cos=59.76,
                               rhythm_sin=-159.46))
        self.assertEqual((p.exchange, p.reserve, p.sources, p.rhythm_cos, p.rhythm_sin), (5.0, 2.0, 0.0, 0.0, 0.0))

    def test_the_rhythm_never_takes_the_sources_below_zero(self):
        p = within(WaterParams(volume=51.0, exchange=9.4, reserve=13.6, sources=147.6, rhythm_cos=48.7, rhythm_sin=-175.3))
        self.assertTrue(all(sources(p, h) >= 0.0 for h in range(24)))
        self.assertAlmostEqual((p.rhythm_cos ** 2 + p.rhythm_sin ** 2) ** 0.5, 147.6, places=6)

    def test_a_sound_twin_is_left_as_it_is(self):
        self.assertEqual(bounded(0.51, 4.69, 9.33, 6.76, -6.32), (0.51, 4.69, 9.33, 6.76, -6.32))

    def test_the_night_learns_and_keeps_within_bounds(self):
        found, _ = airfit.values("water", [0.0, 0.0, 4.0, -4.0, -150.0, 60.0, -160.0], 40.0)
        self.assertEqual((found["exchange"], found["reserve"], found["sources"]), (5.0, 2.0, 0.0))


if __name__ == "__main__":
    unittest.main()
