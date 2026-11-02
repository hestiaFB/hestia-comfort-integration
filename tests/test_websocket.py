"""Real HA command wrappers with an isolated registry and connection fixture."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, floor_registry as fr
from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
from custom_components.hestia_comfort.coordinator import ComfortCoordinator
from custom_components.hestia_comfort.websocket import ws_entries, ws_subscribe


class WebsocketTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self.temp.name)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        await self.hass.config_entries.async_initialize()
        await fr.async_load(self.hass)
        await ar.async_load(self.hass)
        self.conn = Mock(subscriptions={})

    async def asyncTearDown(self):
        for remove in list(self.conn.subscriptions.values()):
            remove()
        await self.hass.async_stop()
        self.temp.cleanup()

    async def add(self, area):
        entry = ConfigEntry(domain="hestia_comfort", title=area, unique_id=area, version=1, minor_version=1,
            source="user", data={"name": area, "area_id": area}, options={}, discovery_keys={}, subentries_data=[])
        coordinator = ComfortCoordinator(self.hass, entry)
        coordinator.data = await coordinator._async_update_data()
        entry.runtime_data = coordinator
        self.hass.config_entries._entries[entry.entry_id] = entry
        entry._async_set_state(self.hass, ConfigEntryState.LOADED, None)
        return entry

    async def test_no_entry(self):
        ws_subscribe(self.hass, self.conn, {"id": 1, "type": "hestia_comfort/subscribe"})
        self.assertEqual(self.conn.send_error.call_args.args[1], "not_configured")

    async def test_multiple_requires_explicit_room(self):
        await self.add("salon")
        await self.add("bureau")
        ws_subscribe(self.hass, self.conn, {"id": 1, "type": "hestia_comfort/subscribe"})
        self.assertEqual(self.conn.send_error.call_args.args[1], "choose_entry")

    async def test_initial_push_updates_unavailable_and_cleanup(self):
        entry = await self.add("salon")
        coordinator = entry.runtime_data
        ws_subscribe(self.hass, self.conn, {"id": 1, "type": "hestia_comfort/subscribe", "entry_id": entry.entry_id})
        self.assertEqual(self.conn.send_message.call_args.args[0]["event"]["view"]["area_id"], "salon")
        self.assertEqual(len(coordinator.stop_listeners), 1)
        coordinator.async_set_update_error(ValueError("fixture unavailable"))
        self.assertTrue(self.conn.send_message.call_args.args[0]["event"]["unavailable"])
        coordinator.async_stopped()
        self.assertTrue(self.conn.send_message.call_args.args[0]["event"]["reload"])
        self.conn.subscriptions[1]()
        self.assertEqual(len(coordinator.stop_listeners), 0)

    async def test_entry_picker_and_removed_room(self):
        entry = await self.add("salon")
        ws_entries(self.hass, self.conn, {"id": 1, "type": "hestia_comfort/entries"})
        self.assertEqual(self.conn.send_result.call_args.args[1][0]["entry_id"], entry.entry_id)
        ws_subscribe(self.hass, self.conn, {"id": 2, "type": "hestia_comfort/subscribe", "entry_id": "missing"})
        self.assertEqual(self.conn.send_error.call_args.args[1], "not_found")

    async def test_registry_changes_refresh_and_failed_room_remains(self):
        from custom_components.hestia_comfort.websocket import ws_home_subscribe
        # The rooms' refreshes are grouped for a second: here the grouped send runs at the loop's next turn.
        grouped = patch('custom_components.hestia_comfort.websocket.async_call_later',
                        lambda hass, delay, action: (hass.loop.call_soon(action), lambda: None)[1])
        grouped.start()
        self.addCleanup(grouped.stop)
        entry = await self.add('salon')
        ar.async_get(self.hass).async_create('Salon')
        floor = fr.async_get(self.hass).async_create('RDC', level=0)
        ws_home_subscribe(self.hass, self.conn, {'id':2,'type':'hestia_comfort/home_subscribe'})
        self.assertIsNone(self.conn.send_message.call_args.args[0]['event']['home']['floors'][0]['floor_id'])
        ar.async_get(self.hass).async_update('salon',floor_id=floor.floor_id)
        await self.hass.async_block_till_done()
        self.assertEqual(self.conn.send_message.call_args.args[0]['event']['home']['floors'][0]['name'],'RDC')
        entry.runtime_data.async_set_update_error(ValueError('fixture unavailable'))
        await self.hass.async_block_till_done()
        event=self.conn.send_message.call_args.args[0]['event']
        self.assertEqual(len(event['rooms']),1)
        self.assertTrue(event['home']['partial'])
        self.assertEqual(event['home']['floors'][0]['measured'],0)
        self.conn.subscriptions[2]()
        count=self.conn.send_message.call_count
        fr.async_get(self.hass).async_update(floor.floor_id,name='Renommé')
        await self.hass.async_block_till_done()
        self.assertEqual(self.conn.send_message.call_count,count)

    async def test_a_room_reloading_without_runtime_data_does_not_break_the_home_feed(self):
        """Issue #45: Home Assistant drops runtime_data while a room unloads; the feed must neither raise nor skip the room."""
        from custom_components.hestia_comfort.websocket import ws_home_subscribe, ws_view, loaded_entries
        grouped = patch('custom_components.hestia_comfort.websocket.async_call_later',
                        lambda hass, delay, action: (hass.loop.call_soon(action), lambda: None)[1])
        grouped.start()
        self.addCleanup(grouped.stop)
        entry = await self.add('salon')
        ws_home_subscribe(self.hass, self.conn, {'id': 3, 'type': 'hestia_comfort/home_subscribe'})
        coordinator = entry.runtime_data
        del entry.runtime_data  # what Home Assistant does on unload
        coordinator.async_set_update_error(ValueError('fixture unavailable'))
        await self.hass.async_block_till_done()
        self.assertEqual(len(self.conn.send_message.call_args.args[0]['event']['rooms']), 1)
        self.assertEqual(loaded_entries(self.hass), [])
        ws_view(self.hass, self.conn, {'id': 4, 'type': 'hestia_comfort/view', 'entry_id': entry.entry_id})
        self.assertEqual(self.conn.send_error.call_args.args[1], 'not_found')

    def test_a_refresh_that_changed_nothing_is_not_sent_again_before_the_heartbeat(self):
        from custom_components.hestia_comfort import websocket
        conn = Mock()
        sender = websocket._Sender(conn, 7)
        view = {"version": 1, "view": {"computed_at": "2026-10-29T10:00:00", "assessment": {"action": "rien"}}}
        with patch.object(websocket.time, "monotonic", return_value=100.0):
            sender(view)
            sender({"version": 1, "view": {**view["view"], "computed_at": "2026-10-29T10:00:10"}})
            self.assertEqual(conn.send_message.call_count, 1)
            sender({"version": 1, "view": {**view["view"], "assessment": {"action": "ouvrir"}}})
            self.assertEqual(conn.send_message.call_count, 2)
        # Unchanged, it still goes out every HEARTBEAT_SECONDS: the card calls a view older than 75 s stale.
        with patch.object(websocket.time, "monotonic", return_value=100.0 + websocket.HEARTBEAT_SECONDS):
            sender({"version": 1, "view": {**view["view"], "assessment": {"action": "ouvrir"}}})
        self.assertEqual(conn.send_message.call_count, 3)


if __name__ == "__main__":
    unittest.main()
