"""« Ce conseil ne va pas » and the gestures followed (CAHIER-MOTEUR.md § 15)."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.decide import Gesture, Now
from advisor.feedback import declined, done, follow, followed_share, pause_until
from advisor.household import Habits

T = datetime(2026, 11, 1, 10, tzinfo=timezone.utc)
WINDOW = ((1.0, 1.2),)
SHUT = Now(air=20.0, walls=19.0, opened=())
OPEN = Now(air=20.0, walls=19.0, opened=WINDOW)


class Followed(unittest.TestCase):
    def test_an_airing_done_while_asked(self):
        asked, out = follow(None, Gesture("open", 10), "Aérez 10 min", False, SHUT, T)
        self.assertEqual(asked.kind, "open")
        self.assertEqual(out, [])
        asked, out = follow(asked, Gesture("close", after=10), "Refermez vers 10 h 25", False, OPEN, T + timedelta(minutes=15))
        self.assertTrue(out[0]["suivi"])
        self.assertEqual(out[0]["minutes"], 15)
        # The window open, « Refermez » is asked in turn.
        self.assertEqual(asked.kind, "close")

    def test_an_advice_replaced_before_it_was_done(self):
        asked, _ = follow(None, Gesture("open", 10), "Aérez 10 min", False, SHUT, T)
        asked, out = follow(asked, Gesture("nothing"), "Rien à faire", False, SHUT, T + timedelta(minutes=40))
        self.assertIsNone(asked)
        self.assertFalse(out[0]["suivi"])

    def test_the_same_gesture_still_shown_waits(self):
        asked, _ = follow(None, Gesture("open", 10), "Aérez 10 min", False, SHUT, T)
        again, out = follow(asked, Gesture("open", 20), "Aérez 20 min", False, SHUT, T + timedelta(minutes=5))
        self.assertEqual((again, out), (asked, []))

    def test_nothing_to_do_asks_nothing(self):
        self.assertEqual(follow(None, Gesture("nothing"), "Rien à faire", False, SHUT, T), (None, []))
        self.assertEqual(follow(None, None, "Rien à faire", False, SHUT, T), (None, []))

    def test_a_gesture_already_done_is_not_asked(self):
        self.assertEqual(follow(None, Gesture("close"), "Refermez", False, SHUT, T), (None, []))

    def test_devices(self):
        self.assertTrue(done("boost", Now(air=20.0, walls=19.0, opened=(), boosting=True)))
        self.assertTrue(done("purify_off", SHUT))
        self.assertFalse(done("nothing", SHUT))

    def test_the_share_followed_keeps_the_trials_apart(self):
        records = [{"suivi": True}, {"suivi": False}, {"suivi": True, "essai": True}]
        self.assertEqual(followed_share(records), {"suivis": 1, "demandes": 2, "essais_faits": 1, "essais": 1})


class NotNow(unittest.TestCase):
    def test_a_gesture_put_aside_for_the_household_s_time(self):
        paused = {"open": pause_until(T, Habits().not_now)}
        self.assertEqual(declined(paused, SHUT, T + timedelta(minutes=59)), frozenset({"open"}))
        self.assertEqual(declined(paused, SHUT, T + timedelta(minutes=61)), frozenset())

    def test_an_opening_put_aside_never_forbids_the_windows_open(self):
        self.assertEqual(declined({"open": T + timedelta(hours=1)}, OPEN, T), frozenset())

    def test_the_pause_is_a_setting(self):
        self.assertEqual(Habits.of({"pas_maintenant_min": 30}).not_now, 30)


if __name__ == "__main__":
    unittest.main()
