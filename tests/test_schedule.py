"""ha-chauffage (issue #42) and Scheduler (issue #46): when the heating changes next, read from their entities, said in the
room and followed by the advisor's scenarios. ha-chauffage's states are those 0.8.1 writes (sensor.py, binary_sensor.py,
runtime.override_info); Scheduler's are copied from a home running it."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.decide import Gesture, Now, Thermostat, Twins, simulate
from advisor.house import Opening, Room
from advisor.knowing import RoomView, heating_planned
from advisor.physics.thermal import Inputs, ordinary
from advisor.words import tip_text
from engine import schedule
from engine.assessment import Settings, assess
from engine.sources import Reading

PARIS = timezone(timedelta(hours=1))
NOW = datetime(2026, 11, 2, 9, 0, tzinfo=PARIS)
# The Salon of Gaël's example: Eco from 08:30 to 17:00, then Confort.
PLANNED = ("eco", {"preset_name": "Eco", "target": {"preset": "eco"}, "next_preset": "comfort", "next_preset_name": "Confort",
                   "next_start": "2026-11-02T17:00:00+01:00", "temperatures": {"comfort": 20.0, "eco": 17.0, "frost": 7.0}})
NO_OVERRIDE = ("off", {"kind": None, "value": None, "preset": None, "end": None})


class Read(unittest.TestCase):
    def test_the_next_slot_of_the_active_schedule(self):
        found = schedule.next_change(PLANNED, NO_OVERRIDE, None, NOW)
        self.assertEqual(found, {"at": "2026-11-02T17:00:00+01:00", "preset": "comfort", "name": "Confort",
                                 "temperature": 20.0, "override": False})

    def test_an_override_ends_before_the_slot_the_slot_planned_now_comes_back(self):
        override = ("on", {"kind": "preset", "value": "comfort", "preset": "comfort", "end": "2026-11-02T11:00:00+01:00"})
        found = schedule.next_change(PLANNED, override, None, NOW)
        self.assertEqual((found["at"], found["preset"], found["temperature"], found["override"]),
                         ("2026-11-02T11:00:00+01:00", "eco", 17.0, True))

    def test_an_override_past_the_slot_its_end_only_the_preset_unknown(self):
        override = ("on", {"kind": "temperature", "value": 22, "preset": None, "end": "2026-11-02T19:00:00+01:00"})
        found = schedule.next_change(PLANNED, override, None, NOW)
        self.assertEqual((found["at"], found["preset"], found["temperature"]), ("2026-11-02T19:00:00+01:00", None, None))

    def test_the_next_change_sensor_comes_first_once_ha_chauffage_has_it(self):
        change = ("2026-11-02T16:30:00+01:00", {"preset": "comfort", "preset_name": "Confort", "temperature": 20.5})
        found = schedule.next_change(PLANNED, NO_OVERRIDE, change, NOW)
        self.assertEqual((found["at"], found["temperature"]), ("2026-11-02T16:30:00+01:00", 20.5))

    def test_nothing_ahead_paused_or_past_is_no_change(self):
        self.assertIsNone(schedule.next_change(("unavailable", {}), None, None, NOW))
        self.assertIsNone(schedule.next_change(("eco", {**PLANNED[1], "next_start": None}), NO_OVERRIDE, None, NOW))
        self.assertIsNone(schedule.next_change(PLANNED, NO_OVERRIDE, None, NOW + timedelta(hours=9)))
        self.assertIsNone(schedule.next_change(None, None, None, NOW))


# Scheduler 3.3.9 as it runs in Frank's home, 4 November 2026 around 18 h 45 (Home Assistant states, copied as they are).
EVENING = datetime(2026, 11, 4, 18, 45, tzinfo=PARIS)
PARENTS = {"weekdays": ["daily"], "timeslots": ["00:00:00 - 20:30:00", "20:30:00 - 22:30:00", "22:30:00 - 00:00:00"],
           "entities": ["climate.thermostat_p"],
           "actions": [{"service": "climate.set_preset_mode", "data": {"preset_mode": "eco"}},
                       {"service": "climate.set_preset_mode", "data": {"preset_mode": "comfort"}},
                       {"service": "climate.set_preset_mode", "data": {"preset_mode": "eco"}}],
           "current_slot": 0, "next_slot": 1, "next_trigger": "2026-11-04T20:30:00+01:00", "tags": []}
ROOMS = {"weekdays": ["daily"], "timeslots": ["00:00:00 - 17:00:00", "17:00:00 - 18:30:00", "18:30:00 - 20:30:00", "20:30:00 - 00:00:00"],
         "entities": ["climate.thermostat_a", "climate.thermostat_al", "climate.thermostat_m"],
         "actions": [{"service": "climate.set_preset_mode", "data": {"preset_mode": p}} for p in ("eco", "comfort", "comfort", "eco")],
         "current_slot": 2, "next_slot": 3, "next_trigger": "2026-11-04T20:30:00+01:00", "tags": []}
THERMOSTAT_P = {"frost_temp": 15, "eco_temp": 17, "boost_temp": 20.5, "comfort_temp": 20}
THERMOSTAT_A = {"frost_temp": 15, "eco_temp": 18, "boost_temp": 21, "comfort_temp": 19}


class SchedulerRead(unittest.TestCase):
    def test_the_next_slot_with_its_preset_temperature(self):
        found = schedule.scheduler_change("on", PARENTS, THERMOSTAT_P, EVENING)
        self.assertEqual(found, {"at": "2026-11-04T20:30:00+01:00", "preset": "comfort", "name": "comfort",
                                 "temperature": 20.0, "override": False})

    def test_a_lower_slot_is_a_change_too(self):
        found = schedule.scheduler_change("on", ROOMS, THERMOSTAT_A, EVENING)
        self.assertEqual((found["preset"], found["temperature"]), ("eco", 18.0))

    def test_a_slot_sending_the_same_preset_is_skipped_to_the_first_that_differs(self):
        # 17 h 30: comfort runs, the 18 h 30 slot sends comfort again; the change is eco at 20 h 30.
        found = schedule.scheduler_change("on", {**ROOMS, "current_slot": 1, "next_slot": 2,
                                                 "next_trigger": "2026-11-04T18:30:00+01:00"}, THERMOSTAT_A,
                                          EVENING.replace(hour=17, minute=30))
        self.assertEqual((found["at"], found["preset"]), ("2026-11-04T20:30:00+01:00", "eco"))

    def test_a_schedule_turned_off_or_unreadable_says_nothing(self):
        self.assertIsNone(schedule.scheduler_change("off", PARENTS, THERMOSTAT_P, EVENING))
        self.assertIsNone(schedule.scheduler_change("on", {**PARENTS, "next_trigger": None}, THERMOSTAT_P, EVENING))
        self.assertIsNone(schedule.scheduler_change("on", {**PARENTS, "timeslots": ["sunrise+00:30", "sunset", "22:30:00"],
                                                           "current_slot": 0, "next_slot": 1}, {}, EVENING)["temperature"])

    def test_a_set_temperature_and_a_switch_off(self):
        actions = [{"service": "climate.set_temperature", "data": {"temperature": 16}},
                   {"service": "climate.set_temperature", "data": {"temperature": 19.5}},
                   {"service": "climate.set_hvac_mode", "data": {"hvac_mode": "off"}}]
        found = schedule.scheduler_change("on", {**PARENTS, "actions": actions}, {}, EVENING)
        self.assertEqual((found["preset"], found["temperature"]), (None, 19.5))
        off = schedule.scheduler_change("on", {**PARENTS, "actions": actions, "current_slot": 1, "next_slot": 2,
                                               "next_trigger": "2026-11-04T22:30:00+01:00"}, {}, EVENING)
        self.assertEqual((off["preset"], off["temperature"]), ("off", None))

    def test_the_soonest_of_two_schedules(self):
        late = schedule.scheduler_change("on", {**PARENTS, "next_trigger": "2026-11-04T22:00:00+01:00"}, THERMOSTAT_P, EVENING)
        soon = schedule.scheduler_change("on", PARENTS, THERMOSTAT_P, EVENING)
        self.assertEqual(schedule.earliest([late, None, soon])["at"], "2026-11-04T20:30:00+01:00")

    def test_a_schedule_is_known_by_its_attributes(self):
        # Copied from another Home Assistant, it keeps the attributes, not the integration.
        self.assertTrue(schedule.is_schedule(PARENTS))
        self.assertFalse(schedule.is_schedule({"entities": ["climate.thermostat_p"]}))
        self.assertFalse(schedule.is_schedule({**PARENTS, "timeslots": None}))
        self.assertFalse(schedule.is_schedule(None))


class Said(unittest.TestCase):
    def run_room(self, thermostat):
        readings = {"indoor_temperature": Reading(17.2, "valid", "sensor.t"), "heating": Reading("idle", "valid", "climate.salon")}
        return assess(readings, Settings(minimum=19, maximum=24), None, {}, None, {}, NOW,
                      context={"heated": True, "thermostat": thermostat}).features["warmth"]

    def test_the_change_rides_with_a_versatile_thermostat(self):
        change = schedule.next_change(PLANNED, NO_OVERRIDE, None, NOW)
        warmth = self.run_room({"name": "Versatile Thermostat", "mode": "heat", "preset": "eco", "target": 17.0, "next": change})
        self.assertEqual(warmth["next"]["at"], "2026-11-02T17:00:00+01:00")
        self.assertTrue(warmth["thermostat"]["lowered"])

    def test_for_another_heating_the_change_alone_never_a_thermostat(self):
        change = schedule.next_change(PLANNED, NO_OVERRIDE, None, NOW)
        warmth = self.run_room({"next": change})
        self.assertEqual(warmth["next"]["name"], "Confort")
        self.assertNotIn("thermostat", warmth)

    def test_the_change_is_said_when_the_room_is_warm(self):
        change = schedule.next_change(PLANNED, NO_OVERRIDE, None, NOW)
        readings = {"indoor_temperature": Reading(21.0, "valid", "sensor.t"), "heating": Reading("idle", "valid", "climate.salon")}
        features = assess(readings, Settings(minimum=19, maximum=24), None, {}, None, {}, NOW,
                          context={"heated": True, "thermostat": {"next": change}}).features
        self.assertIsNone(features["warmth"])
        self.assertEqual(features["planned"]["preset"], "comfort")

    def run_warm(self, thermostat, heating="idle", heated=True):
        readings = {"indoor_temperature": Reading(21.0, "valid", "sensor.t"), "heating": Reading(heating, "valid", "climate.salon")}
        return assess(readings, Settings(minimum=19, maximum=24), None, {}, None, {}, NOW,
                      context={"heated": heated, "thermostat": thermostat}).features["planned"]

    def test_a_heating_switched_off_for_the_summer_says_nothing(self):
        change = schedule.next_change(PLANNED, NO_OVERRIDE, None, NOW)
        self.assertIsNone(self.run_warm({"name": "Versatile Thermostat", "mode": "off", "off_reason": "manual", "next": change}, "off"))
        self.assertIsNone(self.run_warm({"next": change}, "off"))
        self.assertIsNone(self.run_warm({"next": change}, heated=False))

    def test_a_pause_or_a_change_that_switches_it_on_is_still_said(self):
        change = schedule.next_change(PLANNED, NO_OVERRIDE, None, NOW)
        window = self.run_warm({"name": "Versatile Thermostat", "mode": "off", "off_reason": "window", "next": change}, "off")
        self.assertEqual(window["preset"], "comfort")
        on = self.run_warm({"next": {**change, "preset": "heat"}}, "off")
        self.assertEqual(on["preset"], "heat")


class Followed(unittest.TestCase):
    """The advisor's thermostat aims at the next slot's set point once it has come."""
    ROOM = Room("salon", "Salon", volume=40.0, openings=(Opening("binary_sensor.f", "window", area=1.5, height=1.2),),
                heating_power=2000)

    def test_the_set_point_rises_at_the_slot(self):
        thermostat = Thermostat(target=17.0, then=20.0, at=60.0)
        self.assertEqual(thermostat.scheduled(30).target, 17.0)
        self.assertEqual(thermostat.scheduled(60).target, 20.0)
        self.assertEqual(Thermostat(target=17.0).scheduled(600).target, 17.0)

    def test_the_room_warms_after_the_slot_and_not_before(self):
        coming = [(Inputs(8.0, hour=15 + k / 12), None) for k in range(36)]
        now = Now(air=17.0, walls=16.8, opened=())
        kept = Twins(heat=ordinary(self.ROOM), windows=(), thermostat=Thermostat(target=17.0))
        planned = Twins(heat=ordinary(self.ROOM), windows=(), thermostat=Thermostat(target=17.0, then=20.0, at=60.0))
        flat, rising = (simulate(t, now, coming, Gesture("nothing")) for t in (kept, planned))
        self.assertAlmostEqual(flat.air[10], rising.air[10], places=3)
        self.assertGreater(rising.air[-1], flat.air[-1] + 1.0)


class Tip(unittest.TestCase):
    def view(self, at, asleep=False):
        return RoomView(now=NOW, latitude=48.85, longitude=2.35, minimum=19.0, asleep=asleep,
                        heating_planned={"at": at, "temperature": 20.0})

    def test_heating_planned_at_one(self):
        tips = heating_planned(self.view(NOW.replace(hour=13)))
        self.assertEqual(tip_text(tips[0]), "Chauffage prévu à 13 h : 20 °C visés")
        self.assertEqual(tip_text(tips[0], "en"), "Heating planned at 13:00: 20 °C aimed at")

    def test_not_said_too_far_ahead_nor_asleep(self):
        self.assertEqual(heating_planned(self.view(NOW.replace(hour=17))), [])
        self.assertEqual(heating_planned(self.view(NOW.replace(hour=11), asleep=True)), [])


if __name__ == "__main__":
    unittest.main()
