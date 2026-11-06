"""What the card says, as states for automations; rich observations stay out of Recorder."""
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.helpers.entity import EntityCategory

from .engine.assessment import REASONS
from .engine.verdict import ACTING as GESTURES_ACTING, HUMIDITY, STATES, strongest
from .entities import HOME_SENSORS, HomeEntity, VerdictEntity, room_keys

DESCRIPTIONS = {d.key: d for d in (
    # The banner's title, word for word (« Aérez 10 min »); its gesture, stable, is an attribute.
    SensorEntityDescription(key="advice", translation_key="advice", icon="mdi:hand-wave-outline"),
    SensorEntityDescription(key="state", translation_key="state", device_class=SensorDeviceClass.ENUM, options=sorted(set(STATES.values()))),
    # The card's colour, for a light: hex as state, rgb_color and a saturated hs_color as attributes.
    SensorEntityDescription(key="colour", translation_key="colour", icon="mdi:palette-outline"),
    SensorEntityDescription(key="humidity", translation_key="humidity", device_class=SensorDeviceClass.ENUM, options=list(HUMIDITY),
                            icon="mdi:water-percent"),
    SensorEntityDescription(key="learning", translation_key="learning", native_unit_of_measurement=PERCENTAGE, icon="mdi:school-outline"),
    SensorEntityDescription(key="heating_action", translation_key="heating_action", device_class=SensorDeviceClass.ENUM,
                            options=["heating", "idle", "off", "cooling", "unknown", "not_configured"]),
    # Why, in the engine's terms: for diagnosis, the card's words are in « Conseil ».
    SensorEntityDescription(key="reason", translation_key="reason", entity_category=EntityCategory.DIAGNOSTIC,
                            device_class=SensorDeviceClass.ENUM, options=list(REASONS), entity_registry_enabled_default=False),
    SensorEntityDescription(key="coverage", translation_key="coverage", entity_category=EntityCategory.DIAGNOSTIC,
                            device_class=SensorDeviceClass.ENUM, options=["partial", "configured_sources_available"]),
    # The twin's view of the coming hour, to lay over the real sensors in the history: off until asked for.
    SensorEntityDescription(key="twin_temperature", translation_key="twin_temperature", entity_category=EntityCategory.DIAGNOSTIC,
                            device_class=SensorDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                            suggested_display_precision=1, entity_registry_enabled_default=False),
    SensorEntityDescription(key="twin_humidity", translation_key="twin_humidity", entity_category=EntityCategory.DIAGNOSTIC,
                            device_class=SensorDeviceClass.HUMIDITY, native_unit_of_measurement=PERCENTAGE,
                            entity_registry_enabled_default=False),
)}
HOME_DESCRIPTIONS = {
    "rooms_asking": SensorEntityDescription(key="rooms_asking", icon="mdi:home-alert-outline"),
    "advice": SensorEntityDescription(key="advice", icon="mdi:hand-wave-outline"),
    "colour": SensorEntityDescription(key="colour", icon="mdi:palette-outline"),
}


def colour_attributes(verdict):
    return {"rgb_color": verdict["rgb"], "hs_color": [verdict["hue"], 100] if verdict["hue"] is not None else None,
            "niveau": verdict["mood"]}


async def async_setup_entry(hass, entry, async_add_entities):
    if entry.data.get("home"):
        async_add_entities(HomeSensor(entry, HOME_DESCRIPTIONS[k]) for k in HOME_SENSORS)
        return
    coordinator = entry.runtime_data
    async_add_entities(ComfortSensor(coordinator, entry, key) for key in room_keys(coordinator)["sensor"])


class ComfortSensor(VerdictEntity, SensorEntity):
    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator, entry, key)
        self.entity_description = DESCRIPTIONS[self.name_key]

    @property
    def native_value(self):
        data, key = self.coordinator.data, self.name_key
        assessment = data["assessment"]
        if key.startswith("twin_"):
            coming = (data.get("twin") or {}).get("next_hour") or {}
            return coming.get(key[5:])
        if key == "coverage":
            return "partial" if assessment["partial"] else "configured_sources_available"
        if key in ("reason", "heating_action"):
            return assessment[key]
        if key == "learning":
            return ((data.get("twin") or {}).get("progress") or {}).get("percent")
        verdict = self.verdict() if self.shared else data.get("verdict")
        if not verdict:
            return None
        return {"advice": verdict["title"], "state": verdict["state"], "colour": verdict["colour"], "humidity": verdict["humidity"]}[key]

    @property
    def extra_state_attributes(self):
        if self.name_key == "heating_action":
            # Where the state comes from: the thermostat's own action, or the indicator chosen beside it.
            seen = (self.coordinator.data.get("observations") or {}).get("heating") or {}
            source = {"indicator": "indicateur", "hvac_action": "hvac_action", "hvac_mode": "mode"}.get(seen.get("detail"))
            indicator = self.coordinator.sources.get("heating_indicator")
            return {"source": source, **({"indicateur": indicator} if indicator else {})} if seen else None
        if self.name_key == "reason":
            result = self.coordinator.data["assessment"]
            return {k: result[k] for k in ("needs", "constraints", "partial", "missing")}
        if self.name_key not in ("advice", "colour"):
            return None
        verdict = self.verdict() if self.shared else self.coordinator.data.get("verdict")
        if not verdict:
            return None
        if self.name_key == "colour":
            return colour_attributes(verdict)
        return {"geste": verdict["gesture"], "precision": verdict["cap"], "appris": verdict["learned"], "pastille": verdict["pill"]}


class HomeSensor(HomeEntity, SensorEntity):
    def __init__(self, entry, description):
        super().__init__(entry, description.key)
        self.entity_description = description
        self._attr_translation_key = f"home_{description.key}"

    def _first(self):
        found = self.units()
        best = strongest([v for _, v in found])
        return next(((name, v) for name, v in found if v is best), (None, None))

    @property
    def native_value(self):
        found = self.units()
        if self.key == "rooms_asking":
            return sum(1 for _, v in found if v["gesture"] in GESTURES_ACTING)
        name, verdict = self._first()
        if verdict is None:
            return None
        if self.key == "colour":
            return verdict["colour"]
        return f"{name} : {verdict['title']}" if verdict["gesture"] in GESTURES_ACTING else "Rien à faire"

    @property
    def extra_state_attributes(self):
        name, verdict = self._first()
        if verdict is None:
            return None
        if self.key == "colour":
            return colour_attributes(verdict)
        if self.key == "rooms_asking":
            return {"pieces": [n for n, v in self.units() if v["gesture"] in GESTURES_ACTING]}
        return {"piece": name, "geste": verdict["gesture"], "pastille": verdict["pill"]}
