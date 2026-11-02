"""« Télécharger les diagnostics »: what Hestia reads and computes for one room, in one file to share in an issue.

Everything the card is sent (the advice, the measures as read), what the room has learned, the raw state of each
chosen sensor and the first forecast hours, so that a strange advice can be explained without access to the home.
The home's coordinates are removed, and so are the people: their names and where they are (a `person` or a tracker
is in a zone whose name may be a town or an address) are reduced to how many are at home or away.
Entity names stay, they are what the person will recognise.
"""
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.util import dt as dt_util

from . import health, weather_link
from .const import VERSION
from .engine import feedback

TO_REDACT = {"latitude", "longitude", "elevation", "location", "persons", "gps_accuracy"}
# Entities whose state is a zone's name: only « at home » or « away » is kept.
WHEREABOUTS = ("person", "device_tracker")
# The attributes of a sensor or a thermostat that explain a reading; the rest (icons, pictures) is left out.
ATTRIBUTES = ("unit_of_measurement", "device_class", "state_class", "friendly_name", "hvac_action", "hvac_mode",
              "hvac_modes", "preset_mode", "temperature", "current_temperature", "current_position", "percentage",
              "specific_states", "preset_temperatures", "window_manager", "presence_manager", "motion_manager",
              "hvac_off_reason", "temperature_slope", "is_device_active", "window_state", "window_auto_state",
              "presence_state", "motion_state", "eco_temp", "comfort_temp", "frost_temp",
              "window_open", "temp_slope_K_min", "bt_preset_heat_temperatures", "bt_preset_cool_temperatures")


def _state(hass, entity_id):
    state = hass.states.get(entity_id) if isinstance(entity_id, str) else None
    if state is None:
        return {"entity_id": entity_id, "state": None, "missing": True}
    value = state.state
    if entity_id.split(".")[0] in WHEREABOUTS and value not in ("home", "not_home", "unknown", "unavailable"):
        value = "not_home"
    return {"entity_id": entity_id, "state": value, "last_updated": state.last_updated.isoformat(),
            "last_reported": getattr(state, "last_reported", state.last_updated).isoformat(),
            "attributes": {k: state.attributes[k] for k in ATTRIBUTES if k in state.attributes}}


def _entities(config, home_sources):
    """Every entity this room reads: its sources, windows, presence, covers and the home's exterior."""
    found = {f"source:{k}": v for k, v in (config.get("sources") or {}).items() if isinstance(v, str)}
    found.update({f"window:{e}": e for e in config.get("windows") or []})
    found.update({f"presence:{e}": e for e in config.get("presence") or []})
    for entity_id, meta in (config.get("openings") or {}).items():
        for field in ("cover_entity", "auto_entity", "override_entity"):
            if isinstance(meta, dict) and isinstance(meta.get(field), str):
                found[f"{field}:{entity_id}"] = meta[field]
    found.update({f"exterior:{k}": spec["entity_id"] for k, spec in (home_sources or {}).items()
                  if isinstance(spec, dict) and isinstance(spec.get("entity_id"), str)})
    return found


def _without_names(value):
    """The room's view with its people counted instead of named, wherever « people » appears in it."""
    if isinstance(value, list):
        return [_without_names(v) for v in value]
    if not isinstance(value, dict):
        return value
    return {k: ({group: len(names) for group, names in v.items() if isinstance(names, list)}
                if k == "people" and isinstance(v, dict) else _without_names(v)) for k, v in value.items()}


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = getattr(entry, "runtime_data", None)
    config = {**entry.data, **entry.options}
    now = dt_util.utcnow()
    home = getattr(coordinator, "home_configuration", None)
    home_sources = home.live_sources(config) if home is not None and hasattr(home, "live_sources") else {}
    twin = getattr(coordinator, "twin", None) or {}
    model = twin.get("model") or {}
    records = getattr(coordinator, "feedback", None) or []
    outlook = weather_link.outlook(hass, coordinator._weather_place()) if coordinator is not None and hasattr(coordinator, "_weather_place") else {}
    try:
        report = health.report(await health.facts(hass, VERSION))
    except Exception as err:  # noqa: BLE001 - the file must come out even when the report fails.
        report = {"error": repr(err)}
    result = {
        "version": VERSION,
        "generated_at": now.isoformat(),
        "room": {"title": entry.title, "state": entry.state.value, "config": config},
        "view": _without_names(getattr(coordinator, "data", None)),
        "thermostat": coordinator._thermostat() if coordinator is not None and hasattr(coordinator, "_thermostat") else None,
        "learning": {
            "twin": {**{k: twin.get(k) for k in ("status", "days", "samples", "open_samples", "mass", "room", "computed_at")},
                     "model": {k: model.get(k) for k in ("thermal", "water", "samples")} if model else None,
                     # The 24-hour replay is long and already in « view »: its errors are enough here.
                     "precision": {k: v for k, v in (twin.get("precision") or {}).items() if k != "curve"} or None},
            "drying": getattr(coordinator, "drying_model", None),
            "feedback": feedback.summarize(records, now) if records else None,
            "last_airings": records[-10:],
        },
        "states": {key: _state(hass, entity_id) for key, entity_id in _entities(config, home_sources).items()},
        "outlook": {"keys": sorted(outlook) if isinstance(outlook, dict) else None,
                    "first_hours": (outlook.get("hours") or [])[:6] if isinstance(outlook, dict) else None,
                    "tomorrow_max": outlook.get("tomorrow_max") if isinstance(outlook, dict) else None},
        "home": {"sources": home_sources, "weather": weather_link.status(hass)},
        "health": report,
    }
    return async_redact_data(result, TO_REDACT)
