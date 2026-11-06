"""« Participez à l'amélioration du moteur » (field_report.py): the report shared in a public issue names no room, no
entity and no person, keeps the same alias for the same thing throughout, and the lines that name the rooms stay out."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.hestia_comfort import field_report
from custom_components.hestia_comfort.field_report import Anonymous, _room, _signals, assemble, helpful


class Advisor(SimpleNamespace):
    def knowing(self):
        return {"piece": "Salon · Cuisine", "jours": 9.6, "ecart_1h": 0.31,
                "effets": [{"effet": "window:heat", "niveau": "avere", "gestes": 6, "prevu": -1.2, "mesure": -1.0}]}


SALON = {"name": "Salon · Cuisine", "room": {"uses": "sejour", "surface": 42},
         "heaters": [{"kind": "pellet", "entity_id": "climate.poele"}],
         "sources": {"indoor_temperature": "sensor.salon_temperature", "indoor_humidity": "sensor.salon_humidite"},
         "windows": ["binary_sensor.fenetre_salon", "binary_sensor.baie_cuisine"],
         "openings": {"binary_sensor.fenetre_salon": {"width": 1.2, "height": 1.4, "shutter": "manual"}},
         "presence": ["person.frank"]}
CHAMBRE = {"name": "Chambre P", "windows": ["binary_sensor.fenetre_chambre_p"], "openings": {}, "sources": {}}


def rooms():
    salon = Advisor(learned={"heat": {"tau": 30}, "gestures": {"window:heat": [[0, -1.2, -1.0]] * 6}},
                    learned_at="2026-11-06T03:00:00+00:00",
                    report={"piece": "Salon · Cuisine", "chaleur": {"avant": [0.4, 0.9]}, "notes": {}})
    return [_room(SALON, salon), _room(CHAMBRE, None)]


class Report(unittest.TestCase):
    def setUp(self):
        signal = {"avis": "faux", "note": "Trop froid dans la Chambre P", "affiche": {"titre": "Ouvrez la fenêtre du Salon"},
                  "instantane": {"room": "Salon · Cuisine", "windows": {"binary_sensor.fenetre_salon": True},
                                 "people": {"home": ["Frank"]}, "latitude": 43.4}}
        self.report = assemble(rooms(), [signal], {"Salon · Cuisine": {"part": 0.5}},
                               {"weather": "abc", "analysis": True}, datetime(2026, 11, 6, 18, tzinfo=timezone.utc))
        self.text = json.dumps(self.report, ensure_ascii=False)

    def test_no_room_entity_person_or_place_is_named(self):
        for word in ("Salon", "Cuisine", "Chambre P", "sensor.", "binary_sensor", "climate.", "person.", "Frank",
                     "43.4", "fenetre_", "baie_", "salon_"):
            self.assertNotIn(word, self.text, word)

    def test_the_same_room_and_entity_keep_one_alias(self):
        first = self.report["pieces"][0]
        self.assertEqual(first["piece"], "Pièce 1")
        self.assertEqual(self.report["pieces"][1]["piece"], "Pièce 2")
        self.assertEqual(self.report["signalements"][0]["instantane"]["room"], "Pièce 1")
        self.assertIn("Pièce 2", self.report["signalements"][0]["note"])
        self.assertEqual(self.report["gestes_suivis"], {"Pièce 1": {"part": 0.5}})
        self.assertEqual(list(self.report["signalements"][0]["instantane"]["windows"]), ["entité 1"])

    def test_what_the_engine_knows_is_in_it(self):
        first = self.report["pieces"][0]
        self.assertEqual((first["jumeaux"], first["gestes_vus"]), ({"heat": {"tau": 30}}, {"window:heat": 6}))
        self.assertEqual(first["prevu_contre_mesure"][0]["prevu"], -1.2)
        self.assertEqual((first["chauffages"], first["fenetres"], first["fenetres_sans_taille"], first["volets"]),
                         (["pellet"], 2, 1, 1))
        self.assertEqual(self.report["maison"]["chauffages"], ["pellet"])
        self.assertTrue(self.report["maison"]["outils_analyse"])
        self.assertFalse(self.report["pieces"][1]["conseil_a_part"])


class Helpful(unittest.TestCase):
    def test_sizes_history_and_learning_name_the_rooms_for_the_person(self):
        lines = {line["key"]: line for line in helpful(rooms())}
        self.assertEqual(lines["sizes"], {"key": "sizes", "count": 2, "rooms": ["Salon · Cuisine", "Chambre P"]})
        self.assertEqual(lines["history"]["days"], 10)
        # The room advised with another (no advisor of its own) is not « still learning ».
        self.assertNotIn("learning", lines)

    def test_unmeasured_windows_are_not_asked_again(self):
        self.assertEqual(_room({**CHAMBRE, "windows_unmeasured": True}, None)["fenetres_sans_taille"], 0)


class Signals(unittest.TestCase):
    def test_the_last_reports_only_and_a_broken_file_skipped(self):
        with tempfile.TemporaryDirectory() as folder:
            kept = Path(folder) / "hestia_comfort" / "signales"
            kept.mkdir(parents=True)
            for i in range(field_report.SIGNALS + 3):
                (kept / f"signale-salon-202611{i:02d}-120000-faux.json").write_text(json.dumps({"n": i}), encoding="utf-8")
            (kept / "signale-salon-20261199-120000-faux.json").write_text("{", encoding="utf-8")
            found = _signals(folder)
            self.assertEqual(len(found), field_report.SIGNALS - 1)
            self.assertEqual(found[0], {"n": field_report.SIGNALS + 2})
            self.assertEqual(_signals(str(Path(folder) / "ailleurs")), [])


class Alias(unittest.TestCase):
    def test_longest_name_first(self):
        anonymous = Anonymous(["Chambre", "Chambre P"])
        self.assertEqual(anonymous("Chambre P et Chambre"), "Pièce 2 et Pièce 1")


if __name__ == "__main__":
    unittest.main()
