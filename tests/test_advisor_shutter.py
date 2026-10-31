"""The connected shutter (CAHIER-MOTEUR.md § 6.7 ter): the sun it lets in by day, the heat it keeps in at night."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.decide import Gesture, Now, Twins, candidates, decide, effect, shutter_tonight, simulate
from advisor.feedback import done
from advisor.house import Opening, Room
from advisor.knowing import RoomView, shutter_at_night
from advisor.physics.thermal import Inputs, ordinary, shutter_insulation
from advisor.snapshot import capture, replay
from advisor.words import phrase, tip_text

WEST = Opening("binary_sensor.fenetre_p_contact", "window", area=1.1 * 1.21, height=1.21)
CHAMBRE_P = Room("chambre_p", "Chambre P", volume=12.0 * 2.5, openings=(WEST,), heating_power=1000)
TWINS = Twins(heat=ordinary(CHAMBRE_P), windows=(WEST.size,), shutter_area=WEST.area)
OPEN = Now(air=19.5, walls=19.0, opened=(), cover=1.0)


def night(outdoor=5.0, hours=9, start=22.0):
    return [(Inputs(outdoor, hour=(start + k / 12) % 24), None) for k in range(int(hours * 12))]


def sunny(outdoor=12.0, hours=5, start=12.0, shade=0.05, closed=1.0):
    """An autumn afternoon of strong sun, the shutter as it is now: five hours of it bring the room 1.5 °C, the gap a
    gesture needs (decide.SIGNIFICANT); three hours bring 1 °C, too little to be said."""
    return [(Inputs(outdoor, sun=500.0, hour=start + k / 12, shade=shade, shutter=shutter_insulation(WEST.area, closed)), None)
            for k in range(int(hours * 12))]


class Physics(unittest.TestCase):
    def test_the_norm_s_insulation(self):
        self.assertAlmostEqual(shutter_insulation(1.0, 1.0), 0.83, places=2)
        self.assertEqual(shutter_insulation(1.0, 0.0), 0.0)

    def test_a_night_shut_keeps_a_few_tenths(self):
        found = shutter_tonight(TWINS, OPEN, night(), 0)
        self.assertGreater(found["heat"], 0.05)
        self.assertLess(found["heat"], 0.6)

    def test_nothing_to_say_without_a_shutter_moved_by_hand_or_already_shut(self):
        self.assertIsNone(shutter_tonight(TWINS, replace(OPEN, cover=None), night(), 0))
        self.assertIsNone(shutter_tonight(TWINS, replace(OPEN, cover=0.0), night(), 0))
        self.assertIsNone(shutter_tonight(replace(TWINS, shutter_area=0.0), OPEN, night(), 0))


class Gestures(unittest.TestCase):
    def test_proposed_only_for_a_shutter_the_household_moves(self):
        kinds = {g.kind for g in candidates(OPEN, TWINS)}
        self.assertIn("shutter_close", kinds)
        self.assertNotIn("shutter_open", kinds)
        # Adaptive Cover Pro's automatic control drives it: nothing proposed on it.
        self.assertFalse({g.kind for g in candidates(replace(OPEN, cover=None), TWINS)} & {"shutter_close", "shutter_open"})

    def test_opening_lets_the_sun_in(self):
        shut = replace(OPEN, cover=0.0, air=18.0, walls=18.0)
        coming = sunny()
        opened = simulate(TWINS, shut, coming, Gesture("shutter_open"))
        idle = simulate(TWINS, shut, coming, Gesture("nothing"))
        self.assertGreater(opened.air[-1], idle.air[-1] + 0.3)

    def test_a_supposed_effect_is_only_to_try(self):
        shut = replace(OPEN, cover=0.0, air=17.0, walls=17.0)
        decision = decide(TWINS, shut, sunny(), proof={})
        self.assertEqual(decision.gesture, Gesture("nothing"))
        self.assertEqual(decision.passive, Gesture("shutter_open"))
        words = phrase(decision, 16)
        self.assertTrue(words["try"].startswith("À essayer — Ouvrez le volet"))
        self.assertEqual(effect(Gesture("shutter_open"), "energy"), "shutter:heat")

    def test_followed(self):
        self.assertTrue(done("shutter_close", replace(OPEN, cover=0.0)))
        self.assertFalse(done("shutter_close", OPEN))
        self.assertTrue(done("shutter_open", OPEN))

    def test_the_snapshot_replays_the_same_decision(self):
        shut = replace(OPEN, cover=0.0, air=17.0, walls=17.0)
        coming = sunny()
        decision = decide(TWINS, shut, coming, proof={})
        snap = capture(TWINS, shut, coming, proof={}, end_hour=16)
        self.assertEqual(replay(snap)[0].passive, decision.passive)


class Tonight(unittest.TestCase):
    NOW = datetime(2026, 11, 1, 21, tzinfo=timezone.utc)

    def view(self, found, minimum=20.0):
        return RoomView(now=self.NOW, latitude=43.45, longitude=5.46, minimum=minimum, bedtime=self.NOW + timedelta(hours=1),
                        shutter_night=found, wake=self.NOW + timedelta(hours=10))

    def test_said_in_the_evening_when_the_room_wakes_up_cold(self):
        tips = shutter_at_night(self.view({"heat": 0.25, "energy": 0.0, "wake": 17.8}))
        self.assertEqual(tip_text(tips[0]), "Baissez le volet ce soir : environ 0,2 °C de plus au réveil")

    def test_the_heating_saved_when_a_thermostat_keeps_the_room(self):
        tips = shutter_at_night(self.view({"heat": 0.0, "energy": 0.12, "wake": 19.0}))
        self.assertEqual(tip_text(tips[0]), "Baissez le volet ce soir : environ 0,1 kWh de chauffage en moins")

    def test_nothing_said_for_a_room_warm_enough_or_a_tiny_gain(self):
        self.assertEqual(shutter_at_night(self.view({"heat": 0.25, "energy": 0.0, "wake": 20.5})), [])
        self.assertEqual(shutter_at_night(self.view({"heat": 0.05, "energy": 0.0, "wake": 17.8})), [])
        self.assertEqual(shutter_at_night(self.view(None)), [])

    def test_not_once_asleep(self):
        view = replace(self.view({"heat": 0.25, "energy": 0.0, "wake": 17.8}), asleep=True)
        self.assertEqual(shutter_at_night(view), [])


if __name__ == "__main__":
    unittest.main()
