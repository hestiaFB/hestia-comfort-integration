"""The nightly learning in a process of its own (PLAN-OPTIMISATION.md, point 10) learns exactly what it learns in Home
Assistant's threads; each room gets only its own history."""
import pickle
import subprocess
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.hestia_comfort.advisor_home import NIGHT_WORKER, room_history
from custom_components.hestia_comfort.advisor.house import Opening, Room
from custom_components.hestia_comfort.advisor.nightly import MIN_DAYS, RoomSpec, learn_room
from custom_components.hestia_comfort.advisor.observe import Series
from custom_components.hestia_comfort.advisor.physics.thermal import STEP, Inputs, ordinary, step

PARIS = ZoneInfo("Europe/Paris")
WINDOW = "binary_sensor.fenetre_test_contact"
ROOM = Room("test", "Test", volume=30.0, openings=(Opening(WINDOW, "window", area=1.2, height=1.2),), heating_power=1000)
TRUTH = replace(ordinary(ROOM), h_env=25.0, window=0.6)
SPEC = RoomSpec("Test", "sensor.test_temperature", {WINDOW: (1.0, 1.2)})


def recorded(days):
    """A room simulated by its true twin, the window open an hour every morning (as tests/test_advisor_nightly.py)."""
    start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    temperature, outdoor, contact = [], [], [{"entity_id": WINDOW, "state": "off", "last_changed": start.isoformat()}]
    air = walls = 20.0
    for k in range(int(days * 86400 / STEP)):
        when = start + timedelta(seconds=k * STEP)
        hour = when.hour + when.minute / 60
        te = 12.0 + 5.0 * math.sin(2 * math.pi * (hour - 9) / 24)
        temperature.append({"entity_id": SPEC.temperature, "state": f"{air:.2f}", "last_changed": when.isoformat()})
        outdoor.append({"entity_id": "sensor.dehors", "state": f"{te:.2f}", "last_changed": when.isoformat()})
        air, walls = step(TRUTH, air, walls, Inputs(te, windows=((1.2, 1.2),) if 8 <= hour < 9 else (), hour=hour))
        if when.minute == 0 and hour in (8, 9):
            contact.append({"entity_id": WINDOW, "state": "on" if hour == 8 else "off", "last_changed": when.isoformat()})
    return {SPEC.temperature: temperature, "sensor.dehors": outdoor, WINDOW: contact,
            "sensor.autre_piece": temperature[:3]}, start + timedelta(days=days)


class NightProcess(unittest.TestCase):
    def test_a_process_learns_what_a_thread_learns(self):
        history, now = recorded(MIN_DAYS + 1)
        mine = room_history(history, SPEC, "sensor.dehors", "sensor.dehors_humidite", {})
        self.assertNotIn("sensor.autre_piece", mine)
        arguments = (SPEC, {"heat": asdict(replace(TRUTH, h_env=60.0, window=2.0))}, mine, Series([]), now,
                     "sensor.dehors", "sensor.dehors_humidite", (43.4, 5.5), PARIS, {})
        direct = learn_room(*arguments)
        # As advisor_home.py starts it: isolated, the arguments pickled on its input, Home Assistant never imported.
        done = subprocess.run([sys.executable, "-I", str(NIGHT_WORKER)], input=pickle.dumps(arguments), capture_output=True, check=True)
        apart = pickle.loads(done.stdout)
        self.assertNotIn(b"homeassistant", done.stderr)
        self.assertEqual(apart, direct)
        self.assertTrue(apart[1]["appris"])


if __name__ == "__main__":
    unittest.main()
