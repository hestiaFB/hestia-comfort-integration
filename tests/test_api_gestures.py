"""The gestures asked and their kWh, published for Hestia Énergie (api.py `gestures`, CAHIER-MOTEUR.md § 17).

Real decisions only: the snapshots kept at the lab (tests/fixtures), replayed. Nothing is recomputed: the kWh are the
difference the engine's own scenarios already hold, the one its trace shows.
"""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from custom_components.hestia_comfort.advisor.decide import Gesture, gesture_energy
from custom_components.hestia_comfort.advisor.feedback import follow
from custom_components.hestia_comfort.advisor.snapshot import replay, restore, trace
from custom_components.hestia_comfort.advisor_home import DATA
from custom_components.hestia_comfort.api import HestiaComfortApi
from custom_components.hestia_comfort.room.advice import RoomAdvisor

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def real(name):
    """A snapshot kept at the lab: its decision, its words, the gesture the card showed, the room as it was, when."""
    snap = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    decision, words = replay(snap)
    trial = decision.gesture.kind == "nothing" and decision.passive is not None and bool(words["try"])
    return SimpleNamespace(snap=snap, decision=decision, shown=decision.passive if trial else decision.gesture, trial=trial,
                           title=words["try"] if trial else words["title"], words=words, now=restore(snap)["now"],
                           when=datetime.fromisoformat(snap["when"]).astimezone(timezone.utc))


def step(asked, kept, r, **changes):
    """One step of the room's advisor (room/advice.py `advise`): the gesture followed, its kWh, the ended ones kept."""
    r = SimpleNamespace(**{**r.__dict__, **changes})
    asked, ended = follow(asked, r.shown, r.title, r.trial, r.now, r.when, gesture_energy(r.decision.paths, r.shown))
    return asked, kept + [{**e, "fin": r.when.isoformat()} for e in ended]


class Energy(unittest.TestCase):
    def test_shutting_an_unheated_room_saves_the_heat_its_trace_shows(self):
        """Chambre P, 3 November at 19 h 19: « Laissez ouvert encore 10 min », no thermostat simulated."""
        r = real("chambre-p-3-novembre-19h19.json")
        kwh, heated = gesture_energy(r.decision.paths, r.shown)
        self.assertLess(kwh, 0)
        self.assertFalse(heated)
        kept = {json.dumps(s["geste"], sort_keys=True): s["fin"]["kwh"]
                for s in trace(r.snap, r.decision, r.words)["4_scenarios"]}
        shown = kept[json.dumps(r.shown.__dict__, sort_keys=True)]
        idle = kept[json.dumps(Gesture("nothing").__dict__, sort_keys=True)]
        self.assertAlmostEqual(kwh, shown - idle, places=2)

    def test_an_airing_where_the_heating_is_simulated(self):
        """Chambre P, 5 November at 21 h 22: « Aérez 5 min » to try, its thermostat simulated."""
        r = real("chambre-p-5-novembre-21h22.json")
        kwh, heated = gesture_energy(r.decision.paths, r.shown)
        self.assertGreater(kwh, 0)
        self.assertTrue(heated)

    def test_nothing_costs_nothing_and_a_gesture_not_simulated_has_no_kwh(self):
        r = real("salon-cuisine-5-novembre-7h26.json")
        self.assertEqual(gesture_energy(r.decision.paths, Gesture("nothing"))[0], 0.0)
        self.assertIsNone(gesture_energy(r.decision.paths, Gesture("heat_to", target=30.0)))
        self.assertIsNone(gesture_energy(r.decision.paths, None))
        self.assertIsNone(gesture_energy({}, r.shown))


class Kept(unittest.TestCase):
    def test_the_kwh_of_the_first_ask_stay_with_the_gesture(self):
        """Chambre P, 5 November: « Aérez 5 min » to try at 21 h 22, still at 21 h 33, then nothing more to do."""
        first, again = real("chambre-p-5-novembre-21h22.json"), real("chambre-p-5-novembre-21h33.json")
        kwh = round(gesture_energy(first.decision.paths, first.shown)[0], 2)
        asked, kept = step(None, [], first)
        self.assertEqual(asked.kwh, kwh)
        asked, kept = step(asked, kept, again)
        self.assertEqual((kept, asked.kwh), ([], kwh))
        asked, kept = step(asked, kept, again, shown=Gesture("nothing"), trial=False, when=again.when + timedelta(minutes=30))
        self.assertIsNone(asked)
        self.assertEqual([(k["geste"], k["suivi"], k["essai"], k["kwh"], k["chauffage"]) for k in kept],
                         [("open", False, True, kwh, True)])


class Api(unittest.TestCase):
    def setUp(self):
        """Salon · Cuisine, 5 November at 7 h 26: « Aérez 5 min »; the window opened ten minutes later, « Laissez ouvert
        encore 5 min » in its place."""
        r = real("salon-cuisine-5-novembre-7h26.json")
        self.asked_at = r.when
        asked, kept = step(None, [], r)
        asked, kept = step(asked, kept, r, shown=Gesture("close", after=5), trial=False, title="Laissez ouvert encore 5 min",
                           now=replace(r.now, opened=((1.0, 2.0),)), when=r.when + timedelta(minutes=10))
        self.advisor = RoomAdvisor.__new__(RoomAdvisor)
        self.advisor.gestures, self.advisor.asked = kept, asked
        rooms = [SimpleNamespace(entry_id=e, data={}, state="loaded", runtime_data=object(), title=e) for e in ("salon", "cuisine")]
        home = SimpleNamespace(advisor_of=lambda e: self.advisor if e in ("salon", "cuisine") else None)
        self.hass = SimpleNamespace(config_entries=SimpleNamespace(async_entries=lambda domain: rooms), data={DATA: home})
        self.api = HestiaComfortApi(self.hass)
        self.period = (r.when - timedelta(hours=1), r.when + timedelta(hours=1))

    def test_the_airing_followed_and_the_one_on_the_card(self):
        found = self.api.gestures("salon", *self.period)
        self.assertEqual([(g["gesture"], g["followed"], g["end"] is None) for g in found],
                         [("open", True, False), ("close", None, True)])
        self.assertEqual(found[0]["advice"], "Aérez 5 min")
        self.assertEqual(found[0]["start"], self.asked_at.isoformat())
        self.assertGreater(found[0]["kwh"], 0)
        self.assertFalse(found[0]["heating"])

    def test_a_shared_air_gives_the_same_gestures_from_either_room(self):
        self.assertEqual(self.api.gestures("cuisine", *self.period), self.api.gestures("salon", *self.period))

    def test_iso_strings_and_a_period_without_gestures(self):
        before = self.asked_at - timedelta(days=2)
        self.assertEqual(self.api.gestures("salon", before.isoformat(), (before + timedelta(hours=3)).isoformat()), [])
        self.assertEqual(len(self.api.gestures("salon", *(m.isoformat() for m in self.period))), 2)

    def test_unknown_room_or_no_advice(self):
        self.assertIsNone(self.api.gestures("bureau", *self.period))
        self.hass.data.clear()
        self.assertIsNone(self.api.gestures("salon", *self.period))


if __name__ == "__main__":
    unittest.main()
