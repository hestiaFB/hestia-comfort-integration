"""The rooms' sensors checked (CAHIER-MOTEUR.md § 7.3): out of range, an impossible jump, frozen."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.checks import Checker
from advisor.words import doubt_text, doubtful_air

T = datetime(2026, 11, 1, 10, tzinfo=timezone.utc)
FIVE = timedelta(minutes=5)


class Checks(unittest.TestCase):
    def test_the_house_s_faults(self):
        checker = Checker()
        self.assertEqual(checker.check("sensor.co2", "co2", 0.0, T, T).reason, "range")
        self.assertEqual(checker.check("sensor.pm25", "particles", 999.0, T, T).reason, "range")
        self.assertTrue(checker.check("sensor.pm25", "particles", 0.0, T, T).ok)

    def test_a_glitch_is_left_aside_and_the_measure_comes_back(self):
        checker = Checker()
        self.assertTrue(checker.check("sensor.t", "temperature", 19.5, T, T).ok)
        self.assertEqual(checker.check("sensor.t", "temperature", 31.0, T, T + FIVE).reason, "jump")
        self.assertTrue(checker.check("sensor.t", "temperature", 19.6, T, T + 2 * FIVE).ok)

    def test_a_real_change_is_confirmed_by_the_next_reading(self):
        checker = Checker()
        checker.check("sensor.h", "humidity", 55.0, T, T)
        self.assertFalse(checker.check("sensor.h", "humidity", 90.0, T, T + FIVE).ok)
        self.assertTrue(checker.check("sensor.h", "humidity", 92.0, T, T + 2 * FIVE).ok)
        self.assertTrue(checker.check("sensor.h", "humidity", 88.0, T, T + 3 * FIVE).ok)

    def test_cooking_smoke_is_no_jump(self):
        checker = Checker()
        checker.check("sensor.pm25", "particles", 4.0, T, T)
        self.assertTrue(checker.check("sensor.pm25", "particles", 320.0, T, T + FIVE).ok)

    def test_frozen(self):
        checker = Checker()
        found = checker.check("sensor.t", "temperature", 19.5, T, T + timedelta(hours=13))
        self.assertEqual((found.reason, found.since), ("frozen", T))
        self.assertTrue(checker.check("sensor.t", "temperature", 19.5, T, T + timedelta(hours=11)).ok)
        # Clean air may stay at 0 µg/m³ all day.
        self.assertTrue(checker.check("sensor.pm25", "particles", 0.0, T, T + timedelta(hours=20)).ok)

    def test_nothing_known_nothing_doubtful(self):
        self.assertTrue(Checker().check("sensor.t", "temperature", None, None, T).ok)


class Words(unittest.TestCase):
    def test_the_measures_left_aside(self):
        doubts = [{"mesure": "co2", "raison": "range", "valeur": 0.0, "depuis": None},
                  {"mesure": "particles", "raison": "range", "valeur": 999.0, "depuis": None}]
        self.assertEqual(doubt_text(doubts), "Mesure douteuse, laissée de côté : CO₂ (0 ppm : valeur impossible), "
                                             "particules (999 µg/m³ : valeur impossible)")

    def test_a_doubtful_temperature_gives_no_advice(self):
        found = doubtful_air({"mesure": "temperature", "raison": "frozen", "valeur": 19.5, "depuis": T.replace(hour=9, minute=40)})
        self.assertEqual(found, {"title": "Mesure douteuse",
                                 "line": "La température semble fausse (figée depuis 9 h 40) : pas de conseil tant qu'elle l'est"})
        self.assertIsNone(doubt_text([{"mesure": "temperature", "raison": "jump", "valeur": 31.0, "depuis": None}]))


if __name__ == "__main__":
    unittest.main()
