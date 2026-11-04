"""A note for each gesture (CAHIER-MOTEUR.md § 15.1): judged an hour after it ended against the twin without it, left out
when something else acted, and the night's correction of each category from the middle of the recent notes."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.notes import GOOD, LITTLE, MOVE, WORSE, episodes, factor, grade, grades, middle, put_aside, ratio, settle
from advisor.physics.air import ParticleParams, particles_step
from advisor.physics.airfit import notes as air_notes, vector
from advisor.physics.fit import Sample
from advisor.physics.thermal import STEP, Inputs

NOW = datetime(2026, 11, 4, 3, 30, tzinfo=timezone.utc)


def note(days_ago, announced, measured):
    return [(NOW - timedelta(days=days_ago)).isoformat(), announced, measured]


class Notes(unittest.TestCase):
    def test_a_note_says_how_much_of_the_announced_effect_was_done(self):
        self.assertEqual(grade(ratio(-2.0, -1.8)), GOOD)
        self.assertEqual(grade(ratio(-2.0, -5.0)), GOOD)        # more than announced: the twin underrates it
        self.assertEqual(grade(ratio(-2.0, -0.4)), LITTLE)
        self.assertEqual(grade(ratio(-2.0, 0.3)), WORSE)        # wetter than without it
        self.assertEqual(grades([note(3, -2, -2), note(2, -2, -0.2), note(1, -2, 0.5)]), "+ 0 −")

    def test_episodes_need_a_known_start_and_end(self):
        self.assertEqual(episodes([False, True, True, False, None, True, False, True, True]), [(1, 3)])

    def test_the_middle_weighs_the_recent_notes_more(self):
        old = [note(60, -2, -2)] * 3
        recent = [note(1, -2, -0.6)] * 2
        self.assertAlmostEqual(middle(old + recent, NOW)[0], 0.3)
        self.assertEqual(middle([note(1, -2, -2)] * 3 + [note(1, -2, 4)], NOW)[0], 1.0)     # one odd note does not move it

    def test_a_night_moves_a_category_by_half_or_double_at_most(self):
        self.assertEqual(factor([note(1, -2, -0.6)] * 2, NOW)[0], None)          # too few notes
        self.assertEqual(factor([note(1, -2, -0.2)] * 3, NOW)[0], 1 / MOVE)
        self.assertEqual(factor([note(1, -2, 1.0)] * 3, NOW)[0], 1 / MOVE)       # the other way: halved, never reversed
        self.assertEqual(factor([note(1, -2, -10)] * 3, NOW)[0], MOVE)

    def test_settle_follows_the_notes_within_the_bound(self):
        # A window that really does a third of what the twin gives it: halved in one night, a third over two.
        def notes_at(w):
            return [note(1, -2.0 * w, -2.0)] * 3
        value, _, report = settle(notes_at, 3.0, NOW)
        self.assertAlmostEqual(value, 1.5)
        self.assertEqual(report["facteur"], 0.5)
        value, _, _ = settle(notes_at, value, NOW)
        self.assertAlmostEqual(value, 1.0, places=1)

    def test_a_gesture_put_aside_during_the_day_is_left_out_at_night(self):
        skipped = ["2026-11-03T18:19:00+00:00"]
        self.assertTrue(put_aside(skipped, datetime(2026, 11, 3, 18, 15, tzinfo=timezone.utc)))
        self.assertFalse(put_aside(skipped, datetime(2026, 11, 3, 21, 0, tzinfo=timezone.utc)))


TRUTH = ParticleParams(30.0, 0.2, 5.0, 120.0)        # a dusty room: its effect still readable an hour on
X = vector("particles", {"settling": 0.2, "outdoor": 5.0, "sources": 120.0, "rhythm_cos": 0.0, "rhythm_sin": 0.0},
           (1.0, 1.0))


def purified(days=4, window_at=None, strength=1.0):
    """Particles made all day, the purifier run an hour every afternoon at `strength` of its declared flow; a window
    opened a quarter of an hour at `window_at` (hour) if any."""
    start, rows, level = datetime(2026, 10, 1, tzinfo=timezone.utc), [], 20.0
    for k in range(int(days * 86400 / STEP)):
        when = start + timedelta(seconds=k * STEP)
        hour = when.hour + when.minute / 60
        opened = window_at is not None and window_at <= hour < window_at + 0.25
        u = Inputs(15.0, hour=hour, purifier=150.0 if 15 <= when.hour < 16 else 0.0,
                   windows=((1.0, 1.2),) if opened else ())
        rows.append((Sample(when, 20.0, u), level, 0.0))
        level = particles_step(TRUTH, level, 9.0 + (30.0 if opened else 0.0), u.hour, purifier=u.purifier * strength)
    return rows


class Devices(unittest.TestCase):
    def test_each_purifier_run_is_noted_against_the_room_without_it(self):
        found = air_notes("particles", "particles", X, 30.0, purified(), "purify")
        self.assertEqual(len(found), 4)
        for _, announced, measured in found:
            self.assertLess(announced, -4)
            self.assertEqual(grade(ratio(announced, measured)), GOOD)

    def test_a_purifier_weaker_than_declared_is_brought_to_its_real_flow_night_after_night(self):
        # Its clean air a third of the declared flow: the twin, believing the declared one, announces too much. Halved the
        # first night (the most a night moves), then the rest.
        from advisor.nightly import _scaled
        rows = purified(strength=1 / 3)
        now = rows[-1][0].when
        found = air_notes("particles", "particles", X, 30.0, rows, "purify")
        self.assertLess(middle(found, now)[0], 0.8)
        share = 1.0
        for night, expected in ((1, 0.5), (2, 1 / 3)):
            share, _, _ = settle(lambda v: air_notes("particles", "particles", X, 30.0, _scaled(rows, 1.0, v), "purify"),
                                 share, now)
            self.assertAlmostEqual(share, expected, delta=0.05, msg=f"night {night}")

    def test_a_window_opened_while_the_room_settles_leaves_the_run_out(self):
        self.assertEqual(air_notes("particles", "particles", X, 30.0, purified(window_at=16.5), "purify"), [])
        # The morning's airing is apart.
        self.assertEqual(len(air_notes("particles", "particles", X, 30.0, purified(window_at=10.0), "purify")), 4)



class Heat(unittest.TestCase):
    def test_a_gap_in_the_history_before_an_opening_does_not_stop_the_night(self):
        # The lab, 4 November: the Salon · Cuisine's history started with a gap, and the night stopped on it.
        from advisor.physics.fit import notes as heat_notes
        from advisor.house import Opening, Room
        from advisor.physics.thermal import ordinary
        start = datetime(2026, 11, 3, tzinfo=timezone.utc)
        samples = []
        for k in range(60):
            opened = 20 <= k < 26
            u = None if k < 5 else Inputs(8.0, hour=k * STEP / 3600, windows=((1.0, 1.2),) if opened else ())
            samples.append(Sample(start + timedelta(seconds=k * STEP), None if k < 5 else 19.0 - (0.5 if 20 <= k < 40 else 0), u))
        why = {}
        room = Room("test", "Test", volume=30.0, openings=(Opening("binary_sensor.f", "window", area=1.2, height=1.2),))
        heat_notes(ordinary(room), samples, why=why)
        self.assertEqual(sum(why.values()), 1)

if __name__ == "__main__":
    unittest.main()
