"""Shared « Hestia » panel (socle v1): registration, newest copy wins, home page states."""
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from homeassistant.components.frontend import DATA_PANELS
from homeassistant.components.websocket_api import DOMAIN as WS_DOMAIN
from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er, floor_registry as fr
from custom_components.hestia_comfort import socle
from custom_components.hestia_comfort.engine import legacy
from custom_components.hestia_comfort.configuration import get_configuration
from custom_components.hestia_comfort.panel import comfort_status


def brick(status=None, **extra):
    async def ok(hass):
        return {"level": "ok", "summary": "Tout va bien.", "details": [], "links": []}
    return {"domain": "hestia_comfort", "name": "Hestia Confort", "slug": "confort", "version": "1.0",
            "icon": "mdi:home", "module_url": "/a/panel.js", "element": "hestia-comfort-setup",
            "status": status or ok, "legacy_path": "hestia-confort", **extra}


class SocleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.temp.name)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        await self.hass.config_entries.async_initialize()

    async def asyncTearDown(self):
        await self.hass.async_stop()
        self.temp.cleanup()

    def module(self):
        return self.hass.data[DATA_PANELS]["hestia"].config["_panel_custom"]["module_url"]

    async def test_one_brick_opens_the_hestia_panel_and_keeps_its_old_addresses(self):
        await socle.async_register_brick(self.hass, brick(), "/a/hestia-socle.js")
        panels = self.hass.data[DATA_PANELS]
        self.assertEqual(panels["hestia"].sidebar_title, "Hestia")
        self.assertEqual(self.module(), "/a/hestia-socle.js")
        self.assertTrue(panels["hestia"].require_admin)
        # The panel's address before socle 1.12 (legacy.PANEL) leads to /hestia, hidden from the sidebar.
        self.assertIsNone(panels[legacy.PANEL].sidebar_title)
        self.assertEqual(panels[legacy.PANEL].config["redirect"], "/hestia")
        former = panels["hestia-confort"]
        self.assertIsNone(former.sidebar_title)  # hidden from the sidebar
        self.assertEqual(former.config["redirect"], "/hestia/confort")
        self.assertEqual(former.config_panel_domain, "hestia_comfort")  # « Configurer » still works
        self.assertIn("hestia/overview", self.hass.data[WS_DOMAIN])

    async def test_registering_again_changes_nothing(self):
        await socle.async_register_brick(self.hass, brick(), "/a/hestia-socle.js")
        await socle.async_register_brick(self.hass, brick(), "/a/hestia-socle.js")
        self.assertEqual(len(self.hass.data[socle.KEY]["bricks"]), 1)

    async def test_the_newest_copy_shows_the_panel(self):
        await socle.async_register_brick(self.hass, brick(domain="hestia_old", slug="old", legacy_path=None), "/old/hestia-socle.js")
        self.hass.data[socle.KEY]["panel"]["socle"] = (0, 9)  # as written by an older copy
        await socle.async_register_brick(self.hass, brick(), "/new/hestia-socle.js")
        self.assertEqual(self.module(), "/new/hestia-socle.js")
        self.assertEqual(set(self.hass.data[socle.KEY]["bricks"]), {"hestia_old", "hestia_comfort"})

    async def test_an_older_copy_never_replaces_a_newer_panel(self):
        await socle.async_register_brick(self.hass, brick(), "/new/hestia-socle.js")
        self.hass.data[socle.KEY]["panel"]["socle"] = (2, 0)
        await socle.async_register_brick(self.hass, brick(domain="hestia_weather", slug="meteo", legacy_path=None), "/old/hestia-socle.js")
        self.assertEqual(self.module(), "/new/hestia-socle.js")

    async def test_of_two_copies_of_one_version_the_later_build_shows_the_panel(self):
        await socle.async_register_brick(self.hass, brick(domain="hestia_weather", slug="meteo", legacy_path=None), "/w/hestia-socle.js")
        self.hass.data[socle.KEY]["panel"]["build"] = "20260101.0000"  # the same version, copied earlier
        await socle.async_register_brick(self.hass, brick(), "/c/hestia-socle.js")
        self.assertEqual(self.module(), "/c/hestia-socle.js")
        # The earlier build, registering again, leaves it; a copy before 1.22 has no build and loses too.
        self.hass.data[socle.KEY]["panel"]["build"] = "20991231.2359"
        await socle.async_register_brick(self.hass, brick(domain="hestia_weather", slug="meteo", legacy_path=None), "/w/hestia-socle.js")
        self.assertEqual(self.module(), "/c/hestia-socle.js")
        self.assertLess(socle._rank({"socle": socle.SOCLE_VERSION}), (socle.SOCLE_VERSION, socle.SOCLE_BUILD))

    async def test_the_hub_script_has_an_address_of_its_own_build(self):
        # A cache holding an older script under the brick's address would define another element: an empty page.
        served = []
        async def register(paths):
            served.extend(paths)
        self.hass.http = SimpleNamespace(async_register_static_paths=register)
        await socle.async_register_brick(self.hass, brick(module_url="/hestia_comfort-assets/panel.js?v=2.1.0"),
                                         "/hestia_comfort-assets/hestia-socle.js?v=2.1.0")
        await socle.async_register_brick(self.hass, brick(domain="hestia_weather", slug="meteo", legacy_path=None), "/w/hestia-socle.js")
        major, minor = socle.SOCLE_VERSION
        folder = Path(socle.__file__).parent / "frontend"
        base = f"/hestia-socle/{folder.parent.name}/{major}.{minor}.{socle.SOCLE_BUILD}-{socle._content(folder)}"
        self.assertEqual(self.module(), f"{base}/hestia-socle.js")
        # The tab beside it, at the same address: a new hub never meets an old tab kept in a cache.
        self.assertEqual(self.hass.data[socle.KEY]["bricks"]["hestia_comfort"]["module_url"], f"{base}/panel.js")
        self.assertEqual([p.url_path for p in served], [base])  # served once, from this brick's frontend folder
        self.assertEqual(Path(served[0].path), folder)
        # Any script of the folder changes the address.
        with tempfile.TemporaryDirectory() as other:
            (Path(other) / "panel.js").write_text("a")
            first = socle._content(Path(other))
            (Path(other) / "panel.js").write_text("b")
            self.assertNotEqual(first, socle._content(Path(other)))

    async def test_a_copy_whose_script_lacks_its_element_leaves_the_panel_to_another(self):
        # Issue #48: a file of another version under the brick's address; the panel's element is never defined.
        from unittest.mock import patch
        with patch.object(socle, "_defines_element", lambda url: "/bad/" not in url):
            await socle.async_register_brick(self.hass, brick(domain="hestia_weather", slug="meteo", legacy_path=None), "/bad/hestia-socle.js")
            self.assertNotIn("hestia", self.hass.data.get(DATA_PANELS, {}))
            await socle.async_register_brick(self.hass, brick(), "/good/hestia-socle.js")
        self.assertEqual(self.module(), "/good/hestia-socle.js")
        self.assertEqual(set(self.hass.data[socle.KEY]["bricks"]), {"hestia_weather", "hestia_comfort"})  # both listed
        # The real check reads this brick's built script, which defines its element.
        self.assertTrue(socle._defines_element("/hestia_comfort-assets/hestia-socle.js?v=2.1.0"))

    async def test_an_older_copy_under_the_former_name_finds_the_panel_taken(self):
        # Socle 1.14 (Confort 1.7.x, Weather 2.9.x) registers under legacy.SOCLE_KEY and leaves a panel whose socle is >= its own.
        await socle.async_register_brick(self.hass, brick(), "/c/hestia-socle.js")
        held = self.hass.data[legacy.SOCLE_KEY]["panel"]
        self.assertGreaterEqual(tuple(held["socle"]), (1, 14))
        self.assertEqual(held["shell_url"], "/c/hestia-socle.js")

    async def test_a_brick_under_its_former_name_is_listed_once(self):
        async def ok(hass, language=None):
            return {"level": "ok", "summary": "Rien à régler.", "details": [], "links": []}
        former = {"domain": "niak_weather", "name": "Hestia Weather", "slug": "meteo", "tab": "Météo", "version": "2.9.8",
                  "icon": "mdi:weather-partly-cloudy", "module_url": "/niak_weather-assets/panel.js?v=2.9.8",
                  "element": "niak-weather-setup", "navigation": 3, "status": ok, "socle": (1, 14)}
        self.hass.data.setdefault(legacy.SOCLE_KEY, {"bricks": {}, "panel": None})["bricks"]["niak_weather"] = former
        await socle.async_register_brick(self.hass, brick(), "/c/hestia-socle.js")
        overview = await socle.async_overview(self.hass)
        self.assertEqual([b["slug"] for b in overview["bricks"]], ["meteo", "confort"])  # the catalogue's order
        self.assertEqual(overview["bricks"][0]["element"], "niak-weather-setup")
        self.assertEqual(overview["bricks"][0]["status"]["level"], "ok")
        self.assertNotIn("hestia_weather", [o["domain"] for o in overview["others"]])  # not proposed as « À découvrir »
        # Moved to its new name (both loaded for a moment): listed once, under the new one.
        await socle.async_register_brick(self.hass, brick(domain="hestia_weather", name="Hestia Weather", slug="meteo", legacy_path=None),
                                         "/w/hestia-socle.js")
        overview = await socle.async_overview(self.hass)
        self.assertEqual([b["domain"] for b in overview["bricks"]], ["hestia_weather", "hestia_comfort"])

    async def test_home_page_lists_bricks_and_published_ones_not_yet_in_the_panel(self):
        await socle.async_register_brick(self.hass, brick(), "/a/hestia-socle.js")
        self.hass.config.components.add("hestia_weather")
        overview = await socle.async_overview(self.hass)
        self.assertEqual([b["slug"] for b in overview["bricks"]], ["confort"])
        self.assertFalse(any(callable(v) for v in overview["bricks"][0].values()))  # sendable as JSON
        self.assertEqual(overview["bricks"][0]["status"]["level"], "ok")
        weather = next(o for o in overview["others"] if o["domain"] == "hestia_weather")
        self.assertTrue(weather["installed"])
        self.assertEqual(weather["settings_path"], "/config/integrations/integration/hestia_weather")
        self.assertNotIn("hestia_comfort", [o["domain"] for o in overview["others"]])

    async def test_a_failing_brick_is_unknown_and_never_hides_the_others(self):
        async def broken(hass):
            raise RuntimeError("boom")
        await socle.async_register_brick(self.hass, brick(broken), "/a/hestia-socle.js")
        with self.assertLogs("custom_components.hestia_comfort.socle", "ERROR"):
            overview = await socle.async_overview(self.hass)
        self.assertEqual(overview["bricks"][0]["status"]["level"], "unknown")

    async def test_unknown_levels_are_never_shown_as_fine(self):
        async def odd(hass):
            return {"level": "great", "summary": "?"}
        await socle.async_register_brick(self.hass, brick(odd), "/a/hestia-socle.js")
        self.assertEqual((await socle.async_overview(self.hass))["bricks"][0]["status"]["level"], "unknown")

    async def test_the_sidebar_entry_can_be_hidden_and_the_panel_stays_open(self):
        await socle.async_register_brick(self.hass, brick(), "/a/hestia-socle.js")
        self.assertTrue((await socle.async_overview(self.hass))["sidebar"])
        await socle.async_set_sidebar(self.hass, False)
        panel = self.hass.data[DATA_PANELS]["hestia"]
        self.assertIsNone(panel.sidebar_title)  # gone from the sidebar, still served at /hestia
        self.assertEqual(self.module(), "/a/hestia-socle.js")
        self.assertFalse((await socle.async_overview(self.hass))["sidebar"])
        await socle.async_set_sidebar(self.hass, True)
        self.assertEqual(self.hass.data[DATA_PANELS]["hestia"].sidebar_title, "Hestia")

    async def test_the_choice_survives_a_restart_and_applies_to_the_next_brick(self):
        await socle.async_register_brick(self.hass, brick(), "/a/hestia-socle.js")
        await socle.async_set_sidebar(self.hass, False)
        self.hass.data.pop(socle.KEY)  # as after a restart: the file is all that remains
        await socle.async_register_brick(self.hass, brick(), "/a/hestia-socle.js")
        self.assertIsNone(self.hass.data[DATA_PANELS]["hestia"].sidebar_title)
        self.assertIn("hestia/set_sidebar", self.hass.data[WS_DOMAIN])

    async def test_theme_and_sidebar_survive_restart_without_overwriting_each_other(self):
        await socle.async_register_brick(self.hass, brick(), "/a/hestia-socle.js")
        self.assertEqual((await socle.async_overview(self.hass))["theme"], "hestia")
        self.assertIn("hestia/set_theme", self.hass.data[WS_DOMAIN])
        await socle.async_set_theme(self.hass, "ha")
        await socle.async_set_sidebar(self.hass, False)
        self.hass.data.pop(socle.KEY)
        await socle.async_register_brick(self.hass, brick(), "/a/hestia-socle.js")
        overview = await socle.async_overview(self.hass)
        self.assertEqual(overview["theme"], "ha")
        self.assertFalse(overview["sidebar"])
        await socle.async_set_theme(self.hass, "hestia")
        self.assertFalse((await socle.async_overview(self.hass))["sidebar"])
        with self.assertRaises(ValueError):
            await socle.async_set_theme(self.hass, "unknown")
        self.assertEqual((await socle.async_overview(self.hass))["theme"], "hestia")

    async def test_the_move_to_the_hestia_name_shows_until_closed(self):
        async def moving(hass):
            return {"domain": "hestia_comfort", "state": "done", "restart": False}
        await socle.async_register_brick(self.hass, brick(migration=moving), "/a/hestia-socle.js")
        self.assertEqual((await socle.async_overview(self.hass))["migration"], [{"domain": "hestia_comfort", "state": "done", "restart": False}])
        self.assertIn("hestia/close_migration", self.hass.data[WS_DOMAIN])
        await socle.async_close_migration(self.hass)
        self.assertEqual((await socle.async_overview(self.hass))["migration"], [])
        self.hass.data.pop(socle.KEY)  # as after a restart: closed for good
        await socle.async_register_brick(self.hass, brick(migration=moving), "/a/hestia-socle.js")
        self.assertEqual((await socle.async_overview(self.hass))["migration"], [])

    async def test_a_brick_without_a_former_name_shows_nothing(self):
        async def never(hass):
            return None
        async def broken(hass):
            raise RuntimeError("unreadable")
        await socle.async_register_brick(self.hass, brick(migration=never), "/a/hestia-socle.js")
        await socle.async_register_brick(self.hass, brick(domain="hestia_other", slug="other", migration=broken), "/a/hestia-socle.js")
        with self.assertLogs(socle.__name__, level="ERROR"):
            self.assertEqual((await socle.async_overview(self.hass))["migration"], [])

    async def test_old_settings_keep_the_hestia_appearance(self):
        from homeassistant.helpers.storage import Store
        await Store(self.hass, socle.STORE_VERSION, socle.KEY).async_save({"sidebar": False})
        await socle.async_register_brick(self.hass, brick(), "/a/hestia-socle.js")
        overview = await socle.async_overview(self.hass)
        self.assertEqual(overview["theme"], "hestia")
        self.assertFalse(overview["sidebar"])

    async def test_old_copy_loading_first_does_not_erase_stored_theme(self):
        from homeassistant.helpers.storage import Store
        await Store(self.hass, socle.STORE_VERSION, socle.KEY).async_save({"sidebar": False, "theme": "ha"})
        # Socle 1.5/1.6 only imports the sidebar field before the newest copy starts.
        self.hass.data[socle.KEY] = {"bricks": {}, "panel": None, "settings": {"sidebar": False}}
        await socle.async_register_brick(self.hass, brick(), "/new/hestia-socle.js")
        self.assertEqual((await socle.async_overview(self.hass))["theme"], "ha")
        self.assertFalse((await socle.async_overview(self.hass))["sidebar"])

    async def test_older_weather_copy_cannot_replace_theme_handler_or_preference(self):
        from unittest.mock import patch
        await socle.async_register_brick(self.hass, brick(), "/new/hestia-socle.js")
        await socle.async_set_theme(self.hass, "ha")
        handler = self.hass.data[WS_DOMAIN]["hestia/set_theme"]
        with patch.object(socle, "SOCLE_VERSION", (1, 4)):
            await socle.async_register_brick(self.hass, brick(domain="hestia_weather", slug="meteo", legacy_path=None), "/old/hestia-socle.js")
        self.assertEqual(self.module(), "/new/hestia-socle.js")
        self.assertIs(self.hass.data[WS_DOMAIN]["hestia/set_theme"], handler)
        self.assertEqual((await socle.async_overview(self.hass))["theme"], "ha")



class ComfortStatusTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.temp.name)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        await self.hass.config_entries.async_initialize()
        await fr.async_load(self.hass)
        await ar.async_load(self.hass)
        dr.async_setup(self.hass)
        await dr.async_load(self.hass)
        await er.async_load(self.hass)
        self.config = await get_configuration(self.hass)

    async def asyncTearDown(self):
        await self.hass.async_stop()
        self.temp.cleanup()

    def room(self, name, state=ConfigEntryState.LOADED, reason="ventilate"):
        entry = ConfigEntry(domain="hestia_comfort", title=name, unique_id=name, version=1, minor_version=1,
            source="user", data={"name": name, "area_id": None}, options={}, discovery_keys={}, subentries_data=[])
        entry.runtime_data = SimpleNamespace(data={"assessment": {"reason": reason}})
        self.hass.config_entries._entries[entry.entry_id] = entry
        entry._async_set_state(self.hass, state, None)

    async def test_no_room_asks_to_start_with_the_living_room(self):
        status = await comfort_status(self.hass)
        self.assertEqual(status["level"], "action")
        self.assertIn("Salon", status["details"][0])

    async def test_everything_followed_is_blue(self):
        self.room("Salon")
        self.room("Cuisine")
        self.config.home = {"configured": True, "sources": {}, "revision": 1}
        status = await comfort_status(self.hass)
        self.assertEqual(status["level"], "ok")
        self.assertEqual(status["summary"], "2 pièces suivies, rien à régler.")

    async def test_what_to_fix_is_named(self):
        self.room("Salon", reason="incomplete_data")
        self.room("Cuisine", state=ConfigEntryState.SETUP_ERROR)
        status = await comfort_status(self.hass)
        self.assertEqual(status["level"], "action")
        # The same points as the « Confort » tab: a stopped room and the exterior.
        self.assertEqual(status["summary"], "2 pièces suivies, 2 points à régler.")
        self.assertIn("Cuisine : calcul arrêté", status["details"])
        self.assertIn("Extérieur à configurer", status["details"])

    async def test_a_silent_source_is_a_point_to_fix_even_when_advice_stands(self):
        for name in ("Salon", "Chambre"):
            self.room(name, reason="drying_possible")
        self.hass.states.async_set("sensor.atmo", "2")
        silent = {"value": None, "quality": "unknown", "source": "sensor.atmo"}
        for entry in self.hass.config_entries._entries.values():
            entry.runtime_data.data = {"assessment": {"reason": "drying_possible", "missing": ["pollution"]}, "observations": {"pollution": silent}}
        self.config.home = {"configured": True, "sources": {"pollution": {"entity_id": "sensor.atmo", "adapter": "binary"}}, "revision": 1}
        status = await comfort_status(self.hass)
        self.assertEqual(status["level"], "action")
        # Home Assistant still shows it, the advice cannot use it: one point, the same on the tab and on the home page.
        self.assertIn("Extérieur : la pollution ne donne pas de mesure exploitable", status["details"])


class Resources:
    """Dashboard resources as the user interface keeps them (lovelace's storage collection), not loaded yet."""
    def __init__(self, *urls):
        self.loaded, self.items = False, [{"id": str(i), "type": "module", "url": u} for i, u in enumerate(urls)]
    async def async_load(self):
        pass
    def async_items(self):
        return list(self.items)
    async def async_create_item(self, data):
        self.items.append({"id": f"n{len(self.items)}", "type": data["res_type"], "url": data["url"]})
    async def async_update_item(self, item_id, data):
        next(i for i in self.items if i["id"] == item_id)["url"] = data["url"]
    async def async_delete_item(self, item_id):
        self.items = [i for i in self.items if i["id"] != item_id]


class CardResourceTests(unittest.IsolatedAsyncioTestCase):
    URL = "/hestia_comfort-assets/hestia-comfort-card.js"

    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.temp.name)

    async def asyncTearDown(self):
        await self.hass.async_stop()
        self.temp.cleanup()

    def urls(self, resources):
        return [i["url"] for i in resources.items]

    async def test_the_card_becomes_a_dashboard_resource_at_its_version(self):
        resources = self.hass.data["lovelace"] = SimpleNamespace(resources=Resources("/hacsfiles/other/other.js"))
        await socle._card_resource(self.hass, self.URL, self.URL + "?v=1.0")
        self.assertTrue(resources.resources.loaded)
        self.assertEqual(self.urls(resources.resources), ["/hacsfiles/other/other.js", self.URL + "?v=1.0"])

    async def test_a_new_version_updates_it_and_duplicates_go(self):
        resources = Resources(self.URL + "?v=0.9", "/other.js", self.URL)
        self.hass.data["lovelace"] = SimpleNamespace(resources=resources)
        await socle._card_resource(self.hass, self.URL, self.URL + "?v=1.0")
        self.assertEqual(self.urls(resources), [self.URL + "?v=1.0", "/other.js"])
        await socle._card_resource(self.hass, self.URL, self.URL + "?v=1.0")
        self.assertEqual(self.urls(resources), [self.URL + "?v=1.0", "/other.js"])

    async def test_resources_written_in_yaml_are_left_alone(self):
        self.hass.data["lovelace"] = SimpleNamespace(resources=SimpleNamespace(async_items=lambda: []))
        await socle._card_resource(self.hass, self.URL, self.URL + "?v=1.0")  # nothing to create there: no error
        await socle.async_remove_card(self.hass, self.URL)

    async def test_removing_the_card_keeps_the_other_resources(self):
        resources = Resources("/other.js", self.URL + "?v=1.0")
        self.hass.data["lovelace"] = SimpleNamespace(resources=resources)
        await socle.async_remove_card(self.hass, self.URL)
        self.assertEqual(self.urls(resources), ["/other.js"])


if __name__ == "__main__":
    unittest.main()
