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
        self.assertEqual(len(words["why"]), 2)
        self.assertTrue(any(w.startswith("Ouverte : ") for w in words["why"]))
        self.assertTrue(any(w.startswith("Fermée : ") for w in words["why"]))
        self.assertTrue(all("," in w.split(" °C")[0] for w in words["why"]))

    def test_stale_air_says_how_long_and_what_it_brings(self):
        decision = decide(TWINS, Now(air=21.5, walls=21.5, opened=(), humidity=55.0, co2=1600.0), day(outdoor=17.0))
        words = phrase(decision, end_hour=17)
        self.assertRegex(words["title"], r"^(Aérez \d+ min|Ouvrez)$")
        self.assertEqual(words["subject"], "co2")

    def test_nothing_to_do_says_so_and_the_conditional_when_unsure(self):
        decision = decide(TWINS, Now(air=21.5, walls=21.5, opened=(), humidity=50.0, co2=600.0), day(outdoor=21.0))
        self.assertEqual(phrase(decision, end_hour=17)["title"], "Rien à faire")
        unsure = decide(TWINS, Now(air=20.6, walls=20.6, opened=(FRENCH.size,), humidity=66.0, night=True), night())
        self.assertTrue(phrase(unsure, end_hour=7, sure=False)["line"].endswith(", sans doute"))

    def test_every_language_has_every_phrase(self):
        self.assertEqual(set(TEXTS["en"]), set(TEXTS["fr"]))
        self.assertEqual(set(TEXTS["de"]), set(TEXTS["fr"]))
        decision = decide(TWINS, Now(air=20.6, walls=20.6, opened=(FRENCH.size,), humidity=66.0, night=True), night())
        self.assertEqual(phrase(decision, 7, "en")["title"], "Close")
        self.assertEqual(phrase(decision, 7, "de")["title"], "Schließen")


if __name__ == "__main__":
    unittest.main()
