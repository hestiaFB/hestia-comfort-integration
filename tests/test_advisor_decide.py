"""The 3.0 advisor's decision: the night of 30 October says « close », and a tenth of a degree never turns the advice."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.decide import GAIN, Comfort, Gesture, Now, Thermostat, Twins, decide, significant, simulate
from advisor.house import Opening, Room
from advisor.physics.air import AirParams, BREATH
from advisor.physics.thermal import Inputs, ordinary
from advisor.physics.water import WaterParams, absolute

FRENCH = Opening("binary_sensor.porte_fenetre_sg_contact", "french", area=1.18 * 2.10, height=2.10)
WEST = Opening("binary_sensor.fenetre_ouest_contact", "window", area=1.18 * 1.21, height=1.21)
SALON = Room("salon", "Salon", volume=44.03 * 2.5, openings=(FRENCH, WEST), heating_power=3000)
TWINS = Twins(heat=replace(ordinary(SALON), window=0.6), windows=(FRENCH.size, WEST.size),
              water=WaterParams(SALON.air, 0.5, 5.0, 30.0), water_flow=(0.9, 0.4),
              air=AirParams(SALON.air, 2 * BREATH), air_flow=(0.8, 0.1))


def night(outdoor=12.8, hours=6, start=1.0):
    """The coming steps of a night without sun, the outdoor air at 88 %."""
    return [(Inputs(outdoor, hour=(start + k / 12) % 24), absolute(outdoor, 88.0)) for k in range(int(hours * 12))]


def day(outdoor=15.0, hours=3, start=14.0):
    return [(Inputs(outdoor, hour=start + k / 12), absolute(outdoor, 70.0)) for k in range(int(hours * 12))]


class NightOf30October(unittest.TestCase):
    def test_open_at_one_in_the_morning_with_12_8_outside_says_close(self):
        now = Now(air=20.6, walls=20.6, opened=(FRENCH.size,), humidity=66.0, night=True)
        decision = decide(TWINS, now, night())
        self.assertEqual(decision.gesture, Gesture("close"))
        self.assertGreater(decision.gain, GAIN)

    def test_with_its_thermostat_shut_stays_warm_and_open_costs_heating(self):
        heated = replace(TWINS, thermostat=Thermostat(target=19.0))
        now = Now(air=20.6, walls=20.6, opened=(FRENCH.size,), humidity=66.0, night=True)
        decision = decide(heated, now, night())
        self.assertEqual(decision.gesture, Gesture("close"))
        shut, open_ = decision.paths[Gesture("close")], decision.paths[Gesture("nothing")]
        self.assertGreater(shut.air[-1], 18.8)
        self.assertLess(open_.air[-1], shut.air[-1])
        # The thermostat stops while the window is open: the cold room is the price, not the heating.
        self.assertEqual(open_.heating, 0.0)

    def test_a_tenth_of_a_degree_never_turns_the_advice(self):
        # The 2.1 engine said « Refermez » at 21.0 °C, « cela ne change rien » at 21.1 and « Laissez ouvert » at 21.5.
        for air in (20.9, 21.0, 21.1, 21.2, 21.5):
            now = Now(air=air, walls=air, opened=(FRENCH.size,), humidity=66.0, night=True)
            self.assertEqual(decide(TWINS, now, night()).gesture, Gesture("close"), air)


class Gestures(unittest.TestCase):
    def test_nothing_to_do_in_a_comfortable_shut_room(self):
        now = Now(air=21.5, walls=21.5, opened=(), humidity=50.0, co2=600.0)
        decision = decide(TWINS, now, day(outdoor=21.0))
        self.assertEqual(decision.gesture, Gesture("nothing"))

    def test_stale_air_on_a_mild_afternoon_asks_for_an_airing(self):
        now = Now(air=21.5, walls=21.5, opened=(), humidity=55.0, co2=1600.0)
        decision = decide(TWINS, now, day(outdoor=17.0))
        self.assertEqual(decision.gesture.kind, "open")

    def test_the_rain_shuts_what_is_open_and_never_opens(self):
        opened = Now(air=21.0, walls=21.0, opened=(FRENCH.size,), humidity=55.0)
        self.assertEqual(decide(TWINS, opened, day(), forbidden=frozenset({"open"})).rule, "safety")
        stale = Now(air=21.5, walls=21.5, opened=(), co2=1600.0)
        self.assertNotEqual(decide(TWINS, stale, day(outdoor=17.0), forbidden=frozenset({"open"})).gesture.kind, "open")

    def test_a_colder_outside_never_makes_opening_better_for_a_cool_room(self):
        now = Now(air=19.0, walls=19.0, opened=())
        gains = []
        for outdoor in (16.0, 12.0, 8.0, 4.0):
            costs = decide(TWINS, now, day(outdoor=outdoor)).scenarios
            gains.append(costs[Gesture("nothing")]["total"] - costs[Gesture("open")]["total"])
        self.assertEqual(gains, sorted(gains, reverse=True))

    def test_a_gesture_that_changes_almost_nothing_is_not_advised(self):
        # The 2.1 engine said « Aérez » to warm a room at 18.2 °C with 20 °C outside: a few tenths of a degree.
        now = Now(air=18.2, walls=18.2, opened=(), humidity=65.0)
        decision = decide(TWINS, now, day(outdoor=20.1))
        self.assertEqual(decision.gesture, Gesture("nothing"))

    def test_a_later_gesture_is_said_with_its_hour(self):
        from advisor.words import phrase
        decision = decide(TWINS, Now(air=21.5, walls=21.5, opened=(), humidity=55.0, co2=1600.0), day(outdoor=17.0))
        later = replace(decision, gesture=Gesture("open", 10, after=60))
        self.assertEqual(phrase(later, 17, hour=14.0)["title"], "Aérez 10 min vers 15 h")
        self.assertEqual(phrase(replace(decision, gesture=Gesture("close", after=120)), 17, hour=14.0)["title"], "Refermez vers 16 h")
        self.assertEqual(phrase(replace(decision, gesture=Gesture("close", after=10)), 17, hour=14.0)["title"],
                         "Laissez ouvert encore 10 min")
        self.assertEqual(phrase(replace(decision, gesture=Gesture("open", 5, after=75)), 17, hour=14.0)["title"],
                         "Aérez 5 min vers 15 h 15")

    def test_an_advice_shown_stays_unless_another_clearly_beats_it(self):
        now = Now(air=21.5, walls=21.5, opened=(), humidity=55.0, co2=1600.0)
        first = decide(TWINS, now, day(outdoor=17.0))
        again = decide(TWINS, replace(now, co2=1590.0), day(outdoor=17.0), previous=first.gesture)
        self.assertEqual(again.gesture, first.gesture)


class Steady(unittest.TestCase):
    """At most one change per half hour (CAHIER-MOTEUR.md § 18.3): 2 November, « Aérez 30 → 20 → 25 min » in twelve
    minutes, and Chambre P between « Lancez la VMC » and « Rien à faire » four times in an hour."""

    def setUp(self):
        self.now = Now(air=21.5, walls=21.5, opened=(), humidity=55.0, co2=1600.0)
        self.coming = day(outdoor=17.0)
        self.first = decide(TWINS, self.now, self.coming)

    def test_a_duration_shown_stays_while_about_as_good(self):
        # « Ouvrez » is the best; « Aérez 30 min », shown before and about as good, stays.
        self.assertEqual(self.first.gesture.kind, "open")
        other = Gesture("open", 30)
        again = decide(TWINS, self.now, self.coming, previous=other)
        self.assertEqual(again.gesture, other)

    def test_a_gesture_shown_is_held_half_an_hour_while_it_still_helps(self):
        shown = self.first.gesture
        demoted = decide(TWINS, self.now, self.coming, proof={}, previous=shown, held=10.0)
        self.assertEqual((demoted.gesture, demoted.rule), (shown, "kept"))
        later = decide(TWINS, self.now, self.coming, proof={}, previous=shown, held=40.0)
        self.assertEqual(later.rule, "unproven")


if __name__ == "__main__":
    unittest.main()


class SunAndHeating(unittest.TestCase):
    def test_an_open_sash_lets_in_more_sun_than_its_glass(self):
        # 31 October, Chambre P at 15:40: the sun came straight in through the open window.
        now = Now(air=20.0, walls=20.0, opened=())
        glass = [(replace(u, facade=300.0, facade_shut=300.0), w) for u, w in day(outdoor=18.0)]
        sash = [(replace(u, facade_all=500.0), w) for u, w in glass]
        opened, through_glass = (simulate(TWINS, now, coming, Gesture("open")).air[-1] for coming in (sash, glass))
        self.assertGreater(opened, through_glass)
        shut = simulate(TWINS, now, sash, Gesture("nothing")).air[-1]
        self.assertEqual(shut, simulate(TWINS, now, glass, Gesture("nothing")).air[-1])

    def test_heat_let_out_of_a_room_the_heating_would_not_warm_is_no_saving(self):
        # The test Home Assistant said « Refermez » for heat a window let out of a warm bedroom whose thermostat was idle.
        heated = replace(TWINS, thermostat=Thermostat(target=17.0))
        now = Now(air=22.5, walls=22.5, opened=(FRENCH.size, WEST.size))
        coming = day(outdoor=16.0)
        idle, shut = (simulate(heated, now, coming, Gesture(g)) for g in ("nothing", "close"))
        self.assertGreater(idle.lost - shut.lost, 0.5)
        self.assertNotIn("energy", significant(idle, shut, Comfort(minimum=17.0)))

    def test_the_trend_the_twin_missed_carries_into_every_scenario_and_fades(self):
        # The bedroom gained a degree the twin did not see: every scenario starts from it, and it fades within hours.
        now = Now(air=20.0, walls=20.0, opened=(WEST.size,))
        coming = day(outdoor=18.0)
        for g in (Gesture("nothing"), Gesture("close")):
            plain, warmer = (simulate(TWINS, replace(now, missed=m), coming, g) for m in (None, 1.0))
            self.assertAlmostEqual(warmer.air[0] - plain.air[0], 1.0, places=6)
            self.assertLess(warmer.air[-1] - plain.air[-1], 0.5)


class Ranges(unittest.TestCase):
    def test_the_range_set_in_confort_and_its_season(self):
        from advisor.decide import Comfort, for_season
        # Chambre P: 18 to 24 °C in Confort, 26 °C in summer.
        self.assertEqual(for_season(18, 24, 26), Comfort(18, 24))
        self.assertEqual(for_season(18, 24, 26, "autumn"), Comfort(18, 25))
        self.assertEqual(for_season(18, 24, 26, "summer", humidity=65.0), Comfort(18, 26, humidity=65.0))

    def test_a_bedroom_at_19_is_in_its_range_from_18(self):
        from advisor.decide import Comfort
        from advisor.words import phrase
        decision = decide(TWINS, Now(air=19.3, walls=19.3, opened=(), humidity=50.0), day(outdoor=18.0), comfort=Comfort(18, 24))
        self.assertEqual(phrase(decision, 17, marks={"minimum": 18, "maximum": 24})["line"], "La pièce restera dans votre plage")


class Tonight(unittest.TestCase):
    def test_in_the_evening_remember_to_close_before_sleeping(self):
        from advisor.decide import tonight
        from advisor.proof import PROVEN
        from advisor.words import tonight_text
        # 20:00, the French window open, 12.8 °C outside all night: bedtime in two hours, waking at 7.
        now = Now(air=20.6, walls=20.6, opened=(FRENCH.size,), humidity=60.0)
        found = tonight(TWINS, now, night(start=20.0, hours=11), 120, proof={"heat": PROVEN, "humidity": PROVEN})
        self.assertEqual(found.gesture, Gesture("close", after=120))
        self.assertRegex(tonight_text(found, 7), r"^Cette nuit, pensez à refermer : vous gardez \d+,\d °C d'ici 7 h$")

    def test_nothing_to_say_on_a_mild_night(self):
        from advisor.decide import tonight
        now = Now(air=21.0, walls=21.0, opened=(), humidity=50.0)
        self.assertIsNone(tonight(TWINS, now, night(outdoor=19.0, start=20.0, hours=11), 120))


class Sleeping(unittest.TestCase):
    def test_no_window_is_opened_at_night_whatever_the_air(self):
        # 3 a.m., stale and damp air: nobody gets up to air in the middle of the night, nor to start the VMC's fast speed
        # (Frank, 2 November: « Lancez la VMC rapide » was asked all night long in Chambre P).
        now = Now(air=20.0, walls=20.0, opened=(), humidity=75.0, co2=1800.0, night=True)
        decision = decide(replace(TWINS, boost=60.0), now, night(start=3.0, hours=4))
        self.assertFalse(any(g.kind == "open" for g in decision.scenarios))
        self.assertFalse(any(g.kind == "boost" for g in decision.scenarios))
        # A window left open is still to be closed.
        left = decide(TWINS, replace(now, opened=(FRENCH.size,)), night(start=3.0, hours=4))
        self.assertEqual(left.gesture, Gesture("close"))
