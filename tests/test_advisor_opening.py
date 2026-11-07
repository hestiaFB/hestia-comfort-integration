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


class ReadApart(unittest.TestCase):
    """Chambre P, 6 November: opened at 16 h 20 at 19.5 °C and 74 %; at 16 h 48, 18.7 °C and 71 %. The twin had foreseen
    16.7 °C and 83 % (a window fifteen times Chambre A's): the window did a sixth of the heat, and dried the air more."""

    def setUp(self):
        from advisor.decide import decide as decided
        self.args = restore(load(Path(__file__).parent / "fixtures" / "chambre-p-6-novembre-16h20.json"))
        path = decided(**self.args).paths[Gesture("open")]
        now = self.args["now"]
        self.opened = Opened(datetime(2026, 11, 6, 16, 20, tzinfo=PARIS), now.air, now.humidity, tuple(path.air),
                             tuple(path.humidity))
        self.at = datetime(2026, 11, 6, 16, 48, tzinfo=PARIS)

    def test_the_heat_and_the_water_are_read_apart(self):
        from advisor.opening import seen_shares
        shares = seen_shares(self.opened, self.at, 18.7, 71.0)
        self.assertLess(shares["heat"], 0.3)
        self.assertGreater(shares["water"], 1.0)
        # The drying kept: the air's flows follow the water read, the heat its own.
        twins = scaled(self.args["twins"], shares["heat"], water=shares["water"])
        self.assertAlmostEqual(twins.heat.window, self.args["twins"].heat.window * shares["heat"])
        self.assertAlmostEqual(twins.water_flow[1], self.args["twins"].water_flow[1] * shares["water"])

    def test_an_airing_that_dries_is_not_said_to_fail(self):
        from advisor.opening import failed, seen_shares
        shares = seen_shares(self.opened, self.at, 18.7, 71.0)
        self.assertIsNone(failed("humidity", shares, self.opened, self.at, 18.7, 71.0))

    def test_an_airing_that_does_not_dry_is_said_to_fail_as_measured(self):
        # The same airing, the humidity up a point instead: « Refermez », said with what was measured.
        from advisor.opening import failed, seen_shares
        shares = seen_shares(self.opened, self.at, 19.2, 75.0)
        found = failed("humidity", shares, self.opened, self.at, 19.2, 75.0)
        self.assertEqual((found["subject"], found["then"], found["now"], round(found["minutes"])), ("humidity", 74.0, 75.0, 28))
        decision = decide(**{**self.args, "now": replace(self.args["now"], opened=self.args["twins"].windows), "failed": found})
        self.assertEqual((decision.gesture, decision.rule), (Gesture("close"), "ineffective"))
        from advisor.words import phrase
        self.assertEqual(phrase(decision, 19, hour=16.8)["line"],
                         "L'aération ne fait pas l'effet prévu : 74 % → 75 % en 28 min. Refermez pour ne pas empirer")
        # A subject not read on the windows (the CO₂) never says so.
        self.assertIsNone(failed("co2", shares, self.opened, self.at, 19.2, 75.0))


    def test_a_measure_sent_before_the_window_worked_says_nothing(self):
        # Chambre A, 7 November: the hygrometer sent 67 % as the window opened at 9 h 24, then nothing until 63 % at
        # 9 h 56; at 9 h 39 the airing was said useless on the 67 %. A value sent too soon after the opening is not read.
        from advisor.opening import failed, seen_shares
        sent = self.opened.since + timedelta(minutes=2)
        shares = seen_shares(self.opened, self.at, 19.2, 75.0, {"air": sent, "humidity": sent})
        self.assertEqual(shares, {})
        self.assertIsNone(failed("humidity", shares, self.opened, self.at, 19.2, 75.0, {"humidity": sent}))

    def test_a_measure_is_read_at_the_time_it_was_sent(self):
        # Sent at 16 h 48, read at 17 h 10: against the forecast for 16 h 48, and said « en 28 min », not 50.
        from advisor.opening import failed, seen_shares
        sent = {"air": self.at, "humidity": self.at}
        later = self.at + timedelta(minutes=22)
        self.assertEqual(seen_shares(self.opened, later, 19.2, 75.0, sent), seen_shares(self.opened, self.at, 19.2, 75.0))
        found = failed("humidity", seen_shares(self.opened, later, 19.2, 75.0, sent), self.opened, later, 19.2, 75.0, sent)
        self.assertEqual(round(found["minutes"]), 28)


class WithinPhysics(unittest.TestCase):
    def test_a_window_never_does_more_than_physics_allows(self):
        from advisor.physics.thermal import WINDOW_RANGE, bounded
        heat = restore(load(Path(__file__).parent / "fixtures" / "chambre-p-6-novembre-16h20.json"))["twins"].heat
        self.assertGreater(heat.window, 6)          # learned before the bound
        self.assertEqual(bounded(heat).window, WINDOW_RANGE[1])
        self.assertEqual(bounded(replace(heat, window=0.4)).window, 0.4)
        self.assertEqual(bounded(replace(heat, window=0.01)).window, WINDOW_RANGE[0])
