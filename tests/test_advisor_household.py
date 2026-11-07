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


class AiringEndsByBedtime(unittest.TestCase):
    """An airing ends by the room's bedtime; cut short by it, it is said only on a proven effect (Frank, 7 November:
    « si le conseil arrive à 20 h 55 pour 30 minutes d'aération, on ne propose pas d'aérer 5 minutes, sauf si c'est
    vraiment avéré »)."""

    def setUp(self):
        from advisor.snapshot import load, restore
        # Chambre AL, 4 November at 15 h 13: « À essayer — Aérez 25 min ».
        self.args = restore(load(Path(__file__).parent / "fixtures" / "chambre-al-4-novembre-15h13.json"))

    def decide(self, bed_in, **changes):
        from dataclasses import replace
        from advisor.decide import decide
        return decide(**{**self.args, "now": replace(self.args["now"], bed_in=bed_in), **changes})

    def test_an_airing_that_fits_is_unchanged(self):
        from advisor.decide import Gesture
        self.assertEqual(self.decide(None).passive, Gesture("open", 25))
        self.assertEqual(self.decide(45).passive, Gesture("open", 25))
        # Newly proposed, it ends BED_MARGIN before bed: 25 min with bed in 32 no longer is; already shown, it still is.
        self.assertIsNone(self.decide(32).passive)
        self.assertEqual(self.decide(32, tried=Gesture("open", 25)).passive, Gesture("open", 25))

    def test_cut_short_by_bedtime_it_is_not_said_unless_proven(self):
        for bed_in in (20, 10, 3):
            decision = self.decide(bed_in)
            self.assertNotIn(decision.gesture.kind, ("open", "open_more"), bed_in)
            self.assertIsNone(decision.passive, bed_in)

    def test_proven_it_is_said_shorter_only_if_that_still_makes_a_difference(self):
        from advisor.proof import PROVEN
        proven = {k: PROVEN for k in self.args["proof"]}
        self.assertEqual(self.decide(60, proof=proven).gesture.kind, "open")
        for bed_in in (20, 10, 3):
            g = self.decide(bed_in, proof=proven).gesture
            self.assertTrue(g.kind not in ("open", "open_more") or ((g.after or 0) + g.minutes <= bed_in + 2.5), (bed_in, g))

    def test_a_household_that_gets_up_at_night_keeps_its_airing(self):
        from dataclasses import replace
        from advisor.decide import Gesture
        self.assertEqual(self.decide(10, habits=replace(self.args["habits"], open_at_night=True)).passive, Gesture("open", 25))

    def test_a_window_open_is_shut_by_bedtime(self):
        from advisor.decide import Gesture, Now, _past_bedtime
        from advisor.household import Habits
        late = _past_bedtime(Now(air=20.0, walls=20.0, opened=(), bed_in=12.0), Habits())
        self.assertTrue(late(Gesture("close", after=20)))
        self.assertFalse(late(Gesture("close", after=10)))
        self.assertTrue(late(Gesture("open")))          # « Ouvrez » for good, twelve minutes before bed
        self.assertTrue(late(Gesture("open", 10)))      # newly proposed: not 15 min before bed
        self.assertFalse(late(Gesture("open", 10), held=True))   # already on the card: it still fits
        self.assertTrue(late(Gesture("open", 10, after=15), held=True))
