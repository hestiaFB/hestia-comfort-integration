"""The 3.0 advisor's safety rules: rain, rain soon, gusts and red vigilance take « open » away; an empty house only
proposes no opening."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.safety import forbidden, holidays, rained_on


class SafetyTest(unittest.TestCase):
    def test_each_rule_and_its_reason(self):
        self.assertEqual(forbidden(rain_rate=1.2), (frozenset({"open"}), "rain"))
        self.assertEqual(forbidden(rain_in=10), (frozenset({"open"}), "rain_soon"))
        self.assertEqual(forbidden(gust=60.0), (frozenset({"open"}), "gusts"))
        self.assertEqual(forbidden(vigilance="rouge"), (frozenset({"open"}), "vigilance"))
        # Nobody home: no opening proposed, but nothing open is shut (« absent », not « open »).
        self.assertEqual(forbidden(alarm="armed_away"), (frozenset({"absent"}), "away"))

    def test_the_alarm_never_shuts_a_window_open(self):
        # Chambre A, 7 November, 10 h 09 to 11 h 29: the alarm set to away, the window open, « Refermez » in red. Alarmo
        # leaves an open window out when arming: comfort does not stand in for the alarm.
        from advisor.decide import Now, decide
        from test_advisor_decide import FRENCH, TWINS, day
        taken, _ = forbidden(alarm="armed_away")
        opened = Now(air=19.0, walls=19.0, opened=(FRENCH.size,), humidity=62.0)
        decision = decide(TWINS, opened, day(outdoor=12.0), forbidden=taken)
        self.assertNotEqual(decision.rule, "safety")
        # And no window to open while away.
        shut = decide(TWINS, Now(air=19.0, walls=19.0, opened=(), humidity=85.0), day(outdoor=8.0), forbidden=taken)
        self.assertNotIn(shut.gesture.kind, ("open", "open_more"))

    def test_what_is_calm_or_unknown_forbids_nothing(self):
        self.assertEqual(forbidden(rain_rate=0.0, gust=20.0, rain_in=120, vigilance="orange", alarm="disarmed"), (frozenset(), None))
        self.assertEqual(forbidden(), (frozenset(), None))

    def test_the_rain_spares_what_is_sheltered(self):
        # Every opening under an overhang: the rain takes nothing away, the gusts still do.
        self.assertEqual(forbidden(rain_rate=1.2, shelter="all"), (frozenset(), None))
        self.assertEqual(forbidden(rain_in=10, gust=60.0, shelter="all"), (frozenset({"open"}), "gusts"))
        # The sheltered French window open stays so; the exposed window may not be opened as well.
        self.assertEqual(forbidden(rain_rate=1.2, shelter="opened"), (frozenset({"open_more"}), "rain"))

    def test_a_gust_pushes_the_rain_under_the_overhang(self):
        self.assertTrue(rained_on(False, 180.0, None, None))
        self.assertFalse(rained_on(True, 180.0, 15.0, 180.0))
        self.assertTrue(rained_on(True, 180.0, 30.0, 200.0))      # a south wind on a south French window
        self.assertFalse(rained_on(True, 180.0, 30.0, 0.0))       # a north wind on its back
        self.assertTrue(rained_on(True, None, 30.0, 0.0))         # the side it faces not known

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


class RainGaugeFirst(unittest.TestCase):
    """Frank, 9 November: « il faut être au conditionnel et plus se baser sur le pluviomètre quand il y est »."""

    def test_with_a_gauge_the_forecast_never_shuts(self):
        # Light rain two minutes away, a gauge at zero: nothing forbidden, the card says it in the conditional.
        self.assertEqual(forbidden(0.0, rain_in=2, intensity=1), (frozenset(), None))
        # Likely (moderate rain on the radar, or 60 % and more): no new airing, nothing shut.
        self.assertEqual(forbidden(0.0, rain_in=2, intensity=2), (frozenset({"rain_likely"}), "rain_maybe"))
        self.assertEqual(forbidden(0.0, rain_in=2, chance=70), (frozenset({"rain_likely"}), "rain_maybe"))
        # The gauge measuring the rain shuts at once.
        self.assertEqual(forbidden(1.2, rain_in=0, intensity=1), (frozenset({"open"}), "rain"))
        # A gauge under a tree or an overhang does not count as one.
        self.assertEqual(forbidden(0.0, rain_in=2, gauge=False)[1], "rain_soon")

    def test_without_a_gauge_the_chance_decides(self):
        self.assertEqual(forbidden(rain_in=2), (frozenset({"open"}), "rain_soon"))
        self.assertEqual(forbidden(rain_in=2, chance=30), (frozenset(), None))
        self.assertEqual(forbidden(rain_in=2, chance=70)[1], "rain_soon")

    def test_likely_rain_holds_back_an_airing_but_shuts_nothing(self):
        from advisor.decide import Gesture, Now, decide
        from test_advisor_decide import TWINS, day
        stuffy = Now(air=21.5, walls=21.5, opened=(), humidity=55.0, co2=1600.0)
        found = decide(TWINS, stuffy, day(outdoor=17.0), forbidden=frozenset({"rain_likely"}))
        self.assertNotIn(found.gesture.kind, ("open", "open_more"))
        opened = Now(air=21.5, walls=21.5, opened=((1.0, 1.2),), humidity=55.0, co2=1600.0)
        self.assertNotEqual(decide(TWINS, opened, day(outdoor=17.0), forbidden=frozenset({"rain_likely"})).rule, "safety")


class RainThatDoesNotCome(unittest.TestCase):
    """5 November: « la pluie arrive » from 20 h 16, the first drops at the station at 21 h 49."""

    def test_believed_10_minutes_without_a_drop(self):
        # 9 November: the radar stuck at « dans 2 min » for 10 to 50 minutes, no drop.
        from advisor.safety import rain_believed
        rain_in, since = rain_believed(18, 0.0, None, 0)
        self.assertEqual((rain_in, since), (18, 0))
        self.assertEqual(rain_believed(6, 0.0, since, 9 * 60), (6, 0))
        self.assertEqual(rain_believed(6, 0.0, since, 11 * 60), (None, 0))
        # The radar moving a little further keeps the wait; far away or the rain falling ends it.
        self.assertEqual(rain_believed(36, 0.0, since, 50 * 60), (36, 0))
        self.assertEqual(rain_believed(90, 0.0, since, 50 * 60), (90, None))
        self.assertEqual(rain_believed(0, 1.8, since, 50 * 60), (0, None))

    def test_once_said_it_holds_while_the_forecast_stays_close(self):
        # 6 November, Chambre A and Salon: « la pluie arrive » came and went every 5 to 20 minutes, the forecast hovering
        # around 20 minutes. Once said, it holds within 40 minutes; further, or after the wait, it goes.
        from advisor.safety import RAIN_SOON, forbidden, rain_believed
        rain_in, since = rain_believed(18, 0.0, None, 0)
        held, kept = rain_believed(25, 0.0, since, 5 * 60)
        self.assertEqual((held, kept), (RAIN_SOON, 0))
        self.assertEqual(forbidden(0.0, rain_in=held, intensity=2)[1], "rain_maybe")
        self.assertEqual(rain_believed(45, 0.0, since, 5 * 60), (45, 0))
        self.assertEqual(rain_believed(25, 0.0, since, 11 * 60), (25, 0))
        # Never said: 25 minutes away is not « soon ».
        self.assertEqual(rain_believed(25, 0.0, None, 0), (25, None))

    def test_always_believed_without_a_rain_gauge(self):
        from advisor.safety import rain_believed
        self.assertEqual(rain_believed(6, None, 0, 3 * 3600), (6, None))
