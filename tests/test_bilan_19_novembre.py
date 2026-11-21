"""Bilan of 19 November (moteur 3.19.4): what the lab showed on 3.19.2 that read badly.

- The Chambre P's humidity urgency asked « Aérez 30, 25, 20, 25 min » in 35 minutes (18 November from 18 h 38): the
  duration asked is kept while it still does nearly as much.
- The Chambre AL's « Aérez 30 min » said the humidity and the mould by turns, six times in an hour: the slot's subject is
  held while the gesture lowers it at all.
- « Aérez 5 min » beside « le COV devrait retomber en 30 min » (Salon · Cuisine, 19 November at 9 h 26): see
  test_advisor_air.py, the hour is said.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.board import Board, urgent_decision  # noqa: E402
from advisor.decide import Decision, Gesture, Path as Scenario  # noqa: E402
from advisor.words import phrase  # noqa: E402


class UrgencyKeepsItsDuration(unittest.TestCase):
    NOTHING, TWENTY, TWENTY_FIVE, THIRTY = Gesture("nothing"), Gesture("open", 20), Gesture("open", 25), Gesture("open", 30)

    def scenarios(self):
        return {self.NOTHING: {"humidity": 5.0, "total": 6.0}, self.TWENTY: {"humidity": 3.2, "total": 4.4},
                self.TWENTY_FIVE: {"humidity": 3.0, "total": 4.2}, self.THIRTY: {"humidity": 2.9, "total": 4.3}}

    def ask(self, before=None):
        return urgent_decision(Decision(self.NOTHING, 0.0, "nothing", self.scenarios()), "humidity", 82.0, None, before)

    def test_the_shortest_that_does_nearly_as_much_first(self):
        self.assertEqual(self.ask().gesture, self.TWENTY)

    def test_the_duration_asked_is_kept(self):
        self.assertEqual(self.ask(("open", 30)).gesture, self.THIRTY)
        self.assertEqual(self.ask(["open", 25]).gesture, self.TWENTY_FIVE)

    def test_not_kept_once_it_no_longer_does_nearly_as_much(self):
        # Five minutes no longer lower it enough: the shortest that does is asked.
        scenarios = {**self.scenarios(), Gesture("open", 5): {"humidity": 4.5, "total": 5.5}}
        asked = urgent_decision(Decision(self.NOTHING, 0.0, "nothing", scenarios), "humidity", 82.0, None, ("open", 5))
        self.assertEqual(asked.gesture, self.TWENTY)


class UrgencyDoesNotGoAndComeBack(unittest.TestCase):
    """Labo, Salon · Cuisine, 21 November: « Aérez 5 min » at 8 h 56, « Rien à faire » at 9 h 01 (« les particules
    repassent seules sous 15 vers 9 h 20 »), « Aérez 5 min » again at 9 h 06, the windows shut throughout; 26 and
    34 µg/m³ at 9 h 20. The gesture asked is kept while it does no worse than nothing (moteur 3.22.3)."""
    NOTHING, FIVE = Gesture("nothing"), Gesture("open", 5)

    def ask(self, five, before):
        scenarios = {self.NOTHING: {"particles": 2.0, "total": 2.5}, self.FIVE: {"particles": five, "total": five + 0.6}}
        return urgent_decision(Decision(self.NOTHING, 0.0, "nothing", scenarios), "particles", 47.0, None, before)

    def test_kept_when_the_forecast_sees_it_fall_alone(self):
        self.assertIsNone(self.ask(2.0, None))
        self.assertEqual(self.ask(2.0, ("open", 5)).gesture, self.FIVE)

    def test_not_kept_when_airing_makes_it_worse(self):
        # The outside dirtier than the room: airing would bring particles in.
        self.assertIsNone(self.ask(2.4, ("open", 5)))

    def test_forgotten_once_the_urgency_is_over(self):
        from datetime import datetime, timedelta, timezone
        board, now = Board(), datetime(2026, 11, 21, 7, 50, tzinfo=timezone.utc)
        for k in range(2):
            board.urgent_now({"particles": 47.0}, None, None, False, now + timedelta(minutes=5 * k))
        board.asked["particles"] = ("open", 5)
        board.urgent_now({"particles": 30.0}, None, None, False, now + timedelta(minutes=10))
        self.assertIn("particles", board.asked)
        board.urgent_now({"particles": 12.0}, None, None, False, now + timedelta(minutes=15))
        self.assertNotIn("particles", board.asked)


class SlotKeepsItsSubject(unittest.TestCase):
    def decision(self):
        nothing, airing = Gesture("nothing"), Gesture("open", 30)
        # The mould lowered a little more than the humidity: the subject would turn to it.
        zero = dict.fromkeys(("heat", "co2", "particles", "voc", "energy"), 0.0)
        scenarios = {nothing: {**zero, "humidity": 3.0, "mould": 3.0, "total": 6.0},
                     airing: {**zero, "humidity": 2.0, "mould": 1.5, "total": 3.5}}
        paths = {nothing: Scenario(air=[19.0] * 24, humidity=[73.0] * 24),
                 airing: Scenario(air=[18.5] * 24, humidity=[66.0] * 24)}
        return Decision(airing, 2.1, "creneau", scenarios, paths)

    def test_without_the_hold_the_subject_turns(self):
        self.assertEqual(phrase(self.decision(), 23, hour=19.0, subject_before="humidity")["subject"], "mould")

    def test_the_slot_holds_its_subject(self):
        said = phrase(self.decision(), 23, hour=19.0, subject_before="humidity", hold_subject=True)
        self.assertEqual(said["subject"], "humidity")
        self.assertIn("d'humidité", said["line"])

    def test_not_held_once_the_gesture_no_longer_lowers_it(self):
        decision = self.decision()
        flat = {**decision.scenarios, decision.gesture: {**decision.scenarios[decision.gesture], "humidity": 3.0}}
        said = phrase(Decision(decision.gesture, 2.1, "creneau", flat, decision.paths), 23, hour=19.0,
                      subject_before="humidity", hold_subject=True)
        self.assertEqual(said["subject"], "mould")


if __name__ == "__main__":
    unittest.main()
