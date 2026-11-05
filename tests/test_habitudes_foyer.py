"""The household's habits and « Votre maison » (niak-comfort/docs/HABITUDES-FOYER.md, validated by Frank on 5 November)."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.hestia_comfort.foyer import clean_foyer  # noqa: E402
from advisor.house import Opening, Room
from advisor.household import Habits, Sleep
from advisor.nightly import RoomSpec, samples
from advisor.observe import Series
from advisor.physics.surface import misted
from advisor.physics.thermal import ordinary

PARIS = ZoneInfo("Europe/Paris")
WINDOW = "binary_sensor.porte_fenetre_salon"
LOCATION = (43.6, 1.44)


class WeekendSleep(unittest.TestCase):
    """Question 6: « Le week-end, vous vous levez plus tard, vers 9 h »."""

    sleep = Sleep.of({"debut": "22:30", "fin": "07:00", "fin_weekend": "09:00"})

    def test_saturday_morning_is_still_night(self):
        self.assertTrue(self.sleep.asleep(datetime(2026, 11, 7, 8, 0, tzinfo=PARIS)))     # a Saturday
        self.assertFalse(self.sleep.asleep(datetime(2026, 11, 6, 8, 0, tzinfo=PARIS)))    # a Friday

    def test_waking_up_after_friday_night_is_the_weekend_hour(self):
        self.assertEqual(self.sleep.wake(datetime(2026, 11, 6, 23, 0, tzinfo=PARIS)), datetime(2026, 11, 7, 9, 0, tzinfo=PARIS))
        self.assertEqual(self.sleep.wake(datetime(2026, 11, 8, 23, 0, tzinfo=PARIS)), datetime(2026, 11, 9, 7, 0, tzinfo=PARIS))

    def test_without_it_the_week_hour_holds(self):
        sleep = Sleep.of({"debut": "22:30", "fin": "07:00"})
        self.assertIsNone(sleep.weekend_end)
        self.assertFalse(sleep.asleep(datetime(2026, 11, 7, 8, 0, tzinfo=PARIS)))


class Shutters(unittest.TestCase):
    """Questions 1 to 4: when the manual shutters are shut, and when nobody is home."""

    def test_variable_never_says_shut(self):
        habits = Habits.of({})
        night = datetime(2026, 11, 5, 2, 0, tzinfo=PARIS)
        self.assertFalse(habits.shut(night, away=True, summer=True, sun_on=True))

    def test_each_answer_shuts_at_its_moment(self):
        habits = Habits.of({"volets_absence": "fermes", "volets_nuit": "fermes", "volets_ete": "fermes"})
        noon = datetime(2026, 11, 5, 12, 0, tzinfo=PARIS)
        self.assertTrue(habits.shut(noon, away=True, summer=False, sun_on=False))
        self.assertFalse(habits.shut(noon, away=False, summer=False, sun_on=True))
        self.assertTrue(habits.shut(noon, away=False, summer=True, sun_on=True))
        self.assertTrue(habits.shut(datetime(2026, 11, 5, 2, 0, tzinfo=PARIS), away=False, summer=False, sun_on=False))

    def test_the_room_may_differ(self):
        habits = Habits.of({"volets_nuit": "fermes"}, {"volets_nuit": "ouverts"})
        self.assertFalse(habits.shut(datetime(2026, 11, 5, 2, 0, tzinfo=PARIS), away=False, summer=False, sun_on=False))

    def test_an_alarm_says_the_absence_else_the_empty_hours(self):
        habits = Habits.of({"journee_vide": {"de": "08:30", "a": "17:30"}})
        tuesday, saturday = datetime(2026, 11, 3, 10, 0, tzinfo=PARIS), datetime(2026, 11, 7, 10, 0, tzinfo=PARIS)
        self.assertTrue(habits.away(tuesday, None, has_alarm=False))
        self.assertFalse(habits.away(saturday, None, has_alarm=False))
        self.assertFalse(habits.away(tuesday, "disarmed", has_alarm=True))
        self.assertTrue(habits.away(saturday, "armed_away", has_alarm=True))

    def test_kept_as_a_setting(self):
        habits = Habits.of({"volets_absence": "fermes", "journee_vide": {"de": "08:30", "a": "17:30"},
                            "linge_pieces": ["salle"], "sommeil": {"debut": "22:00", "fin": "07:00", "fin_weekend": "09:00"}})
        again = Habits.of(habits.setting())
        self.assertEqual(again, habits)


class TheNightSeesTheShuttersShut(unittest.TestCase):
    """The Salon's sun, its French window's shutter shut while the household is away (Frank, 5 November)."""

    def history(self, alarm):
        start = datetime(2026, 11, 3, 9, 0, tzinfo=timezone.utc)
        rows = lambda e, v: [{"entity_id": e, "state": v, "last_changed": start.isoformat()}]
        return {"sensor.salon": rows("sensor.salon", "20"), "sensor.dehors": rows("sensor.dehors", "10"),
                WINDOW: rows(WINDOW, "off"), "alarm_control_panel.maison": rows("alarm_control_panel.maison", alarm)}, start

    def run_with(self, habits, alarm):
        spec = RoomSpec("Salon", "sensor.salon", {WINDOW: (1.8, 2.1)}, orientations={WINDOW: (180.0, False)},
                        manual=frozenset({WINDOW}), habits=habits, alarm="alarm_control_panel.maison")
        history, start = self.history(alarm)
        sun = Series([(start - timedelta(hours=1), 400.0)])
        return samples(history, spec, "sensor.dehors", sun, start + timedelta(hours=2), start + timedelta(hours=2),
                       LOCATION, PARIS)[0].inputs

    def test_shut_while_away(self):
        shut = self.run_with(Habits.of({"volets_absence": "fermes"}), "armed_away")
        home = self.run_with(Habits.of({"volets_absence": "fermes"}), "disarmed")
        self.assertLess(shut.facade, home.facade * 0.1)
        self.assertGreater(shut.shutter, 0.0)
        self.assertEqual(home.shutter, 0.0)

    def test_a_short_outing_leaves_them_open(self):
        """The alarm set 24 min at noon, the Salon's shutters open in full sun (Frank, 5 November): only an absence of
        two hours or more shuts them; the night knows how long each lasted."""
        habits = Habits.of({"volets_absence": "fermes"})
        start = datetime(2026, 11, 5, 11, 0, tzinfo=timezone.utc)
        spec = RoomSpec("Salon", "sensor.salon", {WINDOW: (1.8, 2.1)}, orientations={WINDOW: (180.0, False)},
                        manual=frozenset({WINDOW}), habits=habits, alarm="alarm_control_panel.maison")
        sun = Series([(start - timedelta(hours=1), 400.0)])

        def at_noon(back):
            history = {e: [{"entity_id": e, "state": v, "last_changed": start.isoformat()}]
                       for e, v in (("sensor.salon", "20"), ("sensor.dehors", "10"), (WINDOW, "off"))}
            history["alarm_control_panel.maison"] = [
                {"state": "disarmed", "last_changed": (start - timedelta(hours=3)).isoformat()},
                {"state": "armed_away", "last_changed": start.isoformat()},
                {"state": "disarmed", "last_changed": (start + back).isoformat()}]
            when = start + timedelta(minutes=10)
            return samples(history, spec, "sensor.dehors", sun, when, when, LOCATION, PARIS)[0].inputs

        short, long = at_noon(timedelta(minutes=24)), at_noon(timedelta(hours=3))
        self.assertEqual(short.shutter, 0.0)
        self.assertGreater(long.shutter, 0.0)
        self.assertLess(long.facade, short.facade * 0.1)

    def test_live_the_shutters_count_after_two_hours(self):
        habits = Habits.of({"volets_absence": "fermes"})
        noon = datetime(2026, 11, 5, 12, 0, tzinfo=PARIS)
        self.assertFalse(habits.shut(noon, away=True, summer=False, sun_on=False, away_for=0.4))
        self.assertTrue(habits.shut(noon, away=True, summer=False, sun_on=False, away_for=2.0))
        self.assertTrue(habits.shut(noon, away=True, summer=False, sun_on=False))
        self.assertFalse(Habits.of({"volets_absence": "fermes", "volets_absence_apres_h": 3})
                         .shut(noon, away=True, summer=False, sun_on=False, away_for=2.5))

    def test_variable_changes_nothing(self):
        away = self.run_with(Habits.of({}), "armed_away")
        home = self.run_with(Habits.of({}), "disarmed")
        self.assertEqual(away.facade, home.facade)


class Glazing(unittest.TestCase):
    """« Vitrage » of the house or of a window: the sun, the heat lost, the mist."""

    def test_a_single_pane_mists_first(self):
        self.assertTrue(misted(20.0, 55.0, 0.0, "simple"))
        self.assertFalse(misted(20.0, 55.0, 0.0, "triple"))

    def test_ordinary_losses_follow_the_glazing(self):
        def room(pane):
            return Room("r", "r", volume=30.0, openings=(Opening("w", "window", area=2.0, height=1.2, pane=pane),))
        self.assertGreater(ordinary(room("simple")).h_env, ordinary(room("double")).h_env)
        self.assertLess(ordinary(room("triple")).h_env, ordinary(room(None)).h_env)
        self.assertEqual(ordinary(room(None)), ordinary(room("double")))


class SavedSettings(unittest.TestCase):
    def test_habits_and_house_are_kept(self):
        value = {"volets_absence": "fermes", "volets_nuit": "variable", "journee_vide": {"de": "08:30", "a": "17:30"},
                 "linge_pieces": ["a", "a", "b"], "volet": "manual", "hauteur": 2.5, "murs": "heavy",
                 "plage": {"minimum": 19, "maximum": 23}, "sommeil": {"debut": "22:00", "fin": "07:00", "fin_weekend": "09:30"}}
        cleaned = clean_foyer(value)
        self.assertEqual(cleaned["linge_pieces"], ["a", "b"])
        self.assertEqual(cleaned["sommeil"]["fin_weekend"], "09:30")
        self.assertEqual(cleaned["plage"], {"minimum": 19, "maximum": 23})

    def test_laundry_inside_some_days(self):
        self.assertEqual(clean_foyer({"linge_pieces": ["a"], "linge_parfois": True}), {"linge_pieces": ["a"], "linge_parfois": True})
        self.assertEqual(clean_foyer({"linge_pieces": [], "linge_parfois": False}), {"linge_pieces": []})

    def test_wrong_values_are_refused(self):
        for value in ({"volets_nuit": "oui"}, {"linge_parfois": "oui"}, {"journee_vide": {"de": "18:00", "a": "08:00"}}, {"hauteur": 12},
                      {"plage": {"minimum": 25, "maximum": 22}}, {"volet": "bois"},
                      {"sommeil": {"debut": "22:00", "fin": "07:00", "fin_weekend": "23:00"}}):
            with self.assertRaises(ValueError, msg=value):
                clean_foyer(value)

    def test_a_room_may_set_its_shutters_only(self):
        self.assertEqual(clean_foyer({"volets_nuit": "ouverts"}, room=True), {"volets_nuit": "ouverts"})
        with self.assertRaises(ValueError):
            clean_foyer({"hauteur": 2.5}, room=True)


if __name__ == "__main__":
    unittest.main()
