"""The 3.0 advisor's words: a title, a gain in plain units, « Pourquoi ? », the same in three languages."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.decide import Now, decide
from advisor.words import TEXTS, measured_out, phrase
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
        self.assertEqual(phrase(decision, end_hour=17, reason="rain_soon")["line"], "la pluie pourrait arriver")
        # A shut room under the same rain: nothing to do, because the rain takes the openings away.
        shut = decide(TWINS, Now(air=19.8, walls=19.8, opened=(), humidity=59.0, co2=613.0), day(outdoor=13.0),
                      forbidden=frozenset({"open"}))
        self.assertEqual(phrase(shut, end_hour=21, reason="rain_soon")["line"], "Gardez fermé : la pluie pourrait arriver")

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


class MeasuredPill(unittest.TestCase):
    """« Au mieux » or « Tout va bien » on the measures now, with a margin at each bound (9 November)."""
    MARKS = {"minimum": 20.0, "maximum": 25.0, "humidity": 60.0, "co2": 1000.0, "particles": 15.0, "voc": 150.0}

    def room(self, **values):
        return Now(**{"air": 21.0, "walls": 21.0, "opened": (), "humidity": 50.0, **values})

    def test_out_in_and_the_margin(self):
        self.assertTrue(measured_out(self.room(humidity=80.0), self.MARKS))
        self.assertFalse(measured_out(self.room(), self.MARKS))
        self.assertTrue(measured_out(self.room(air=19.5), self.MARKS))
        self.assertTrue(measured_out(self.room(co2=1100.0), self.MARKS))
        # Within the margin of a bound, as said before.
        self.assertTrue(measured_out(self.room(humidity=59.0), self.MARKS, before=True))
        self.assertFalse(measured_out(self.room(humidity=59.0), self.MARKS, before=False))
        self.assertFalse(measured_out(self.room(humidity=57.0), self.MARKS, before=True))
        # A measure the room does not have counts for nothing.
        self.assertFalse(measured_out(self.room(humidity=None), self.MARKS))


class StaleAir(unittest.TestCase):
    """The CO₂ measured high: said as a fact (Salon · Cuisine, 8 November, 1 519 ppm)."""

    def test_said_as_measured(self):
        now = Now(air=21.5, walls=21.5, opened=(), humidity=55.0, co2=1519.0)
        d = decide(TWINS, now, day(outdoor=17.0), proof={})
        self.assertEqual(d.rule, "stale")
        words = phrase(d, 18)
        self.assertEqual(words["title"], "Aérez 10 min")
        self.assertEqual(words["line"], "CO₂ mesuré à 1519 ppm : l'air est à renouveler")
        self.assertEqual(words["subject"], "co2")


class EdgeOfTheRange(unittest.TestCase):
    def test_near_a_bound_the_last_word_holds(self):
        # 7 November, every room, all night: « Au mieux » and « Tout va bien » took turns every half hour, the forecast at
        # 18,6 °C for a range from 18,5 °C. Within EDGE of a bound, what was said last is kept.
        from advisor.words import EDGE, _outside
        self.assertTrue(_outside(18.0, 18.5, 22.0, EDGE["heat"], None))
        self.assertFalse(_outside(19.0, 18.5, 22.0, EDGE["heat"], True))
        self.assertTrue(_outside(18.6, 18.5, 22.0, EDGE["heat"], True))
        self.assertFalse(_outside(18.4, 18.5, 22.0, EDGE["heat"], False))
        # Nothing said before: the plain bound.
        self.assertTrue(_outside(18.4, 18.5, 22.0, EDGE["heat"], None))
        self.assertFalse(_outside(18.6, 18.5, 22.0, EDGE["heat"], None))


class BackAlone(unittest.TestCase):
    """8 November, Salon · Cuisine: « La pièce restera dans votre plage » at 1 118 ppm of CO₂, then at a VOC of 441 while
    cooking — the forecast back under the marks by 13 h, the room above them now."""

    def _nothing(self, **series):
        from advisor.decide import Decision, Gesture, Path as Scenario
        idle = Scenario(air=[21.0] * 36, **series)
        return Decision(Gesture("nothing"), 0.0, "nothing", {Gesture("nothing"): {"total": 0.0}}, {Gesture("nothing"): idle})

    def test_a_measure_above_its_mark_now_says_it_comes_back_alone(self):
        decision = self._nothing(co2=[1090.0, 1060.0, 1020.0, 990.0] + [900.0] * 32)
        words = phrase(decision, end_hour=13, hour=10 + 40 / 60, marks={"minimum": 20.0, "maximum": 24.0})
        self.assertEqual(words["line"], "Le CO₂ repasse seul sous 1000 ppm vers 11 h : aucun geste ne ferait vraiment mieux")
        self.assertTrue(words["beyond"])
        self.assertIn("within 20 min", phrase(decision, 13, "en", marks={"minimum": 20.0, "maximum": 24.0})["line"])

    def test_under_its_mark_now_the_range_is_said(self):
        decision = self._nothing(co2=[1020.0] + [900.0] * 35)
        words = phrase(decision, end_hour=13, hour=10.5, marks={"minimum": 20.0, "maximum": 24.0})
        self.assertEqual(words["line"], "La pièce restera dans votre plage")
        self.assertFalse(words["beyond"])

    def test_au_mieux_kept_says_no_gesture_would_do_better(self):
        # « Au mieux » kept a while (room/advice.py CALM_MINUTES): its line stays true, as the card's pill reads it.
        decision = self._nothing(co2=[700.0] * 36)
        words = phrase(decision, end_hour=13, marks={"minimum": 20.0, "maximum": 24.0}, beyond_before=True, keep_beyond=True)
        self.assertEqual(words["line"], "Aucun geste ne ferait vraiment mieux : 21,0 °C à 13 h")
        self.assertTrue(words["beyond"])
