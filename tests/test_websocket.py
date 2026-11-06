"""Real HA command wrappers with an isolated registry and connection fixture."""
import json
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
from custom_components.hestia_comfort.websocket import _texts, ws_entries, ws_subscribe


def sent(connection):
    """The last message sent: already turned into text for a room's view (PLAN-OPTIMISATION.md, point 4), a dict otherwise."""
    message = connection.send_message.call_args.args[0]
    return json.loads(message) if isinstance(message, (bytes, str)) else message


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
        self.assertEqual(sent(self.conn)["event"]["view"]["area_id"], "salon")
        self.assertEqual(len(coordinator.stop_listeners), 1)
        coordinator.async_set_update_error(ValueError("fixture unavailable"))
        self.assertTrue(sent(self.conn)["event"]["unavailable"])
        coordinator.async_stopped()
        self.assertTrue(sent(self.conn)["event"]["reload"])
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
        self.assertIsNone(sent(self.conn)['event']['home']['floors'][0]['floor_id'])
        ar.async_get(self.hass).async_update('salon',floor_id=floor.floor_id)
        await self.hass.async_block_till_done()
        self.assertEqual(sent(self.conn)['event']['home']['floors'][0]['name'],'RDC')
        entry.runtime_data.async_set_update_error(ValueError('fixture unavailable'))
        await self.hass.async_block_till_done()
        event=sent(self.conn)['event']
        self.assertEqual(len(event['rooms']),1)
        self.assertTrue(event['home']['partial'])
        self.assertEqual(event['home']['floors'][0]['measured'],0)
        self.conn.subscriptions[2]()
        count=self.conn.send_message.call_count
        fr.async_get(self.hass).async_update(floor.floor_id,name='Renommé')
        await self.hass.async_block_till_done()
        self.assertEqual(self.conn.send_message.call_count,count)

    async def test_the_home_card_gets_every_room_once_then_only_those_that_changed(self):
        from custom_components.hestia_comfort.websocket import ws_home_subscribe
        grouped = patch('custom_components.hestia_comfort.websocket.async_call_later',
                        lambda hass, delay, action: (hass.loop.call_soon(action), lambda: None)[1])
        grouped.start()
        self.addCleanup(grouped.stop)
        salon, cuisine = await self.add('salon'), await self.add('cuisine')
        ws_home_subscribe(self.hass, self.conn, {'id': 3, 'type': 'hestia_comfort/home_subscribe', 'changes': True})
        event = sent(self.conn)['event']
        self.assertEqual(sorted(v['entry_id'] for v in event['changed']), sorted([salon.entry_id, cuisine.entry_id]))
        self.assertEqual(event['order'], [cuisine.entry_id, salon.entry_id])
        self.assertNotIn('rooms', event)
        count = self.conn.send_message.call_count
        # The salon computed again, its view the same but for its time: nothing goes out.
        salon.runtime_data.async_set_updated_data({**salon.runtime_data.data, 'computed_at': '2026-11-06T15:00:00+00:00'})
        await self.hass.async_block_till_done()
        self.assertEqual(self.conn.send_message.call_count, count)
        # The salon's advice changed: only the salon goes out, with the order and the synthesis.
        salon.runtime_data.async_set_updated_data({**salon.runtime_data.data, 'title': 'Salon (nouveau)'})
        await self.hass.async_block_till_done()
        event = sent(self.conn)['event']
        self.assertEqual([v['entry_id'] for v in event['changed']], [salon.entry_id])
        self.assertEqual(len(event['order']), 2)
        self.assertIn('home', event)
        self.conn.subscriptions[3]()

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


class SharedText(unittest.TestCase):
    def test_a_view_is_converted_once_for_every_card(self):
        view = {"entry_id": "a", "computed_at": "2026-11-06T12:00:00+00:00", "rooms": [{"computed_at": "x", "t": 20.5}]}
        first = _texts(view)
        self.assertIs(_texts(view)[1], first[1])
        self.assertNotIn(b"computed_at", first[0])
        self.assertEqual(json.loads(first[1]), view)
        # The same view computed again a minute later: the cards are told nothing changed.
        self.assertEqual(_texts({**view, "computed_at": "2026-11-06T12:01:00+00:00"})[0], first[0])


if __name__ == "__main__":
    unittest.main()
