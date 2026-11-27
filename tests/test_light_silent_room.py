"""A room whose sensor went silent never holds the light, the light's memory survives a restart, and the room says why."""
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from custom_components.hestia_comfort import light_driver
from custom_components.hestia_comfort.advisor_home import NO_AIR, silent_sensor
from custom_components.hestia_comfort.engine import light_plan as lp
from custom_components.hestia_comfort.room.advice import banner_level

CALM = {"gesture": "none", "level": "calm", "mood": "calm"}
WAITING = {"gesture": "none", "level": "neutral", "mood": "neutral"}
GESTURE = {"gesture": "open", "level": "action", "mood": "action"}


class SilentRoomLightTest(unittest.TestCase):
    def test_a_waiting_room_does_not_outrank_the_calm_ones(self):
        # 27 November: the bathroom « Conseil en attente » held the LED orange on its last gesture, the house calm.
        self.assertEqual(lp.state_key(lp.for_light([CALM, WAITING, CALM])), "calm")

    def test_a_gesture_still_wins(self):
        self.assertEqual(lp.state_key(lp.for_light([WAITING, GESTURE, CALM])), "action")

    def test_only_rooms_without_a_look_leave_the_light_as_it_is(self):
        self.assertIsNone(lp.for_light([WAITING]))
        self.assertIsNone(lp.for_light([]))


class SilentSensorTest(unittest.TestCase):
    def state(self, value, since):
        return SimpleNamespace(state=value, entity_id="sensor.temperature_piece", last_changed=since)

    def test_a_silent_sensor_is_said_with_since_when(self):
        since = datetime(2026, 11, 25, 0, 43, tzinfo=timezone.utc)
        now = datetime(2026, 11, 27, 17, 0, tzinfo=timezone.utc)
        with patch("homeassistant.util.dt.DEFAULT_TIME_ZONE", timezone(timedelta(hours=1))):
            said = silent_sensor(self.state("unavailable", since), now.astimezone(timezone(timedelta(hours=1))))
        self.assertEqual(said["title"], "Capteur muet")
        self.assertIn("depuis le 25 novembre à 1 h 43", said["phrase"])
        self.assertEqual(said["manque"], "temperature")
        self.assertEqual(said["muet"], "sensor.temperature_piece")

    def test_a_sensor_that_answers_is_not_silent(self):
        self.assertIsNone(silent_sensor(self.state("19.5", datetime.now(timezone.utc)), datetime.now(timezone.utc)))
        self.assertIsNone(silent_sensor(None, datetime.now(timezone.utc)))

    def test_a_missing_measure_is_to_check_not_starting(self):
        self.assertEqual(banner_level({**NO_AIR}), ("neutral", "À vérifier"))
        self.assertEqual(banner_level({"regle": "waiting", "geste": "nothing"}), ("neutral", "Démarrage"))


class FakeStore:
    saved = {}

    def __init__(self, *_):
        pass

    async def async_load(self):
        return FakeStore.saved.get("data")

    def async_delay_save(self, data, _delay):
        FakeStore.saved["data"] = data()


class LightMemoryTest(unittest.TestCase):
    def setUp(self):
        FakeStore.saved = {}

    def driver(self):
        with patch.object(light_driver, "Store", FakeStore):
            return light_driver.LightDriver(SimpleNamespace(), SimpleNamespace(home={}))

    def test_how_the_light_was_survives_a_restart(self):
        before = self.driver()
        before.kept = {"light.led": {"on": True, "rgb_color": [170, 214, 229], "brightness": 102}}
        before.speeds = {"light.led": ("number.led_speed", "128")}
        before.mains = {"light.strip": {"kept": {"on": False}, "users": {"light.led"}}}
        before._save()
        after = self.driver()
        asyncio.run(after.async_load())
        self.assertEqual(after.kept, before.kept)
        self.assertEqual(after.speeds, before.speeds)
        self.assertEqual(after.mains, before.mains)

    def test_nothing_is_written_while_nothing_changes(self):
        driver = self.driver()
        asyncio.run(driver.async_load())
        driver._save()
        self.assertNotIn("data", FakeStore.saved)
        driver.kept["light.led"] = {"on": False}
        driver._save()
        self.assertIn("data", FakeStore.saved)


if __name__ == "__main__":
    unittest.main()
