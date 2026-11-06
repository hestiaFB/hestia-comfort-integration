"""Admin configuration API: drafts, provenance review and optimistic concurrency."""
import asyncio
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import math

from homeassistant.helpers.storage import Store
from homeassistant.helpers import area_registry as ar
from . import cover_link, weather_link
from .domain_migration import async_entry_ids
from .floors import floor_catalog, room_floor
from .const import DOMAIN, OUTDOOR_AREAS, SOURCES
from .engine.i18n import t
from .discovery import OUTDOOR, candidate, catalog, overview, suggestions, voc_device_class
from .engine.assessment import EXPOSURES, KINDS, Settings
from .air_references import AIR_DEFAULTS, AIR_REFERENCE_VERSION
from .foyer import clean_foyer
from .advisor.physics.heaters import KINDS as HEATER_BEHAVIOURS

DATA_CONFIG = DOMAIN + "_configuration"


# The third-party integrations a person can turn off in the general settings.
# The equipment a room may declare (« Équipements »): each one changes how its air is read.
EQUIPMENT = ("shower", "hob", "oven", "hood", "drying", "fan")
# What an equipment added by hand changes (« Ajouter un autre équipement », REGLAGES-3.md § 4.4).
EFFECTS = ("heat", "cool", "humid", "dry", "voc", "particles", "purify")
# How a room is described (« Pour aller plus loin » of « La pièce »): each answer is optional.
ROOM_CHOICES = {"uses": ("bedroom", "living", "kitchen", "bathroom", "office", "other"), "wall_material": ("heavy", "wood"),
                "insulation": ("inside", "outside", "none"), "partitions": ("light", "heavy")}
ROOM_NUMBERS = {"surface": (2, 200), "height": (1.8, 8)}
SIDES = ("N", "E", "S", "O")
# The kinds of heating (advisor/physics/heaters.py): convector, radiant panel, radiator with a core, floor, wood stove,
# pellet stove, heat pump.
HEATER_KINDS = HEATER_BEHAVIOURS
FLOWS = {"purifier": (20, 1000), "ventilation_boost": (10, 600)}
SWITCHABLE = ("versatile_thermostat", "adaptive_cover_pro", "cover_automatic", "cover_extender", "wled", "alarmo")
# A coloured light that shows the advice (« Lumières »): for the whole home or room by room, one look per state of the banner.
LIGHT_STATES = ("calm", "benefit", "action", "airing", "urgent")
LIGHT_EFFECTS = ("keep", "off", "solid", "flash")


def clean_light(rule):
    """One light's settings, kept only when they make sense; None without a light."""
    if not isinstance(rule, dict) or not isinstance(rule.get("entity_id"), str) or not rule["entity_id"].startswith("light."):
        return None
    looks = {}
    for key in LIGHT_STATES:
        look = (rule.get("states") or {}).get(key)
        if not isinstance(look, dict):
            continue
        colour = look.get("colour")
        colour = colour if isinstance(colour, str) and len(colour) == 7 and colour.startswith("#") else None
        effect = look.get("effect") if isinstance(look.get("effect"), str) and look.get("effect") else "solid"
        brightness = look.get("brightness")
        brightness = max(1, min(100, int(brightness))) if isinstance(brightness, (int, float)) and not isinstance(brightness, bool) else 60
        speed = look.get("speed") if look.get("speed") in ("slow", "normal", "fast") else "normal"
        looks[key] = {"colour": colour, "effect": effect, "brightness": brightness, "speed": speed}
    follow = rule.get("follow") if isinstance(rule.get("follow"), str) else "home"
    return {"entity_id": rule["entity_id"], "follow": follow, "wake": rule.get("wake") is True,
            "night": rule.get("night") is not False, "presence": rule.get("presence") is not False, "states": looks}


def clean_lights(value):
    """The « Lumières » settings: who drives the light (the whole home or each room) and each light's looks."""
    if not isinstance(value, dict):
        raise ValueError(t("Réglage des lumières invalide."))
    rooms = value.get("rooms") if isinstance(value.get("rooms"), dict) else {}
    return {"mode": "rooms" if value.get("mode") == "rooms" else "home", "home": clean_light(value.get("home")),
            "rooms": {k: r for k, r in ((k, clean_light(v)) for k, v in rooms.items() if isinstance(k, str)) if r}}

class Configuration:
    def __init__(self, hass):
        self.hass = hass
        self.store = Store(hass, 1, DOMAIN + ".home")
        self.home = {"sources": {}, "revision": 0}
        self.lock = asyncio.Lock()

    async def load(self):
        saved = await self.store.async_load()
        # Over the defaults: a file written by an older version may lack a key read later (« revision », « sources »).
        # A file that cannot be read stops the setup, so that nothing is ever saved over the person's settings.
        if saved:
            self.home = {**self.home, **saved}
        # The Hestia Weather place this home is linked to took a new id when Hestia Weather moved to its Hestia name.
        moved = (await async_entry_ids(self.hass)).get(self.home.get("weather") or "")
        if moved:
            self.home["weather"] = moved
            await self.store.async_save(self.home)

    def entries(self):
        return [e for e in self.hass.config_entries.async_entries(DOMAIN) if not e.data.get("home")]

    def revision(self):
        values = [(e.entry_id, dict(e.data), dict(e.options)) for e in self.entries()]
        # The answers to the learning questions, the alarm, the pollen allergy and the lights, set on their own, never block a room being edited.
        home = {k: v for k, v in self.home.items() if k not in ("answers", "alarm", "pollen_allergy", "lights", "foyer")}
        return hashlib.sha256(json.dumps([home, values], sort_keys=True, default=str).encode()).hexdigest()

    def home_sources(self):
        if self.home.get("configured"):
            return deepcopy(self.home["sources"])
        # Migration is a proposal only. No existing room silently joins the shared profile.
        result = {}
        entries = self.entries()
        for key in OUTDOOR:
            selected = [{**e.data, **e.options}.get("sources", {}).get(key) for e in entries]
            if selected and all(v and v == selected[0] for v in selected):
                entity_id = selected[0]
                c = candidate(self.hass, entity_id, key, include_legacy=True)
                if c:
                    result[key] = {"entity_id": entity_id, "adapter": c["adapter"]}
        return result

    def snapshot(self):
        entries = []
        for e in self.entries():
            config = deepcopy({**e.data, **e.options})
            entries.append({"entry_id": e.entry_id, "title": e.title, "loaded": e.state.value == "loaded", "config": config, "floor": room_floor(self.hass, config)})
        areas = [{"area_id": a.id, "name": a.name, "floor_id": a.floor_id, "outdoor": a.name.strip().casefold() in OUTDOOR_AREAS}
                 for a in ar.async_get(self.hass).areas.values()]
        return {"version": 1, "revision": self.revision(), "home": {"sources": self.home_sources(), "configured": bool(self.home.get("configured")), "acknowledged": self.home.get("acknowledged", []), "weather": self.home.get("weather"), "alarm": self.home.get("alarm"), "pollen_allergy": bool(self.home.get("pollen_allergy")), "analysis": bool(self.home.get("analysis")), "disabled": list(self.home.get("disabled") or []), "lights": self.home.get("lights") or {"mode": "home", "home": None, "rooms": {}}, "foyer": self.home.get("foyer") or {}}, "hestia_weather": weather_link.status(self.hass), "integrations": {"atmofrance": bool(self.hass.config_entries.async_entries("atmofrance"))}, "rooms": entries, "floors": floor_catalog(self.hass), "areas": sorted(areas, key=lambda a: (a["name"].casefold() != "salon", a["name"].casefold()))}

    def discover(self, area_id=None, entry_id=None):
        if area_id and not ar.async_get(self.hass).async_get_area(area_id):
            raise ValueError(t("Pièce Home Assistant introuvable."))
        selected = {}
        if entry_id:
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if not entry or entry.domain != DOMAIN or entry.data.get("home"):
                raise ValueError(t("Pièce Hestia Confort introuvable."))
            config = {**entry.data, **entry.options}
            selected = {**config.get("sources", {}), "windows": config.get("windows", []), "presence": config.get("presence", [])}
        for key, spec in self.home_sources().items():
            selected.setdefault(key, spec["entity_id"])
        indoor_ids = {{**e.data, **e.options}.get("sources", {}).get(k) for e in self.entries()
                      for k in ("indoor_temperature", "indoor_humidity")} - {None}
        candidates = catalog(self.hass, area_id, selected, indoor_ids)
        return {"version": 1, "revision": self.revision(), "candidates": candidates,
                "suggestions": suggestions(candidates, area_id) if area_id else {},
                # Covers driven with the sun (cover_link.py): their signals are read without being chosen.
                "drivers": {cover: self._driver(roles) for cover, roles in cover_link.find_all(self.hass).items()}}

    def _driver(self, roles):
        """What the panel shows of a cover's driver: each signal Hestia-FB reads, with its current state."""
        def signal(role):
            state = self.hass.states.get(roles[role]) if roles.get(role) else None
            available = state and state.state not in ("unknown", "unavailable")
            return {"entity_id": roles[role], "name": state.name, "on": state.state == "on"} if available else None
        known = cover_link.facts(self.hass, roles)
        return {"name": roles["name"], "driver": roles.get("driver", "adaptive_cover_pro"), "auto": roles.get("auto"), "override": roles.get("override"),
                "signals": {role: signal(role) for role in ("enabled", "auto", "tracking", "detection", "override", "sun", "climate")},
                "azimuth": known["azimuth"], "exposure": cover_link.exposure(known["azimuth"]),
                "width": known["width"], "height": known["height"]}

    def weather_proposal(self, entry_id=None):
        """Hestia Weather's station as exterior sources, ready for the exterior page."""
        found = weather_link.exterior(self.hass, entry_id)
        if not found:
            raise ValueError(t("Hestia Weather n’a pas de lieu disponible."))
        sources = {}
        for key, entity_id in found["proposals"].items():
            if c := candidate(self.hass, entity_id, key):
                sources[key] = {"entity_id": entity_id, "adapter": c["adapter"], **({"block_from": 4} if c["adapter"] == "hestia_index" else {})}
        # Hestia Weather 2.5.7 gives its air through api.air() (Atmo France or a WAQI station), without an entity of its own.
        air = weather_link.air(self.hass, found["entry_id"])
        if "pollution" not in sources and air:
            sources["pollution"] = {"entity_id": air["entity_id"], "adapter": "hestia_air", "block_from": 4}
        shown = {"provider": air["provider"], "index": air.get("index"), "label": air.get("label")} if air else None
        # Its season too (2.6.2): from its own Season sensor or the date, read through its interface.
        season = weather_link.season(self.hass, found["entry_id"])
        return {"entry_id": found["entry_id"], "title": found["title"], "sources": sources, "air": shown, "season": season}

    def overview(self):
        used = {{**e.data, **e.options}.get("area_id") for e in self.entries()}
        return {"version": 1, "revision": self.revision(), "areas": overview(self.hass, used)}

    def validate(self, payload, *, home=False):
        if not isinstance(payload, dict):
            raise ValueError(t("Configuration invalide."))
        warnings = []
        if home:
            sources = payload.get("sources", {})
            if not isinstance(sources, dict) or set(sources) - set(OUTDOOR):
                raise ValueError(t("Sources extérieures invalides."))
            cleaned = {"sources": {}}
            for key, spec in sources.items():
                if not isinstance(spec, dict) or not isinstance(spec.get("entity_id"), str):
                    raise ValueError(t("Choisissez une source extérieure existante."))
                threshold = spec.get("block_from", 4)
                if spec.get("adapter") == "hestia_air":
                    # The air of the linked Hestia Weather place, whatever its source; read again on every update.
                    air = weather_link.air(self.hass, payload.get("weather"))
                    if key != "pollution" or not air or air["entity_id"] != spec["entity_id"]:
                        raise ValueError(t("La qualité de l’air de Hestia Weather n’est plus disponible : rechargez la page."))
                    if isinstance(threshold, bool) or not isinstance(threshold, int) or not 2 <= threshold <= 6:
                        raise ValueError(t("Choisissez un niveau ATMO entre Moyen et Extrêmement mauvais."))
                    cleaned["sources"][key] = {"entity_id": spec["entity_id"], "adapter": "hestia_air", "block_from": threshold}
                    continue
                c = candidate(self.hass, spec["entity_id"], key, include_legacy=True)
                if not c or spec.get("adapter") != c["adapter"]:
                    raise ValueError(t("Source extérieure incompatible : {name}", name=key))
                daily = c["adapter"] in ("atmo_daily", "hestia_index")
                if daily and (isinstance(threshold, bool) or not isinstance(threshold, int) or not 2 <= threshold <= 6):
                    raise ValueError(t("Choisissez un niveau ATMO entre Moyen et Extrêmement mauvais."))
                cleaned["sources"][key] = {"entity_id": c["entity_id"], "adapter": c["adapter"]}
                if daily:
                    cleaned["sources"][key]["block_from"] = threshold
                if c["warnings"]:
                    warnings.append({"key": key, "entity_id": c["entity_id"], "warnings": c["warnings"]})
            weather = payload.get("weather")
            if weather is not None and weather not in {p["entry_id"] for p in weather_link.status(self.hass)["places"]}:
                raise ValueError(t("Ce lieu Hestia Weather n’est plus disponible."))
            cleaned["weather"] = weather
            return cleaned, warnings
        area_id = payload.get("area_id") or None
        area = ar.async_get(self.hass).async_get_area(area_id) if isinstance(area_id, str) else None
        if area_id is not None and not area:
            raise ValueError(t("Cette pièce Home Assistant n’existe plus. Choisissez-en une autre ou une pièce libre."))
        floor_id = payload.get("floor_id") or None
        if area_id:
            floor_id = None  # Home Assistant owns the floor of a linked area.
        elif floor_id is not None and (not isinstance(floor_id, str) or floor_id not in {f["floor_id"] for f in floor_catalog(self.hass)}):
            raise ValueError(t("Cet étage n’existe plus. Choisissez un étage existant ou aucun étage."))
        sources = payload.get("sources", {})
        if not isinstance(sources, dict) or set(sources) - set(SOURCES):
            raise ValueError(t("Sources de pièce invalides."))
        if not sources.get("indoor_temperature"):
            raise ValueError(t("Choisissez la température intérieure de cette pièce."))
        windows = payload.get("windows", [])
        if not isinstance(windows, list) or any(not isinstance(e, str) for e in windows):
            raise ValueError(t("Contacts de fenêtres invalides."))
        presence = payload.get("presence", [])
        if not isinstance(presence, list) or any(not isinstance(e, str) for e in presence):
            raise ValueError(t("Capteurs de présence invalides."))
        evolution = payload.get("evolution", {})
        if not isinstance(evolution, dict) or set(evolution) - {"voc_threshold", "glazing_factor", "presence_delay_minutes",
                                                                   "voc_delay_minutes", "voc_pause_minutes"}:
            raise ValueError(t("Préférences avancées invalides."))
        cleaned_evolution = {}
        for key, default, low, high in (("glazing_factor", 0.7, 0, 1), ("presence_delay_minutes", 5, 0, 120),
                                         ("voc_delay_minutes", 10, 0, 120), ("voc_pause_minutes", 45, 0, 240)):
            value = evolution.get(key, default)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError(t("Valeur avancée invalide : {name}", name=key))
            cleaned_evolution[key] = value
        threshold = evolution.get("voc_threshold")
        if threshold is not None:
            value = threshold.get("value") if isinstance(threshold, dict) else None
            unit = threshold.get("unit") if isinstance(threshold, dict) else None
            state = self.hass.states.get(sources.get("voc", ""))
            source_unit = state.attributes.get("unit_of_measurement") if state else None
            explicit_index = voc_device_class(self.hass, sources.get("voc", "")) == "volatile_organic_compounds_index"
            expected_unit = "" if source_unit is None and explicit_index else source_unit
            if (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0
                or not isinstance(unit, str) or not state or unit != expected_unit):
                raise ValueError(t("Le seuil COV doit correspondre à l’unité exacte du capteur choisi."))
            cleaned_evolution["voc_threshold"] = {"value": value, "unit": unit}
        name = payload.get("name", area.name if area else "")
        if not isinstance(name, str) or not name.strip() or len(name) > 100:
            raise ValueError(t("Donnez un nom à la pièce (1 à 100 caractères)."))
        settings = payload.get("settings", {})
        if not isinstance(settings, dict):
            raise ValueError(t("Préférences de confort invalides."))
        settings = {**AIR_DEFAULTS, **settings}
        action = settings.get("co2_action")
        if isinstance(action, (int, float)) and not isinstance(action, bool) and math.isfinite(action) and action > 300:
            settings["co2_potential"] = min(settings.get("co2_potential", 800), action - 200)
            settings["co2_urgent"] = max(settings.get("co2_urgent", 1500), action + 300)
        settings = asdict(Settings(**settings))
        heated = payload.get("heated", True)
        if not isinstance(heated, bool):
            raise ValueError(t("« Pièce chauffée » doit être oui ou non."))
        # A Versatile Thermostat's comfort temperature stands as the room's minimum unless the person says otherwise.
        thermostat_reference = payload.get("thermostat_reference", True)
        if not isinstance(thermostat_reference, bool):
            raise ValueError(t("« Minimum repris du thermostat » doit être oui ou non."))
        # What the room holds that changes its air (« Équipements »): a shower or a bath, in the room or opening onto it.
        equipment = payload.get("equipment", [])
        if not isinstance(equipment, list) or any(e not in EQUIPMENT for e in equipment):
            raise ValueError(t("Choisissez les équipements parmi ceux proposés."))
        # Each equipment may say when it runs: a switch, a plug or a power sensor (« Pour savoir quand il marche »).
        links = payload.get("equipment_links", {})
        if not isinstance(links, dict) or set(links) - set(equipment) or any(
                not isinstance(v, str) or not self.hass.states.get(v) for v in links.values()):
            raise ValueError(t("Choisissez l’entité d’un équipement parmi celles de Home Assistant."))
        custom = payload.get("custom_equipment", [])
        if not isinstance(custom, list) or len(custom) > 10:
            raise ValueError(t("Équipements ajoutés invalides."))
        cleaned_custom = []
        for item in custom:
            name_ = item.get("name") if isinstance(item, dict) else None
            effects = item.get("effects", []) if isinstance(item, dict) else None
            entity = item.get("entity_id") if isinstance(item, dict) else None
            if (not isinstance(name_, str) or not name_.strip() or len(name_) > 40 or not isinstance(effects, list)
                    or any(e not in EFFECTS for e in effects) or (entity is not None and (not isinstance(entity, str) or not self.hass.states.get(entity)))):
                raise ValueError(t("Équipements ajoutés invalides."))
            cleaned_custom.append({"name": name_.strip(), "effects": list(dict.fromkeys(effects)), "entity_id": entity})
        # How the room is built (« Pour aller plus loin »): every answer optional.
        built = payload.get("room", {})
        if not isinstance(built, dict) or set(built) - {*ROOM_CHOICES, *ROOM_NUMBERS, "outside"}:
            raise ValueError(t("Description de la pièce invalide."))
        cleaned_room = {}
        for key, choices in ROOM_CHOICES.items():
            if built.get(key) is not None:
                if built[key] not in choices:
                    raise ValueError(t("Description de la pièce invalide."))
                cleaned_room[key] = built[key]
        for key, (low, high) in ROOM_NUMBERS.items():
            if built.get(key) is not None:
                value = built[key]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
                    raise ValueError(t("Valeur hors des bornes : {name}", name=key))
                cleaned_room[key] = value
        if built.get("outside") is not None:
            if not isinstance(built["outside"], list) or any(s not in SIDES for s in built["outside"]):
                raise ValueError(t("Description de la pièce invalide."))
            cleaned_room["outside"] = [s for s in SIDES if s in built["outside"]]
        # The flow of the VMC's fast speed and of the purifier (m³/h), when the person knows it.
        flows = payload.get("flows", {})
        if not isinstance(flows, dict) or set(flows) - set(FLOWS):
            raise ValueError(t("Débits invalides."))
        cleaned_flows = {}
        for key, (low, high) in FLOWS.items():
            if flows.get(key) is not None:
                value = flows[key]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
                    raise ValueError(t("Valeur hors des bornes : {name}", name=key))
                cleaned_flows[key] = value
        # What differs from the household's settings in this room only.
        room_foyer = clean_foyer(payload.get("foyer"), room=True)
        # The people the room is for (`person` entities): a bedroom's one, a living room's several, or none for everyone.
        persons = payload.get("persons", [])
        if not isinstance(persons, list) or any(not isinstance(p, str) or not p.startswith("person.") for p in persons):
            raise ValueError(t("Choisissez les personnes parmi celles de Home Assistant."))
        # No contact on the windows, on purpose (a garage, a room that is never aired): not suggested again.
        windows_unmeasured = payload.get("windows_unmeasured", False)
        if not isinstance(windows_unmeasured, bool):
            raise ValueError(t("« Pas de contact, c’est voulu » doit être oui ou non."))
        # Rooms with no wall between them (a salon open onto its kitchen) share one air.
        open_to = payload.get("open_to", [])
        known = {e.entry_id for e in self.entries()}
        if not isinstance(open_to, list) or any(not isinstance(e, str) for e in open_to):
            raise ValueError(t("Pièces ouvertes l’une sur l’autre invalides."))
        # A room removed since is simply forgotten.
        open_to = [e for e in open_to if e in known]
        legacy_sheltered = payload.get("rain_exposed") is False
        openings = payload.get("openings", {})
        if not isinstance(openings, dict):
            raise ValueError(t("Description des ouvrants invalide."))
        cleaned_openings = {}
        for entity_id in windows:
            meta = openings.get(entity_id, {})
            if not isinstance(meta, dict):
                raise ValueError(t("Description des ouvrants invalide."))
            exposure = meta.get("exposure")
            kind = meta.get("kind", "window")
            sheltered = meta.get("sheltered", legacy_sheltered)
            if exposure is not None and exposure not in EXPOSURES:
                raise ValueError(t("Exposition inconnue pour {name}", name=entity_id))
            if kind not in KINDS or not isinstance(sheltered, bool):
                raise ValueError(t("Type d’ouvrant invalide pour {name}", name=entity_id))
            shutter = meta.get("shutter", "none")
            if shutter not in ("none", "manual", "connected"):
                raise ValueError(t("Type de volet invalide pour {name}", name=entity_id))
            item = {"exposure": exposure, "kind": kind, "sheltered": sheltered}
            # A precise angle, when the person knows it: 0 north, 90 east, 180 south, 270 west.
            azimuth = meta.get("azimuth")
            if azimuth is not None:
                if isinstance(azimuth, bool) or not isinstance(azimuth, (int, float)) or not math.isfinite(azimuth) or not 0 <= azimuth < 360:
                    raise ValueError(t("Angle invalide pour {name} : entre 0 et 359 degrés.", name=entity_id))
                item["azimuth"] = azimuth
            if "shutter" in meta:
                item["shutter"] = shutter
            # A manual shutter's habit, and the glazing (« Pour aller plus loin »).
            habit = meta.get("shutter_habit")
            if habit is not None:
                if habit not in ("open", "closed", "varies") or shutter != "manual":
                    raise ValueError(t("Habitude du volet invalide pour {name}", name=entity_id))
                item["shutter_habit"] = habit
            glazing = meta.get("glazing")
            if glazing is not None:
                if glazing not in ("simple", "double", "triple"):
                    raise ValueError(t("Vitrage invalide pour {name}", name=entity_id))
                item["glazing"] = glazing
            for field, role in (("cover_entity", "covers"), ("auto_entity", "shutter_auto"), ("override_entity", "shutter_override")):
                value = meta.get(field)
                if value:
                    found = candidate(self.hass, value, role, area_id) if isinstance(value, str) else None
                    if shutter != "connected" or not found:
                        raise ValueError(t("Source du volet incompatible : {name}", name=field))
                    if found["warnings"]:
                        warnings.append({"key": role, "entity_id": value, "warnings": found["warnings"]})
                    item[field] = value
            for field in ("width", "height", "overhang_depth", "overhang_gap"):
                value = meta.get(field)
                if value is not None:
                    minimum = 0 if field.startswith("overhang") else 0.01
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= 20:
                        raise ValueError(t("Dimension invalide : {name}", name=field))
                    item[field] = value
            cleaned_openings[entity_id] = item
        # The room's heatings (several: the stove and the radiators of a living room), each for this room or the whole
        # house, and the one its range follows. The 2.1 engine reads one heating: the one the range follows.
        heaters = payload.get("heaters", [])
        if not isinstance(heaters, list) or len(heaters) > 6:
            raise ValueError(t("Chauffages invalides."))
        cleaned_heaters = []
        for item in heaters:
            entity = item.get("entity_id") if isinstance(item, dict) else None
            scope = item.get("scope", "room") if isinstance(item, dict) else None
            kind, power = (item.get("kind"), item.get("power")) if isinstance(item, dict) else (None, None)
            if (not isinstance(entity, str) or scope not in ("room", "house") or (kind is not None and kind not in HEATER_KINDS)
                    or (power is not None and (isinstance(power, bool) or not isinstance(power, (int, float)) or not 100 <= power <= 20000))):
                raise ValueError(t("Chauffages invalides."))
            if not candidate(self.hass, entity, "heating", area_id, include_legacy=True):
                raise ValueError(t("Capteur incompatible ou retiré : {name}", name=entity))
            cleaned_heaters.append({"entity_id": entity, "scope": scope, **({"kind": kind} if kind else {}), **({"power": power} if power else {})})
        ids = [h["entity_id"] for h in cleaned_heaters]
        if len(set(ids)) != len(ids):
            raise ValueError(t("Chauffages invalides."))
        plage = payload.get("thermostat_plage")
        if plage is not None and plage not in ids:
            raise ValueError(t("La plage suit un chauffage de la pièce, ou aucun."))
        if cleaned_heaters:
            sources = {**sources}
            main = plage or ids[0]
            sources["heating"] = main
            if plage is None and payload.get("thermostat_reference") is not False:
                plage = main
        # Rooms use the shared exterior. Older rooms keep their own sources only until it is configured.
        legacy = not self.uses_home(payload)
        cleaned_sources = {}
        for key, value in {**sources, "windows": windows, "presence": presence}.items():
            if key in OUTDOOR and not legacy:
                continue
            ids = value if key in ("windows", "presence") else [value]
            for entity_id in ids:
                if not isinstance(entity_id, str):
                    raise ValueError(t("Choisissez une entité existante pour chaque source."))
                c = candidate(self.hass, entity_id, key, area_id, include_legacy=True)
                if not c:
                    raise ValueError(t("Capteur incompatible ou retiré : {name}", name=entity_id))
                # Exterior sources kept by an older room are not shown in the page: never ask to confirm them.
                if c["warnings"] and key not in OUTDOOR:
                    warnings.append({"key": key, "entity_id": entity_id, "warnings": c["warnings"]})
            if key not in ("windows", "presence"):
                cleaned_sources[key] = value
        cleaned = {"name": name.strip(), "area_id": area_id, "floor_id": floor_id, "sources": cleaned_sources,
                   "windows": list(dict.fromkeys(windows)), "openings": cleaned_openings, "settings": settings,
                   "presence": list(dict.fromkeys(presence)), "evolution": cleaned_evolution, "use_home": not legacy,
                   "air_reference_version": AIR_REFERENCE_VERSION, "heated": heated, "thermostat_reference": thermostat_reference,
                   "windows_unmeasured": windows_unmeasured and not windows,
                   "persons": list(dict.fromkeys(persons)), "open_to": list(dict.fromkeys(open_to)), "equipment": list(dict.fromkeys(equipment)),
                   "equipment_links": links, "custom_equipment": cleaned_custom, "room": cleaned_room, "flows": cleaned_flows,
                   "foyer": room_foyer, "heaters": cleaned_heaters, "thermostat_plage": plage}
        return cleaned, warnings

    @staticmethod
    def ensure_acknowledged(warnings, acknowledged):
        if not isinstance(acknowledged, list) or any(not isinstance(item, str) for item in acknowledged):
            raise ValueError(t("Confirmez les sources dont le rôle est à vérifier."))
        needed = {w["key"] + ":" + w["entity_id"] for w in warnings}
        if needed - set(acknowledged):
            raise ValueError(t("Confirmez la provenance et le rôle des sources signalées avant d’enregistrer."))
        # Only confirmations that still apply are remembered, so a later change asks again.
        return sorted(needed)

    async def save(self, payload, revision, entry_id=None, *, home=False, acknowledged=None):
        async with self.lock:
            if revision != self.revision():
                raise ValueError(t("La configuration a changé ailleurs. Rechargez les pièces avant d’enregistrer."))
            cleaned, warnings = self.validate(payload, home=home)
            remembered = self.ensure_acknowledged(warnings, acknowledged or [])
            if home:
                updated = {**cleaned, "acknowledged": remembered, "configured": True, "revision": self.home["revision"] + 1,
                           "answers": self.home.get("answers", {}), "alarm": self.home.get("alarm"),
                           "pollen_allergy": bool(self.home.get("pollen_allergy")), "lights": self.home.get("lights"),
                           # Set on its own page (set_foyer): saving the exterior never drops it.
                           "foyer": self.home.get("foyer") or {},
                           # Our analysis tools (set_analysis), off for everyone but the lab.
                           "analysis": bool(self.home.get("analysis"))}
                await self.store.async_save(updated)
                self.home = updated
                for entry in self.entries():
                    if entry.state.value == "loaded":
                        await self.hass.config_entries.async_reload(entry.entry_id)
                return self.snapshot()
            cleaned["acknowledged"] = remembered
            unique_id = cleaned["area_id"]
            if unique_id and any(e.unique_id == unique_id and e.entry_id != entry_id for e in self.entries()):
                raise ValueError(t("Cette pièce Home Assistant est déjà utilisée par une autre pièce Hestia Confort."))
            if entry_id:
                entry = self.hass.config_entries.async_get_entry(entry_id)
                if not entry or entry.domain != DOMAIN or entry.data.get("home"):
                    raise ValueError(t("Cette pièce Hestia Confort n’existe plus."))
                cleaned["open_to"] = [e for e in cleaned["open_to"] if e != entry_id]
                before = set(self.volume(entry_id))
                # Preserve unknown future settings only at the top level; explicit sources
                # and windows replace their prior selections, including deliberate clears.
                options = {**entry.data, **entry.options, **cleaned}
                options.pop("rain_exposed", None)
                self.hass.config_entries.async_update_entry(entry, title=cleaned["name"], options=options,
                                                            unique_id=unique_id or entry.unique_id)
                # The rooms that join or leave this one's air are recomputed with it.
                await self._reload_rooms((before | set(self.volume(entry_id))) - {entry_id})
            else:
                result = await self.hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"}, data={"panel_config": cleaned, "acknowledged": acknowledged or []})
                if result["type"] != "create_entry":
                    raise ValueError(t("La pièce n’a pas pu être ajoutée."))
            return self.snapshot()

    async def remove(self, entry_id, revision):
        """Deletes one room; its Home Assistant area becomes a proposal again on the home page."""
        async with self.lock:
            if revision != self.revision():
                raise ValueError(t("La configuration a changé ailleurs. Rechargez les pièces avant de supprimer."))
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if not entry or entry.domain != DOMAIN or entry.data.get("home"):
                raise ValueError(t("Cette pièce Hestia Confort n’existe plus."))
            partners = set(self.volume(entry_id))
            await self.hass.config_entries.async_remove(entry_id)
            await self._reload_rooms(partners)
            return self.snapshot()

    async def set_alarm(self, value):
        """The home's alarm: None to find Alarmo by itself, "" for none, or an `alarm_control_panel` entity."""
        if value is not None and not (isinstance(value, str) and (value == "" or value.startswith("alarm_control_panel."))):
            raise ValueError(t("Choisissez une alarme de Home Assistant."))
        async with self.lock:
            self.home = {**self.home, "alarm": value}
            await self.store.async_save(self.home)
            for entry in self.entries():
                if entry.state.value == "loaded":
                    await self.hass.config_entries.async_reload(entry.entry_id)
            return self.snapshot()

    async def set_pollen_allergy(self, value):
        """Someone at home is allergic to pollens: on days of high pollens, airings are kept short and early. Off by default."""
        if not isinstance(value, bool):
            raise ValueError(t("Réglage d’allergie invalide."))
        async with self.lock:
            self.home = {**self.home, "pollen_allergy": value}
            await self.store.async_save(self.home)
            for entry in self.entries():
                if entry.state.value == "loaded":
                    await self.hass.config_entries.async_reload(entry.entry_id)
            return self.snapshot()

    async def set_analysis(self, value):
        """Our analysis tools (PLAN-OPTIMISATION.md, point 16): the advisor's snapshots, its journal, the gestures followed
        and the nightly reports, written for the Atelier. Off by default: the advice and the learning never read them, and
        a HA Green writes on an eMMC memory. On at the lab. No room is reloaded: read at each step."""
        if not isinstance(value, bool):
            raise ValueError(t("Réglage invalide."))
        async with self.lock:
            self.home = {**self.home, "analysis": value}
            await self.store.async_save(self.home)
        return self.snapshot()

    async def set_foyer(self, value):
        """The household's settings (« Réglages du foyer »), saved at once: only what the person set, the rest keeps its default."""
        foyer = clean_foyer(value)
        async with self.lock:
            self.home = {**self.home, "foyer": foyer}
            await self.store.async_save(self.home)
        # No room is reloaded: the advisor reads the household afresh at each step (room/advice.py `spec`, `Habits.of`) and
        # the ressenti at each refresh. A reload re-registered the panel and the page started again a few seconds after
        # each answer of « Vos habitudes » (Frank, 5 November).
        from .advisor_home import DATA as ADVISOR
        if (advisor := self.hass.data.get(ADVISOR)) is not None:
            self.hass.async_create_task(advisor.tick(None))
        for entry in self.entries():
            if entry.state.value == "loaded" and hasattr(coordinator := getattr(entry, "runtime_data", None), "async_request_refresh"):
                self.hass.async_create_task(coordinator.async_request_refresh())
        return self.snapshot()

    async def set_lights(self, value):
        """The « Lumières » settings, saved at once; they change no advice, so no room is reloaded."""
        lights = clean_lights(value)
        async with self.lock:
            self.home = {**self.home, "lights": lights}
            await self.store.async_save(self.home)
        if driver := self.hass.data.get("hestia_comfort_lights"):
            driver.refresh()
        return self.snapshot()

    def pollen(self):
        """Today's pollens of the linked Hestia Weather place, only when someone at home is allergic; None otherwise."""
        if not self.home.get("pollen_allergy") or not self.weather():
            return None
        return weather_link.pollen(self.hass, self.weather())

    async def set_extension(self, key, enabled):
        """Uses a third-party integration or not, for every room: Alarmo found by itself or no alarm; the others listed when off."""
        if key not in SWITCHABLE:
            raise ValueError(t("Extension inconnue."))
        async with self.lock:
            if key == "alarmo":
                self.home = {**self.home, "alarm": None if enabled else ""}
            else:
                off = [k for k in self.home.get("disabled") or [] if k != key] + ([] if enabled else [key])
                self.home = {**self.home, "disabled": off}
            await self.store.async_save(self.home)
            for entry in self.entries():
                if entry.state.value == "loaded":
                    await self.hass.config_entries.async_reload(entry.entry_id)
            if driver := self.hass.data.get("hestia_comfort_lights"):
                driver.refresh()
            return self.snapshot()

    def weather(self):
        """The Hestia Weather place that gives the outdoor to every room, or None: the one link both bricks show."""
        return self.home.get("weather") if self.home.get("configured") else None

    async def set_weather(self, entry_id):
        """Links the outdoor to a Hestia Weather place (its measures replace the others), or unlinks it (the sensors stay,
        Hestia Weather's air is dropped), as « Hestia Weather » or « Vos propres capteurs » then Enregistrer would."""
        if entry_id == self.weather():
            return self.snapshot()
        sources = (self.weather_proposal(entry_id)["sources"] if entry_id
                   else {k: v for k, v in self.home_sources().items() if v.get("adapter") != "hestia_air"})
        payload = {"sources": sources, "weather": entry_id}
        # Choosing the link is choosing its sensors: their roles need no second confirmation.
        _, warnings = self.validate(payload, home=True)
        return await self.save(payload, self.revision(), home=True, acknowledged=[w["key"] + ":" + w["entity_id"] for w in warnings])

    async def answer(self, entry_id, key, value):
        """Keeps the person's answer to a learning question (« yes », « no », « unknown »)."""
        if value not in ("yes", "no", "unknown") or not isinstance(key, str) or not key:
            raise ValueError(t("Réponse invalide."))
        if not any(e.entry_id == entry_id for e in self.entries()):
            raise ValueError(t("Cette pièce Hestia Confort n’existe plus."))
        async with self.lock:
            answers = {**(self.home.get("answers") or {})}
            answers[entry_id] = {**answers.get(entry_id, {}), key: value}
            self.home = {**self.home, "answers": answers}
            await self.store.async_save(self.home)

    def volume(self, entry_id):
        """The other rooms sharing this room's air: « open onto » is mutual and passes from room to room."""
        links = {e.entry_id: set({**e.data, **e.options}.get("open_to", [])) for e in self.entries()}
        group, frontier = {entry_id}, [entry_id]
        while frontier:
            current = frontier.pop()
            for other in links.get(current, set()) | {k for k, v in links.items() if current in v}:
                if other in links and other not in group:
                    group.add(other)
                    frontier.append(other)
        return sorted(group - {entry_id})

    async def _reload_rooms(self, entry_ids):
        for entry_id in sorted(entry_ids):
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if entry and entry.state.value == "loaded":
                await self.hass.config_entries.async_reload(entry_id)

    def uses_home(self, config):
        if self.home.get("configured") or config.get("use_home") is True:
            return True
        return not any(config.get("sources", {}).get(k) for k in OUTDOOR)

    def live_sources(self, config=None):
        """The exterior sources as read now: those saved, with the outdoor air following the source chosen in
        Hestia Weather when the home is linked to it, unless another kind of pollution sensor or no air at all was picked."""
        sources = self.effective_sources(config) if config is not None else (self.home_sources() if self.home.get("configured") else {})
        if config is not None and not self.uses_home(config):
            return sources
        spec = sources.get("pollution")
        if not spec or spec.get("adapter") not in ("atmo_daily", "hestia_index", "hestia_air"):
            return sources
        found = weather_link.air(self.hass, self.home.get("weather")) if self.home.get("configured") else None
        if found:
            sources["pollution"] = {"entity_id": found["entity_id"], "adapter": "hestia_air", "block_from": (spec or {}).get("block_from", 4),
                                    "index": found.get("index"), "provider": found.get("provider"), "at": found.get("at")}
        return sources

    def effective_sources(self, config):
        if self.uses_home(config):
            return self.home_sources()
        return {key: {"entity_id": value, "adapter": "direct" if key in ("outdoor_temperature", "outdoor_humidity") else "binary"} for key, value in config.get("sources", {}).items() if key in OUTDOOR}


async def get_configuration(hass):
    if DATA_CONFIG not in hass.data:
        service = Configuration(hass)
        hass.data[DATA_CONFIG] = service
        hass.data[DATA_CONFIG + "_load"] = hass.async_create_task(service.load())
    if task := hass.data.get(DATA_CONFIG + "_load"):
        await task
    return hass.data[DATA_CONFIG]
