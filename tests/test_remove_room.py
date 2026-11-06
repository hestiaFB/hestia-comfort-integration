"""A room removed takes its files with it (PLAN-OPTIMISATION.md, point 17); the other rooms keep theirs."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntries
from homeassistant.helpers.storage import Store
import custom_components.hestia_comfort as comfort


class RemoveRoom(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.temp.name)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        await self.hass.config_entries.async_initialize()

    async def asyncTearDown(self):
        await self.hass.async_stop()
        self.temp.cleanup()

    async def test_its_files_go_with_it(self):
        for room in ("gone", "kept"):
            for kind in comfort.ROOM_STORES:
                await Store(self.hass, 1, f"hestia_comfort.{kind}.{room}").async_save({"x": 1})
        folder = Path(self.temp.name) / ".storage"
        self.assertEqual(len(list(folder.glob("hestia_comfort.*.gone"))), 4)
        with patch.object(comfort, "async_remove_card", AsyncMock()):
            await comfort.async_remove_entry(self.hass, SimpleNamespace(entry_id="gone"))
        await self.hass.async_block_till_done()
        self.assertEqual(list(folder.glob("hestia_comfort.*.gone")), [])
        self.assertEqual(len(list(folder.glob("hestia_comfort.*.kept"))), 4)


if __name__ == "__main__":
    unittest.main()
