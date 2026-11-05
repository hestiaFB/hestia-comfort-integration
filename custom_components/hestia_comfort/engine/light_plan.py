"""« Lumières »: what a coloured light should do for a verdict, decided without Home Assistant (light_driver.py sends it)."""

# The look of each state when the person kept Hestia-FB's colours (frontend/lights.ts holds the same).
DEFAULT_LOOKS = {"calm": {"colour": "#aad6e5", "effect": "keep", "brightness": 40},
                 "benefit": {"colour": "#a5d6ae", "effect": "solid", "brightness": 50},
                 "action": {"colour": "#f1b277", "effect": "solid", "brightness": 70},
                 "airing": {"colour": "#aad6e5", "effect": "solid", "brightness": 60},
                 "urgent": {"colour": "#e8857f", "effect": "flash", "brightness": 100}}
# Only a gesture or an alert may turn on a light that was off (« L'allumer pour un geste ou une alerte »).
WAKING = ("action", "urgent")
MOODS = {"calm": "calm", "best": "calm", "benefit": "benefit", "action": "action", "urgent": "urgent"}
NIGHT = (22, 7)


def state_key(verdict):
    """The banner's state as the light knows it: an airing going on before its mood; « À vérifier » has no look."""
    if not verdict:
        return None
    if verdict.get("gesture") == "keep_open":
        return "airing"
    return MOODS.get(verdict.get("mood"))


def is_night(hour):
    start, end = NIGHT
    return hour >= start or hour < end


def blocked(rule, hour, someone_home):
    """The safeguards chosen in the hub: never at night, only when someone is home."""
    return bool((rule.get("night") and is_night(hour)) or (rule.get("presence") and not someone_home))


def rgb(colour):
    return [int(colour[i:i + 2], 16) for i in (1, 3, 5)]


def plan(rule, key, *, is_on, hour, someone_home, ours):
    """What to send: ("on", data), ("off", None), ("restore", None) to put back what was there before Hestia-FB, or None.

    `ours` says Hestia-FB changed this light and remembers how it was; a light Hestia-FB never touched is only ever changed
    when it is on, or woken for a gesture or an alert when the person allowed it."""
    if key is None:
        return None
    look = (rule.get("states") or {}).get(key) or DEFAULT_LOOKS[key]
    if look["effect"] == "keep" or blocked(rule, hour, someone_home):
        return ("restore", None) if ours else None
    if not is_on and not ours and not (rule.get("wake") and key in WAKING):
        return None
    if look["effect"] == "off":
        return ("off", None)
    data = {"brightness_pct": look["brightness"]}
    if look.get("colour"):
        data["rgb_color"] = rgb(look["colour"])
    if look["effect"] == "flash":
        data["flash"] = "long"
    elif look["effect"] != "solid":
        data["effect"] = look["effect"]
    return ("on", data)


# A WLED effect's speed (its segment's « Vitesse », 0 to 255), by the hub's three words.
SPEEDS = {"slow": 60, "normal": 128, "fast": 220}


def speed(rule, key):
    """The WLED speed of a state's effect, or None when the look does not move (nothing changed, off, fixed, a flash)."""
    look = (rule.get("states") or {}).get(key) or DEFAULT_LOOKS.get(key) or {}
    if look.get("effect") in (None, "keep", "off", "solid", "flash"):
        return None
    return SPEEDS.get(look.get("speed") or "normal", SPEEDS["normal"])


# LightEntityFeature.FLASH: a light without it ignores « flash ».
FLASH = 8


def _named(effects, name):
    return next((e for e in effects or () if str(e).lower() == name), None)


def fit(data, attributes):
    """The call fitted to what the light can do: a light that cannot flash blinks with its own « Blink » effect, and
    « Fixe » stops an effect already running (a WLED strip keeps its rainbow under a new colour otherwise)."""
    data, effects = dict(data), attributes.get("effect_list") or ()
    if "flash" in data and not int(attributes.get("supported_features") or 0) & FLASH:
        del data["flash"]
        blink = _named(effects, "blink")
        if blink:
            data["effect"] = blink
    if "effect" not in data and "flash" not in data:
        solid = _named(effects, "solid")
        if solid:
            data["effect"] = solid
    return data


def snapshot(state, attributes):
    """How a light was before Hestia-FB changed it, enough to put it back."""
    if state != "on":
        return {"on": False}
    kept = {"on": True}
    if attributes.get("brightness") is not None:
        kept["brightness"] = attributes["brightness"]
    if attributes.get("rgb_color") is not None:
        kept["rgb_color"] = list(attributes["rgb_color"])
    elif attributes.get("color_temp_kelvin") is not None:
        kept["color_temp_kelvin"] = attributes["color_temp_kelvin"]
    if attributes.get("effect") and attributes["effect"] in (attributes.get("effect_list") or ()):
        kept["effect"] = attributes["effect"]
    return kept


def restore(kept):
    """The service call that puts a light back as `snapshot` saw it."""
    if not kept.get("on"):
        return ("turn_off", {})
    return ("turn_on", {k: v for k, v in kept.items() if k != "on"})
