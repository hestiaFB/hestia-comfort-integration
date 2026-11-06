"""The 3.0 settings as saved (niak-comfort/docs/REGLAGES-3.md, validated by Frank on 1 November 2026): the household's
page, and what a room says more (heatings, flows, equipment, how it is built). Only what the person set is written."""
from homeassistant.helpers import area_registry as ar
import test_configuration_workspace as workspace  # a module, so that its tests are not run again from here
from test_ha_adapter import AdapterFixture
from custom_components.hestia_comfort.configuration import Configuration
from custom_components.hestia_comfort.foyer import clean_foyer


class Fixture(AdapterFixture):
    """The workspace's fixture, without running its own tests a second time."""
    register, config = workspace.WorkspaceTests.register, workspace.WorkspaceTests.config

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.service = Configuration(self.hass)
        await self.service.load()
        self.hass.config.language = "fr"
        ar.async_get(self.hass).async_create("Cuisine")
        self.register("sensor.local", "temperature", unit="°C")


class Foyer(Fixture):
    async def test_the_household_keeps_only_what_is_set_within_its_bounds(self):
        self.assertEqual(clean_foyer(None), {})
        set_ = {"sommeil": {"debut": "22:30", "fin": "06:45"}, "ouvrir_la_nuit": True, "tolerance": 1.5,
                "aeration_max_min": 20, "plus_tard_max_min": 90, "appareils_max_min": 45, "hors_gel": 8.5,
                "poele_tient_h": 2.5, "depassement": 1.5, "depassement_min": 45, "isolation": "peu", "vitrage": "simple"}
        self.assertEqual(clean_foyer(set_), set_)
        for wrong in ({"aeration_max_min": 7}, {"aeration_max_min": 90}, {"aeration_max_min": 12}, {"tolerance": 3},
                      {"hors_gel": 4}, {"sommeil": {"debut": "22:00", "fin": "23:00"}}, {"sommeil": {"debut": "25:00", "fin": "07:00"}},
                      {"ouvrir_la_nuit": "oui"}, {"inconnu": 1}, {"pas_maintenant_min": True}, {"isolation": "forte"}, {"vitrage": 2}):
            with self.assertRaises(ValueError, msg=wrong):
                clean_foyer(wrong)

    async def test_a_room_sets_apart_only_sleep_night_and_how_much_advice(self):
        self.assertEqual(clean_foyer({"tolerance": 2}, room=True), {"tolerance": 2})
        with self.assertRaises(ValueError):
            clean_foyer({"aeration_max_min": 20}, room=True)
        # The walls and the glazing are the house's, never a room's.
        with self.assertRaises(ValueError):
            clean_foyer({"isolation": "bien"}, room=True)

    async def test_saved_at_once_never_blocking_a_room_and_kept_by_the_exterior(self):
        before = self.service.revision()
        snapshot = await self.service.set_foyer({"aeration_max_min": 20})
        self.assertEqual(snapshot["home"]["foyer"], {"aeration_max_min": 20})
        self.assertEqual(self.service.revision(), before)
        # Saving the exterior page used to keep only answers, alarm, pollens and lights (PASSAGE-CONFORT-3.md § 5.3).
        await self.service.save({"sources": {}}, self.service.revision(), home=True)
        self.assertEqual(self.service.home["foyer"], {"aeration_max_min": 20})
        with self.assertRaises(ValueError):
            await self.service.set_foyer({"aeration_max_min": 5})
        self.assertEqual(self.service.home["foyer"], {"aeration_max_min": 20})


class Room(Fixture):
    def heater(self, entity_id, target=20):
        self.register(entity_id, None, value="heat", attrs={"hvac_modes": ["off", "heat"], "hvac_action": "idle", "temperature": target})

    async def test_several_heatings_each_for_the_room_or_the_house_and_the_range_follows_one(self):
        self.heater("climate.poele", 21)
        self.heater("climate.radiateurs", 17)
        heaters = [{"entity_id": "climate.radiateurs", "scope": "room"},
                   {"entity_id": "climate.poele", "scope": "house", "kind": "stove", "power": 8500}]
        cleaned, _ = self.service.validate(self.config(heaters=heaters, thermostat_plage="climate.poele"))
        self.assertEqual(cleaned["heaters"], heaters)
        self.assertEqual(cleaned["thermostat_plage"], "climate.poele")
        # The seven kinds of heating the advisor tells apart (engine 3.9.5).
        for kind in ("radiator", "radiant", "inertia", "floor", "stove", "pellet", "ac"):
            kinded = [{**heaters[0], "kind": kind}, heaters[1]]
            self.assertEqual(self.service.validate(self.config(heaters=kinded, thermostat_plage="climate.poele"))[0]["heaters"], kinded)
        # Confort 2.1 reads one heating: the one the range follows.
        self.assertEqual(cleaned["sources"]["heating"], "climate.poele")
        # « Aucun »: the range stays as set, the 2.1 engine keeps the first heating to read.
        cleaned, _ = self.service.validate(self.config(heaters=heaters, thermostat_plage=None, thermostat_reference=False))
        self.assertEqual((cleaned["thermostat_plage"], cleaned["thermostat_reference"], cleaned["sources"]["heating"]),
                         (None, False, "climate.radiateurs"))
        for wrong in ({"heaters": heaters, "thermostat_plage": "climate.autre"},
                      {"heaters": [{"entity_id": "climate.poele", "scope": "cuisine"}]},
                      {"heaters": [{"entity_id": "climate.poele", "scope": "room", "power": 50}]},
                      {"heaters": [{"entity_id": "climate.poele", "scope": "house", "kind": "bois"}]},
                      {"heaters": heaters + [heaters[0]]}):
            with self.assertRaises(ValueError, msg=wrong):
                self.service.validate(self.config(**wrong))

    async def test_flows_room_description_and_its_own_household(self):
        cleaned, _ = self.service.validate(self.config(
            flows={"purifier": 150, "ventilation_boost": 60},
            room={"uses": "living", "surface": 16, "height": 2.5, "outside": ["O", "S"], "wall_material": "heavy",
                  "insulation": "inside", "partitions": "light"},
            foyer={"sommeil": {"debut": "21:00", "fin": "07:00"}}))
        self.assertEqual(cleaned["flows"], {"purifier": 150, "ventilation_boost": 60})
        self.assertEqual(cleaned["room"]["outside"], ["S", "O"])
        self.assertEqual(cleaned["foyer"], {"sommeil": {"debut": "21:00", "fin": "07:00"}})
        for wrong in ({"flows": {"purifier": 5000}}, {"flows": {"vmc": 60}}, {"room": {"surface": 1}},
                      {"room": {"outside": ["Ouest"]}}, {"room": {"insulation": "laine"}}, {"foyer": {"hors_gel": 7}}):
            with self.assertRaises(ValueError, msg=wrong):
                self.service.validate(self.config(**wrong))

    async def test_equipment_with_what_says_it_runs_and_one_added_by_hand(self):
        self.register("sensor.four_puissance", "power", unit="W", value="0")
        self.register("switch.deshumidificateur", None, value="off")
        cleaned, _ = self.service.validate(self.config(
            equipment=["oven", "shower"], equipment_links={"oven": "sensor.four_puissance"},
            custom_equipment=[{"name": "Déshumidificateur", "effects": ["dry"], "entity_id": "switch.deshumidificateur"}]))
        self.assertEqual(cleaned["equipment"], ["oven", "shower"])
        self.assertEqual(cleaned["equipment_links"], {"oven": "sensor.four_puissance"})
        self.assertEqual(cleaned["custom_equipment"][0]["effects"], ["dry"])
        for wrong in ({"equipment": ["oven"], "equipment_links": {"hob": "sensor.four_puissance"}},
                      {"equipment": ["oven"], "equipment_links": {"oven": "sensor.absent"}},
                      {"custom_equipment": [{"name": "", "effects": []}]},
                      {"custom_equipment": [{"name": "Aquarium", "effects": ["fishes"]}]}):
            with self.assertRaises(ValueError, msg=wrong):
                self.service.validate(self.config(**wrong))

    async def test_glazing_and_a_manual_shutters_habit(self):
        self.register("binary_sensor.fenetre", "window", value="off")
        cleaned, _ = self.service.validate(self.config(windows=["binary_sensor.fenetre"], openings={"binary_sensor.fenetre": {
            "exposure": "O", "kind": "window", "sheltered": False, "shutter": "manual", "shutter_habit": "open", "glazing": "double"}}))
        meta = cleaned["openings"]["binary_sensor.fenetre"]
        self.assertEqual((meta["shutter_habit"], meta["glazing"]), ("open", "double"))
        with self.assertRaises(ValueError):
            self.service.validate(self.config(windows=["binary_sensor.fenetre"], openings={"binary_sensor.fenetre": {
                "exposure": "O", "kind": "window", "sheltered": False, "shutter": "none", "shutter_habit": "open"}}))

    async def test_one_co2_mark_keeps_the_two_others_of_confort_2_1_in_order(self):
        cleaned, _ = self.service.validate(self.config(settings={"minimum": 20, "maximum": 24, "co2_action": 1600}))
        s = cleaned["settings"]
        self.assertLess(s["co2_potential"], s["co2_action"])
        self.assertLess(s["co2_action"], s["co2_urgent"])
        # Nothing set more: the new keys stay empty.
        plain, _ = self.service.validate(self.config())
        self.assertEqual((plain["heaters"], plain["flows"], plain["room"], plain["foyer"], plain["custom_equipment"]), ([], {}, {}, {}, []))
        self.assertEqual(plain["settings"]["co2_action"], 1000)
