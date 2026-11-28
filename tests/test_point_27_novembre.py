"""Point of 27 November at home: an urgency does not come back right after another, the calm line holds its subject."""
from datetime import datetime, timedelta
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.board import REST, Board  # noqa: E402

from custom_components.hestia_comfort.room.advice import LINE_HOLD, RoomAdvisor  # noqa: E402

PARIS = ZoneInfo("Europe/Paris")


def at(hour, minute=0):
    return datetime(2026, 11, 27, hour, minute, tzinfo=PARIS)


def run(board, measures, start, steps):
    out = []
    for k in range(steps):
        found = board.urgent_now(measures, None, None, False, start + timedelta(minutes=5 * k))
        out.append(found[0] if found else None)
    return out


class UrgencyRestTest(unittest.TestCase):
    def ended_particles(self):
        board = Board()
        self.assertIn("particles", run(board, {"particles": 30}, at(13, 25), 3))
        # The particles back under their bound at 13 h 37: over.
        self.assertIsNone(board.urgent_now({"particles": 10}, None, None, False, at(13, 37)))
        return board

    def test_another_urgency_waits_after_one_ends(self):
        board = self.ended_particles()
        # The VOC at 300 ppb from 13 h 42 (enter 250): not shown within the rest.
        self.assertEqual(run(board, {"particles": 10, "voc": 300}, at(13, 42), 11), [None] * 11)
        # Still there once the rest is over: shown.
        later = at(13, 37) + timedelta(minutes=REST)
        self.assertEqual(run(board, {"particles": 10, "voc": 300}, later, 2)[-1], "voc")

    def test_a_measure_clearly_worse_does_not_wait(self):
        board = self.ended_particles()
        # 360 ppb: worse than its threshold by more than 100.
        self.assertEqual(run(board, {"particles": 10, "voc": 360}, at(13, 42), 2), [None, "voc"])

    def test_the_rest_is_kept_across_a_restart(self):
        board = self.ended_particles()
        again = Board()
        again.load(board.state())
        self.assertEqual(again.ended, board.ended)
        self.assertEqual(run(again, {"particles": 10, "voc": 300}, at(13, 42), 3), [None] * 3)

    def test_rest_is_an_hour(self):
        self.assertEqual(REST, 60)


class CalmLineTest(unittest.TestCase):
    def advisor(self):
        room = SimpleNamespace(line_held=None)
        room._calm_line = RoomAdvisor._calm_line.__get__(room)
        return room

    def test_new_figures_are_said_at_once(self):
        room = self.advisor()
        self.assertEqual(room._calm_line("Rien à faire", "COV 467 : retombe vers 13 h 15", at(13)), "COV 467 : retombe vers 13 h 15")
        self.assertEqual(room._calm_line("Rien à faire", "COV 420 : retombe vers 13 h 20", at(13, 5)), "COV 420 : retombe vers 13 h 20")

    def test_another_subject_waits_its_turn(self):
        room = self.advisor()
        room._calm_line("Rien à faire", "COV 467 : retombe vers 13 h 15", at(13))
        self.assertEqual(room._calm_line("Rien à faire", "La pièce reste dans votre plage.", at(13, 10)),
                         "COV 467 : retombe vers 13 h 15")
        self.assertEqual(room._calm_line("Rien à faire", "La pièce reste dans votre plage.", at(13) + timedelta(minutes=LINE_HOLD)),
                         "La pièce reste dans votre plage.")

    def test_another_title_starts_again(self):
        room = self.advisor()
        room._calm_line("Rien à faire", "COV 467 : retombe vers 13 h 15", at(13))
        self.assertEqual(room._calm_line("Laissez ouvert", "Encore 5 min.", at(13, 5)), "Encore 5 min.")


if __name__ == "__main__":
    unittest.main()
