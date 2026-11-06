"""The window open now, seen at work: a leaf ajar does a fraction of what the twin gives the window (advisor/opening.py)."""
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.decide import Gesture, decide, simulate
from advisor.knowing import RoomView, window_weak
from advisor.opening import OBSERVE_MINUTES, SETTLE, Opened, closed_cases, disturbed, scaled, seen_share, settling
from advisor.snapshot import load, replay, restore
from advisor.words import tip_text

PARIS = ZoneInfo("Europe/Paris")
OPENED = datetime(2026, 11, 3, 19, 19, tzinfo=PARIS)


def chambre_p():
    """Chambre P, 3 November at 19 h 19, one leaf just opened, and the twin's forecast for it."""
    snap = load(Path(__file__).parent / "fixtures" / "chambre-p-3-novembre-19h19.json")
    decision, _ = replay(snap)
    path = decision.paths[Gesture("nothing")]
    return snap, Opened(OPENED, snap["now"]["air"], snap["now"]["humidity"], tuple(path.air), tuple(path.humidity))


class SeenAtWork(unittest.TestCase):
    def test_a_leaf_ajar_does_a_fraction_of_the_forecast(self):
        # Measured at 19 h 34: 18.1 °C and 69 %, where the twin forecast 17.4 °C and 54 %.
        snap, opened = chambre_p()
        self.assertIsNone(seen_share(opened, OPENED + timedelta(minutes=OBSERVE_MINUTES - 1), 18.1, 69.0))
        share = seen_share(opened, OPENED + timedelta(minutes=15), 18.1, 69.0)
        self.assertLess(share, 0.2)
        # Judged with what the window really does, it no longer promises to dry the room.
        args = restore(snap)
        args.update(twins=scaled(args["twins"], share), now=replace(args["now"], air=18.1, humidity=69.0),
                    previous=Gesture("close", after=10))
        self.assertNotEqual(decide(**args).gesture, Gesture("close", after=5))
        # Left open for the evening, even ajar, it still dries the room more than shutting: « Laissez ouvert » (3.9.3).
        self.assertEqual(decide(**args).gesture.kind, "keep")

    def test_a_window_doing_as_forecast_keeps_its_share(self):
        snap, opened = chambre_p()
        k = 2   # fifteen minutes on
        share = seen_share(opened, OPENED + timedelta(minutes=15), opened.forecast_air[k], opened.forecast_humidity[k])
        self.assertAlmostEqual(share, 1.0, places=2)

    def test_the_airing_is_judged_an_hour_after_it_was_shut_against_the_twin_without_it(self):
        # Shut at 19 h 36: the twin's forecasts for the airing as it was, open seventeen minutes then shut, and without it.
        from advisor.notes import GOOD, LITTLE, WORSE, grade, ratio
        from advisor.proof import SUPPOSED, level
        from advisor.physics.water import absolute
        snap, opened = chambre_p()
        args = restore(snap)
        shut = OPENED + timedelta(minutes=17)
        path = simulate(args["twins"], args["now"], args["coming"], Gesture("close", after=17))
        without = simulate(args["twins"], args["now"], args["coming"], Gesture("close"))
        closed = settling(opened, shut, path.air, path.humidity, without.air, without.humidity)
        self.assertIsNone(settling(opened, OPENED + timedelta(minutes=OBSERVE_MINUTES - 1), path.air, path.humidity,
                                   without.air, without.humidity))
        self.assertFalse(closed.due(shut + SETTLE - timedelta(minutes=5)))
        self.assertTrue(closed.due(shut + SETTLE))
        judged = shut + SETTLE
        k = int((judged - OPENED).total_seconds() / 300) - 1
        # As the twin said: a good note. As without it: nothing done. Wetter than without it: the other way.
        as_said = closed_cases(closed, judged, path.air[k], path.humidity[k])["humidity"]
        self.assertEqual(grade(ratio(*as_said)), GOOD)
        self.assertAlmostEqual(as_said[1], as_said[0], places=2)
        nothing = closed_cases(closed, judged, without.air[k], without.humidity[k])["humidity"]
        self.assertEqual(grade(ratio(*nothing)), LITTLE)
        # Frank, 3 November: an hour on, the humidity back where it was, and higher.
        back = closed_cases(closed, judged, 18.2, 70.0)["humidity"]
        self.assertLess(back[0], 0)
        self.assertIn(grade(ratio(*back)), (LITTLE, WORSE))
        # Two such airings in a row: the next one is no longer put forward, whatever came before.
        self.assertEqual(level([(-2.0, -2.1), (-1.5, -1.4), (-1.8, -1.7), back, (-2.4, -0.6)], reinforced=True), SUPPOSED)
        self.assertEqual(closed_cases(closed, OPENED - timedelta(minutes=5), 18.2, 70.0), {})

    def test_beyond_the_forecasts_nothing_is_kept(self):
        _, opened = chambre_p()
        self.assertIsNone(settling(opened, OPENED + timedelta(minutes=17), opened.forecast_air[:12], (),
                                   opened.forecast_air[:12]))

    def test_anything_else_meanwhile_puts_it_aside(self):
        _, opened = chambre_p()
        closed = settling(opened, OPENED + timedelta(minutes=17), opened.forecast_air, (), opened.forecast_air)
        self.assertFalse(disturbed(closed, (), (False, False), {}))
        self.assertTrue(disturbed(closed, ((1.0, 1.2),), (False, False), {}))     # opened again
        self.assertTrue(disturbed(closed, (), (True, False), {}))                 # the VMC's fast speed
        self.assertTrue(disturbed(closed, (), (False, False), {"humidity": 2.0}))  # a shower
        self.assertFalse(disturbed(closed, (), (False, False), {"co2": 1.0}))     # someone breathing

    def test_said_in_good_to_know(self):
        view = RoomView(OPENED + timedelta(minutes=15), 43.4, 5.5, air=18.1, humidity=69.0, opened_at=OPENED,
                        air_at_opening=18.2, humidity_at_opening=67.0, window_share=0.12)
        [tip] = window_weak(view)
        self.assertEqual(tip_text(tip), "Ouverte depuis 19 h 19 : 18,2 → 18,1 °C, 67 → 69 % : elle renouvelle peu l'air")
        self.assertEqual(window_weak(replace(view, window_share=0.8)), [])


if __name__ == "__main__":
    unittest.main()
