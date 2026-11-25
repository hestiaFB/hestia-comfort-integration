"""Forum, 25 November: « l’apprentissage reste bloqué à 0 % depuis des semaines ». A room learned nothing, without a word,
when a measure it learns from was missing (a Hestia Weather place without a station) or not kept by the recorder. Now
the cause is said, with what to set: on the « Confort » home, the room's « Apprentissage » page, its card, and in one
of Home Assistant's repairs."""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.hestia_comfort import learning_check  # noqa: E402
from custom_components.hestia_comfort.engine.i18n import speaking  # noqa: E402
from custom_components.hestia_comfort.health import Facts, Room, Sensor, report  # noqa: E402

ALL = {"indoor_temperature": "sensor.salon_t", "indoor_humidity": "sensor.salon_h",
       "outdoor_temperature": "sensor.dehors_t", "outdoor_humidity": "sensor.dehors_h"}


def hass(components=("recorder",), names=None):
    states = {e: SimpleNamespace(attributes={"friendly_name": n}) for e, n in (names or {}).items()}
    return SimpleNamespace(config=SimpleNamespace(components=set(components), language="fr"), states=SimpleNamespace(get=states.get))


def blocks(h, sources, recorded=lambda e: True, keep=10, **extra):
    with patch("homeassistant.components.recorder.is_entity_recorded", lambda _h, e: recorded(e)), \
            patch("homeassistant.components.recorder.get_instance", lambda _h: SimpleNamespace(keep_days=keep)):
        return learning_check.blocks(h, sources, **extra)


class Causes(unittest.TestCase):
    def test_a_room_with_its_four_measures_kept_learns(self):
        self.assertEqual(blocks(hass(), ALL), [])

    def test_a_weather_place_without_station_is_named_once(self):
        found = blocks(hass(), {**ALL, "outdoor_temperature": None, "outdoor_humidity": None}, weather_linked=True)
        self.assertEqual(found, [{"cause": "no_station", "scope": "all", "key": "outdoor_temperature"}])
        self.assertIn("n’a pas de station", learning_check.text(found[0]))
        self.assertIn("Extérieur", learning_check.text(found[0]))

    def test_without_an_outdoor_thermometer_nothing_is_learned(self):
        found = blocks(hass(), {**ALL, "outdoor_temperature": None})
        self.assertEqual([(b["cause"], b["scope"], b["key"]) for b in found], [("missing", "all", "outdoor_temperature")])

    def test_without_a_humidity_only_the_temperature_is_learned(self):
        found = blocks(hass(), {**ALL, "outdoor_humidity": None, "indoor_humidity": None})
        self.assertEqual([(b["scope"], b["key"]) for b in found], [("part", "indoor_humidity"), ("part", "outdoor_humidity")])
        self.assertIn("seule la température est apprise", learning_check.text(found[1]))

    def test_a_sensor_left_out_of_the_recorder_is_named(self):
        found = blocks(hass(names={"sensor.dehors_t": "Station dehors"}), ALL, recorded=lambda e: e != "sensor.dehors_t")
        self.assertEqual((found[0]["cause"], found[0]["scope"], found[0]["name"]), ("not_recorded", "all", "Station dehors"))
        self.assertEqual(learning_check.text(found[0]),
                         "« Station dehors » (la température du dehors) n’est pas gardé par l’historique de Home Assistant : "
                         "retirez-le des exclusions du recorder dans configuration.yaml.")

    def test_without_the_recorder_one_cause_only(self):
        self.assertEqual(blocks(hass(components=()), {}), [{"cause": "recorder", "scope": "all"}])

    def test_a_history_kept_too_short_is_said(self):
        found = blocks(hass(), ALL, keep=2)
        self.assertEqual(found, [{"cause": "short_history", "scope": "all", "days": 2}])
        self.assertIn("ne garde que 2 j", learning_check.text(found[0]))

    def test_a_history_that_cannot_be_read_is_said_when_nothing_else_explains_it(self):
        self.assertEqual(blocks(hass(), ALL, unread=True), [{"cause": "unread", "scope": "all"}])
        found = blocks(hass(), {**ALL, "outdoor_temperature": None}, unread=True)
        self.assertEqual([b["cause"] for b in found], ["missing"])

    def test_the_causes_stopping_everything_come_first(self):
        found = blocks(hass(), {**ALL, "indoor_humidity": None, "outdoor_temperature": None})
        self.assertEqual([b["scope"] for b in found], ["all", "part"])

    def test_in_english(self):
        with speaking("en"):
            self.assertEqual(learning_check.text({"cause": "missing", "key": "outdoor_temperature", "scope": "all"}),
                             "No outdoor temperature: choose it in Outside.")


def stopped(cause="no_station", key="outdoor_temperature"):
    block = {"cause": cause, "scope": "all", "key": key}
    return {**block, "text": learning_check.text(block)}


class Home(unittest.TestCase):
    def rooms(self, *blocked):
        return [Room(entry_id=f"r{i}", title=title, sensors=[Sensor("indoor_temperature", "T", "ok", 1)], blocked=list(b))
                for i, (title, b) in enumerate(blocked)]

    def test_a_shared_cause_is_one_line_naming_every_room(self):
        r = report(Facts(rooms=self.rooms(("Salon", [stopped()]), ("Chambre", [stopped()])), configured=True, weather="Gardanne"))
        lines = [x for x in r["todo"] if x["text"].startswith("Apprentissage")]
        self.assertEqual([x["text"] for x in lines], ["Apprentissage arrêté : toutes les pièces"])
        self.assertIn("n’a pas de station", lines[0]["why"])
        self.assertEqual(lines[0]["target"]["kind"], "exterior")
        self.assertEqual(r["level"], "action")

    def test_a_room_cause_points_to_the_room(self):
        block = stopped("missing", "indoor_temperature")
        r = report(Facts(rooms=self.rooms(("Salon", [block]), ("Chambre", [])), configured=True))
        line = next(x for x in r["todo"] if x["text"].startswith("Apprentissage"))
        self.assertEqual((line["text"], line["target"]["entry_id"]), ("Apprentissage arrêté : Salon", "r0"))

    def test_a_missing_humidity_outside_is_a_tip(self):
        block = {"cause": "missing", "scope": "part", "key": "outdoor_humidity"}
        r = report(Facts(rooms=self.rooms(("Salon", [{**block, "text": learning_check.text(block)}])), configured=True))
        self.assertEqual([x["text"] for x in r["tips"] if "température" in x["text"]], ["Seule la température est apprise : Salon"])
        self.assertFalse(any(x["text"].startswith("Apprentissage") for x in r["todo"]))


    def test_learning_with_the_forecast_is_one_tip_for_the_home(self):
        block = {"cause": "forecast", "scope": "part", "key": "outdoor_temperature"}
        block = {**block, "text": learning_check.text(block)}
        r = report(Facts(rooms=self.rooms(("Salon", [block]), ("Chambre", [block])), configured=True, weather="Gardanne"))
        tips = [x for x in r["tips"] if x["text"].startswith("Appris")]
        self.assertEqual([x["text"] for x in tips], ["Appris avec les prévisions : toutes les pièces"])
        self.assertEqual(tips[0]["target"]["kind"], "exterior")


class Repair(unittest.TestCase):
    def entries(self, *blocked):
        return [SimpleNamespace(data={}, title=title, runtime_data=SimpleNamespace(learning_blocked=lambda b=b: b))
                for title, b in blocked]

    def run_with(self, entries):
        h = SimpleNamespace(config=SimpleNamespace(language="fr"), config_entries=SimpleNamespace(async_entries=lambda _d: entries))
        with patch.object(learning_check.ir, "async_create_issue") as create, patch.object(learning_check.ir, "async_delete_issue") as delete:
            learning_check.async_update_issue(h)
        return create, delete

    def test_one_repair_lists_each_cause_with_its_rooms(self):
        create, delete = self.run_with(self.entries(("Salon", [stopped()]), ("Chambre", [stopped()]), ("Bureau", [])))
        delete.assert_not_called()
        items = create.call_args.kwargs["translation_placeholders"]["items"]
        self.assertTrue(items.startswith("- Le lieu Hestia Weather n’a pas de station"))
        self.assertTrue(items.endswith("(Chambre, Salon)"))
        self.assertEqual(create.call_args.kwargs["translation_key"], "learning_blocked")
        self.assertFalse(create.call_args.kwargs["is_fixable"])

    def test_the_repair_goes_once_every_room_learns(self):
        part = {"cause": "missing", "scope": "part", "key": "outdoor_humidity"}
        create, delete = self.run_with(self.entries(("Salon", [part]), ("Chambre", [])))
        create.assert_not_called()
        delete.assert_called_once()


if __name__ == "__main__":
    unittest.main()
