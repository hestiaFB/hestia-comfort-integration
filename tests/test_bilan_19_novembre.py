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
from advisor.board import urgent_decision  # noqa: E402
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
