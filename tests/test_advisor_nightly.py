"""Learning every night: a twin started wrong comes closer to the room it watches, keeps only what forecasts better,
and counts the gestures it saw; with too few days it only counts them."""
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.house import Opening, Room
from advisor.nightly import MIN_DAYS, RoomSpec, _merge, learn_room
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
        self.assertEqual(report["gestes"]["heat"], MIN_DAYS - 1)     # one airing a morning
        when, forecast, measured = entry["gestures"]["heat"][0]
        self.assertLess(measured, 0)
        self.assertAlmostEqual(forecast, measured, delta=0.1)       # the true twin forecasts it right

    def test_gestures_seen_again_replace_the_old_ones_and_old_ones_fade(self):
        now = datetime(2026, 12, 31, tzinfo=timezone.utc)
        kept = [["2026-10-01T08:00:00+00:00", -0.2, -0.1], ["2026-12-30T08:00:00+00:00", -0.3, -0.3]]
        found = [["2026-12-30T08:00:00+00:00", -0.25, -0.3]]
        merged = _merge(kept, found, now - timedelta(days=2), now, now)
        self.assertEqual(merged, found)     # October is older than 60 days; the 30th was seen again


if __name__ == "__main__":
    unittest.main()
