"""Yes or no, for automations: a gesture to make, air the room, shut a window, run the VMC or its turbo, too humid."""
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .engine import ventilation
from .engine.verdict import ACTING
from .entities import HOME_BINARIES, HomeEntity, VerdictEntity, binary_value, room_keys

DESCRIPTIONS = {d.key: d for d in (
    BinarySensorEntityDescription(key="gesture", translation_key="gesture", icon="mdi:hand-back-right-outline"),
    BinarySensorEntityDescription(key="airing", translation_key="airing", icon="mdi:window-open-variant"),
    BinarySensorEntityDescription(key="close", translation_key="close", icon="mdi:window-closed-variant"),
    BinarySensorEntityDescription(key="ventilation", translation_key="ventilation", icon="mdi:fan"),
    BinarySensorEntityDescription(key="boost", translation_key="boost", icon="mdi:fan-speed-3"),
    BinarySensorEntityDescription(key="humid", translation_key="humid", device_class=BinarySensorDeviceClass.MOISTURE),
)}


async def async_setup_entry(hass, entry, async_add_entities):
    if entry.data.get("home"):
        async_add_entities(HomeBinary(entry, key) for key in HOME_BINARIES)
        return
    coordinator = entry.runtime_data
    async_add_entities(ComfortBinary(coordinator, entry, key) for key in room_keys(coordinator)["binary_sensor"])


class ComfortBinary(VerdictEntity, BinarySensorEntity, RestoreEntity):
    """Its last state is kept across a restart: « VMC conseillée » goes on from it."""

    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator, entry, key)
        self.entity_description = DESCRIPTIONS[self.name_key]

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        # Running before the restart or the reload, the VMC goes on (engine/ventilation.py `resume`), before this entity
        # first says anything: an automation that follows it stopped the extractor for the minute the advisor needed to
        # speak again (Chambre P, 8 November at 12 h 53).
        data = self.coordinator.data
        if self.key != "ventilation" or not data or (last := await self.async_get_last_state()) is None or last.state != "on":
            return
        now = dt_util.utcnow()
        ventilation.resume(self.coordinator.vmc_memory, True, now)
        data["vmc"] = ventilation.advise(data, self.coordinator.config, self.coordinator.vmc_memory, now)

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
