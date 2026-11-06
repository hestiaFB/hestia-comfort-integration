"""Versioned, one-time adoption of the explained operating references."""
from copy import deepcopy
import re

from homeassistant.helpers import entity_registry as er

from .discovery import candidate, voc_reference

AIR_REFERENCE_VERSION = 1
AIR_DEFAULTS = {"co2_potential": 800, "co2_action": 1000, "co2_urgent": 1500,
                "pm25_action": 15, "humidity_high": 60}


FRESHNESS_VERSION = 1
OLD_MAX_AGE, MAX_AGE = 1800, 10800


def apply_freshness(hass, entry):
    """Once: rooms saved with the former 30-minute expiry move to 3 hours (sensors that report only on change)."""
    config = deepcopy({**entry.data, **entry.options})
    if config.get("home") or config.get("freshness_version", 0) >= FRESHNESS_VERSION:
        return False
    settings = config.get("settings", {})
    if settings.get("max_age_seconds") == OLD_MAX_AGE:
        config["settings"] = {**settings, "max_age_seconds": MAX_AGE}
    config["freshness_version"] = FRESHNESS_VERSION
    hass.config_entries.async_update_entry(entry, options=config)
    return True


def apply_air_references(hass, entry):
    """Apply once before the coordinator/update listener starts, preserving edits thereafter."""
    config = deepcopy({**entry.data, **entry.options})
    if config.get("home") or config.get("air_reference_version", 0) >= AIR_REFERENCE_VERSION:
        return False
    config["settings"] = {**config.get("settings", {}), **AIR_DEFAULTS}
    eid = config.get("sources", {}).get("voc")
    reference = None
    if eid:
        found = candidate(hass, eid, "voc")
        reference = found.get("voc_reference") if found else None
        # At startup MQTT may not have restored a state yet. Its explicit property
        # id plus identified hardware still establish an IKEA index, without using
        # a user-assigned entity name or guessing a concentration unit.
        registry = er.async_get(hass).async_get(eid)
        if (hass.states.get(eid) is None and registry and registry.platform == "mqtt"
                and re.fullmatch(r"0x[0-9a-fA-F]{16}_voc_index_zigbee2mqtt", registry.unique_id or "")):
            reference = voc_reference(hass, registry, "volatile_organic_compounds_index", None)
    if reference:
        config["evolution"] = {**config.get("evolution", {}),
                               "voc_threshold": {"value": reference["value"], "unit": reference["unit"]}}
    config["air_reference_version"] = AIR_REFERENCE_VERSION
    hass.config_entries.async_update_entry(entry, options=config)
    return True
