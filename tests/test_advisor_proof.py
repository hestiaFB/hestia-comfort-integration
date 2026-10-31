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
        decision = decide(TWINS, self.NIGHT, night(), proof={})
        self.assertEqual((decision.gesture, decision.rule, decision.passive), (Gesture("nothing"), "unproven", Gesture("close")))
        words = phrase(decision, end_hour=7)
        self.assertEqual(words["title"], "Rien à faire")
        self.assertTrue(words["try"].startswith("À essayer — Refermez : vous gardez"))
        self.assertTrue(words["try"].endswith(", sans doute"))

    def test_a_reinforced_effect_needs_a_clear_cut_gain_and_is_said_in_the_conditional(self):
        # 12.8 °C outside against 20.6 inside: the moment backs the window's effect on the heat, and closing keeps
        # about 3 °C — at night the gaps are already doubled, the reinforced level adds nothing.
        decision = decide(TWINS, self.NIGHT, night(), proof={"heat": REINFORCED, "humidity": REINFORCED})
        self.assertEqual((decision.gesture, decision.level), (Gesture("close"), REINFORCED))
        self.assertTrue(phrase(decision, end_hour=7)["line"].endswith(", sans doute"))
        # By day, 1.8 °C kept is significant for a proven effect, not clear-cut enough for a reinforced one.
        mild = Now(air=20.2, walls=20.2, opened=(FRENCH.size,), humidity=55.0)
        proven = decide(TWINS, mild, day(outdoor=14.0), proof={"heat": PROVEN, "humidity": PROVEN})
        reinforced = decide(TWINS, mild, day(outdoor=14.0), proof={"heat": REINFORCED, "humidity": REINFORCED})
        self.assertEqual(proven.gesture, Gesture("close"))
        self.assertEqual((reinforced.gesture, reinforced.passive), (Gesture("nothing"), Gesture("close")))


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
