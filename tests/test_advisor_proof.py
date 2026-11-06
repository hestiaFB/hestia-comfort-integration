"""Three levels of proof (CAHIER-MOTEUR.md § 4.1) and « Bon à savoir »: the sun on the windows, a gesture seen to work."""
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.decide import Gesture, Now, decide
from advisor.knowing import RoomView, Window, gesture_seen, sun_on_windows, tips
from advisor.proof import PROVEN, REINFORCED, SUPPOSED, learned, level, live, window_reinforced
from advisor.words import phrase, tip_text
from test_advisor_decide import FRENCH, TWINS, day, night

PARIS = ZoneInfo("Europe/Paris")
HOME = (43.447, 5.470)


class Levels(unittest.TestCase):
    def test_learned_needs_three_gestures_right_on_direction_and_size(self):
        # The salon's 33 airings of October: −0.13 °C measured for −0.25 forecast, within a factor of two.
        self.assertTrue(learned([(-0.25, -0.13)] * 3))
        self.assertFalse(learned([(-0.25, -0.13)] * 2))
        self.assertFalse(learned([(-0.54, -0.18)] * 3))     # Chambre A: three times too strong
        self.assertFalse(learned([(-0.2, 0.2)] * 5))        # the wrong way

    def test_seen_now_needs_time_and_half_the_significant_gap(self):
        self.assertTrue(live(1.4, +1, 1.5, 120))
        self.assertFalse(live(1.4, +1, 1.5, 10))
        self.assertFalse(live(0.5, +1, 1.5, 120))
        self.assertFalse(live(-1.4, +1, 1.5, 120))

    def test_reinforced_by_the_measures_of_the_moment(self):
        self.assertTrue(window_reinforced("heat", 20.6, 12.8))
        self.assertFalse(window_reinforced("heat", 19.6, 18.6))
        self.assertTrue(window_reinforced("co2", 21.0, 20.0))
        self.assertEqual(level(reinforced=True), REINFORCED)
        self.assertEqual(level([(-0.25, -0.13)] * 3), PROVEN)
        self.assertEqual(level(), SUPPOSED)


class DecisionByProof(unittest.TestCase):
    NIGHT = Now(air=20.6, walls=20.6, opened=(FRENCH.size,), humidity=66.0, night=True)

    def test_a_proven_effect_is_advised_as_before(self):
        decision = decide(TWINS, self.NIGHT, night(), proof={"heat": PROVEN, "humidity": PROVEN})
        self.assertEqual((decision.gesture, decision.level), (Gesture("close"), PROVEN))

    def test_a_supposed_effect_stays_a_passive_advice_to_try(self):
        # An opening, a device, the heating: tried first. Shutting what is open never is (engine 3.9.4): held back, the
        # banner said « Rien à faire » and left the window open all night (Chambre M, 5 November at 21 h 02).
        decision = decide(TWINS, self.NIGHT, night(), proof={})
        self.assertEqual((decision.gesture, decision.level, decision.passive), (Gesture("close"), SUPPOSED, None))
        words = phrase(decision, end_hour=7)
        self.assertEqual(words["title"], "Refermez")
        # Never seen in this room: « pourrait », and « à vérifier ».
        self.assertRegex(words["line"], r"^vous pourriez garder \d+,\d °C d'ici 7 h, à vérifier$")

    def test_a_reinforced_effect_needs_a_clear_cut_gain_and_is_said_in_the_conditional(self):
        # 12.8 °C outside against 20.6 inside: the moment backs the window's effect on the heat, and closing keeps
        # about 3 °C — at night the gaps are already doubled, the reinforced level adds nothing.
        decision = decide(TWINS, self.NIGHT, night(), proof={"heat": REINFORCED, "humidity": REINFORCED})
        self.assertEqual((decision.gesture, decision.level), (Gesture("close"), REINFORCED))
        self.assertTrue(phrase(decision, end_hour=7)["line"].startswith("vous devriez garder "))
        # By day, 1.8 °C kept: shut whatever the proof, said in the conditional unless proven.
        mild = Now(air=20.2, walls=20.2, opened=(FRENCH.size,), humidity=55.0)
        proven = decide(TWINS, mild, day(outdoor=14.0), proof={"heat": PROVEN, "humidity": PROVEN})
        reinforced = decide(TWINS, mild, day(outdoor=14.0), proof={"heat": REINFORCED, "humidity": REINFORCED})
        self.assertEqual(proven.gesture, Gesture("close"))
        self.assertEqual((reinforced.gesture, reinforced.passive), (Gesture("close"), None))
        self.assertTrue(phrase(reinforced, end_hour=17)["line"].startswith("vous devriez garder "))
        self.assertTrue(phrase(proven, end_hour=17)["line"].startswith("vous gardez "))

class GoodToKnow(unittest.TestCase):
    NOW = datetime(2026, 10, 31, 11, 0, tzinfo=PARIS)

    def test_the_sun_on_the_west_window_of_chambre_p(self):
        view = RoomView(self.NOW, *HOME, windows=[Window("binary_sensor.fenetre_p_contact", 270)])
        [tip] = sun_on_windows(view)
        self.assertEqual(tip.level, SUPPOSED)
        self.assertEqual(tip_text(tip, now=self.NOW), "Soleil sur la fenêtre ouest de 13 h 15 à 17 h")
        self.assertEqual(tip_text(tip, "en", now=self.NOW), "Sun on the west window from 13:15 to 17:00")

    def test_a_strong_sun_forecast_reinforces_it_and_adaptive_cover_pro_knows_better(self):
        hours = {self.NOW.replace(hour=h): 420.0 for h in range(12, 17)}
        acp = (self.NOW.replace(hour=12, minute=50), self.NOW.replace(hour=16, minute=35))
        view = RoomView(self.NOW, *HOME, windows=[Window("binary_sensor.fenetre_p_contact", 270, acp)], sun_forecast=hours)
        [tip] = sun_on_windows(view)
        self.assertEqual(tip.level, REINFORCED)
        self.assertEqual(tip_text(tip, now=self.NOW), "Grand soleil prévu sur la fenêtre ouest de 12 h 50 à 16 h 35")
        later = self.NOW.replace(hour=15, minute=40)
        self.assertEqual(tip_text(tip, now=later), "Grand soleil sur la fenêtre ouest jusqu'à 16 h 35")

    def test_one_line_for_the_room_and_only_when_the_sun_counts(self):
        # Frank, 3 November: three windows, three sun lines; the sun is said once, and only when it warms the room.
        windows = [Window("binary_sensor.fenetre_c_contact", 90), Window("binary_sensor.porte_fenetre_sd_contact", 180),
                   Window("binary_sensor.fenetre_ouest_contact", 270)]
        morning = self.NOW.replace(hour=9)
        [tip] = sun_on_windows(RoomView(morning, *HOME, windows=windows, sun_gain=0.8))
        self.assertEqual(tip_text(tip, now=morning),
                         "Soleil sur les fenêtres est, sud et ouest jusqu'à 17 h : +0,8 °C dans la pièce")
        self.assertEqual(sun_on_windows(RoomView(morning, *HOME, windows=windows, sun_gain=0.3)), [])

    def test_same_facade_windows_are_said_once_and_the_past_sun_is_not_said(self):
        windows = [Window("binary_sensor.porte_fenetre_sd_contact", 180), Window("binary_sensor.porte_fenetre_sg_contact", 180),
                   Window("binary_sensor.fenetre_c_contact", 90)]
        found = sun_on_windows(RoomView(self.NOW.replace(hour=12), *HOME, windows=windows))
        self.assertEqual([tip_text(t, now=self.NOW.replace(hour=12)) for t in found], ["Soleil sur les fenêtres sud jusqu'à 17 h"])

    def test_chambre_p_warming_with_its_window_open_says_leave_it_open(self):
        # 31 October: opened at 13:52 at 18.3 °C, 19.7 °C two hours later, under a range from 20 °C.
        opened = self.NOW.replace(hour=13, minute=52)
        view = RoomView(opened + timedelta(hours=2), *HOME, air=19.7, opened_at=opened, air_at_opening=18.3)
        [tip] = gesture_seen(view)
        self.assertEqual(tip.level, PROVEN)
        self.assertEqual(tip_text(tip), "Laissez ouvert : la pièce a gagné 1,4 °C depuis 13 h 52")
        self.assertEqual(gesture_seen(replace(view, now=opened + timedelta(minutes=10))), [])
        self.assertEqual(gesture_seen(replace(view, air_at_opening=21.0, air=22.4)), [])  # already in its range

    def test_a_failing_provider_never_stops_the_others(self):
        def broken(view):
            raise ValueError
        view = RoomView(self.NOW, *HOME, windows=[Window("binary_sensor.fenetre_p_contact", 270)])
        self.assertEqual(len(tips(view, [broken, sun_on_windows])), 1)


if __name__ == "__main__":
    unittest.main()


class Mist(unittest.TestCase):
    def test_misted_panes_tonight(self):
        from advisor.knowing import mist_tonight
        evening = datetime(2026, 11, 20, 19, 0, tzinfo=PARIS)
        view = RoomView(evening, *HOME, air=19.0, humidity=70.0, coldest_tonight=1.0, bedtime=evening.replace(hour=22))
        [tip] = mist_tonight(view)
        self.assertEqual(tip_text(tip), "Buée probable sur les vitres cette nuit (1,0 °C dehors)")
        self.assertEqual(mist_tonight(replace(view, humidity=45.0)), [])
        self.assertEqual(mist_tonight(replace(view, now=evening.replace(hour=11))), [])


class OutsideWater(unittest.TestCase):
    def test_the_outside_air_said_in_water(self):
        # Chambre P, 3 November: 69 % at 18.1 °C inside, 78 % at 9.9 °C outside. In %, opening looks like raising the
        # humidity; in water, the outside air is the drier one (Frank: « sans explication je vais comparer »).
        from advisor.knowing import outside_water
        evening = datetime(2026, 11, 3, 19, 30, tzinfo=PARIS)
        view = RoomView(evening, *HOME, air=18.1, humidity=69.0, outdoor=9.9, outdoor_humidity=78.0, water_matters=True)
        [tip] = outside_water(view)
        self.assertEqual(tip_text(tip), "Dehors, l'air est plus sec qu'ici : aérer assèche")
        self.assertEqual(outside_water(replace(view, water_matters=False)), [])
        [wetter] = outside_water(replace(view, outdoor=18.0, outdoor_humidity=90.0))
        self.assertEqual(wetter.kind, "outside_wetter")
        [same] = outside_water(replace(view, outdoor=15.0, outdoor_humidity=80.0))
        self.assertEqual(same.kind, "outside_same")


class Belied(unittest.TestCase):
    def test_airings_that_did_not_dry_bring_the_effect_back_to_supposed(self):
        # Chambre P, 3 November: two airings forecast to take 2 g/m³ of water from the air; an hour on, 0.2 and +0.1.
        from advisor.proof import belied
        cases = [(-2.0, -0.2), (-2.1, 0.1)]
        self.assertTrue(belied(cases))
        self.assertEqual(level(cases, reinforced=True), SUPPOSED)
        # One airing is not enough to belie it; airings that did as forecast prove it.
        self.assertEqual(level(cases[:1], reinforced=True), REINFORCED)
        self.assertEqual(level([(-2.0, -1.8)] * 3, reinforced=True), PROVEN)
        # Seen working now, it is proven for this airing, whatever the past ones did.
        self.assertEqual(level(cases, reinforced=True, seen=True), PROVEN)


class UntrainedTwin(unittest.TestCase):
    def test_a_twin_never_fitted_backs_nothing(self):
        # Salon · Cuisine, 4-5 November: the VOC twin still as it started, its sensor without a history in the lab.
        from advisor.physics.airfit import TWINS as AIR_TWINS, first, untrained, values
        learned = {}
        for key, kind, _ in AIR_TWINS:
            learned[key], learned[f"{key}_flow"] = values(kind, first(kind), 110.0)
        self.assertEqual(untrained(learned), {"humidity", "co2", "particles", "voc"})
        learned["air"] = {**learned["air"], "sources": 0.01}
        self.assertNotIn("co2", untrained(learned))
        self.assertEqual(untrained({"heat": {}}), set())
