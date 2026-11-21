"""The morning of 21 November at the house (Confort 3.1.1, moteur 3.22.4), Salon · Cuisine and Chambre A.

- Salon · Cuisine: « Aérez 10 min côté Salon » for the particles. The French windows opened at 10 h 56 min 25 s; the card
  still said « Aérez » until 10 h 58 min 57 s, then « Aération en cours · refermez vers 11 h 06 », then « Refermez,
  particules 9 µg/m³ » at 11 h: the living room's sensor, the kitchen's still at 24. « Ouvrez aussi » never came.
- Chambre A: « l'humidité devrait passer à 58 % vers 8 h 15 » still shown at 10 h 57, the morning's plan kept by 3.1.0b18
  (`test_creneaux.PlanTests.test_a_plan_kept_by_an_older_version_is_planned_again`).
"""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.hestia_comfort.advisor.checks import Checker  # noqa: E402
from custom_components.hestia_comfort.advisor.decide import Gesture, Now, _open  # noqa: E402
from custom_components.hestia_comfort.room.advice import RoomAdvisor, first_windows  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_advisor_decide import TWINS  # noqa: E402

PARIS = timezone(timedelta(hours=1))
NOW = datetime(2026, 11, 21, 10, 58, 57, tzinfo=PARIS)

SALON_CUISINE = {
    "windows": {"ouest": (1.0, 1.2), "pf_d": (1.0, 2.1), "pf_g": (1.0, 2.1), "cuisine": (0.8, 1.0)},
    "orientations": {"ouest": (270.0, None), "pf_d": (180.0, None), "pf_g": (180.0, None), "cuisine": (90.0, None)},
    "parts": [{"name": "Salon", "windows": ["ouest", "pf_d", "pf_g"],
               "sources": ["co2", "indoor_humidity", "indoor_temperature", "pm25"],
               "measures": {"co2": "sensor.salon_co2", "pm25": "sensor.salon_pm25"}},
              {"name": "Cuisine", "windows": ["cuisine"], "sources": ["indoor_humidity", "indoor_temperature", "pm25", "voc"],
               "measures": {"pm25": "sensor.cuisine_pm25", "voc": "sensor.cuisine_voc"}}],
}


def state(value, changed=NOW - timedelta(minutes=3)):
    return SimpleNamespace(state=str(value), attributes={}, last_changed=changed)


def advisor(states, others):
    found = RoomAdvisor.__new__(RoomAdvisor)
    found.hass = SimpleNamespace(states=SimpleNamespace(get=states.get))
    found.checker = Checker()
    found.room = {"name": "Salon · Cuisine", "temperature": "sensor.salon_t", "humidity": None, "co2": None,
                  "particles": "sensor.salon_pm25", "voc": None, "others": others}
    return found


class TheWorstSensorOfASharedAir(unittest.TestCase):
    def test_the_kitchens_particles_count_for_the_room(self):
        room = advisor({"sensor.salon_t": state(20.4), "sensor.salon_pm25": state(9), "sensor.cuisine_pm25": state(24)},
                       {"particles": ["sensor.cuisine_pm25"]})
        found, doubts = room._measures(NOW)
        self.assertEqual((found["particles"], room.worst), (24.0, {"particles": "sensor.cuisine_pm25"}))
        self.assertEqual(doubts, [])
        # The Fiabilité page still shows the room's own sensor.
        self.assertEqual(room.sensors["particles"]["valeur"], 9.0)

    def test_the_room_s_own_sensor_when_it_is_the_worst(self):
        room = advisor({"sensor.salon_t": state(20.4), "sensor.salon_pm25": state(30), "sensor.cuisine_pm25": state(24)},
                       {"particles": ["sensor.cuisine_pm25"]})
        found, _ = room._measures(NOW)
        self.assertEqual((found["particles"], room.worst), (30.0, {}))

    def test_a_doubtful_sensor_in_another_part_is_left_aside(self):
        # The PM2.5 sensor at 999 µg/m³ of 31 October: out of range, never the worst.
        room = advisor({"sensor.salon_t": state(20.4), "sensor.salon_pm25": state(9), "sensor.cuisine_pm25": state(999)},
                       {"particles": ["sensor.cuisine_pm25"]})
        found, _ = room._measures(NOW)
        self.assertEqual((found["particles"], room.worst), (9.0, {}))
        room = advisor({"sensor.salon_t": state(20.4), "sensor.salon_pm25": state(9)}, {"particles": ["sensor.cuisine_pm25"]})
        self.assertEqual(room._measures(NOW)[0]["particles"], 9.0)

    def test_the_airing_opens_where_it_is_worst(self):
        self.assertEqual(first_windows(SALON_CUISINE, "particles", "sensor.cuisine_pm25"), (("cuisine",), "Cuisine"))
        self.assertEqual(first_windows(SALON_CUISINE, "particles", "sensor.salon_pm25"), (("pf_d", "pf_g"), "Salon"))
        # Without the worst known, as before: the first part that measures it.
        self.assertEqual(first_windows(SALON_CUISINE, "particles"), (("pf_d", "pf_g"), "Salon"))


class TheWindowSeenAtOnce(unittest.TestCase):
    def room(self):
        found = RoomAdvisor.__new__(RoomAdvisor)
        found.opening = found.opened_seen = found.opened_from = None
        return found

    def test_the_opening_counts_from_when_the_window_moved(self):
        # The decision 10 s after the opening saw it first; the one at OPEN_LEAST + 5 s must find it open a minute.
        room, moved = self.room(), datetime(2026, 11, 21, 10, 56, 25, tzinfo=PARIS)
        opened = ((1.0, 2.1),)
        self.assertEqual(room._opening(moved + timedelta(seconds=10), opened, 20.4, 55.0, moved)[0], moved)
        self.assertEqual(room._opening(moved + timedelta(seconds=65), opened, 20.2, 54.0, moved)[0], moved)

    def test_without_its_moment_the_step_s_own(self):
        room, now = self.room(), NOW
        self.assertEqual(room._opening(now, ((1.0, 2.1),), 20.4, 55.0)[0], now)
        # A clock ahead of the step's never puts the opening in the future.
        self.assertEqual(self.room()._opening(now, ((1.0, 2.1),), 20.4, 55.0, now + timedelta(seconds=5))[0], now)


class TheOtherSideOpenedAsWell(unittest.TestCase):
    def test_the_crossing_ends_with_the_household_s_airing(self):
        # Simulated left open for good after its minutes, the crossing cost hours of heat and was never advised.
        west, south, east = (1.0, 1.2), (1.0, 2.1), (0.8, 1.0)
        twins = replace(TWINS, windows=(west, south, east), bearings=(270.0, 180.0, 90.0))
        now = Now(air=20.4, walls=20.4, opened=(east,), closing_in=10.0)
        more = Gesture("open_more", 5)
        self.assertEqual(_open(more, now, twins, 0), (west, south, east))
        self.assertEqual(_open(more, now, twins, 1), (east,))
        self.assertEqual(_open(more, now, twins, 2), ())
        # Outside the cold season, nothing shuts it: left as it is.
        self.assertEqual(_open(more, replace(now, closing_in=None), twins, 12), (east,))


if __name__ == "__main__":
    unittest.main()
