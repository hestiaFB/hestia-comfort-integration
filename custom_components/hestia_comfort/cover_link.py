"""The integrations that drive a cover with the sun, each recognised by itself: one adapter per integration.

Every adapter answers the same questions for each cover it drives: is it on, does it drive the cover now, has
a hand taken over, is the sun in front of the window and from when to when, where it aims, and why. Hestia-FB
reads them and commands nothing. Entities are recognised by their platform and stable unique id, never by
their name. Each cover's roles carry `driver` (the integration's key, also its switch in the general settings),
`name`, and `watch` (every entity whose change refreshes the room).
"""
import re

from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

# The roles read straight from an entity, the same for every adapter (coordinator.py reads them).
SIGNALS = ("auto", "enabled", "override", "sun", "target", "sun_start", "sun_end", "override_end", "tracking", "detection", "climate")
GONE = ("unknown", "unavailable")


def _live(hass, entity_id):
    state = hass.states.get(entity_id) if entity_id else None
    return state if state is not None and state.state not in GONE else None


def _today_at(clock):
    """« 13:50 », said for today, as the local moment the engine reads."""
    match = re.fullmatch(r"(\d{1,2}):(\d{2})(?::\d{2})?", clock or "")
    if not match:
        return None
    return dt_util.now().replace(hour=int(match[1]), minute=int(match[2]), second=0, microsecond=0).isoformat()


def _number(value, low=0, high=100):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if low <= number <= high else None


class AdaptiveCoverPro:
    KEY = "adaptive_cover_pro"
    NAME = "Adaptive Cover Pro"
    # The original Adaptive Cover is read like the Pro one.
    PLATFORMS = ("adaptive_cover_pro", "adaptive_cover")
    # Role → (domain, key at the end of the unique id, translation key or entity id).
    ROLES = {"auto": ("switch", "automatic_control"), "enabled": ("switch", "integration_enabled"),
             "override": ("binary_sensor", "manual_override"), "sun": ("binary_sensor", "sun_infront"),
             "target": ("sensor", "target_position"), "sun_start": ("sensor", "start_sun"), "sun_end": ("sensor", "end_sun"),
             "override_end": ("sensor", "manual_override_end_time"), "tracking": ("switch", "sun_tracking"),
             "detection": ("switch", "manual_override_detection"), "climate": ("switch", "climate_mode")}

    @classmethod
    def _role(cls, entry):
        domain = entry.entity_id.split(".", 1)[0]
        for role, (want, key) in cls.ROLES.items():
            if domain == want and (entry.translation_key == key or (entry.unique_id or "").endswith(key) or entry.entity_id.endswith("_" + key)):
                return role
        return None

    @staticmethod
    def _covers(hass, config_entry_id, roles):
        """The covers one Adaptive Cover Pro entry drives: from its settings, else from what it reports."""
        found = set()
        config = hass.config_entries.async_get_entry(config_entry_id) if config_entry_id else None
        if config:
            for source in (config.options, config.data):
                group = source.get("group") or source.get("entities")
                if isinstance(group, str):
                    group = [group]
                if isinstance(group, list):
                    found.update(g for g in group if isinstance(g, str))
        target = hass.states.get(roles["target"]) if roles.get("target") else None
        for attr in ("actual_positions", "linear_actual_positions"):
            value = target.attributes.get(attr) if target else None
            if isinstance(value, dict):
                found.update(k for k in value if isinstance(k, str))
        return found

    @classmethod
    def find_all(cls, hass, registry):
        entries = {}
        for entry in registry.entities.values():
            if entry.platform in cls.PLATFORMS and not entry.disabled_by and (role := cls._role(entry)):
                entries.setdefault(entry.config_entry_id, {})[role] = entry.entity_id
        result = {}
        for config_entry_id, roles in entries.items():
            for cover in cls._covers(hass, config_entry_id, roles):
                result[cover] = {**roles, "driver": cls.KEY, "name": cls.NAME, "entry": config_entry_id, "watch": list(roles.values())}
        return result

    @staticmethod
    def facts(hass, roles):
        target = hass.states.get(roles["target"]) if roles.get("target") else None
        attrs = target.attributes if target else {}
        config = hass.config_entries.async_get_entry(roles["entry"]) if roles.get("entry") else None
        options = {**config.data, **config.options} if config else {}
        azimuth = attrs.get("azimuth_window", options.get("set_azimuth"))
        reason = attrs.get("position_explanation") or attrs.get("reason")
        # The window's size, as told to Adaptive Cover Pro (metres).
        size = lambda key: float(options[key]) if isinstance(options.get(key), (int, float)) and 0 < options[key] < 20 else None
        return {"azimuth": float(azimuth) if isinstance(azimuth, (int, float)) and 0 <= azimuth <= 360 else None,
                "reason": reason if isinstance(reason, str) and reason else None,
                "width": size("window_width"), "height": size("window_height")}

    @staticmethod
    def values(hass, roles):
        return {}


class CoverAutomatic:
    """crandler/CoverAutomatic: one status sensor and one switch per cover, the sun read per facade."""
    KEY = "cover_automatic"
    NAME = "CoverAutomatic"
    PLATFORMS = ("cover_automatic",)
    STATUS = re.compile(r"^cover_automatic_(cover\..+)_status$")
    # A hand on the cover, or the automation waiting after one.
    HELD = ("manual", "paused")
    WHY = {"locked": "fenêtre ouverte", "venting": "aération", "wind_protected": "protégé du vent", "paused": "en pause", "manual": "réglé à la main"}

    @staticmethod
    def _storage(hass):
        """Its covers and facades as it keeps them; nothing when it changed shape."""
        for config in hass.config_entries.async_entries("cover_automatic"):
            storage = getattr(getattr(config, "runtime_data", None), "storage", None)
            try:
                return dict(storage.covers), dict(storage.facades)
            except (AttributeError, TypeError):
                continue
        return {}, {}

    @classmethod
    def find_all(cls, hass, registry):
        uid = {e.unique_id: e.entity_id for e in registry.entities.values() if e.platform in cls.PLATFORMS and not e.disabled_by}
        covers, facades = cls._storage(hass)
        result = {}
        for unique_id, status in uid.items():
            if not (match := cls.STATUS.match(unique_id or "")):
                continue
            cover = match[1]
            config = covers.get(cover)
            facade_id = getattr(config, "facade_id", None) or next((f for f, facade in facades.items() if cover in (getattr(facade, "cover_ids", None) or [])), None)
            roles = {"driver": cls.KEY, "name": cls.NAME, "status": status, "auto": uid.get(f"cover_automatic_{cover}_auto"),
                     "enabled": uid.get("cover_automatic_master")}
            if facade_id:
                facade = facades.get(facade_id)
                roles.update(sun=uid.get(f"cover_automatic_facade_{facade_id}_sun"), sun_entry=uid.get(f"cover_automatic_facade_{facade_id}_sun_entry"),
                             sun_exit=uid.get(f"cover_automatic_facade_{facade_id}_sun_exit"),
                             facade=[getattr(facade, "azimuth_start", None), getattr(facade, "azimuth_end", None)])
            roles = {k: v for k, v in roles.items() if v}
            roles["watch"] = [v for k, v in roles.items() if k in ("status", "auto", "enabled", "sun", "sun_entry", "sun_exit")]
            result[cover] = roles
        return result

    @staticmethod
    def facts(hass, roles):
        """The facade's bearing: the middle of the arc the sun lights it on."""
        start, end = [_number(x, 0, 360) for x in (roles.get("facade") or [None, None])]
        azimuth = None
        if start is not None and end is not None:
            azimuth = round((start + ((end - start) % 360) / 2) % 360, 1)
        return {"azimuth": azimuth, "reason": None, "width": None, "height": None}

    @classmethod
    def values(cls, hass, roles):
        status = _live(hass, roles.get("status"))
        values = {}
        if status is not None:
            values["override"] = status.state in cls.HELD
            values["target"] = _number(status.attributes.get("target_position"))
            rule = status.attributes.get("rule_name")
            values["reason"] = rule if isinstance(rule, str) and rule else cls.WHY.get(status.state)
        for role, entity in (("sun_start", "sun_entry"), ("sun_end", "sun_exit")):
            state = _live(hass, roles.get(entity))
            values[role] = _today_at(state.state) if state else None
        return values


class CoverExtender:
    """Pulpyyyy/cover-extender: a mode, a lock and automatic shading per cover, the sun facing it as the cover's attribute."""
    KEY = "cover_extender"
    NAME = "Cover Extender"
    PLATFORMS = ("cover_extender",)
    # Unique id → role, the cover's stable key (its registry id) in between.
    KINDS = ((re.compile(r"^cover_extender_switch_(.+)_auto_shade$"), "auto"), (re.compile(r"^cover_extender_switch_(.+)_lock$"), "override"),
             (re.compile(r"^cover_extender_binary_sensor_(.+)_sun_facing$"), "sun"), (re.compile(r"^cover_extender_select_mode_(.+)$"), "mode"))

    @classmethod
    def find_all(cls, hass, registry):
        by_id = {e.id: e.entity_id for e in registry.entities.values()}
        result = {}
        for entry in registry.entities.values():
            if entry.platform not in cls.PLATFORMS or entry.disabled_by:
                continue
            for pattern, role in cls.KINDS:
                if match := pattern.match(entry.unique_id or ""):
                    # Older helpers carry the cover's object id instead of its registry id.
                    cover = by_id.get(match[1]) or f"cover.{match[1]}"
                    result.setdefault(cover, {"driver": cls.KEY, "name": cls.NAME, "cover": cover})[role] = entry.entity_id
                    break
        for cover, roles in result.items():
            roles["watch"] = [v for k, v in roles.items() if k in ("auto", "override", "sun", "mode", "cover")]
        return result

    @staticmethod
    def facts(hass, roles):
        return {"azimuth": None, "reason": None, "width": None, "height": None}

    @staticmethod
    def values(hass, roles):
        values = {}
        cover = hass.states.get(roles.get("cover") or "")
        facing = cover.attributes.get("sun_facing") if cover else None
        if not roles.get("sun") and isinstance(facing, bool):
            values["sun"] = facing
        mode = _live(hass, roles.get("mode"))
        if mode is not None:
            values["reason"] = f"mode « {mode.state} »"
        return values


ADAPTERS = {a.KEY: a for a in (AdaptiveCoverPro, CoverAutomatic, CoverExtender)}
NAMES = {key: a.NAME for key, a in ADAPTERS.items()}
PLATFORMS = tuple(p for a in ADAPTERS.values() for p in a.PLATFORMS)
# Kept for the extension card that has always said Adaptive Cover Pro.
NAME = AdaptiveCoverPro.NAME


def _adapter(roles):
    return ADAPTERS.get((roles or {}).get("driver"), AdaptiveCoverPro)


def find_all(hass, drivers=None):
    """{cover entity: roles} for every cover a driver drives; `drivers` keeps only those the person uses.

    One that changed shape is left out, never stopping the others; a cover two of them claim keeps the first.
    """
    registry, result = er.async_get(hass), {}
    for key, adapter in ADAPTERS.items():
        if drivers is not None and key not in drivers:
            continue
        for cover, roles in adapter.find_all(hass, registry).items():
            result.setdefault(cover, roles)
    return result


def facts(hass, roles):
    """What the driver knows of the window: its exact bearing and size, and why the cover stands where it does."""
    return _adapter(roles).facts(hass, roles)


def values(hass, roles):
    """The signals a driver gives in its own words, said in the common ones: {role: value}, None when not known."""
    return _adapter(roles).values(hass, roles)


def exposure(azimuth):
    """The nearest of the eight exposures for an exact bearing."""
    if azimuth is None:
        return None
    return ("N", "NE", "E", "SE", "S", "SO", "O", "NO")[round(azimuth / 45) % 8]


def find(hass, cover_entity):
    return find_all(hass).get(cover_entity) if cover_entity else None
