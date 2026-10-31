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
