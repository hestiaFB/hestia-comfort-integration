"""The 3.0 advisor's words: a title, a gain in plain units, « Pourquoi ? », the same in three languages."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.decide import Now, decide
from advisor.words import TEXTS, phrase
from test_advisor_decide import FRENCH, TWINS, day, night


class WordsTest(unittest.TestCase):
    def test_the_night_of_30_october_in_words(self):
        decision = decide(TWINS, Now(air=20.6, walls=20.6, opened=(FRENCH.size,), humidity=66.0, night=True), night())
        words = phrase(decision, end_hour=7)
        self.assertEqual(words["title"], "Refermez")
        self.assertEqual(words["subject"], "heat")
        self.assertRegex(words["line"], r"^vous gardez \d+,\d °C d'ici 7 h$")
        self.assertIn(len(words["why"]), (2, 3))
        self.assertTrue(any(w.startswith("Ouverte : ") for w in words["why"]))
        self.assertTrue(any(w.startswith("Fermée : ") for w in words["why"]))
        self.assertTrue(all("," in w.split(" °C")[0] for w in words["why"]))

    def test_stale_air_says_how_long_and_what_it_brings(self):
        decision = decide(TWINS, Now(air=21.5, walls=21.5, opened=(), humidity=55.0, co2=1600.0), day(outdoor=17.0))
        words = phrase(decision, end_hour=17)
        self.assertRegex(words["title"], r"^(Aérez \d+ min|Ouvrez)$")
        self.assertEqual(words["subject"], "co2")

    def test_nothing_to_do_says_so_and_the_conditional_when_unsure(self):
        # No CO₂ sensor: with one at 600 ppm, the twin sees it reach 1 200 ppm by 17 h, and says so.
        decision = decide(TWINS, Now(air=21.5, walls=21.5, opened=(), humidity=50.0), day(outdoor=21.0))
        self.assertEqual(phrase(decision, end_hour=17)["title"], "Rien à faire")
        # A shut room is not told « open or shut » (first advice in the test Home Assistant, 31 October).
        self.assertEqual(phrase(decision, end_hour=17)["line"], "La pièce restera dans votre plage")
        unsure = decide(TWINS, Now(air=20.6, walls=20.6, opened=(FRENCH.size,), humidity=66.0, night=True), night())
        self.assertTrue(phrase(unsure, end_hour=7, sure=False)["line"].startswith("vous devriez garder "))

    def test_nothing_to_do_never_says_in_your_range_when_the_room_is_not(self):
        # 31 October, Chambre P at 18.3 °C, its window open on a mild afternoon: « restera dans votre plage » was false.
        decision = decide(TWINS, Now(air=18.3, walls=18.3, opened=(FRENCH.size,), humidity=50.0), day(outdoor=18.3))
        words = phrase(decision, end_hour=17)
        self.assertEqual(words["title"], "Rien à faire")
        self.assertRegex(words["line"], r"^Ouverte ou fermée : \d+,\d °C à 17 h$")
        self.assertNotIn("plage", words["line"])

    def test_a_safety_close_says_why(self):
        # Test Home Assistant, 31 October: « Refermez » with no line while rain was coming.
        from advisor.decide import Gesture
        decision = decide(TWINS, Now(air=20.6, walls=20.6, opened=(FRENCH.size,)), day(), forbidden=frozenset({"open"}))
        self.assertEqual(decision.gesture, Gesture("close"))
        self.assertEqual(phrase(decision, end_hour=17, reason="rain_soon")["line"], "la pluie arrive")
        # A shut room under the same rain: nothing to do, because the rain takes the openings away.
        shut = decide(TWINS, Now(air=19.8, walls=19.8, opened=(), humidity=59.0, co2=613.0), day(outdoor=13.0),
                      forbidden=frozenset({"open"}))
        self.assertEqual(phrase(shut, end_hour=21, reason="rain_soon")["line"], "Gardez fermé : la pluie arrive")

    def test_in_your_range_only_when_humidity_and_air_are_too(self):
        # Rejeu of 10 days, Chambre P on 23 October: 77 % of humidity, a humid outside, « la pièce restera dans votre plage ».
        decision = decide(TWINS, Now(air=19.5, walls=19.5, opened=(), humidity=77.0), day(outdoor=17.6, hours=3)[:1] * 36)
        words = phrase(decision, end_hour=17, marks={"minimum": 18.0, "maximum": 24.0})
        if decision.gesture.kind == "nothing":
            self.assertNotIn("plage", words["line"])
            self.assertRegex(words["line"], r"^Humidité \d+ % à 17 h : aucun geste ne ferait vraiment mieux$")

    def test_every_language_has_every_phrase(self):
        self.assertEqual(set(TEXTS["en"]), set(TEXTS["fr"]))
        self.assertEqual(set(TEXTS["de"]), set(TEXTS["fr"]))
        decision = decide(TWINS, Now(air=20.6, walls=20.6, opened=(FRENCH.size,), humidity=66.0, night=True), night())
        self.assertEqual(phrase(decision, 7, "en")["title"], "Close")
        self.assertEqual(phrase(decision, 7, "de")["title"], "Schließen")


if __name__ == "__main__":
    unittest.main()
