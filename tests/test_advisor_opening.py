"""The window open now, seen at work: a leaf ajar does a fraction of what the twin gives the window (advisor/opening.py)."""
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.decide import Gesture, decide
from advisor.knowing import RoomView, window_weak
from advisor.opening import OBSERVE_MINUTES, Opened, closed_cases, scaled, seen_share
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
        self.assertEqual(decide(**args).gesture.kind, "nothing")

    def test_a_window_doing_as_forecast_keeps_its_share(self):
        snap, opened = chambre_p()
        k = 2   # fifteen minutes on
        share = seen_share(opened, OPENED + timedelta(minutes=15), opened.forecast_air[k], opened.forecast_humidity[k])
        self.assertAlmostEqual(share, 1.0, places=2)

    def test_the_airing_ended_is_kept_as_a_gesture_that_belies_the_twin(self):
        # Shut at 19 h 36, seventeen minutes on: the air barely cooled, its water went up instead of down.
        from advisor.proof import SUPPOSED, level
        _, opened = chambre_p()
        cases = closed_cases(opened, OPENED + timedelta(minutes=17), 18.1, 69.0)
        forecast, measured = cases["humidity"]
        self.assertLess(forecast, -1.0)
        self.assertGreater(measured, 0.0)
        self.assertLess(cases["heat"][1] / cases["heat"][0], 0.5)
        # With the evening's second airing (40 min, a quarter of the forecast), the next one is no longer put forward.
        self.assertEqual(level([cases["humidity"], (-2.4, -0.6)], reinforced=True), SUPPOSED)
        self.assertEqual(closed_cases(opened, OPENED + timedelta(minutes=5), 18.1, 69.0), {})

    def test_said_in_good_to_know(self):
        view = RoomView(OPENED + timedelta(minutes=15), 43.4, 5.5, air=18.1, humidity=69.0, opened_at=OPENED,
                        air_at_opening=18.2, humidity_at_opening=67.0, window_share=0.12)
        [tip] = window_weak(view)
        self.assertEqual(tip_text(tip), "Ouverte depuis 19 h 19 : 18,2 → 18,1 °C, 67 → 69 % : elle renouvelle peu l'air")
        self.assertEqual(window_weak(replace(view, window_share=0.8)), [])


if __name__ == "__main__":
    unittest.main()
