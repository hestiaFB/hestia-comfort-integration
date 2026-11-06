"""Days of high pollens for an allergic household (advisor/pollen.py), as Frank validated them on 6 November 2026: the
humidity, the mould and the CO₂ keep the airing they need at any hour; the rest only early in the morning or after the
rain, 10 min at most; a window open shut after 10 min unless it helps them; no window open for the night."""
from dataclasses import replace
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from advisor.decide import Comfort, Gesture, Now, decide, main_subject, tonight
from advisor.household import Habits, Sleep
from advisor.knowing import RoomView, pollen_today
from advisor.pollen import AIRING, Pollen, today
from advisor.snapshot import capture, replay
from advisor.words import phrase, tip_text
from test_advisor_decide import FRENCH, TWINS, day, night

PARIS = timezone(timedelta(hours=1))
HIGH = {"level": 3, "high": True, "main": "Graminées"}
# Mid-afternoon, far from the morning and from any rain.
AFTERNOON = Pollen(level=3, main="Graminées", good=((1020.0, 1140.0),))
# The rain just washed the air: a good moment now.
WASHED = Pollen(level=3, good=((-10.0, 50.0),), after_rain=True)


def opened(minutes):
    return replace(AFTERNOON, open_for=minutes)


class Today(unittest.TestCase):
    def test_nothing_without_high_pollens_or_without_an_answer(self):
        local = datetime(2026, 5, 6, 14, 0, tzinfo=PARIS)
        self.assertIsNone(today(None, local))
        self.assertIsNone(today({"level": 2, "high": False}, local))
        self.assertIsNone(today({"level": None, "high": False}, local))

    def test_the_two_hours_after_waking_are_a_good_moment(self):
        sleep = Sleep(end=time(7, 0))
        early = today(HIGH, datetime(2026, 5, 6, 7, 30, tzinfo=PARIS), sleep)
        self.assertTrue(early.good_at(0))
        afternoon = today(HIGH, datetime(2026, 5, 6, 14, 0, tzinfo=PARIS), sleep)
        self.assertFalse(afternoon.good_at(0))
        # Tomorrow's morning, 17 h from now.
        self.assertTrue(afternoon.good_at(17 * 60 + 30))
        self.assertFalse(afternoon.after_rain)

    def test_the_hour_after_the_rain_is_a_good_moment(self):
        local = datetime(2026, 5, 6, 14, 0, tzinfo=PARIS)
        washed = today(HIGH, local, rained_at=local - timedelta(minutes=20))
        self.assertTrue(washed.after_rain)
        self.assertTrue(washed.good_at(0))
        self.assertFalse(washed.good_at(45))
        self.assertFalse(today(HIGH, local, rained_at=local - timedelta(minutes=90)).after_rain)
        # Still raining: not « after » the rain (safety keeps the windows shut anyway).
        self.assertFalse(today(HIGH, local, rained_at=local, raining=True).after_rain)

    def test_how_long_the_window_has_been_open(self):
        local = datetime(2026, 5, 6, 14, 0, tzinfo=PARIS)
        found = today(HIGH, local, open_since=local - timedelta(minutes=7))
        self.assertAlmostEqual(found.open_for, 7.0)
        self.assertAlmostEqual(found.left(), 3.0)


class Airings(unittest.TestCase):
    def test_stale_air_keeps_the_airing_it_needs(self):
        now = Now(air=21.5, walls=21.5, opened=(), humidity=55.0, co2=1600.0)
        coming = day(outdoor=17.0)
        self.assertEqual(decide(TWINS, now, coming, pollen=AFTERNOON).gesture, decide(TWINS, now, coming).gesture)

    def test_cooling_never_longer_than_ten_minutes_nor_without_an_end(self):
        now = Now(air=26.5, walls=26.5, opened=(), humidity=45.0, co2=600.0)
        decision = decide(TWINS, now, day(outdoor=17.0), pollen=WASHED)
        for g in decision.scenarios:
            if g.kind == "open":
                self.assertIsNotNone(g.minutes)
                self.assertLessEqual(g.minutes, AIRING)

    def test_cooling_a_warm_room_waits_for_a_good_moment(self):
        now = Now(air=26.5, walls=26.5, opened=(), humidity=45.0, co2=600.0)
        coming = day(outdoor=17.0)
        plain = decide(TWINS, now, coming)
        self.assertEqual(plain.gesture.kind, "open")
        self.assertEqual(main_subject(plain.scenarios, plain.gesture), "heat")
        self.assertNotEqual(decide(TWINS, now, coming, pollen=AFTERNOON).gesture.kind, "open")
        # Just after the rain, the short airing for the heat is weighed again (worth it or not, it is no longer left out).
        self.assertNotIn(Gesture("open", AIRING), decide(TWINS, now, coming, pollen=AFTERNOON).scenarios)
        self.assertIn(Gesture("open", AIRING), decide(TWINS, now, coming, pollen=WASHED).scenarios)


class OpenWindow(unittest.TestCase):
    def test_shut_after_ten_minutes_when_it_does_not_dry_the_room(self):
        now = Now(air=21.0, walls=21.0, opened=(FRENCH.size,), humidity=50.0)
        decision = decide(TWINS, now, day(outdoor=19.0), pollen=opened(12))
        self.assertEqual((decision.gesture, decision.rule), (Gesture("close"), "pollen"))
        self.assertEqual(phrase(decision, 17)["line"], "Pollens élevés aujourd'hui : 10 min d'aération suffisent")

    def test_before_ten_minutes_never_left_open_beyond_them(self):
        now = Now(air=21.0, walls=21.0, opened=(FRENCH.size,), humidity=50.0)
        decision = decide(TWINS, now, day(outdoor=19.0), pollen=opened(4))
        self.assertNotEqual(decision.rule, "pollen")
        self.assertNotIn(Gesture("keep"), decision.scenarios)
        for g in decision.scenarios:
            if g.kind == "close" and g.after:
                self.assertLessEqual(g.after, 6)

    def test_a_window_drying_a_damp_room_stays_as_on_any_day(self):
        # 78 % at 21 °C, dry and mild outside: the window dries the room.
        now = Now(air=21.0, walls=21.0, opened=(FRENCH.size,), humidity=78.0, co2=600.0)
        coming = [(u, w * 0.6) for u, w in day(outdoor=16.0)]
        decision = decide(TWINS, now, coming, pollen=opened(25))
        self.assertNotEqual(decision.rule, "pollen")
        self.assertEqual(decision.gesture, decide(TWINS, now, coming).gesture)


class Night(unittest.TestCase):
    def test_no_window_open_for_the_night(self):
        # A summer room at 28 °C, 15 °C outside all night, a household that would open: worth it, but not these days.
        warm, coming = Now(air=28.0, walls=28.0, opened=(), humidity=50.0), night(outdoor=15.0, start=20.0, hours=11)
        habits = Habits(open_at_night=True)
        self.assertEqual(tonight(TWINS, warm, coming, 120, Comfort(19, 24), habits=habits).gesture, Gesture("open", after=120))
        self.assertIsNone(tonight(TWINS, warm, coming, 120, Comfort(19, 24), habits=habits, pollen=AFTERNOON))


class Words(unittest.TestCase):
    def test_good_to_know(self):
        view = RoomView(datetime(2026, 5, 6, 14, 0, tzinfo=PARIS), 43.45, 5.47, pollen=AFTERNOON)
        tips = pollen_today(view)
        self.assertEqual(tip_text(tips[0]), "Pollens élevés aujourd'hui (graminées) : aérez seulement si c'est utile, de préférence tôt le matin")
        view.pollen = WASHED
        self.assertEqual(tip_text(pollen_today(view)[0]), "La pluie a lavé l'air des pollens : bon moment pour aérer")
        view.pollen = None
        self.assertEqual(pollen_today(view), [])


class Snapshot(unittest.TestCase):
    def test_the_pollens_are_kept_and_replayed(self):
        now = Now(air=21.0, walls=21.0, opened=(FRENCH.size,), humidity=50.0)
        snap = capture(TWINS, now, day(outdoor=19.0), pollen=opened(12), end_hour=17)
        self.assertEqual(replay(snap)[0].rule, "pollen")
        self.assertNotEqual(replay({**snap, "pollen": None})[0].rule, "pollen")


if __name__ == "__main__":
    unittest.main()
