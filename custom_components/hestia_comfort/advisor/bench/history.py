"""Reads a Home Assistant history download (GET /api/history/period, with attributes) into the advisor's series."""
from datetime import datetime
import json

from ..observe import Series


def load(*paths) -> dict[str, list[dict]]:
    """One or several downloads, merged by entity."""
    out = {}
    for path in paths:
        with open(path, encoding="utf-8") as f:
            out.update({series[0]["entity_id"]: series for series in json.load(f) if series})
    return out


def _when(state, key="last_changed"):
    return datetime.fromisoformat(state.get(key) or state["last_changed"])


def numbers(history, entity_id) -> Series:
    points = []
    for state in history.get(entity_id, ()):
        try:
            points.append((_when(state), float(state["state"])))
        except (TypeError, ValueError):
            # « unavailable », « unknown »: the value is not known, the last one does not hold.
            points.append((_when(state), None))
    return Series(points, keep_none=True)


def contacts(history, entity_id) -> Series:
    known = {"on": True, "off": False}
    return Series([(_when(state), known.get(state["state"])) for state in history.get(entity_id, ())], keep_none=True)


def attribute(history, entity_id, name, scale=1.0) -> Series:
    points = []
    for state in history.get(entity_id, ()):
        value = (state.get("attributes") or {}).get(name)
        points.append((_when(state, "last_updated"), float(value) * scale if isinstance(value, (int, float)) else None))
    return Series(points, keep_none=True)


def lit_power(history, entity_id) -> Series:
    """Share (0-1) of its power a house heater gave off: what its thermostat asked, nothing while it said it was idle,
    waiting to be lit (the Salon's stove, 10 November: 100 % asked at 6 h and 17 h, never lit — room/advice.py
    `stove_waiting`). A history without the thermostat's action keeps what it asked."""
    points = []
    for state in history.get(entity_id, ()):
        attributes = state.get("attributes") or {}
        value, action = attributes.get("power_percent"), attributes.get("hvac_action")
        if not isinstance(value, (int, float)):
            points.append((_when(state, "last_updated"), None))
            continue
        waiting = value > 0 and action is not None and action != "heating"
        points.append((_when(state, "last_updated"), 0.0 if waiting else float(value) / 100))
    return Series(points, keep_none=True)
