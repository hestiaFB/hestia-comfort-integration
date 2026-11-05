"""Versatile Thermostat: what Hestia-FB reads from it, and how it changes « Rallumez le chauffage »."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from engine import thermostat
from engine.assessment import Settings, assess
from engine.sources import Reading

NOW = datetime(2026, 10, 26, 18, tzinfo=timezone.utc)
# Versatile Thermostat 7 and later: grouped attributes (10.6.1 here).
GROUPED = {"hvac_action": "off", "hvac_mode": "off", "preset_mode": "comfort", "temperature": 19.5,
           "specific_states": {"hvac_off_reason": "hvac_off_manual", "temperature_slope": -0.4, "is_device_active": False},
           "preset_temperatures": {"frost_temp": 7, "eco_temp": 17, "comfort_temp": 19, "boost_temp": 0},
           "window_manager": {"window_state": "off", "window_auto_state": "on"},
           "presence_manager": {"presence_state": "on"}}
# Earlier versions: flat attributes.
FLAT = {"hvac_action": "heating", "preset_mode": "eco", "temperature": 17, "hvac_off_reason": None, "temperature_slope": 0.2,
        "eco_temp": 17, "comfort_temp": 19.5, "frost_temp": 7, "window_state": "off", "motion_state": "off"}


def run(ti, vt, previous=None, now=NOW, reference=True, heating="off", **context):
    values = {"indoor_temperature": ti, "outdoor_temperature": 10, "indoor_humidity": 55, "outdoor_humidity": 80, "heating": heating}
    readings = {k: Reading(v, "valid", "sensor.x") for k, v in values.items()}
    return assess(readings, Settings(minimum=20, maximum=24), previous, {}, None, {}, now,
                  context={"heated": True, "thermostat": vt, "thermostat_reference": reference, **context})


class Reading_(unittest.TestCase):
    def test_grouped_attributes(self):
        t = thermostat.read("off", GROUPED)
        self.assertEqual((t["mode"], t["off_reason"], t["comfort"], t["eco"], t["slope"]), ("off", "manual", 19, 17, -0.4))
        self.assertTrue(t["window"])
        self.assertTrue(t["occupied"])

    def test_flat_attributes(self):
        t = thermostat.read("heat", FLAT)
        self.assertEqual((t["mode"], t["preset"], t["comfort"], t["slope"]), ("heat", "eco", 19.5, 0.2))
        self.assertIsNone(t["off_reason"])
        self.assertFalse(t["window"])
        self.assertFalse(t["occupied"])
        self.assertTrue(thermostat.lowered(t))

    def test_unused_preset_and_reference_bounds(self):
        t = thermostat.read("off", GROUPED)
        self.assertNotIn("boost", t)
        # The set point it aims at now (19.5 °C), else its comfort temperature.
        self.assertEqual(thermostat.reference(t, 24), 19.5)
        self.assertEqual(thermostat.reference({**t, "target": None}, 24), 19)
        self.assertIsNone(thermostat.reference(t, 19))


class Advice(unittest.TestCase):
    def test_set_point_stands_as_minimum(self):
        vt = thermostat.read("off", GROUPED)
        # 19.6 °C: under the room's own 20 °C, above the thermostat's 19.5 °C set point.
        self.assertNotEqual(run(19.6, vt).reason, "heat_needed")
        self.assertEqual(run(19.6, vt, reference=False).reason, "heat_needed")

    def test_eco_or_frost_set_point_is_not_too_cool(self):
        # Chambre P, 26 October 2026: thermostat off on its eco preset, 17 °C; the room at 18.2 °C is where it was asked.
        eco = thermostat.read("off", {**GROUPED, "preset_mode": "eco", "temperature": 17})
        self.assertNotEqual(run(18.2, eco).reason, "heat_needed")
        # Frost protection is a safeguard: the comfort temperature (19.5 °C) stays the minimum, the room at 15 °C is cool,
        # and still not told to switch the heating on (a stove kept at 14 °C).
        frost = thermostat.read("heat", {**FLAT, "preset_mode": "frost_protection", "temperature": 14})
        a = run(15, frost, heating="idle")
        self.assertEqual(a.reason, "heat_needed")
        self.assertTrue(a.features["warmth"]["thermostat"]["lowered"])
        self.assertIn(a.level, ("calm", "neutral"))

    def test_off_by_hand_asks_after_half_an_hour(self):
        vt = {**thermostat.read("off", GROUPED), "slope": None}
        first = run(17.5, vt)
        self.assertEqual(run(17.5, vt, first, NOW + timedelta(minutes=31)).level, "action")

    def test_off_for_an_open_window_or_its_own_stop_is_not_the_persons(self):
        for reason in ("hvac_off_window_detection", "hvac_off_auto_start_stop", "hvac_off_central_mode"):
            attrs = {**GROUPED, "specific_states": {**GROUPED["specific_states"], "hvac_off_reason": reason, "temperature_slope": None}}
            vt = thermostat.read("off", attrs)
            first = run(17.5, vt)
            later = run(17.5, vt, first, NOW + timedelta(minutes=31))
            self.assertIn(later.level, ("calm", "neutral"), reason)
            self.assertEqual(later.features["warmth"]["thermostat"]["off_reason"], thermostat.OFF_REASONS[reason])

    def test_eco_preset_aims_lower_on_purpose(self):
        vt = thermostat.read("heat", FLAT)
        # Under its eco set point (17 °C) the room is cool, and still the thermostat's to warm: no « Rallumez ».
        a = run(15.5, vt, heating="idle")
        self.assertEqual(a.reason, "heat_needed")
        self.assertTrue(a.features["warmth"]["thermostat"]["lowered"])
        self.assertIn(a.level, ("calm", "neutral"))

    def test_slope_stands_in_for_a_twin_still_learning(self):
        attrs = {**GROUPED, "specific_states": {**GROUPED["specific_states"], "temperature_slope": 0.6}}
        vt = thermostat.read("off", attrs)
        first = run(17.5, vt)
        later = run(17.5, vt, first, NOW + timedelta(minutes=31))
        self.assertTrue(later.features["warmth"]["warming"])
        self.assertIn(later.level, ("calm", "neutral"))

    def test_window_seen_by_the_thermostat_is_said(self):
        a = run(21, thermostat.read("off", GROUPED))
        self.assertTrue(a.features["thermostat"]["window"])

    def test_presence_followed_by_the_thermostat(self):
        vt = {**thermostat.read("off", GROUPED), "slope": None}
        a = run(17.5, vt, None, NOW)
        self.assertTrue(a.features["warmth"]["occupied"])


if __name__ == "__main__":
    unittest.main()
