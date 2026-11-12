"""The house's day of 12 November (moteur 3.15.0), read with Frank.

1. The line's subject held under the same title, « best » then « kept » included.
2. A drizzle switched « Gardez fermé : il pleut » on and off six times in three hours: the rain is held 30 min.
3. The bedrooms' « Ouvrez » in the evening, never followed three evenings running: a heated room airs for a set length.
4. « Aérez 25 min », then « Aérez 10 min vers 21 h 30 » five minutes after.
6. The pellet stove at 0 % still burns: its idle flame warms (Frank: « il tourne au ralenti mais il chauffe quand même »).
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.hestia_comfort.advisor.bench.history import lit_power  # noqa: E402
from custom_components.hestia_comfort.advisor.physics.heaters import heater  # noqa: E402
from custom_components.hestia_comfort.advisor.safety import RAIN_KEPT, rain_held  # noqa: E402
from custom_components.hestia_comfort.room.advice import house_given_now  # noqa: E402
from dataclasses import replace  # noqa: E402
from custom_components.hestia_comfort.advisor.decide import (Gesture, Now, Thermostat, Twins,  # noqa: E402
                                                             simulate)
from custom_components.hestia_comfort.advisor.house import Opening, Room  # noqa: E402
from custom_components.hestia_comfort.advisor.physics.thermal import Inputs, ordinary  # noqa: E402

WEST = Opening("binary_sensor.fenetre_p_contact", "window", area=1.33, height=0.95)
ROOM = Room("salon", "Salon", volume=90.0, openings=(WEST,), heating_power=0)

NOW = datetime(2026, 11, 12, 11, 0, tzinfo=timezone.utc)


def hass_with(**states):
    return SimpleNamespace(states=SimpleNamespace(get=lambda e: states.get(e)),
                           config_entries=SimpleNamespace(async_entries=lambda domain: []))


def poele(action, power):
    return SimpleNamespace(state="heat", attributes={"hvac_action": action, "power_percent": power})


class RainHeldTests(unittest.TestCase):
    def test_a_dry_reading_just_after_the_rain_keeps_it(self):
        t = NOW.timestamp()
        rate, last = rain_held(1.8, None, t)
        self.assertEqual(rate, 1.8)
        rate, last = rain_held(0.0, last, t + 10 * 60)
        self.assertEqual(rate, 1.8)
        rate, last = rain_held(0.0, last, t + (RAIN_KEPT + 1) * 60)
        self.assertEqual((rate, last), (0.0, None))

    def test_unknown_stays_unknown(self):
        self.assertEqual(rain_held(None, None, NOW.timestamp()), (None, None))


class IdleStoveTests(unittest.TestCase):
    def test_a_pellet_stove_burning_at_zero_gives_its_idle_flame(self):
        self.assertEqual(heater("pellet").idle, 0.3)
        hass = hass_with(**{"climate.poele": poele("heating", 0)})
        self.assertEqual(house_given_now(hass, "climate.poele", {"climate.poele": "pellet"}), 0.3)
        self.assertEqual(house_given_now(hass, "climate.poele", {"climate.poele": "pellet"}), 0.3)
        hass = hass_with(**{"climate.poele": poele("heating", 75)})
        self.assertEqual(house_given_now(hass, "climate.poele", {"climate.poele": "pellet"}), 0.75)

    def test_idle_or_waiting_it_gives_nothing(self):
        for state in (poele("idle", 0), poele("idle", 100)):
            hass = hass_with(**{"climate.poele": state})
            self.assertEqual(house_given_now(hass, "climate.poele", {"climate.poele": "pellet"}), 0.0)

    def test_the_night_learns_with_the_idle_flame(self):
        history = {"climate.poele": [
            {"last_updated": NOW.isoformat(), "attributes": {"power_percent": 0, "hvac_action": "heating"}},
            {"last_updated": (NOW + timedelta(minutes=30)).isoformat(), "attributes": {"power_percent": 0, "hvac_action": "idle"}}]}
        series = lit_power(history, "climate.poele", heater("pellet").idle)
        self.assertEqual(series.at(NOW + timedelta(minutes=5)), 0.3)
        self.assertEqual(series.at(NOW + timedelta(minutes=35)), 0.0)



class IdleStoveSimulatedTests(unittest.TestCase):
    """12 November, 13 h 07: the stove at 0 %, still burning, its set point held; the room it stands in is warmer than
    its target. Before, the twin put it out at once."""

    def setUp(self):
        self.twins = Twins(heat=replace(ordinary(ROOM), share=0.4), windows=(WEST.size,),
                           house_thermostat=Thermostat(target=21.5, inside=0.8, kind="pellet"), house_power=8500.0,
                           house_now=0.0, house_idle=0.3)
        self.coming = [(Inputs(15.0, hour=13 + k / 12, house_heat=0.0), None) for k in range(36)]
        self.now = Now(air=22.0, walls=21.5, opened=(), house_running=True)

    def test_burning_it_gives_its_idle_flame(self):
        # The house's heat now holds the idle flame (AdvisorHome.house_heat, `house_given_now`).
        lit = [(replace(u, house_heat=0.3 * 8500.0), w) for u, w in self.coming]
        path = simulate(self.twins, self.now, lit, Gesture("nothing"))
        self.assertTrue(all(s >= 0.3 - 1e-9 for s in path.stove))
        out = simulate(self.twins, replace(self.now, house_running=False), self.coming, Gesture("nothing"))
        self.assertGreater(path.air[-1], out.air[-1] + 0.3)

    def test_its_schedule_puts_it_out(self):
        twins = replace(self.twins, house_thermostat=replace(self.twins.house_thermostat, then=14.0, at=30.0))
        lit = [(replace(u, house_heat=0.3 * 8500.0), w) for u, w in self.coming]
        path = simulate(twins, self.now, lit, Gesture("nothing"))
        self.assertLess(path.stove[-1], 0.05)

    def test_stopping_it_stops_the_flame(self):
        lit = [(replace(u, house_heat=0.3 * 8500.0), w) for u, w in self.coming]
        path = simulate(self.twins, self.now, lit, Gesture("heat_stop"))
        self.assertLess(path.stove[-1], 0.05)


if __name__ == "__main__":
    unittest.main()
