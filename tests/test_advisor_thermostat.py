"""The thermostat's set point as the room's minimum, and the heating bringing the room back (CAHIER-MOTEUR.md § 6.8)."""
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from dataclasses import replace

from advisor.decide import (Comfort, Gesture, Now, Thermostat, Twins, candidates, decide, from_thermostat, heating_back,
                            heating_off, simulate, stove_idle)
from advisor.feedback import done
from advisor.house import Opening, Room
from advisor.household import Habits
from advisor.knowing import RoomView, heating_catches_up, heating_is_off, stove_at_its_lowest
from advisor.physics.thermal import Inputs, ordinary
from advisor.proof import PROVEN
from advisor.snapshot import capture, replay
from advisor.words import phrase, tip_text

RANGE = Comfort(minimum=18.0, maximum=24.0)
WEST = Opening("binary_sensor.fenetre_p_contact", "window", area=1.33, height=0.95)
CHAMBRE_P = Room("chambre_p", "Chambre P", volume=12.0 * 2.5, openings=(WEST,), heating_power=1500)


class Range(unittest.TestCase):
    def test_eco_lowers_the_minimum_on_purpose(self):
        self.assertEqual(from_thermostat(RANGE, 17.0, "eco", 20.0).minimum, 17.0)

    def test_frost_protection_is_a_safeguard_the_comfort_temperature_stands(self):
        self.assertEqual(from_thermostat(RANGE, 7.0, "frost", 20.0).minimum, 20.0)

    def test_a_set_point_out_of_bounds_keeps_the_room_s_own(self):
        self.assertEqual(from_thermostat(RANGE, 25.0, "boost", 20.0).minimum, 18.0)
        self.assertEqual(from_thermostat(RANGE, None, None, None).minimum, 18.0)


class Back(unittest.TestCase):
    def setUp(self):
        self.twins = Twins(heat=ordinary(CHAMBRE_P), windows=(WEST.size,), thermostat=Thermostat(target=17.0, inside=0.8))
        self.coming = [(Inputs(11.8, hour=11 + k / 12), None) for k in range(36)]

    def test_the_heating_brings_the_room_back(self):
        now = Now(air=16.4, walls=16.0, opened=())
        found = heating_back(self.twins, simulate(self.twins, now, self.coming, Gesture("nothing")), now, 17.0)
        self.assertLess(found["minutes"], 180)

    def test_a_house_heater_short_of_the_range_says_where_the_room_will_be(self):
        # The Salon's stove: no thermostat of the room's own, a share of the house heater, a range out of reach by 3 h.
        twins = Twins(heat=replace(ordinary(CHAMBRE_P), share=0.05), windows=(WEST.size,))
        stove = [(replace(u, house_heat=8500.0), w) for u, w in self.coming]
        now = Now(air=18.5, walls=18.0, opened=())
        found = heating_back(twins, simulate(twins, now, stove, Gesture("nothing")), now, 22.0, stove)
        self.assertGreater(found["air"], 19.0)
        view = RoomView(now=datetime(2026, 11, 1, 12, 40, tzinfo=timezone.utc), latitude=43.45, longitude=5.46, minimum=21.5,
                        heating_back={"air": 19.7}, end_hour=15)
        self.assertEqual(tip_text(heating_catches_up(view)[0]),
                         "Le chauffage réchauffe la pièce : 19,7 °C prévus à 15 h (21,5 °C visés)")

    def test_nothing_to_say_in_range_or_without_a_thermostat(self):
        warm = Now(air=17.5, walls=17.0, opened=())
        self.assertIsNone(heating_back(self.twins, simulate(self.twins, warm, self.coming, Gesture("nothing")), warm, 17.0))
        cold = Now(air=16.4, walls=16.0, opened=())
        bare = Twins(heat=ordinary(CHAMBRE_P), windows=(WEST.size,))
        self.assertIsNone(heating_back(bare, simulate(bare, cold, self.coming, Gesture("nothing")), cold, 17.0))

    def test_said_in_good_to_know(self):
        view = RoomView(now=datetime(2026, 11, 1, 11, 2, tzinfo=timezone.utc), latitude=43.45, longitude=5.46, minimum=17.0,
                        heating_back={"minutes": 88.0})
        self.assertEqual(tip_text(heating_catches_up(view)[0]), "Le chauffage ramène la pièce à 17 °C vers 12 h 30")
        self.assertEqual(heating_catches_up(RoomView(now=view.now, latitude=43.45, longitude=5.46)), [])


class Gestures(unittest.TestCase):
    """« Rallumez le chauffage », « Remettez le chauffage à 20 °C » (CAHIER-MOTEUR.md § 9.1 bis)."""

    def setUp(self):
        self.heat = ordinary(CHAMBRE_P)
        # A cold autumn morning, three hours ahead.
        self.coming = [(Inputs(5.0, hour=9 + k / 12), None) for k in range(36)]
        self.cold = Now(air=15.5, walls=15.0, opened=())

    def test_turned_off_and_under_its_set_point_is_only_a_passive_advice(self):
        twins = Twins(heat=self.heat, windows=(WEST.size,), idle_thermostat=Thermostat(target=17.0, inside=0.8))
        decision = decide(twins, self.cold, self.coming, Comfort(minimum=17.0), proof={"heating:heat": PROVEN})
        self.assertNotIn(Gesture("heat_on"), decision.scenarios)
        self.assertGreater(heating_off(twins, self.cold, self.coming, Comfort(minimum=17.0)), 1.0)
        view = RoomView(now=datetime(2026, 11, 1, 9, tzinfo=timezone.utc), latitude=43.45, longitude=5.46, heating_off=1.5,
                        end_hour=12)
        self.assertEqual(tip_text(heating_is_off(view)[0]), "Chauffage éteint : le rallumer donnerait 1,5 °C de plus d'ici 12 h")

    def test_quiet_while_a_house_heater_warms_the_room(self):
        twins = Twins(heat=replace(self.heat, share=0.3), windows=(WEST.size,), idle_thermostat=Thermostat(target=17.0, inside=0.8))
        stove = [(replace(u, house_heat=8500.0), w) for u, w in self.coming]
        self.assertIsNone(heating_off(twins, self.cold, stove, Comfort(minimum=17.0)))

    def test_never_at_night(self):
        twins = Twins(heat=self.heat, windows=(WEST.size,), idle_thermostat=Thermostat(target=17.0, inside=0.8))
        self.assertIsNone(heating_off(twins, replace(self.cold, night=True), self.coming, Comfort(minimum=17.0)))

    def test_frost_protection_under_the_range_says_set_it_back(self):
        twins = Twins(heat=self.heat, windows=(WEST.size,), thermostat=Thermostat(target=7.0, inside=0.8))
        decision = decide(twins, self.cold, self.coming, Comfort(minimum=20.0), proof={"heating:heat": PROVEN})
        self.assertEqual(decision.gesture, Gesture("heat_to", target=20.0))
        self.assertEqual(phrase(decision, 12)["title"], "Remettez le chauffage à 20 °C")

    def test_nothing_when_the_thermostat_already_aims_at_the_range(self):
        twins = Twins(heat=self.heat, windows=(WEST.size,), thermostat=Thermostat(target=17.0, inside=0.8))
        self.assertFalse({g.kind for g in candidates(self.cold, twins, comfort=Comfort(minimum=17.0))} & {"heat_on", "heat_to"})

    def test_followed(self):
        self.assertTrue(done("heat_on", Now(air=15.5, walls=15.0, opened=(), heating=True)))
        self.assertFalse(done("heat_on", Now(air=15.5, walls=15.0, opened=(), heating=False)))
        self.assertTrue(done("heat_to", Now(air=15.5, walls=15.0, opened=(), heating=True, heating_target=20.0), 20.0))
        self.assertFalse(done("heat_to", Now(air=15.5, walls=15.0, opened=(), heating=True, heating_target=7.0), 20.0))

    def test_the_snapshot_replays_it(self):
        twins = Twins(heat=self.heat, windows=(WEST.size,), thermostat=Thermostat(target=7.0, inside=0.8),
                      idle_thermostat=Thermostat(target=17.0, inside=0.8))
        comfort = Comfort(minimum=20.0)
        snap = capture(twins, self.cold, self.coming, comfort, proof={"heating:heat": PROVEN}, end_hour=12)
        self.assertEqual(replay(snap)[0].gesture, Gesture("heat_to", target=20.0))


class Stove(unittest.TestCase):
    """The Salon's stove, its main heating: simulated as its thermostat, not held at the power it had (1 November: the
    room at 22 °C, the stove paused at its set point, the advisor foresaw 19.4 °C at 16 h)."""

    def setUp(self):
        self.twins = Twins(heat=replace(ordinary(CHAMBRE_P), share=0.3), windows=(WEST.size,),
                           house_thermostat=Thermostat(target=21.5, inside=0.8), house_power=8500.0, house_now=0.0)
        self.coming = [(Inputs(8.0, hour=13 + k / 12), None) for k in range(36)]
        self.now = Now(air=22.0, walls=20.0, opened=())

    def test_the_stove_starts_again_when_the_room_cools(self):
        held = simulate(replace(self.twins, house_thermostat=None), self.now, self.coming, Gesture("nothing"))
        followed = simulate(self.twins, self.now, self.coming, Gesture("nothing"))
        self.assertGreater(followed.air[-1], held.air[-1] + 0.5)
        self.assertGreater(followed.air[-1], 20.5)

    def test_turning_the_buffer_on_is_never_said_while_the_stove_runs(self):
        twins = replace(self.twins, idle_thermostat=Thermostat(target=21.0, inside=0.8))
        self.assertIsNone(heating_off(twins, Now(air=19.0, walls=18.5, opened=()), self.coming, Comfort(minimum=21.5)))

    def test_the_snapshot_keeps_it(self):
        snap = capture(self.twins, self.now, self.coming, Comfort(minimum=21.5), end_hour=16)
        self.assertEqual(replay(snap)[0].paths[Gesture("nothing")].air[-1],
                         decide(self.twins, self.now, self.coming, Comfort(minimum=21.5)).paths[Gesture("nothing")].air[-1])


class StoveAtItsLowest(unittest.TestCase):
    """The stove does not stop by itself, its thermostat only lowers the flame (Frank, 1 November): said worth stopping
    when the room holds without it, « Coupez le poêle » once the room stays too warm for too long."""

    def setUp(self):
        self.twins = Twins(heat=replace(ordinary(CHAMBRE_P), share=0.3), windows=(WEST.size,),
                           house_thermostat=Thermostat(target=21.5, inside=0.8), house_power=8500.0, house_now=0.0)
        self.coming = [(Inputs(8.0, hour=13 + k / 12), None) for k in range(36)]
        self.warm = Now(air=22.5, walls=22.0, opened=(), house_running=True)

    def test_stopping_it_is_said_when_the_room_holds_without_it(self):
        found = stove_idle(self.twins, self.warm, self.coming, 20.0, 1.0)
        self.assertIsNotNone(found)
        self.assertTrue(found.get("minutes") is None or found["minutes"] >= 60)
        local = datetime(2026, 11, 1, 13, 40, tzinfo=timezone.utc)
        tip = stove_at_its_lowest(RoomView(local, 45.0, 4.0, minimum=20.0, stove_idle=found, end_hour=16))[0]
        self.assertIn("Le poêle tourne au minimum : sans lui", tip_text(tip, "fr"))

    def test_a_room_still_warming_is_said_when_it_would_not_hold(self):
        rising = replace(self.warm, house_rise=0.6)
        found = stove_idle(self.twins, rising, self.coming, 20.0, 12.0)
        self.assertEqual(found, {"rise": 0.6})
        local = datetime(2026, 11, 1, 13, 40, tzinfo=timezone.utc)
        tip = stove_at_its_lowest(RoomView(local, 45.0, 4.0, stove_idle=found))[0]
        self.assertEqual(tip_text(tip, "fr"), "Le poêle tourne au minimum et la pièce monte encore : 0,6 °C de plus en 30 min")

    def test_nothing_while_it_heats_under_its_set_point_or_is_off(self):
        self.assertIsNone(stove_idle(self.twins, replace(self.warm, air=20.5), self.coming, 20.0, 1.0))
        self.assertIsNone(stove_idle(self.twins, replace(self.warm, house_running=False), self.coming, 20.0, 1.0))
        self.assertIsNone(stove_idle(replace(self.twins, house_now=0.6), self.warm, self.coming, 20.0, 1.0))
        self.assertIsNone(stove_idle(self.twins, replace(self.warm, night=True), self.coming, 20.0, 1.0))

    def test_too_warm_for_too_long_is_a_gesture(self):
        hot = replace(self.warm, air=22.7, overheated=35.0)
        decision = decide(self.twins, hot, self.coming, Comfort(minimum=21.5), proof={"heating:heat": PROVEN})
        self.assertEqual((decision.gesture.kind, decision.rule), ("heat_stop", "overheat"))
        words = phrase(decision, 16)
        self.assertEqual(words["title"], "Coupez le poêle")
        self.assertEqual(words["line"], "22,7 °C pour 21,5 °C visés, depuis 35 min")
        self.assertTrue(done("heat_stop", replace(hot, house_running=False)))

    def test_not_before_the_household_s_delay_nor_at_night(self):
        comfort = Comfort(minimum=21.5)
        self.assertEqual(decide(self.twins, replace(self.warm, overheated=20.0), self.coming, comfort).rule != "overheat", True)
        self.assertNotEqual(decide(self.twins, replace(self.warm, overheated=20.0), self.coming, comfort,
                                   habits=Habits.of({"depassement_min": 15})).gesture.kind, "nothing")
        self.assertNotEqual(decide(self.twins, replace(self.warm, overheated=60.0, night=True), self.coming, comfort).rule,
                            "overheat")


if __name__ == "__main__":
    unittest.main()
