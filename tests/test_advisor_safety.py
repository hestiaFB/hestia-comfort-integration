"""The 3.0 advisor's safety rules: rain, rain soon, gusts, red vigilance and an empty house take « open » away."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.safety import forbidden, holidays


class SafetyTest(unittest.TestCase):
    def test_each_rule_and_its_reason(self):
        self.assertEqual(forbidden(rain_rate=1.2), (frozenset({"open"}), "rain"))
        self.assertEqual(forbidden(rain_in=10), (frozenset({"open"}), "rain_soon"))
        self.assertEqual(forbidden(gust=60.0), (frozenset({"open"}), "gusts"))
        self.assertEqual(forbidden(vigilance="rouge"), (frozenset({"open"}), "vigilance"))
        self.assertEqual(forbidden(alarm="armed_away"), (frozenset({"open"}), "away"))

    def test_what_is_calm_or_unknown_forbids_nothing(self):
        self.assertEqual(forbidden(rain_rate=0.0, gust=20.0, rain_in=120, vigilance="orange", alarm="disarmed"), (frozenset(), None))
        self.assertEqual(forbidden(), (frozenset(), None))

    def test_holidays_come_from_the_alarm(self):
        self.assertTrue(holidays("armed_vacation"))
        self.assertFalse(holidays("armed_night"))


if __name__ == "__main__":
    unittest.main()
