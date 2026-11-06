"""Our analysis tools, off by default (PLAN-OPTIMISATION.md, point 16): the switch is kept through the general settings,
and « Ce conseil ne va pas » keeps the situation without any snapshot written before."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.hestia_comfort.advisor_store import AdvisorFiles


class Signal(unittest.TestCase):
    def test_a_report_keeps_the_situation_held_in_memory(self):
        with tempfile.TemporaryDirectory() as folder:
            files = AdvisorFiles(folder)
            # No snapshot written (the tools off): without the one in memory, nothing could be joined.
            self.assertIsNone(files.signal("salon", datetime(2026, 11, 6, 18, tzinfo=timezone.utc), "faux", "", {}))
            snap = {"room": "Salon"}
            with patch("custom_components.hestia_comfort.advisor_store.replay", return_value=("decision", {})), \
                 patch("custom_components.hestia_comfort.advisor_store.trace", return_value={"trace": 1}):
                name = files.signal("salon", datetime(2026, 11, 6, 18, tzinfo=timezone.utc), "faux", "trop chaud", {}, snap)
            kept = json.loads((Path(folder) / "hestia_comfort" / "signales" / name).read_text(encoding="utf-8"))
            self.assertEqual((kept["instantane"], kept["note"]), (snap, "trop chaud"))
            self.assertFalse((Path(folder) / "hestia_comfort" / "instantanes").exists())


class Switch(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from homeassistant.config_entries import ConfigEntries
        from homeassistant.core import HomeAssistant
        from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er, floor_registry as fr
        from custom_components.hestia_comfort.configuration import get_configuration
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

    async def test_off_by_default_and_kept_through_the_general_settings(self):
        self.assertFalse(self.config.snapshot()["home"]["analysis"])
        self.assertTrue((await self.config.set_analysis(True))["home"]["analysis"])
        await self.config.save({}, self.config.revision(), home=True)
        self.assertTrue(self.config.home["analysis"])
        with self.assertRaises(ValueError):
            await self.config.set_analysis("oui")


if __name__ == "__main__":
    unittest.main()
