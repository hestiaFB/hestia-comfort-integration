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


class Dwelling(unittest.TestCase):
    """The dwelling (CAHIER-MOTEUR.md § 4): mould on the coldest corner, misted panes, frost, a long absence."""

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))

    def test_the_coldest_corner_and_the_pane(self):
        from advisor.physics.surface import dew_point, misted, mould_risk, surface
        self.assertAlmostEqual(surface(20.0, 0.0), 14.0)
        self.assertFalse(mould_risk(20.0, 55.0, 5.0))
        self.assertTrue(mould_risk(20.0, 75.0, 0.0))        # 75 % in the room is 100 % in a corner at 14 °C
        self.assertAlmostEqual(dew_point(20.0, 50.0), 9.3, delta=0.1)
        self.assertTrue(misted(19.0, 70.0, 2.0))

    def test_frost_takes_only_the_long_openings_away(self):
        from advisor.decide import Gesture, Now, decide
        from advisor.safety import forbidden
        from test_advisor_decide import TWINS, night
        taken, reason = forbidden(coldest=-2.0)
        self.assertEqual((taken, reason), (frozenset({"open_long"}), "frost"))
        decision = decide(TWINS, Now(air=21.0, walls=21.0, opened=(), co2=1800.0), night(outdoor=-2.0), forbidden=taken)
        self.assertNotIn(Gesture("open"), decision.scenarios)
        self.assertIn(Gesture("open", 10), decision.scenarios)

    def test_a_damp_room_on_a_cold_day_is_told_to_dry_for_its_walls(self):
        from dataclasses import replace
        from advisor.decide import Now, Thermostat, decide
        from test_advisor_decide import TWINS, day
        # 78 % in a bedroom its thermostat keeps at 20 °C, 3 °C outside: its coldest corner would stay at 80 % or more.
        heated = replace(TWINS, thermostat=Thermostat(20.0))
        decision = decide(heated, Now(air=19.5, walls=19.5, opened=(), humidity=78.0), day(outdoor=3.0))
        self.assertEqual(decision.gesture.kind, "open")
        self.assertGreater(decision.paths[decision.gesture.__class__("nothing")].mould, decision.paths[decision.gesture].mould)

    def test_away_for_days_only_the_dwelling_counts(self):
        from advisor.decide import Now, decide
        from test_advisor_decide import TWINS, night
        # 16 °C, the household away: comfortable enough for an empty house, nothing to do.
        decision = decide(TWINS, Now(air=16.0, walls=16.0, opened=(), humidity=55.0), night(outdoor=8.0), holidays=True)
        self.assertEqual(decision.gesture.kind, "nothing")
        self.assertEqual(decision.scenarios[decision.gesture]["heat"], 0.0)


class Units(unittest.TestCase):
    def test_rain_due_tomorrow_is_not_rain_soon(self):
        # 31 October, 19:37: Hestia Weather's « Pluie dans » at 18.4 h (1 103 minutes), read as 18.4 minutes until then.
        from advisor.safety import minutes
        self.assertAlmostEqual(minutes(18.4, "h"), 1104.0)
        self.assertEqual(forbidden(rain_in=minutes(18.4, "h")), (frozenset(), None))
        self.assertEqual(forbidden(rain_in=minutes(15, "min"))[1], "rain_soon")
        self.assertIsNone(minutes(18.4, "furlongs"))

    def test_a_green_vigilance_in_french(self):
        self.assertEqual(forbidden(vigilance="verte"), (frozenset(), None))
        self.assertEqual(forbidden(vigilance="rouge")[1], "vigilance")
