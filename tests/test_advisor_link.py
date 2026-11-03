"""The 3.0 advisor in the integration (PASSAGE-CONFORT-3.md § 2): the room read from Confort's settings, the room that
advises a shared air, the decision said to the entities and the lights, what is kept on disk, what the hub shows."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.hestia_comfort import advisor_home  # noqa: E402
from custom_components.hestia_comfort.advisor_store import AdvisorFiles  # noqa: E402
from custom_components.hestia_comfort.room.advice import (RoomAdvisor, banner_level, first_twins, house_heaters, leads,  # noqa: E402
                                                          room_spec, spec, verdict)


def state(value, **attributes):
    return SimpleNamespace(state=value, attributes=attributes)


def entry(entry_id, config):
    return SimpleNamespace(entry_id=entry_id, title=config.get("name"), data={}, options=config)


SALON = {"name": "Salon", "windows": ["binary_sensor.ouest", "binary_sensor.porte"],
         "openings": {"binary_sensor.ouest": {"kind": "window", "exposure": "O", "width": 1.18, "height": 1.21},
                      "binary_sensor.porte": {"kind": "french", "exposure": "S", "sheltered": True}},
         "sources": {"indoor_temperature": "sensor.salon_t", "indoor_humidity": "sensor.salon_h", "co2": "sensor.co2",
                     "heating": "climate.poele"},
         "heaters": [{"entity_id": "climate.poele", "scope": "house", "kind": "stove"},
                     {"entity_id": "climate.salon", "scope": "room", "kind": "radiator"}],
         "thermostat_plage": "climate.poele", "settings": {"minimum": 19, "maximum": 24, "humidity_high": 60}}
CUISINE = {"name": "Cuisine", "windows": ["binary_sensor.cuisine"],
           "openings": {"binary_sensor.cuisine": {"kind": "window", "exposure": "E"}},
           "sources": {"indoor_temperature": "sensor.cuisine_t", "voc": "sensor.cov", "purifier": "fan.purificateur"},
           "flows": {"purifier": 150}, "evolution": {"voc_threshold": {"unit": "", "value": 150}}}


def hass(states=None, entries=()):
    found = {e.entry_id: e for e in entries}
    return SimpleNamespace(states=SimpleNamespace(get=lambda i: (states or {}).get(i)),
                           config_entries=SimpleNamespace(async_get_entry=found.get, async_entries=lambda domain: list(entries)))


def salon(states=None):
    """The Salon leading the « Salon · Cuisine » air, the kitchen's sources shared as the coordinator shares them."""
    entries = [entry("salon", SALON), entry("cuisine", CUISINE)]
    h = hass({"sensor.cov": state("120"), "climate.poele": state("heat", power_manager={"device_power": 8500}), **(states or {})}, entries)
    return SimpleNamespace(hass=h, entry_id="salon", config=SALON, config_entry=SimpleNamespace(title="Salon"),
                           partners=[{"entry_id": "cuisine", "title": "Cuisine", "sources": 3}],
                           sources={**SALON["sources"], "voc": "sensor.cov", "purifier": "fan.purificateur"},
                           volume_name="Salon · Cuisine", drivers={})


class TheRoomFromConfortsSettings(unittest.TestCase):
    def test_the_best_equipped_room_advises_the_shared_air(self):
        self.assertTrue(leads(salon()))
        kitchen = SimpleNamespace(entry_id="cuisine", config=CUISINE, partners=[{"entry_id": "salon", "title": "Salon", "sources": 4}])
        self.assertFalse(leads(kitchen))

    def test_the_shared_air_reads_both_rooms(self):
        coordinator = salon()
        houses = house_heaters(coordinator.hass)
        room = spec(coordinator, houses)
        self.assertEqual(houses, {"climate.poele": 8500.0})
        self.assertEqual(room["name"], "Salon · Cuisine")
        self.assertEqual(room["members"], ["salon", "cuisine"])
        # The declared size, then an ordinary one for its kind: a French window 1.8 m² by 2.1 m.
        self.assertEqual(room["windows"]["binary_sensor.ouest"], (1.18, 1.21))
        width, height = room["windows"]["binary_sensor.porte"]
        self.assertAlmostEqual(width * height, 1.8)
        self.assertEqual(room["orientations"]["binary_sensor.porte"], (180.0, True))
        self.assertEqual(room["orientations"]["binary_sensor.cuisine"], (90.0, False))
        # Its own radiator, and the stove its range follows.
        self.assertEqual((room["thermostat"], room["thermostat_plage"]), ("climate.salon", "climate.poele"))
        self.assertEqual(room["purifier"], ("fan.purificateur", 150.0))
        self.assertEqual((room["voc"], room["comfort"]["voc"]), ("sensor.cov", 150))
        self.assertEqual((room["comfort"]["minimum"], room["comfort"]["humidity"]), (19, 60))

    def test_one_air_one_volume(self):
        # Lab, 3 November: nothing declared, 40 m³ taken for the Salon · Cuisine; its CO₂ rose three times too fast.
        self.assertIsNone(spec(salon(), {})["volume"])
        SALON["room"], CUISINE["room"] = {"surface": 30.0}, {"surface": 12.0, "height": 2.4}
        try:
            self.assertAlmostEqual(spec(salon(), {})["volume"], 30.0 * 2.5 + 12.0 * 2.4)
            del CUISINE["room"]
            self.assertAlmostEqual(spec(salon(), {})["volume"], 75.0)
        finally:
            SALON.pop("room", None)
            CUISINE.pop("room", None)

    def test_twins_made_again_when_the_size_is_declared_later(self):
        from custom_components.hestia_comfort.room.advice import _resized
        coordinator = salon()
        before = first_twins(spec(coordinator, {}), coordinator.hass, {})
        self.assertEqual((before["volume"], before["air"]["volume"]), (40.0, 40.0))
        self.assertFalse(_resized(before, spec(coordinator, {})))
        SALON["room"] = {"surface": 44.03}
        try:
            room = spec(coordinator, {})
            self.assertTrue(_resized(before, room))
            # Twins kept from before the marker: their air's volume says what they were made for.
            self.assertTrue(_resized({k: v for k, v in before.items() if k != "volume"}, room))
            self.assertFalse(_resized(first_twins(room, coordinator.hass, {}), room))
        finally:
            SALON.pop("room", None)

    def test_a_voc_sensor_in_ppb_is_not_read_as_an_index(self):
        room = spec(salon({"sensor.cov": state("300", unit_of_measurement="ppb")}), {})
        self.assertIsNone(room["voc"])
        self.assertNotIn("voc", room["comfort"])

    def test_a_fresh_room_starts_from_ordinary_twins(self):
        coordinator = salon()
        room = spec(coordinator, {"climate.poele": 8500.0})
        twins = first_twins(room, coordinator.hass, {"climate.poele": 8500.0})
        self.assertEqual(set(twins) - {"heat", "gestures", "volume"}, {"water", "water_flow", "air", "air_flow", "voc", "voc_flow"})
        self.assertEqual(twins["heat"]["share"], 0.2)
        self.assertEqual(room_spec(room).windows, room["windows"])


def decided(**attributes):
    return {"title": "Rien à faire", "geste": "nothing", "regle": "nothing", "phrase": "La pièce restera dans votre plage", **attributes}


class OneDecisionForTheCardTheEntitiesAndTheLights(unittest.TestCase):
    view = {"observations": {}, "assessment": {"features": {}, "needs": []}}

    def test_the_levels_are_the_cards(self):
        self.assertEqual(banner_level(decided()), ("calm", "Tout va bien"))
        self.assertEqual(banner_level(decided(phrase="Fermée : 20,4 °C à 15 h")), ("calm", "Au mieux"))
        self.assertEqual(banner_level(decided(a_essayer="À essayer — Aérez 10 min")), ("benefit", "À saisir"))
        self.assertEqual(banner_level(decided(geste="close", regle="safety")), ("urgent", "Attention"))
        self.assertEqual(banner_level(advisor_home.WAITING), ("neutral", "Démarrage"))

    def test_a_later_gesture_is_not_a_gesture_now(self):
        later = verdict(decided(title="Aérez 15 min vers 13 h 50", geste="open", apres=75, regle="best"), self.view)
        self.assertEqual((later["gesture"], later["state"], later["level"]), ("later", "action", "action"))
        soon = verdict(decided(title="Laissez ouvert encore 5 min", geste="close", apres=5, regle="best"), self.view)
        self.assertEqual(soon["gesture"], "keep_open")
        now = verdict(decided(title="Lancez la VMC rapide 30 min", geste="boost", regle="best"), self.view)
        self.assertEqual((now["gesture"], now["colour"]), ("ventilation", "#f1b277"))

    def test_a_doubtful_air_asks_to_check_the_sensor(self):
        found = verdict(decided(title="Température douteuse", regle="doubtful"), self.view)
        self.assertEqual((found["gesture"], found["state"], found["hue"]), ("check_sensors", "neutral", None))


class WhatIsKeptOnDisk(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.files = AdvisorFiles(self.folder.name)

    def tearDown(self):
        self.folder.cleanup()

    def test_the_journal_keeps_sixty_days(self):
        now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
        self.files.journal({"heure": (now - timedelta(days=61)).isoformat(), "piece": "Salon", "conseil": "Aérez"})
        self.files.journal({"heure": now.isoformat(), "piece": "Salon", "conseil": "Rien à faire"})
        self.files.prune(now)
        self.assertEqual([line["conseil"] for line in self.files.atelier(now)["journal"]], ["Rien à faire"])

    def test_the_atelier_reads_the_opinions_and_the_gestures_followed(self):
        now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
        self.files.feedback({"heure": now.isoformat(), "piece": "Salon", "type": "suivi", "geste": "open", "suivi": True})
        self.files.feedback({"heure": now.isoformat(), "piece": "Salon", "type": "avis", "avis": "faux"})
        found = self.files.atelier(now)
        self.assertEqual(found["suivis"]["Salon"]["suivis"], 1)
        self.assertEqual([a["avis"] for a in found["avis"]], ["faux"])

    def test_a_trace_is_read_only_from_its_own_folders(self):
        (Path(self.folder.name) / "secret.json").write_text(json.dumps({"x": 1}))
        for name in ("../secret.json", "..\\secret.json", ".hidden.json", "absent.json"):
            self.assertIsNone(self.files.trace(name))


def advisor(learned, result=None, fitted=False, thermostat="climate.chambre"):
    found = RoomAdvisor.__new__(RoomAdvisor)
    found.room = {"name": "Chambre", "boost": ("fan.vmc", 60.0), "purifier": None, "thermostat": thermostat, "thermostat_plage": None}
    found.learned = {**learned, "fitted": fitted}
    found.learned_at, found.report, found.result, found.sensors = "2026-11-03T03:30:00+00:00", {"jours": 3.0}, result, {}
    return found


class WhatTheHubShows(unittest.TestCase):
    seen = {"heat": [["2026-11-02T10:00:00+00:00", -0.8, -0.7]] * 3, "humidity": [["2026-11-02T10:00:00+00:00", -2, -1]]}

    def test_each_effect_with_its_proof_and_what_is_missing(self):
        found = advisor({"heat": {}, "gestures": self.seen}).knowing()
        effects = {e["effet"]: e for e in found["effets"]}
        self.assertEqual(effects["heat"]["niveau"], "proven")
        self.assertEqual(effects["humidity"]["manque"], {"gestes": 2})
        # The devices and the heating are listed before they were ever seen.
        self.assertEqual(effects["boost:humidity"]["gestes"], 0)
        self.assertEqual(found["pourcent"], 25)

    def test_the_heating_is_proven_only_once_a_night_fitted_the_twin(self):
        unfitted = {e["effet"]: e for e in advisor({"heat": {}, "gestures": {}}).knowing()["effets"]}
        self.assertEqual((unfitted["heating:heat"]["niveau"], unfitted["heating:heat"]["manque"]), ("supposed", {"nuit": True}))
        fitted = {e["effet"]: e for e in advisor({"heat": {}, "gestures": {}}, fitted=True).knowing()["effets"]}
        self.assertEqual(fitted["heating:heat"]["niveau"], "proven")
        self.assertNotIn("heating:heat", {e["effet"] for e in advisor({"heat": {}}, thermostat=None).knowing()["effets"]})

    def test_the_last_decision_says_the_level_of_the_moment(self):
        found = advisor({"heat": {}, "gestures": self.seen}, result={"preuves": {"humidity": "reinforced"}}).knowing()
        self.assertEqual({e["effet"]: e["niveau"] for e in found["effets"]}["humidity"], "reinforced")

    def test_a_room_without_its_first_decision_waits(self):
        room = advisor({"heat": {}})
        room.room["members"] = ["chambre"]
        h = SimpleNamespace(data={advisor_home.DATA: SimpleNamespace(advisor_of=lambda i: room if i == "chambre" else None)})
        self.assertEqual(advisor_home.result(h, "chambre")["regle"], "waiting")
        self.assertIsNone(advisor_home.result(h, "buanderie"))
        room.result = decided()
        self.assertEqual(advisor_home.result(h, "chambre")["title"], "Rien à faire")


class TheEnginesOwnVersion(unittest.TestCase):
    def test_its_number_and_its_history_go_together(self):
        from custom_components.hestia_comfort.advisor import VERSION
        major, minor, fix = VERSION.split(".")
        self.assertTrue(major.isdigit() and minor.isdigit() and fix.isdigit())
        history = (Path(__file__).resolve().parents[1] / "docs" / "dev" / "MOTEUR-VERSIONS.md").read_text(encoding="utf-8")
        # The newest entry of the history is the version the code says.
        self.assertEqual(history.split("\n### ")[1].split(" ")[0], VERSION)


if __name__ == "__main__":
    unittest.main()
