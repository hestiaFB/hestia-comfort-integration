"""The 3.0 advisor's first layers: windows read once, the physical twin, and how it learns a room."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.house import Opening, Room
from advisor.observe import Series, window_open
from advisor.physics.fit import Sample, fit, score
from advisor.physics.thermal import STEP, Inputs, ordinary, step, time_constant
from advisor.physics.vents import window_flow

START = datetime(2026, 10, 30, 22, tzinfo=timezone.utc)
ROOM = Room("salon", "Salon", openings=(Opening("binary_sensor.fenetre", "window"),))
WINDOW = ROOM.openings[0].size


class WindowsTest(unittest.TestCase):
    def test_short_opening_does_not_count_yet(self):
        # The night of 30 October: the west window open 14 seconds.
        series = Series([(START, False), (START + timedelta(seconds=7), True), (START + timedelta(seconds=21), False)])
        self.assertFalse(window_open(series, START + timedelta(seconds=10)))
        self.assertFalse(window_open(series, START + timedelta(seconds=25)))

    def test_opening_counts_after_the_bounce(self):
        series = Series([(START, False), (START + timedelta(seconds=3), True)])
        self.assertFalse(window_open(series, START + timedelta(seconds=20)))
        self.assertTrue(window_open(series, START + timedelta(seconds=40)))

    def test_closing_counts_at_once_and_silence_is_unknown(self):
        series = Series([(START, True), (START + timedelta(minutes=10), False), (START + timedelta(minutes=20), None)],
                        keep_none=True)
        self.assertFalse(window_open(series, START + timedelta(minutes=10, seconds=1)))
        self.assertIsNone(window_open(series, START + timedelta(minutes=21)))


class VentsTest(unittest.TestCase):
    def test_an_open_window_renews_the_room_many_times_an_hour(self):
        flow = window_flow(*WINDOW, 20.6, 12.8)
        self.assertGreater(flow / ROOM.air, 5)
        self.assertLess(flow / ROOM.air, 30)

    def test_no_gap_and_no_wind_no_flow_and_the_wind_adds(self):
        self.assertEqual(window_flow(*WINDOW, 20.0, 20.0), 0.0)
        self.assertGreater(window_flow(*WINDOW, 20.0, 20.0, wind=3.0), 0.0)
        self.assertGreater(window_flow(*WINDOW, 20.0, 12.0, wind=3.0), window_flow(*WINDOW, 20.0, 12.0))


def night(p, hours, opened=False, outdoor=12.8, heating=0.0, air=20.6):
    walls = air
    for _ in range(int(hours * 3600 / STEP)):
        air, walls = step(p, air, walls, Inputs(outdoor, heating=heating, windows=(WINDOW,) if opened else ()))
    return air


class ThermalTest(unittest.TestCase):
    p = ordinary(ROOM)

    def test_the_night_of_30_october_open_costs_degrees_shut_does_not(self):
        shut, open_ = night(self.p, 6), night(self.p, 6, opened=True)
        self.assertLess(20.6 - shut, 1.0)
        self.assertGreater(shut - open_, 1.5)

    def test_physical_directions(self):
        base = night(self.p, 3)
        self.assertLess(night(self.p, 3, outdoor=5.0), base)
        self.assertGreater(night(self.p, 3, heating=1.0), base)
        self.assertLess(night(self.p, 3, opened=True, outdoor=5.0), night(self.p, 3, opened=True))

    def test_open_window_settles_between_walls_and_outside(self):
        air = night(self.p, 0.5, opened=True)
        self.assertGreater(air, 12.8)
        self.assertLess(air, 20.6)

    def test_stable_with_a_window_open_wide_at_freezing(self):
        air = night(replace(self.p, window=20.0), 2, opened=True, outdoor=-10.0)
        self.assertTrue(math.isfinite(air))
        self.assertGreaterEqual(air, -10.0)

    def test_ordinary_room_has_a_plausible_inertia(self):
        self.assertGreater(time_constant(self.p), 15)
        self.assertLess(time_constant(self.p), 150)


def history(p, days=2):
    """A room made with known parameters: a daily outdoor swing, sun at noon, heating mornings, an evening airing."""
    out, air, walls, when = [], 20.0, 20.0, START
    for _ in range(int(days * 86400 / STEP)):
        hour = (when.hour + 1) % 24 + when.minute / 60
        u = Inputs(outdoor=10 + 5 * math.sin(2 * math.pi * (hour - 9) / 24), sun=max(0.0, 600 * math.sin(math.pi * (hour - 7) / 11)),
                   heating=0.6 if 6 <= hour < 8 else 0.0, windows=(WINDOW,) if 19 <= hour < 19.25 else (), hour=hour)
        out.append(Sample(when, round(air, 1), u))
        air, walls = step(p, air, walls, u)
        when += timedelta(seconds=STEP)
    return out


class FitTest(unittest.TestCase):
    def test_it_finds_back_a_known_room_better_than_its_ordinary_start(self):
        base = ordinary(ROOM)
        truth = replace(base, h_env=base.h_env * 0.6, window=0.4, heat=base.heat * 0.5, gains=120.0)
        data = history(truth)
        start = score(base, data)
        found = score(fit(base, data, iterations=120), data)
        self.assertLess(found.three, start.three / 2)
        self.assertLess(found.three, 0.15)

    def test_the_test_days_stay_out_of_the_fit(self):
        data = history(ordinary(ROOM), days=1)
        until = data[len(data) // 2].when
        both = score(ordinary(ROOM), data, until=until).forecasts + score(ordinary(ROOM), data, since=until).forecasts
        self.assertEqual(both, score(ordinary(ROOM), data).forecasts)


if __name__ == "__main__":
    unittest.main()
