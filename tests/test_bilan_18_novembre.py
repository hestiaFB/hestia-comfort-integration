"""Bilan of 18 November (moteur 3.19.2): the line under « Rien à faire », the slot's gesture under the rain, the VOC.

- The line under « Rien à faire » changed 6 to 8 times a day in each room, 23 times in the Chambre P: « rien de mieux »,
  « Gardez fermé : il pleut », « Gardez fermé : la maison est en mode absence », « normal pour cette pièce ». The safety
  now takes the line only when it holds back a gesture the room needs; otherwise it is said in « À savoir ».
- At the lab, the Chambre A's « Aérez 45 min » went at 12 h 55 with the rain, then « Rien à faire » for the slot.
- A VOC put aside came back eleven minutes later on a peak of cooking (17 November at 12 h 11).
"""
from datetime import datetime, timedelta
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.board import ASIDE_LEAST, PATIENCE, WORSE, Board, held_back  # noqa: E402
from advisor.decide import Gesture  # noqa: E402
from advisor.safety import forbidden  # noqa: E402
from advisor.words import TEXTS  # noqa: E402

PARIS = ZoneInfo("Europe/Paris")


def at(hour, minute=0):
    return datetime(2026, 11, 18, hour, minute, tzinfo=PARIS)


class HeldBackTests(unittest.TestCase):
    def test_the_rain_holds_back_an_airing_only(self):
        rain, _ = forbidden(rain_rate=1.0)
        self.assertTrue(held_back(Gesture("open", 45), rain))
        self.assertTrue(held_back(Gesture("open_more", 10), rain))
        # A device, the heating or nothing at all: the rain holds back nothing.
        self.assertFalse(held_back(Gesture("nothing"), rain))
        self.assertFalse(held_back(Gesture("boost", 30), rain))

    def test_nobody_home_and_the_likely_rain(self):
        away, reason = forbidden(alarm="armed_away")
        self.assertEqual(reason, "away")
        self.assertTrue(held_back(Gesture("open", 10), away))
        likely, reason = forbidden(rain_rate=0.0, rain_in=10, chance=80, gauge=True)
        self.assertEqual(reason, "rain_maybe")
        self.assertTrue(held_back(Gesture("open", 10), likely))

    def test_a_sheltered_window_open_and_the_frost(self):
        sheltered, _ = forbidden(rain_rate=1.0, shelter="opened")
        self.assertFalse(held_back(Gesture("open", 10), sheltered))
        self.assertTrue(held_back(Gesture("open_more", 10), sheltered))
        frost, reason = forbidden(coldest=-2.0)
        self.assertEqual(reason, "frost")
        self.assertFalse(held_back(Gesture("open", 10), frost))
        self.assertTrue(held_back(Gesture("open", None), frost))

    def test_calm_forbids_nothing(self):
        self.assertFalse(held_back(Gesture("open", 10), frozenset()))

    def test_the_safety_in_a_known_line(self):
        for language in ("fr", "en", "de"):
            for reason in ("rain", "rain_soon", "gusts", "vigilance", "away"):
                self.assertIn(f"known_{reason}", TEXTS[language])
        self.assertEqual(TEXTS["fr"]["known_rain"], "Il pleut")


class AsideTests(unittest.TestCase):
    def put_aside(self, board, subject, value, start):
        """Shown two steps in, left unfollowed PATIENCE minutes: put aside."""
        now = start
        for _ in range(PATIENCE // 5 + 3):
            board.urgent_now({subject: value}, None, None, False, now)
            now += timedelta(minutes=5)
        self.assertIn(subject, board.aside(now))
        return now

    def test_a_voc_put_aside_rests_an_hour_however_it_goes(self):
        board = Board()
        now = self.put_aside(board, "voc", 300.0, at(11))
        # A peak of cooking, worse by WORSE, within the hour: still aside.
        peak = 300.0 + WORSE["voc"] + 50
        for k in range(ASIDE_LEAST // 5 - 2):
            self.assertIsNone(board.urgent_now({"voc": peak}, None, None, False, now + timedelta(minutes=5 * k)))
        # Still worse an hour on: back.
        later = now + timedelta(minutes=ASIDE_LEAST + 5)
        board.urgent_now({"voc": peak}, None, None, False, later)
        self.assertEqual(board.urgent_now({"voc": peak}, None, None, False, later + timedelta(minutes=5)), ("voc", peak))

    def test_kept_across_a_restart(self):
        board = Board()
        now = self.put_aside(board, "voc", 300.0, at(11))
        board.calm_normal = True
        again = Board()
        again.load(board.state())
        self.assertIsNotNone(again.urgent["voc"].aside_since)
        self.assertTrue(again.calm_normal)
        self.assertIsNone(again.urgent_now({"voc": 500.0}, None, None, False, now + timedelta(minutes=10)))

    def test_an_old_state_loads(self):
        board = Board()
        board.load({"urgent": {"voc": {"since": None, "above": 0, "aside_until": at(13).isoformat(), "aside_value": 300.0}}})
        self.assertIsNone(board.urgent["voc"].aside_since)
        self.assertFalse(board.calm_normal)


class StepSourceTests(unittest.TestCase):
    """The room's step (room/advice.py) is too big to run here without Home Assistant: its rules are checked in its source."""

    def setUp(self):
        path = Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort" / "room" / "advice.py"
        self.source = path.read_text(encoding="utf-8")

    def test_the_safety_said_under_nothing_to_do_only_when_it_holds_back(self):
        self.assertIn("reason=calm_reason", self.source)
        self.assertIn("calm_reason = reason if held_plan or urgent_held else None", self.source)

    def test_the_slot_held_back_is_neither_refreshed_nor_sent_again(self):
        self.assertIn("and plan_before.left(now).after is None and not held_plan):", self.source)
        self.assertIn('if family == "creneau" and held_plan:', self.source)
        self.assertIn("if not held_plan:\n            self.notified = notice", self.source)


if __name__ == "__main__":
    unittest.main()
