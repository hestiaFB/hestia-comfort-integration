"""What each device carries: a room alone, the rooms of one air (« Salon · Cuisine »), and the home.

The verdict entities (advice, state, colour, gestures) belong to whoever the card speaks for: a room alone, or the
shared air of several rooms. A room of a shared air keeps only its own measures (humidity, heating, learning)."""
from datetime import timedelta

from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .engine.verdict import ACTING, strongest
from .websocket import loaded_entries

# The keys of the verdict, by platform: on the room alone, or on the device of the shared air.
VERDICT_SENSORS = ("advice", "state", "colour")
VERDICT_BINARIES = ("gesture", "airing", "close", "ventilation")
# Each room keeps these, alone or in a shared air.
ROOM_SENSORS = ("humidity", "learning", "heating_action", "reason", "coverage", "twin_temperature", "twin_humidity")
ROOM_BINARIES = ("humid",)
HOME_SENSORS = ("rooms_asking", "advice", "colour")
HOME_BINARIES = ("gesture",)
HUMID = ("slightly_humid", "humid", "very_humid")


def room_device(entry):
    return {"identifiers": {(DOMAIN, entry.entry_id)}, "name": entry.title, "manufacturer": "Hestia-FB",
            "model": "Comfort · observation", "configuration_url": "homeassistant://hestia/confort"}


def volume_device(coordinator):
    return {"identifiers": {(DOMAIN, volume_id(coordinator))}, "name": coordinator.volume_name, "manufacturer": "Hestia-FB",
            "model": "Comfort · même air", "configuration_url": "homeassistant://hestia/confort"}


def volume_id(coordinator):
    return "volume_" + "_".join(sorted([coordinator.entry_id, *(p["entry_id"] for p in coordinator.partners)]))


def volume_owner(coordinator):
    """One room carries the shared air's device: the first named in « Salon · Cuisine », the best equipped."""
    if not coordinator.partners:
        return False
    first = coordinator.volume_name.split(" · ")[0]
    return (coordinator.config.get("name") or coordinator.config_entry.title) == first


def partner_coordinators(hass, coordinator):
    found = []
    for partner in coordinator.partners:
        entry = hass.config_entries.async_get_entry(partner["entry_id"])
        if (other := getattr(entry, "runtime_data", None)) is not None and getattr(other, "data", None):
            found.append(other)
    return found


def room_keys(coordinator):
    """Which keys this room's entry creates, by platform: its own, and the shared air's when it carries it."""
    alone = not coordinator.partners
    sensors = [*(VERDICT_SENSORS if alone else ()), *ROOM_SENSORS]
    binaries = [*(VERDICT_BINARIES if alone else ()), *ROOM_BINARIES]
    if volume_owner(coordinator):
        sensors += [f"volume:{k}" for k in VERDICT_SENSORS]
        binaries += [f"volume:{k}" for k in VERDICT_BINARIES]
    return {"sensor": sensors, "binary_sensor": binaries}


def unique_id(entry, coordinator, key):
    return f"{volume_id(coordinator)}_{key[7:]}" if key.startswith("volume:") else f"{entry.entry_id}_{key}"


def async_clean(hass, entry, coordinator):
    """The entities and devices this entry no longer provides go: « Situation » and « Geste », or a room joining a shared air."""
    keys = room_keys(coordinator)
    wanted = {unique_id(entry, coordinator, k) for platform in keys.values() for k in platform}
    registry = er.async_get(hass)
    for item in er.async_entries_for_config_entry(registry, entry.entry_id):
        if item.unique_id not in wanted:
            registry.async_remove(item.entity_id)
    # The shared air changed hands (the other room is now the best equipped): its entities follow, their history with them.
    for platform, platform_keys in keys.items():
        for key in platform_keys:
            entity_id = registry.async_get_entity_id(platform, DOMAIN, unique_id(entry, coordinator, key))
            if entity_id and (item := registry.async_get(entity_id)).config_entry_id != entry.entry_id:
                registry.async_update_entity(entity_id, config_entry_id=entry.entry_id)
    devices = dr.async_get(hass)
    # The room that carries the shared air shows only « Salon · Cuisine »: its own measures move there, history kept.
    if volume_owner(coordinator):
        shared = devices.async_get_or_create(config_entry_id=entry.entry_id, **volume_device(coordinator))
        own = {(DOMAIN, volume_id(coordinator))}
        for item in er.async_entries_for_config_entry(registry, entry.entry_id):
            if item.device_id != shared.id:
                registry.async_update_entity(item.entity_id, device_id=shared.id)
    else:
        own = {(DOMAIN, entry.entry_id)}
    for device in dr.async_entries_for_config_entry(devices, entry.entry_id):
        # Its entities moved or gone first: removing a device takes its remaining entities with it.
        if not device.identifiers & own:
            devices.async_remove_device(device.id)


def home_clean(hass, entry):
    registry = er.async_get(hass)
    wanted = {f"{entry.entry_id}_{k}" for k in (*HOME_SENSORS, *HOME_BINARIES)}
    for item in er.async_entries_for_config_entry(registry, entry.entry_id):
        if item.unique_id not in wanted:
            registry.async_remove(item.entity_id)


def ventilation_useful(views):
    """The VMC is worth running: the card asks for it, or it is running and the air is still humid (do not stop it then)."""
    for view in views:
        v = view.get("verdict") or {}
        if v.get("gesture") == "ventilation":
            return True
        running = (((view["assessment"].get("features") or {}).get("air") or {}).get("ventilation") or {}).get("on") is True
        if running and v.get("humidity") in HUMID:
            return True
    return False


def binary_value(key, verdict, views):
    gesture = verdict["gesture"]
    if key == "gesture":
        return gesture in ACTING
    if key == "airing":
        return gesture == "open"
    if key == "close":
        return gesture == "close"
    if key == "ventilation":
        return ventilation_useful(views)
    if key == "humid":
        return verdict.get("humidity") in HUMID
    return None


def units(hass, entries):
    """The home's units, each said once: a room alone, or the shared air of several rooms: (name, verdict)."""
    seen, out = set(), []
    for entry in entries:
        coordinator = getattr(entry, "runtime_data", None)
        if coordinator is None or not getattr(coordinator, "data", None) or not coordinator.data.get("verdict"):
            continue
        if coordinator.partners:
            key = volume_id(coordinator)
            if key in seen:
                continue
            seen.add(key)
            views = [coordinator.data, *(c.data for c in partner_coordinators(hass, coordinator))]
            out.append((coordinator.volume_name, strongest([v["verdict"] for v in views if v.get("verdict")])))
        else:
            out.append((coordinator.config.get("name") or entry.title, coordinator.data["verdict"]))
    return out


class VerdictEntity(CoordinatorEntity):
    """An entity of a room alone (key « advice »), of one of its own measures, or of its shared air (« volume:advice »)."""
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator)
        self.key = key
        self.shared = key.startswith("volume:")
        self.name_key = key[7:] if self.shared else key
        self._attr_unique_id = unique_id(entry, coordinator, key)
        self._attr_translation_key = self.name_key
        self._attr_device_info = room_device(entry)
        if self.shared:
            self._attr_device_info = volume_device(coordinator)
        elif volume_owner(coordinator):
            # Its own measures, on the shared air's device: « Humidité · Salon », never confused with the kitchen's.
            self._attr_device_info = volume_device(coordinator)
            self._attr_translation_key = f"{self.name_key}_room"
            self._attr_translation_placeholders = {"room": coordinator.config.get("name") or entry.title}
        self._listening = set()

    def views(self):
        own = self.coordinator.data
        if not self.shared:
            return [own]
        others = partner_coordinators(self.hass, self.coordinator)
        # The other rooms of the air refresh this entity too, once they are loaded.
        for other in others:
            if id(other) not in self._listening:
                self._listening.add(id(other))
                self.async_on_remove(other.async_add_listener(self._handle_coordinator_update))
        return [own, *(o.data for o in others)]

    def verdict(self):
        views = [v for v in self.views() if v and v.get("verdict")]
        return strongest([v["verdict"] for v in views]) if views else None


class HomeEntity:
    """An entity of « Mon logement »: the rooms' verdicts, refreshed when any room changes (rooms may load after the home)."""
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry, key):
        super().__init__()
        self.key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = f"home_{key}"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": entry.title, "manufacturer": "Hestia-FB",
                                  "model": "Comfort · logement", "configuration_url": "homeassistant://hestia/confort"}
        self._listening = {}

    async def async_added_to_hass(self):
        self.async_on_remove(async_track_time_interval(self.hass, callback(lambda _now: self._attach()), timedelta(seconds=60)))
        self.async_on_remove(lambda: [remove() for remove in self._listening.values()])
        self._attach()

    @callback
    def _attach(self):
        """Listen to every loaded room; a room reloaded brings a new coordinator, listened to in turn."""
        current = {id(e.runtime_data): e.runtime_data for e in loaded_entries(self.hass) if getattr(e, "runtime_data", None)}
        for key in [k for k in self._listening if k not in current]:
            self._listening.pop(key)()
        for key, coordinator in current.items():
            if key not in self._listening:
                self._listening[key] = coordinator.async_add_listener(self.async_write_ha_state)
        self.async_write_ha_state()

    def units(self):
        return units(self.hass, loaded_entries(self.hass))
