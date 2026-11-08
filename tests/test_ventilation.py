"""The VMC's advice for automations (engine/ventilation.py): « VMC conseillée » and « Turbo conseillé ».

Frank, 7 November: the Chambre P's extractor ran all night, « VMC conseillée » kept on by a humid room it could not dry.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from engine.ventilation import OFF_DELAY, Memory, advise  # noqa: E402

NOW = datetime(2026, 11, 7, 14, 0, tzinfo=timezone.utc)
VMC = {"sources": {"ventilation": "fan.contacteurs_l1"}}
TWO_SPEEDS = {"sources": {"ventilation": "fan.contacteurs_l1", "ventilation_boost": "fan.contacteurs_l2"}}
DELAY = OFF_DELAY.seconds // 60


def view(humidity="normal", measured=60, night=False, inside=13.5, outside=7.0, shower=None, geste="nothing", minutes=None,
         co2="not_configured"):
    return {"verdict": {"humidity": humidity, "gesture": "none"},
            "observations": {"indoor_humidity": {"value": measured}},
            "assessment": {"indoor_absolute_humidity": inside, "outdoor_absolute_humidity": outside,
                           "features": {"air": {"co2_status": co2}, "humidity": {"shower": shower}}},
            "advice3": {"geste": geste, "minutes": minutes, "nuit": night}}


def run(config, steps, memory=None):
    """Each step (minutes from NOW, view) → the advice at that minute."""
    memory = memory or Memory()
    return [advise(v, config, memory, NOW + timedelta(minutes=m)) for m, v in steps]


SHOWER = {"since": NOW.isoformat(), "minutes": 5, "base": 60, "peak": 80}


class ContinuousTests(unittest.TestCase):
    def test_a_classic_vmc_never_stops_its_slow_speed(self):
        config = {**VMC, "ventilation_mode": "continuous"}
        found = run(config, [(0, view()), (60, view(night=True)), (120, view(humidity="very_dry"))])
        self.assertTrue(all(a["slow"] for a in found))
        self.assertIsNone(found[0]["fast"])


class OnDemandTests(unittest.TestCase):
    def test_it_is_the_default_and_starts_when_the_air_is_humid_and_drier_outside(self):
        found = run(VMC, [(0, view()), (1, view(humidity="humid", measured=72))])
        self.assertEqual([a["slow"] for a in found], [False, True])
        self.assertEqual(found[1]["mode"], "on_demand")

    def test_never_when_the_outdoor_air_holds_as_much_water(self):
        self.assertFalse(run(VMC, [(0, view(humidity="very_humid", inside=9.0, outside=8.8))])[0]["slow"])

    def test_it_stops_at_the_rooms_bedtime(self):
        """Frank's night: 78 % at 23 h, the extractor ran until 8 h."""
        wet = lambda night: view(humidity="very_humid", measured=78, night=night)  # noqa: E731
        found = run(VMC, [(0, wet(False)), (30, wet(True)), (30 + DELAY, wet(True))])
        self.assertEqual([a["slow"] for a in found], [True, True, False])

    def test_an_hour_that_does_not_dry_rests_it_two_hours(self):
        humid = lambda m: view(humidity="very_humid", measured=m)  # noqa: E731
        memory = Memory()
        found = run(VMC, [(0, humid(78)), (60, humid(78)), (60 + DELAY, humid(78))], memory)
        self.assertEqual([a["slow"] for a in found], [True, True, False])
        self.assertFalse(run(VMC, [(120, humid(78))], memory)[0]["slow"])
        self.assertTrue(run(VMC, [(181, humid(78))], memory)[0]["slow"])

    def test_an_hour_that_dries_keeps_it_running_while_a_little_humid(self):
        found = run(VMC, [(0, view(humidity="humid", measured=70)), (60, view(humidity="slightly_humid", measured=65)),
                          (90, view(humidity="normal", measured=60)), (90 + DELAY, view(measured=60))])
        self.assertEqual([a["slow"] for a in found], [True, True, True, False])

    def test_a_humidity_that_wavers_a_minute_does_not_stop_it(self):
        found = run(VMC, [(0, view(humidity="humid", measured=72)), (10, view(measured=59)),
                          (11, view(humidity="slightly_humid", measured=61))])
        self.assertTrue(all(a["slow"] for a in found))

    def test_no_run_starts_before_the_advisor_knows_the_night(self):
        """Home Assistant restarted at 23 h 45: the first reading has no advice yet."""
        for advice in (None, {"title": "Conseil en attente", "geste": "nothing"}):
            starting = {**view(humidity="very_humid", measured=78), "advice3": advice}
            self.assertFalse(run(VMC, [(0, starting)])[0]["slow"])

    def test_too_much_co2_runs_it_too(self):
        self.assertTrue(run(VMC, [(0, view(co2="high"))])[0]["slow"])

    def test_no_vmc_no_advice(self):
        found = advise(view(humidity="very_humid"), {"sources": {}}, Memory(), NOW)
        self.assertEqual((found["slow"], found["fast"]), (False, None))


class TurboTests(unittest.TestCase):
    def test_a_shower_runs_the_turbo_and_the_slow_speed_with_it_even_at_night(self):
        found = run(TWO_SPEEDS, [(0, view(night=True, shower=SHOWER))])[0]
        self.assertEqual((found["slow"], found["fast"]), (True, True))

    def test_the_turbo_ends_with_the_shower(self):
        found = run(TWO_SPEEDS, [(0, view(shower=SHOWER)), (30, view()), (30 + DELAY, view())])
        self.assertEqual([a["fast"] for a in found], [True, True, False])

    def test_the_advisors_turbo_lasts_the_minutes_it_says(self):
        found = run(TWO_SPEEDS, [(0, view(geste="boost", minutes=15)), (14, view()), (16, view()), (16 + DELAY, view())])
        self.assertEqual([a["fast"] for a in found], [True, True, True, False])

    def test_the_advisors_stop_ends_it(self):
        found = run(TWO_SPEEDS, [(0, view(geste="boost", minutes=30)), (5, view(geste="boost_off")), (5 + DELAY, view())])
        self.assertEqual([a["fast"] for a in found], [True, True, False])

    def test_no_turbo_without_its_entity(self):
        self.assertIsNone(run(VMC, [(0, view(shower=SHOWER))])[0]["fast"])


if __name__ == "__main__":
    unittest.main()


class ResumeTests(unittest.TestCase):
    """8 November at 12 h 53, Home Assistant restarted: the extractor stopped a minute, « VMC conseillée » forgotten until
    the advisor spoke again (entities.py `resume_ventilation`)."""

    def test_running_before_it_goes_on_while_the_advisor_is_silent(self):
        from engine.ventilation import resume
        memory = Memory()
        resume(memory, True, NOW)
        waiting = view(humidity="humid", measured=72)
        waiting["advice3"] = {}
        self.assertTrue(advise(waiting, VMC, memory, NOW)["slow"])

    def test_it_stops_as_usual_once_the_advisor_says_night(self):
        from engine.ventilation import resume
        memory = Memory()
        resume(memory, True, NOW)
        found = run(VMC, [(0, view(humidity="humid", night=True)), (DELAY, view(humidity="humid", night=True))], memory)
        self.assertEqual([f["slow"] for f in found], [True, False])

    def test_stopped_before_nothing_starts_on_a_guess(self):
        from engine.ventilation import resume
        memory = Memory()
        resume(memory, False, NOW)
        waiting = view(humidity="humid")
        waiting["advice3"] = {}
        self.assertFalse(advise(waiting, VMC, memory, NOW)["slow"])
