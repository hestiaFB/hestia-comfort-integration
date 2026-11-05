"""Explain candidates using registry metadata and explicit sensor provenance."""
import re

from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er

from . import weather_link
from .const import OUTDOOR_AREAS, SOURCES
from .engine import thermostat as thermostats
from .engine.sources import INDICATOR_RESTING, INDICATOR_RUNNING

INDOOR = ("indoor_temperature", "indoor_humidity", "co2", "windows", "heating", "heating_indicator", "illuminance", "pm25", "voc", "purifier", "ventilation", "ventilation_boost", "presence")
OPENING_SOURCES = ("covers", "shutter_auto", "shutter_override")
OUTDOOR = ("outdoor_temperature", "outdoor_humidity", "rain", "wind_gust", "wind_bearing", "solar", "pollution", "season")
# A season sensor (the Season integration, or a template): its state, in English or in French.
# The names of what says a heating runs: a valve, a relay, a work state.
INDICATOR_WORDS = ("vanne", "valve", "work_state", "chauffe", "heating", "relais", "relay", "demand", "demande")
SEASONS = {"spring": "spring", "printemps": "spring", "summer": "summer", "ete": "summer", "été": "summer",
           "autumn": "autumn", "fall": "autumn", "automne": "autumn", "winter": "winter", "hiver": "winter"}
CLASSES = {"temperature": "temperature", "humidity": "humidity", "co2": "carbon_dioxide",
           "wind": "wind_speed", "irradiance": "irradiance", "bearing": "wind_direction"}
UNITS = {"temperature": ("°C", "°F", "K"), "humidity": ("%",), "co2": ("ppm",),
         "wind": ("km/h", "m/s", "mph", "kn", "ft/s"), "irradiance": ("W/m²",), "bearing": ("°",)}


def voc_device_class(hass, entity_id):
    """Identify VOC semantics from declared metadata or a known Z2M property.

    Zigbee2MQTT exposes voc_index without a HA class or unit on VINDSTYRKA.
    Its registry unique id identifies the property independently of user names.
    Atmo France's pollen concentrations also carry a VOC class: exclude them.
    """
    state = hass.states.get(entity_id)
    entry = er.async_get(hass).async_get(entity_id)
    if not state or (entry and entry.platform == "atmofrance"):
        return None
    kind = (state.attributes.get("device_class") or
            (entry.device_class or entry.original_device_class if entry else None))
    if (kind is None and entry and entry.platform == "mqtt" and
            re.fullmatch(r"0x[0-9a-fA-F]{16}_voc_index_zigbee2mqtt", entry.unique_id or "")):
        return "volatile_organic_compounds_index"
    return kind if kind in ("volatile_organic_compounds", "volatile_organic_compounds_parts", "volatile_organic_compounds_index") else None


def voc_reference(hass, entry, device_class, unit):
    """Offer a manufacturer-based index preset only for identified hardware."""
    device = dr.async_get(hass).async_get(entry.device_id) if entry.device_id else None
    if (device_class == "volatile_organic_compounds_index" and unit in (None, "index", "indice", "VOC index")
            and device and (device.manufacturer or "").casefold() == "ikea"
            and (device.model or "").casefold() in ("e2112", "vindstyrka", "vindstyrka air quality and humidity sensor")):
        return {"id": "sensirion_index", "value": 150, "unit": unit or ""}
    return None


def outdoor_area(hass, area_id):
    area = ar.async_get(hass).async_get_area(area_id) if area_id else None
    return bool(area and area.name.strip().casefold() in OUTDOOR_AREAS)


def effective_area(hass, entry):
    device = dr.async_get(hass).async_get(entry.device_id) if entry.device_id else None
    return entry.area_id or (device.area_id if device else None)


def provenance(hass, entity_id):
    """Follow explicitly declared aliases; never guess a room from entity names."""
    seen, chain = set(), []
    current = entity_id
    while current and current not in seen and len(chain) < 16:
        seen.add(current)
        state = hass.states.get(current)
        registry = er.async_get(hass).async_get(current)
        chain.append({"entity_id": current, "name": state.name if state else current,
                      "area_id": effective_area(hass, registry) if registry else None})
        external = state.attributes.get("external_sensor") if state else None
        current = external if isinstance(external, str) else None
    return chain


def niak_weather(entry, key):
    """A Hestia Weather entity, recognised by its stable unique id, never by its name."""
    return entry.platform in weather_link.PLATFORMS and (entry.unique_id or "").endswith("_" + key)


def atmo_daily(hass, entry, state):
    # This adapter explicitly supports the Atmo France integration's daily index.
    # AQI classes alone are insufficient: pollutant subindices and tomorrow differ.
    attrs = state.attributes
    return (entry.platform == "atmofrance" and attrs.get("device_class") is None and attrs.get("Libellé") in
            ("Bon", "Moyen", "Dégradé", "Mauvais", "Très mauvais", "Extrêmement mauvais")
            and "pollen" not in state.entity_id and "_j_" not in state.entity_id
            and "J+" not in state.name and "Date de mise à jour" in attrs)


VENTILATION_WORDS = ("vmc", "ventil", "extract", "aérat", "aerat", "hotte")
BOOST_WORDS = ("turbo", "boost", "grande vitesse", "rapide", "vitesse 2", "speed 2")


def candidate(hass, entity_id, key, area_id=None, *, include_legacy=False, indoor_ids=()):
    entry = er.async_get(hass).async_get(entity_id)
    state = hass.states.get(entity_id)
    if not entry or entry.disabled_by or entry.entity_category is not None or not state:
        return None
    # Hidden by Home Assistant (the switch behind a « switch as fan »): never offered again, unless already chosen.
    if entry.hidden_by and not include_legacy:
        return None
    attrs = state.attributes
    domain = state.domain
    device_class = attrs.get("device_class") or entry.device_class or entry.original_device_class
    kind = SOURCES.get(key)
    adapter = "direct"
    if key == "windows":
        if domain != "binary_sensor" or device_class not in ("window", "door", "opening"):
            return None
    elif key == "presence":
        if domain != "binary_sensor" or device_class not in ("occupancy", "presence", "motion"):
            return None
    elif key == "covers":
        if domain != "cover":
            return None
    elif key in ("shutter_auto", "shutter_override"):
        if domain not in ("switch", "binary_sensor") or device_class in ("problem", "battery", "connectivity"):
            return None
    elif key == "purifier":
        # A fan named as a ventilation unit belongs to « Ventilation », not to the purifier.
        if domain != "fan" or any(word in f"{state.name} {entity_id}".casefold() for word in VENTILATION_WORDS):
            return None
    elif key in ("ventilation", "ventilation_boost"):
        # A ventilation unit (VMC): any fan but a purifier, or a relay or sensor whose name says ventilation.
        # A water heater, a pilot wire or a plug in the same room is never offered.
        label = f"{state.name} {entity_id}".casefold()
        if domain == "fan":
            if "purif" in label:
                return None
        elif domain in ("switch", "binary_sensor"):
            if device_class == "outlet" or not any(word in label for word in VENTILATION_WORDS):
                return None
        else:
            return None
    elif key == "illuminance":
        if domain != "sensor" or device_class != "illuminance" or attrs.get("unit_of_measurement") not in ("lx", "lux"):
            return None
    elif key == "pm25":
        if domain != "sensor" or device_class != "pm25" or attrs.get("unit_of_measurement") not in ("µg/m³", "μg/m³", "mg/m³"):
            return None
    elif key == "voc":
        device_class = voc_device_class(hass, entity_id)
        if domain != "sensor" or device_class is None:
            return None
        if attrs.get("unit_of_measurement") not in ("µg/m³", "μg/m³", "mg/m³", "ppb", "ppm", "index", "indice", "VOC index", None):
            return None
        if attrs.get("unit_of_measurement") is None and device_class != "volatile_organic_compounds_index":
            return None
    elif key == "heating":
        if domain != "climate" or not any(m in attrs.get("hvac_modes", []) for m in ("heat", "heat_cool")):
            if not include_legacy or domain != "climate":
                return None
    elif key == "heating_indicator":
        # A valve, a relay or a « work state » that says when the heating runs: offered by its name or its words,
        # an input_boolean always (a test, a template's helper).
        label = f"{state.name} {entity_id}".casefold()
        words = {str(w).casefold() for w in (state.state, *(attrs.get("options") or []))}
        if domain == "input_boolean":
            pass
        elif domain in ("binary_sensor", "switch"):
            if device_class not in ("heat", "running") and not any(w in label for w in INDICATOR_WORDS) and not include_legacy:
                return None
        elif domain == "sensor":
            # A state without unit that speaks the indicator's words (« heating », « open »), named as one or listing them.
            spoken = words & {*INDICATOR_RUNNING, *INDICATOR_RESTING}
            named = any(w in label for w in INDICATOR_WORDS)
            if (attrs.get("unit_of_measurement") or not spoken or not (named or words & {"heating", "open", "opened"})) and not include_legacy:
                return None
        else:
            return None
    elif key == "rain":
        if domain == "sensor" and device_class == "precipitation_intensity" and attrs.get("unit_of_measurement") in ("mm/h", "in/h"):
            adapter = "rain_rate"
        elif domain == "binary_sensor" and niak_weather(entry, "pluie_en_cours"):
            adapter = "binary"  # Hestia Weather's own « it is raining now »
        elif include_legacy and domain == "binary_sensor" and device_class not in ("problem", "battery", "connectivity"):
            adapter = "binary"
        else:
            return None
    elif key == "season":
        if domain != "sensor" or (entry.platform != "season" and str(state.state).casefold().strip() not in SEASONS):
            return None
        adapter = "season"
    elif key == "pollution":
        if atmo_daily(hass, entry, state):
            adapter = "atmo_daily"
        elif domain == "sensor" and niak_weather(entry, "qualite_air"):
            adapter = "niak_index"  # Hestia Weather's Atmo index of the day, 1 to 6
        elif include_legacy and domain == "binary_sensor" and device_class not in ("problem", "battery", "connectivity"):
            adapter = "binary"
        else:
            return None
    elif domain != "sensor" or device_class != CLASSES.get(kind):
        return None
    if kind in CLASSES:
        if attrs.get("unit_of_measurement") not in UNITS[kind]:
            return None
    own_area = effective_area(hass, entry)
    chain = provenance(hass, entity_id)
    warnings = []
    if len(chain) > 1:
        warnings.append("alias")
    if area_id and any(p["area_id"] and p["area_id"] != area_id for p in chain):
        warnings.append("other_area")
    if key == "windows" and device_class != "window":
        warnings.append("contact_role")
    # A temperature derived by Versatile Thermostat is second-hand; its climate entity, as the heating, is the extension.
    if entry.platform in ("template", "plant") or (entry.platform == thermostats.PLATFORM and key != "heating"):
        warnings.append("derived")
    if key == "heating" and not attrs.get("hvac_action"):
        warnings.append("no_hvac_action")
    # Hestia Weather describes the outside by design; outdoor areas are the user's own statement.
    outside = outdoor_area(hass, own_area) or entry.platform in weather_link.PLATFORMS
    if key in ("outdoor_temperature", "outdoor_humidity"):
        # A mixed station sits outside but also measures indoors: its use in a room decides.
        if entity_id in indoor_ids:
            warnings.append("used_indoor")
        elif not outside:
            warnings.append("outdoor_role")
    if adapter == "binary":
        warnings.append("binary_meaning")
    if adapter in ("atmo_daily", "niak_index"):
        warnings.append("daily_forecast")
    area = ar.async_get(hass).async_get_area(area_id) if area_id else None
    reference = area and ((key == "indoor_temperature" and area.temperature_entity_id == entity_id)
                           or (key == "indoor_humidity" and area.humidity_entity_id == entity_id))
    if reference and len(chain) == 1 and "other_area" not in warnings:
        warnings = [warning for warning in warnings if warning != "derived"]
    local = bool(area_id and own_area == area_id)
    available = state.state not in ("unknown", "unavailable", "none", "")
    return {"entity_id": entity_id, "name": state.name, "value": state.state,
            "unit": attrs.get("unit_of_measurement"), "area_id": own_area,
            "local": local, "outside": outside, "reference": bool(reference), "available": available,
            "adapter": adapter, "warnings": list(dict.fromkeys(warnings)), "provenance": chain,
            "device_class": device_class, "atmo_label": attrs.get("Libellé") if adapter == "atmo_daily" else None,
            **({"voc_reference": voc_reference(hass, entry, device_class, attrs.get("unit_of_measurement"))} if key == "voc" else {}),
            **({"thermostat": thermostats.read(state.state, dict(attrs))} if key == "heating" and entry.platform == thermostats.PLATFORM else {})}


def catalog(hass, area_id=None, selected=None, indoor_ids=(), *, keys=None, entries=None):
    selected = selected or {}
    result = {}
    entries = tuple(er.async_get(hass).entities.values()) if entries is None else entries
    for key in keys if keys is not None else (*INDOOR, *OUTDOOR, *OPENING_SOURCES):
        ids = selected.get(key, [])
        ids = ids if isinstance(ids, list) else [ids] if ids else []
        items = []
        for entry in entries:
            c = candidate(hass, entry.entity_id, key, area_id, include_legacy=entry.entity_id in ids, indoor_ids=indoor_ids)
            if c:
                items.append(c)
        # Outside: sensors of outdoor areas first. Inside: the room's own reference first.
        first = (lambda c: not c["outside"]) if key in OUTDOOR else (lambda c: not c["reference"])
        # A two-speed ventilation: the high-speed position goes to « grande vitesse », the other one first for the normal speed.
        speed = (lambda c: not any(w in c["name"].casefold() for w in BOOST_WORDS)) if key == "ventilation_boost" else \
            (lambda c: any(w in c["name"].casefold() for w in BOOST_WORDS)) if key == "ventilation" else (lambda c: False)
        # Each speed of a two-speed unit is offered in its own setting only, when the room has both.
        fast = lambda c: any(w in c["name"].casefold() for w in BOOST_WORDS)
        if key in ("ventilation", "ventilation_boost") and any(c["local"] and fast(c) for c in items) and any(c["local"] and not fast(c) for c in items):
            items = [c for c in items if fast(c) == (key == "ventilation_boost") or not c["local"]]
        result[key] = sorted(items, key=lambda c: (first(c), not c["local"], speed(c), bool(c["warnings"]), c["name"].casefold()))
    return result


def suggestions(candidates, area_id):
    result = {}
    for key in INDOOR:
        # An indicator is the person's choice next to a thermostat: proposed in its list, never chosen for them.
        if key == "heating_indicator":
            continue
        items = candidates[key]
        local = [c for c in items if c["local"] and c["available"] and not c["warnings"]]
        references = [c for c in local if c["reference"]]
        if key in ("windows", "presence"):
            if local:
                result[key] = [c["entity_id"] for c in local]
        elif references:
            result[key] = references[0]["entity_id"]
        elif len(local) == 1:
            result[key] = local[0]["entity_id"]
    return result


def overview(hass, exclude=()):
    """Proposals for every indoor area at once, in a single pass over the entities."""
    areas = {a.id: a for a in ar.async_get(hass).areas.values()
             if a.id not in exclude and a.name.strip().casefold() not in OUTDOOR_AREAS}
    grouped = {area_id: {key: [] for key in INDOOR} for area_id in areas}
    for entry in er.async_get(hass).entities.values():
        own = effective_area(hass, entry)
        if own not in grouped:
            continue
        for key in INDOOR:
            c = candidate(hass, entry.entity_id, key, own)
            if c:
                grouped[own][key].append(c)
    result = []
    for area_id, found in grouped.items():
        proposed = suggestions(found, area_id)
        result.append({"area_id": area_id, "name": areas[area_id].name, "suggestions": proposed,
                       "temperatures": len(found["indoor_temperature"])})
    return sorted(result, key=lambda r: (not bool(r["suggestions"].get("indoor_temperature")), r["name"].casefold()))
