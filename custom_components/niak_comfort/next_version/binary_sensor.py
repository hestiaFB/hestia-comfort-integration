"""Yes or no, for automations: a gesture to make, air the room, shut a window, run the VMC, too humid."""
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity, BinarySensorEntityDescription

from .engine.verdict import ACTING
from .entities import HOME_BINARIES, HomeEntity, VerdictEntity, binary_value, room_keys

DESCRIPTIONS = {d.key: d for d in (
    BinarySensorEntityDescription(key="gesture", translation_key="gesture", icon="mdi:hand-back-right-outline"),
    BinarySensorEntityDescription(key="airing", translation_key="airing", icon="mdi:window-open-variant"),
    BinarySensorEntityDescription(key="close", translation_key="close", icon="mdi:window-closed-variant"),
    BinarySensorEntityDescription(key="ventilation", translation_key="ventilation", icon="mdi:fan"),
    BinarySensorEntityDescription(key="humid", translation_key="humid", device_class=BinarySensorDeviceClass.MOISTURE),
)}


async def async_setup_entry(hass, entry, async_add_entities):
    if entry.data.get("home"):
        async_add_entities(HomeBinary(entry, key) for key in HOME_BINARIES)
        return
    coordinator = entry.runtime_data
    async_add_entities(ComfortBinary(coordinator, entry, key) for key in room_keys(coordinator)["binary_sensor"])


class ComfortBinary(VerdictEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator, entry, key)
        self.entity_description = DESCRIPTIONS[self.name_key]

    @property
    def is_on(self):
        views = self.views() if self.shared else [self.coordinator.data]
        verdict = self.verdict() if self.shared else self.coordinator.data.get("verdict")
        return binary_value(self.name_key, verdict, views) if verdict else None


class HomeBinary(HomeEntity, BinarySensorEntity):
    _attr_icon = "mdi:hand-back-right-outline"

    @property
    def is_on(self):
        return any(v["gesture"] in ACTING for _, v in self.units())
