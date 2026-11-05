"""Learning every night: a twin started wrong comes closer to the room it watches, keeps only what forecasts better,
and counts the gestures it saw; with too few days it only counts them."""
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.house import Opening, Room
from advisor.nightly import MIN_DAYS, RoomSpec, _merge, judged, learn_room
from advisor.physics.fit import _nelder_mead
from advisor.observe import Series
from advisor.physics.thermal import STEP, Inputs, ordinary, step

PARIS = ZoneInfo("Europe/Paris")
WINDOW = "binary_sensor.fenetre_test_contact"
ROOM = Room("test", "Test", volume=30.0, openings=(Opening(WINDOW, "window", area=1.2, height=1.2),), heating_power=1000)
TRUTH = replace(ordinary(ROOM), h_env=25.0, window=0.6)
SPEC = RoomSpec("Test", "sensor.test_temperature", {WINDOW: (1.0, 1.2)})


def recorded(days, truth=TRUTH):
    """A room simulated by its true twin: cool nights, mild days, the window open an hour every morning."""
    start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    temperature, outdoor, contact = [], [], []
    air = walls = 20.0
    for k in range(int(days * 86400 / STEP)):
        when = start + timedelta(seconds=k * STEP)
        hour = when.hour + when.minute / 60
        te = 12.0 + 5.0 * math.sin(2 * math.pi * (hour - 9) / 24)
        opened = 8 <= hour < 9
        stamp = when.isoformat()
        # The air measured at `when`, then what acts over the next five minutes.
        temperature.append({"entity_id": SPEC.temperature, "state": f"{air:.2f}", "last_changed": stamp})
        outdoor.append({"entity_id": "sensor.dehors", "state": f"{te:.2f}", "last_changed": stamp})
        air, walls = step(truth, air, walls, Inputs(te, windows=((1.2, 1.2),) if opened else (), hour=hour))
        if when.minute == 0 and hour in (8, 9):
            contact.append({"entity_id": WINDOW, "state": "on" if hour == 8 else "off", "last_changed": stamp})
    contact.insert(0, {"entity_id": WINDOW, "state": "off", "last_changed": start.isoformat()})
    return {SPEC.temperature: temperature, "sensor.dehors": outdoor, WINDOW: contact}, start + timedelta(days=days)


def learn(history, now, entry):
    return learn_room(SPEC, entry, history, Series([]), now, "sensor.dehors", "sensor.dehors_humidite", (43.4, 5.5), PARIS)


class Nightly(unittest.TestCase):
    def test_a_twin_started_wrong_comes_closer_and_keeps_only_better(self):
        history, now = recorded(MIN_DAYS + 1)
        wrong = replace(TRUTH, h_env=60.0, window=2.0)
        entry, report = learn(history, now, {"heat": asdict(wrong)})
        self.assertTrue(report["appris"])
        self.assertTrue(report["chaleur"]["garde"])
        self.assertLess(sum(report["chaleur"]["apres"]), sum(report["chaleur"]["avant"]))
        self.assertLess(abs(entry["heat"]["h_env"] - TRUTH.h_env), abs(wrong.h_env - TRUTH.h_env))

    def test_with_too_few_days_it_only_counts_the_gestures(self):
        history, now = recorded(MIN_DAYS - 1)
        entry, report = learn(history, now, {"heat": asdict(TRUTH)})
        self.assertFalse(report["appris"])
        self.assertEqual(entry["heat"], asdict(TRUTH))
        # One airing a morning, judged an hour after it was shut against the twin without it (advisor/notes.py): the
        # second morning's, in a room already cool, left 0.2 °C an hour on — too little to be read.
        self.assertEqual(report["gestes"]["heat"], 1)
        when, announced, measured = entry["gestures"]["heat"][0]
        self.assertLess(measured, 0)
        self.assertAlmostEqual(announced, measured, delta=0.1)      # the true twin forecasts it right

    def test_gestures_seen_again_replace_the_old_ones_and_old_ones_fade(self):
        now = datetime(2026, 12, 31, tzinfo=timezone.utc)
        kept = [["2026-10-01T08:00:00+00:00", -0.2, -0.1], ["2026-12-30T08:00:00+00:00", -0.3, -0.3]]
        found = [["2026-12-30T08:00:00+00:00", -0.25, -0.3]]
        merged = _merge(kept, found, now - timedelta(days=2), now, now)
        self.assertEqual(merged, found)     # October is older than 60 days; the 30th was seen again

    def test_an_airing_the_night_cannot_read_again_is_kept(self):
        # Noted as it ended (advisor/opening.py), then a gap in the recorder: the night does not find it, it stays.
        now = datetime(2026, 11, 4, 3, 30, tzinfo=timezone.utc)
        noted = [["2026-11-03T18:19:00+00:00", -2.0, 0.25]]
        self.assertEqual(_merge(noted, [], now - timedelta(days=3), now, now), noted)
        found = [["2026-11-03T18:15:00+00:00", -1.9, 0.2]]
        self.assertEqual(_merge(noted, found, now - timedelta(days=3), now, now), found)


if __name__ == "__main__":
    unittest.main()


class Judged(unittest.TestCase):
    """Lab night of 5 November: the new twin is judged on one day only, a noisy judge."""

    def test_a_twin_as_good_within_five_percent_is_kept_as_even(self):
        self.assertEqual(judged(1.0, 0.9), (True, "meilleur"))
        self.assertEqual(judged(1.0, 1.04), (True, "egal"))
        self.assertEqual(judged(0.809, 1.063), (False, "pire"))      # Chambre P's humidity

    def test_a_twin_that_forecasts_nothing_is_never_kept(self):
        inf = float("inf")
        self.assertEqual(judged(inf, inf), (False, "pire"))
        self.assertEqual(judged(inf, 0.5), (True, "meilleur"))
        self.assertEqual(judged(1.0, float("nan")), (False, "pire"))

    def test_the_report_has_no_infinity(self):
        history, now = recorded(MIN_DAYS + 1)
        _, report = learn(history, now, {"heat": asdict(TRUTH)})
        self.assertIn(report["chaleur"]["verdict"], ("meilleur", "egal", "pire"))
        json.dumps(report, allow_nan=False)


class Search(unittest.TestCase):
    def test_the_search_stops_once_it_learns_nothing(self):
        calls = []

        def flat(x):
            calls.append(x)
            return 0.001
        _nelder_mead(flat, [0.0] * 7, [0.7] * 7, 400)
        # Lab, 5 November: a flat cost ran 3 328 evaluations, the shrinks multiplying them.
        self.assertLess(len(calls), 20)

    def test_it_still_finds_the_bottom(self):
        best = _nelder_mead(lambda x: (x[0] - 1.0) ** 2 + (x[1] + 2.0) ** 2 + 1.0, [0.0, 0.0], [0.5, 0.5], 400)
        self.assertAlmostEqual(best[0], 1.0, delta=0.05)
        self.assertAlmostEqual(best[1], -2.0, delta=0.05)

    def test_nothing_to_forecast_ends_at_once(self):
        calls = []
        _nelder_mead(lambda x: calls.append(x) or float("inf"), [0.0] * 5, [0.7] * 5, 400)
        self.assertEqual(len(calls), 6)


class Devices(unittest.TestCase):
    def test_each_purifier_start_is_counted_with_what_it_did(self):
        # Particles made all day, the purifier run an hour every afternoon: each start is a gesture, forecast right by
        # the true twin.
        from advisor.physics.air import ParticleParams, particles_step
        from advisor.physics.airfit import _run, vector
        from advisor.physics.fit import Sample
        truth = ParticleParams(30.0, 0.2, 5.0, 40.0)
        start, rows, level = datetime(2026, 10, 1, tzinfo=timezone.utc), [], 20.0
        for k in range(int(2 * 86400 / STEP)):
            when = start + timedelta(seconds=k * STEP)
            on = 15 <= when.hour < 16
            u = Inputs(15.0, hour=when.hour + when.minute / 60, purifier=150.0 if on else 0.0)
            rows.append((Sample(when, 20.0, u), level, 0.0))
            level = particles_step(truth, level, 0.3 * 30.0 * 0 + 9.0, u.hour, purifier=u.purifier)
        x = vector("particles", {"settling": 0.2, "outdoor": 5.0, "sources": 40.0, "rhythm_cos": 0.0, "rhythm_sin": 0.0},
                   (9.0 / 9.0, 1.0))
        found = _run("particles", x, 30.0, rows, start, start + timedelta(days=2))["devices"]
        self.assertEqual([d for *_, d in found], ["purify", "purify"])
        for measured, forecast, when, _ in found:
            self.assertLess(measured, -5)
            self.assertAlmostEqual(forecast, measured, delta=0.5)
