"""« Ce conseil ne va pas » and the gestures followed (CAHIER-MOTEUR.md § 15)."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.decide import Gesture, Now
from advisor.feedback import IGNORED_MINUTES, declined, done, follow, followed_share, ignored, left_aside, pause_until
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
        # Seen open: followed once open half of what was asked (5 min at least), not at once.
        asked, out = follow(asked, Gesture("close", after=10), "Refermez vers 10 h 25", False, OPEN, T + timedelta(minutes=15))
        self.assertEqual(out, [])
        asked, out = follow(asked, Gesture("close", after=5), "Refermez vers 10 h 25", False, OPEN, T + timedelta(minutes=20))
        self.assertTrue(out[0]["suivi"])
        self.assertEqual(out[0]["minutes"], 20)
        # Then « Refermez » is asked in turn.
        asked, out = follow(asked, Gesture("close", after=5), "Refermez vers 10 h 25", False, OPEN, T + timedelta(minutes=20))
        self.assertEqual(asked.kind, "close")

    def test_an_airing_too_short_is_not_followed(self):
        # Bilan of 11 November: « Aérez 20 min », the window open two minutes.
        asked, _ = follow(None, Gesture("open", 20), "Aérez 20 min", False, SHUT, T)
        asked, out = follow(asked, Gesture("close", after=20), "Refermez vers 10 h 20", False, OPEN, T + timedelta(minutes=5))
        self.assertEqual(out, [])
        asked, out = follow(asked, Gesture("open", 20), "Aérez 20 min", False, SHUT, T + timedelta(minutes=7))
        self.assertFalse(out[0]["suivi"])
        self.assertEqual(out[0]["trop_court"], 2)

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


class Left(unittest.TestCase):
    """A gesture left on the card without being followed is not asked again for two hours (Chambre P, 8 November:
    « Ouvrez » at 18 h, 19 h and 20 h, each held 40 min, never followed)."""

    def record(self, minutes=40, followed=False, trial=False, kind="open"):
        return {"geste": kind, "suivi": followed, "essai": trial, "minutes": minutes}

    def test_left_only_when_gone_long_enough_and_not_by_safety(self):
        self.assertTrue(ignored(self.record(), gone=True, safety=False))
        self.assertFalse(ignored(self.record(), gone=False, safety=False))      # replaced by the VMC
        self.assertFalse(ignored(self.record(), gone=True, safety=True))        # taken away by the rain
        self.assertFalse(ignored(self.record(minutes=5), gone=True, safety=False))
        self.assertFalse(ignored(self.record(followed=True), gone=True, safety=False))
        self.assertFalse(ignored(self.record(trial=True), gone=True, safety=False))
        self.assertFalse(ignored(self.record(kind="close"), gone=True, safety=False))

    def test_put_aside_two_hours_unless_the_room_gets_clearly_worse(self):
        left = {"open": (T + timedelta(minutes=IGNORED_MINUTES), "mould", 75.0)}
        room = Now(air=20.0, walls=19.0, opened=(), humidity=77.0)
        self.assertEqual(set(left_aside(left, room, T + timedelta(minutes=60))), {"open"})
        self.assertEqual(left_aside(left, room, T + timedelta(minutes=IGNORED_MINUTES + 5)), {})
        worse = Now(air=20.0, walls=19.0, opened=(), humidity=80.5)
        self.assertEqual(left_aside(left, worse, T + timedelta(minutes=60)), {})


if __name__ == "__main__":
    unittest.main()
