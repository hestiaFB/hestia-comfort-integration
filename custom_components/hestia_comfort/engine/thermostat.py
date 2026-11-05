"""Versatile Thermostat, recognised by itself: the extension that lets the heating speak for itself.

Any climate entity gives its mode and, often, what it is doing. A Versatile Thermostat says much more, and Hestia-FB reads
it when the room's heating is one (its platform, never its name):

- its set point, which can stand as the room's minimum: the person chose it there, and a room at 18 °C in eco at
  17 °C is not « too cool ». Frost protection is a safeguard, not a comfort: its set point (7 °C, or 14 °C for a stove
  kept low) never stands as the minimum, the comfort temperature does;
- why it is off (by hand, an open window it detected, its own start-stop, a central mode, a power cut-off…): only
  an « off by hand » is the person's to undo, the others resume by themselves;
- its preset (eco, frost protection, away): the heating runs, aiming lower on purpose;
- the slope of the room's temperature, in °C per hour, for a room whose twin has not learned yet;
- the presence or motion it follows, for a room without a presence sensor of its own;
- the window it saw open, said to the person when no contact of the room says it.

Versatile Thermostat 7 and later group these attributes (`specific_states`, `preset_temperatures`, `window_manager`…);
earlier versions kept them flat. Both are read. Hestia-FB still commands nothing.
"""
import math

PLATFORM = "versatile_thermostat"
NAME = "Versatile Thermostat"
# Why the thermostat is off, in its own words, and whether the person is the one to switch it back on.
OFF_REASONS = {"hvac_off_manual": "manual", "hvac_off_window_detection": "window", "hvac_off_auto_start_stop": "auto_start_stop",
               "hvac_off_sleep_mode": "sleep", "hvac_off_safety_detection": "safety", "hvac_off_central_mode": "central_mode",
               "hvac_off_inhibition": "inhibition"}
# Presets that aim lower on purpose: a room under its range is then expected.
LOWERED = ("eco", "frost", "away")


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _first(attrs, *paths):
    """The first value found at one of the paths: ("specific_states", "hvac_off_reason") or a flat key."""
    for path in paths:
        node = attrs
        for key in (path if isinstance(path, tuple) else (path,)):
            node = node.get(key) if isinstance(node, dict) else None
        if node is not None:
            return node
    return None


def _on(value):
    if value in (True, "on", "home", "detected"):
        return True
    if value in (False, "off", "not_home", "not_detected"):
        return False
    return None


def read(state, attrs):
    """What one Versatile Thermostat says, from its state and attributes; values it does not give stay None."""
    attrs = attrs if isinstance(attrs, dict) else {}
    mode = attrs.get("hvac_mode") or state
    preset = attrs.get("preset_mode")
    preset = None if preset in (None, "none", "") else str(preset)
    reason = _first(attrs, ("specific_states", "hvac_off_reason"), "hvac_off_reason")
    temperatures = attrs.get("preset_temperatures") if isinstance(attrs.get("preset_temperatures"), dict) else attrs
    # A preset temperature of 0 is a preset the thermostat does not use.
    preset_temperature = lambda key: (v if (v := _number(temperatures.get(key))) else None)
    window = [_on(_first(attrs, ("window_manager", key), key)) for key in ("window_state", "window_auto_state")]
    presence = _on(_first(attrs, ("presence_manager", "presence_state"), "presence_state"))
    motion = _on(_first(attrs, ("motion_manager", "motion_state"), "motion_state"))
    return {"name": NAME, "mode": mode if isinstance(mode, str) else None, "action": attrs.get("hvac_action"), "preset": preset,
            "target": _number(attrs.get("temperature")),
            "comfort": preset_temperature("comfort_temp"), "eco": preset_temperature("eco_temp"), "frost": preset_temperature("frost_temp"),
            "off_reason": OFF_REASONS.get(reason) if mode == "off" else None,
            "slope": _number(_first(attrs, ("specific_states", "temperature_slope"), "temperature_slope")),
            "window": True if True in window else False if False in window else None,
            # Presence first: motion only says someone moved lately.
            "occupied": presence if presence is not None else motion,
            "active": _first(attrs, ("specific_states", "is_device_active"), "is_device_active")}


def lowered(thermostat):
    """The thermostat runs on a preset that aims lower on purpose (eco, frost protection, away)."""
    preset = (thermostat or {}).get("preset") or ""
    return thermostat is not None and thermostat.get("mode") not in (None, "off") and any(p in preset for p in LOWERED)


def reference(thermostat, maximum):
    """The thermostat's set point (its comfort temperature when it gives none, or on frost protection), when it can
    stand as the room's minimum; else None. Eco lowers it on purpose: the room is then expected cooler."""
    thermostat = thermostat or {}
    guard = "frost" in (thermostat.get("preset") or "")
    target = thermostat.get("target") if thermostat.get("target") is not None and not guard else thermostat.get("comfort")
    return target if target is not None and 5 <= target < maximum else None
