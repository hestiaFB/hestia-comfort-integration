"""The sleeping hours are a setting of each room, the alarm armed for the night counts as sleep."""
from datetime import datetime, time
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.household import Sleep

PARIS = ZoneInfo("Europe/Paris")
AT = lambda h, m=0: datetime(2026, 10, 31, h, m, tzinfo=PARIS)


class Sleeping(unittest.TestCase):
    def test_by_default_22_to_7(self):
        sleep = Sleep.of(None)
        self.assertEqual((sleep.start, sleep.end), (time(22), time(7)))
        self.assertTrue(sleep.asleep(AT(23)))
        self.assertTrue(sleep.asleep(AT(3)))
        self.assertFalse(sleep.asleep(AT(7)))
        self.assertFalse(sleep.asleep(AT(21, 59)))

    def test_set_for_a_room(self):
        sleep = Sleep.of({"debut": "23:30", "fin": "06:15"})
        self.assertFalse(sleep.asleep(AT(23)))
        self.assertTrue(sleep.asleep(AT(6)))
        self.assertEqual(sleep.wake(AT(23, 45)), datetime(2026, 11, 1, 6, 15, tzinfo=PARIS))
        self.assertEqual(sleep.bedtime(AT(20)), AT(23, 30))

    def test_a_day_sleep_and_the_night_alarm(self):
        nap = Sleep.of({"debut": "13:00", "fin": "15:00"})        # a night worker, a baby's room
        self.assertTrue(nap.asleep(AT(14)))
        self.assertFalse(nap.asleep(AT(16)))
        self.assertTrue(Sleep.of(None).asleep(AT(16), alarm="armed_night"))


if __name__ == "__main__":
    unittest.main()


class HouseholdHabits(unittest.TestCase):
    """The household's way of life is a setting (CAHIER-MOTEUR.md § 10.3): the house's, then the room's."""

    def test_the_room_overrides_the_house_and_a_snapshot_keeps_it(self):
        from advisor.household import Habits
        habits = Habits.of({"aeration_max_min": 15, "sommeil": {"debut": "23:00"}}, {"ouvrir_la_nuit": True})
        self.assertEqual((habits.airings, habits.open_at_night, habits.sleep.start), ((5, 10, 15), True, time(23)))
        self.assertEqual(Habits.of(habits.setting()), habits)

    def test_the_engine_follows_them(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from advisor.decide import Gesture, Now, decide
        from advisor.household import Habits
        from test_advisor_decide import TWINS, night
        stale = Now(air=21.0, walls=21.0, opened=(), co2=1800.0, night=True)
        self.assertFalse(any(g.kind == "open" for g in decide(TWINS, stale, night()).scenarios))
        allowed = decide(TWINS, stale, night(), habits=Habits(open_at_night=True, airing_max=5))
        self.assertIn(Gesture("open", 5), allowed.scenarios)
        self.assertNotIn(Gesture("open", 10), allowed.scenarios)

    def test_the_shortest_airing_that_is_enough_counts_down(self):
        from advisor.decide import Gesture, aged
        from advisor.household import Habits
        self.assertEqual(Habits().airings, (5, 10, 15, 20, 25, 30))
        self.assertEqual(Habits().later[:2], (15, 30))
        self.assertEqual(Habits().devices[0], 10)
        # « Laissez ouvert encore 10 min », five minutes on, is « encore 5 min », then « Refermez ».
        self.assertEqual(aged(Gesture("close", after=10), 5), Gesture("close", after=5))
        self.assertEqual(aged(Gesture("close", after=5), 6), Gesture("close"))
