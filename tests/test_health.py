"""The technical state shown on the « Confort » tab: orange only for what stops working, tips for what could be better."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.hestia_comfort.health import Facts, Room, Sensor, ago, report


def room(title="Salon", sensors=None, **extra):
    sensors = sensors if sensors is not None else [Sensor("indoor_temperature", "Salon température", "ok", 1),
                                                   Sensor("windows", "Fenêtre", "ok", 3)]
    return Room(entry_id=title.lower(), title=title, sensors=sensors, **extra)


class HealthTests(unittest.TestCase):
    def test_everything_answering_is_blue(self):
        r = report(Facts(rooms=[room()], configured=True, weather="Gardanne", exterior=[Sensor("outdoor_temperature", "T", "ok", 1)], version="0.5.0"))
        self.assertEqual((r["level"], r["summary"], r["rooms_summary"]), ("ok", "Tout est suivi", "1 pièce suivie"))
        self.assertEqual(r["sources"][0], {"label": "Extérieur", "level": "ok", "text": "Hestia Weather · Gardanne"})
        self.assertEqual(r["versions"][1]["text"], "Relié à Hestia Weather · Gardanne")
        self.assertEqual([c["text"] for c in r["rooms"][0]["cells"]], ["répond", "—", "—", "1 contact", "—"])

    def test_a_silent_sensor_is_to_fix_with_what_it_stops(self):
        r = report(Facts(rooms=[room("Cuisine", [Sensor("indoor_temperature", "T", "ok", 1), Sensor("co2", "Cuisine CO₂", "silent", 300),
                                                 Sensor("windows", "F", "ok", 1)])], configured=True))
        self.assertEqual(r["todo"][0]["text"], "Cuisine : le CO₂ ne répond pas")
        self.assertEqual(r["todo"][0]["why"], "Depuis 5 h. Cuisine CO₂ · Le conseil d’aération est en pause.")
        self.assertEqual(r["todo"][0]["target"], {"kind": "room", "entry_id": "cuisine", "label": "Cuisine"})
        self.assertEqual(r["rooms"][0]["cells"][2], {"level": "bad", "text": "ne répond pas"})

    def test_exterior_missing_or_silent(self):
        r = report(Facts(rooms=[room()]))
        self.assertEqual(r["todo"][0]["text"], "Extérieur à configurer")
        self.assertEqual(r["sources"][0]["level"], "bad")
        r = report(Facts(rooms=[room()], configured=True, exterior=[Sensor("rain", "Pluie", "silent", 20)]))
        self.assertEqual(r["todo"][0]["text"], "Extérieur : la pluie ne répond pas")

    def test_tips_name_what_home_assistant_already_has(self):
        r = report(Facts(rooms=[room(available={"indoor_humidity": "Salon humidité"}), room("Salle de bain", [Sensor("indoor_temperature", "T", "ok", 1)])],
                         configured=True, weather_installed=True, free_areas=[("ete", "Séjour d’été")]))
        texts = [t["text"] for t in r["tips"]]
        self.assertEqual(texts, ["Salon : ajouter l’humidité", "Salle de bain : ouvrants non mesurés", "Séjour d’été pas encore suivie",
                                 "Reprendre l’extérieur de Hestia Weather"])
        self.assertIn("« Salon humidité » est disponible", r["tips"][0]["why"])
        self.assertEqual(r["tips"][2]["target"], {"kind": "area", "area_id": "ete", "label": "Ajouter"})
        self.assertEqual(r["level"], "ok")

    def test_extensions_linked_found_or_missing(self):
        r = report(Facts(rooms=[room(thermostat=True)], weather="Gardanne", weather_installed=True,
                         installed=frozenset({"versatile_thermostat", "adaptive_cover_pro", "better_thermostat"})))
        ext = {e["key"]: e for e in r["extensions"]}
        self.assertEqual([e["key"] for e in r["extensions"]], ["hestia_weather", "versatile_thermostat", "chauffage", "scheduler", "adaptive_cover_pro", "cover_automatic", "cover_extender", "wled", "alarmo"])
        self.assertEqual((ext["hestia_weather"]["state"], ext["hestia_weather"]["official"]), ("linked", True))
        self.assertEqual((ext["versatile_thermostat"]["state"], ext["versatile_thermostat"]["rooms"]), ("linked", ["Salon"]))
        self.assertEqual((ext["adaptive_cover_pro"]["state"], ext["adaptive_cover_pro"]["level"]), ("found", "none"))
        self.assertEqual((ext["alarmo"]["state"], ext["alarmo"]["text"]), ("missing", "non installée"))
        self.assertTrue(all(e["use"] and e["without"] and e["url"].startswith("https://github.com/") for e in r["extensions"]))
        self.assertEqual([o["name"] for o in r["others"]], ["Better Thermostat"])
        self.assertRegex(r["socle"], r"^1\.\d+$")

    def test_ha_chauffage_is_a_first_beta_linked_where_it_schedules_the_heating(self):
        r = report(Facts(rooms=[room(planners=frozenset({"chauffage"}))], installed=frozenset({"chauffage", "scheduler"})))
        ext = {e["key"]: e for e in r["extensions"]}
        self.assertEqual((ext["chauffage"]["state"], ext["chauffage"]["rooms"], ext["chauffage"]["beta"]), ("linked", ["Salon"], True))
        self.assertEqual((ext["scheduler"]["state"], ext["scheduler"]["beta"]), ("found", True))
        self.assertFalse(ext["versatile_thermostat"]["beta"])

    def test_an_extension_turned_off_says_so(self):
        r = report(Facts(rooms=[room()], installed=frozenset({"adaptive_cover_pro", "alarmo"}), disabled=frozenset({"adaptive_cover_pro", "alarmo"})))
        ext = {e["key"]: e for e in r["extensions"]}
        self.assertEqual([(ext[k]["state"], ext[k]["text"]) for k in ("adaptive_cover_pro", "alarmo")], [("off", "désactivée")] * 2)

    def test_weather_installed_but_not_linked_is_found(self):
        r = report(Facts(weather_installed=True, alarm="Alarmo · désarmée", installed=frozenset({"alarmo"})))
        ext = {e["key"]: e for e in r["extensions"]}
        self.assertEqual((ext["hestia_weather"]["state"], ext["hestia_weather"]["text"]), ("found", "installé, pas relié"))
        self.assertEqual((ext["alarmo"]["state"], ext["alarmo"]["text"]), ("linked", "Alarmo · désarmée"))
        self.assertEqual(r["others"], [])

    def test_ages_read_naturally(self):
        self.assertEqual([ago(0.5), ago(12), ago(300)], ["à l’instant", "il y a 12 min", "il y a 5 h"])




class Counts(unittest.TestCase):
    def test_one_sensor_count_for_rooms_and_exterior(self):
        r = report(Facts(rooms=[room(sensors=[Sensor("indoor_temperature", "T", "ok", 1), Sensor("presence", "P", "silent", 9),
                                              Sensor("windows", "F", "ok", 1), Sensor("windows", "G", "ok", 1)])],
                         configured=True, exterior=[Sensor("rain", "Pluie", "ok", 1)]))
        # The presence sensor has no column of its own: it still counts, and is still a point to fix.
        self.assertEqual(r["sensors"], {"answering": 4, "total": 5})
        self.assertEqual([t["text"] for t in r["todo"]], ["Salon : la présence ne répond pas"])

    def test_stale_reading_is_named(self):
        r = report(Facts(rooms=[room(sensors=[Sensor("indoor_temperature", "T", "stale", 300), Sensor("windows", "F", "ok", 1)])], configured=True))
        self.assertEqual(r["todo"][0]["text"], "Salon : la température ne donne pas de mesure exploitable")
        self.assertEqual(r["sensors"], {"answering": 1, "total": 2})

    def test_windows_without_contact_on_purpose_are_not_suggested(self):
        r = report(Facts(rooms=[room("Garage", [Sensor("indoor_temperature", "T", "ok", 1)], windows_intended=True)], configured=True))
        self.assertNotIn("Garage : ouvrants non mesurés", [t["text"] for t in r["tips"]])


if __name__ == "__main__":
    unittest.main()
