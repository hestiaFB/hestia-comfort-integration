"""Home synthesis from the room views: it summarises rooms, it never replaces their advice."""
from math import isfinite

SEVERITY = {"urgent": 4, "action": 3, "benefit": 2, "neutral": 1, "calm": 0}
OPPOSITE = {("E", "O"), ("N", "S"), ("NE", "SO"), ("SE", "NO")}


def _value(view, key):
    reading = view.get("observations", {}).get(key)
    if reading and reading.get("quality") == "valid" and isinstance(reading.get("value"), (int, float)) and not isinstance(reading["value"], bool) and isfinite(reading["value"]):
        return reading["value"]
    return None


def synthesis(views):
    """Views are the per-room payloads published by the coordinators."""
    rooms = []
    for view in views:
        a = view["assessment"]
        names = view.get("names", {})
        openings = a.get("openings", [])
        # A room airing as advised asks nothing more: its banner is blue, it does not lead the home.
        verdict = view.get("verdict") or {}
        level = verdict["level"] if verdict.get("gesture") == "keep_open" else a["level"]
        rooms.append({"entry_id": view["entry_id"], "title": view["title"], "level": level, "action": a["action"],
                      "floor": view.get("floor"), "temperature": _value(view, "indoor_temperature"), "needs": list(a["needs"]),
                      "open": [names.get(o["entity_id"], o["entity_id"]) for o in openings if o.get("open")],
                      "open_exposures": [o["exposure"] for o in openings if o.get("open") and o.get("exposure")],
                      "sun_entering": [names.get(o["entity_id"], o["entity_id"]) for o in openings if "sun_entering" in o.get("flags", [])],
                      "partial": a["partial"]})
    # The room that needs the most attention leads; a gesture to make beats a mere observation.
    focus = max(rooms, key=lambda r: (SEVERITY.get(r["level"], 0), r["action"] not in ("ok", "unknown"),
                                     r["temperature"] if "cool" in r["needs"] and r["temperature"] is not None else float("-inf")), default=None)
    measured = [r for r in rooms if r["temperature"] is not None]
    hottest = max(measured, key=lambda r: r["temperature"]) if len(measured) > 1 else None
    coolest = min(measured, key=lambda r: r["temperature"]) if len(measured) > 1 else None
    exposures = {e for r in rooms for e in r["open_exposures"]}
    if any((a, b) in OPPOSITE or (b, a) in OPPOSITE for a in exposures for b in exposures):
        crossing = "strong"
    elif len(exposures) > 1:
        crossing = "partial"
    elif exposures:
        crossing = "none"
    else:
        crossing = None
    # Where to start cooling: the warmest room that needs fresh air and can get it now.
    candidates = [r for r in measured if "cool" in r["needs"] and r["action"] == "ouvrir"]
    start = max(candidates, key=lambda r: r["temperature"], default=None)
    outdoor = next((_value(v, "outdoor_temperature") for v in views if _value(v, "outdoor_temperature") is not None), None)
    floors = []
    for room in rooms:
        floor = room["floor"] or {"floor_id": None, "name": "Sans étage", "level": None}
        group = next((f for f in floors if f["floor_id"] == floor["floor_id"]), None)
        if group is None:
            group = {**floor, "room_ids": [], "measured": 0, "total": 0, "mean": None,
                     "hottest": None, "level_of_attention": "calm", "partial": False}
            floors.append(group)
        group["room_ids"].append(room["entry_id"])
        group["total"] += 1
        group["partial"] |= room["partial"] or room["temperature"] is None
        if SEVERITY[room["level"]] > SEVERITY[group["level_of_attention"]]:
            group["level_of_attention"] = room["level"]
    for group in floors:
        values = [r for r in measured if r["entry_id"] in group["room_ids"]]
        group["measured"] = len(values)
        if values:
            group["mean"] = round(sum(r["temperature"] for r in values) / len(values), 1)
            hot = max(values, key=lambda r: r["temperature"])
            group["hottest"] = {k: hot[k] for k in ("entry_id", "title", "temperature")}
    floors.sort(key=lambda f: (f["floor_id"] is None, f["level"] is None, f["level"] or 0, f["name"].casefold()))
    known = [f for f in floors if f["floor_id"] is not None and f["mean"] is not None]
    contrast = None
    if len(known) > 1:
        warm = max(known, key=lambda f: f["mean"])
        cool_floor = min(known, key=lambda f: f["mean"])
        if warm["mean"] > cool_floor["mean"]:
            contrast = {"warmer": warm["name"], "cooler": cool_floor["name"],
                        "difference": round(warm["mean"] - cool_floor["mean"], 1),
                        "partial": warm["measured"] < warm["total"] or cool_floor["measured"] < cool_floor["total"]}
    ventilation = _ventilation(views)
    return {"floors": floors, "floor_contrast": contrast, "ventilation": ventilation,
            "start_floor": start and start["floor"], "level": focus["level"] if focus else "neutral",
            "focus": focus["entry_id"] if focus else None,
            "hottest": hottest and {"entry_id": hottest["entry_id"], "title": hottest["title"], "temperature": hottest["temperature"]},
            "coolest": coolest and {"entry_id": coolest["entry_id"], "title": coolest["title"], "temperature": coolest["temperature"]},
            "spread": round(hottest["temperature"] - coolest["temperature"], 1) if hottest and coolest else None,
            "open_rooms": [{"title": r["title"], "open": r["open"]} for r in rooms if r["open"]],
            "crossing": crossing, "start_with": start and start["title"],
            "sun_entering": [{"title": r["title"], "openings": r["sun_entering"]} for r in rooms if r["sun_entering"]],
            "outdoor_temperature": outdoor, "partial": any(r["partial"] for r in rooms)}


def _ventilation(views):
    """Conditional pairs only; contacts and wind do not prove an indoor air path."""
    candidates = []
    for view in views:
        a = view["assessment"]
        ti, te = _value(view, "indoor_temperature"), _value(view, "outdoor_temperature")
        # Do not turn a short CO2 airing exception into a whole-house cooling advice.
        if (a.get("constraints") or a.get("partial") or a.get("action") not in ("ouvrir", "ok")
                or "cool" not in a.get("opportunities", []) or "heat" in a.get("needs", [])
                or ti is None or te is None or te >= ti
                or ti <= view.get("comfort_minimum", 20) + 1):
            continue
        for opening in a.get("openings", []):
            if opening.get("open") is None or opening.get("flags"):
                continue
            candidates.append({"entry_id": view["entry_id"], "title": view["title"],
                "floor": view.get("floor"), "temperature": ti,
                "needs_cooling": "cool" in a.get("needs", []) or "precool" in a.get("needs", []),
                "entity_id": opening["entity_id"],
                "name": view.get("names", {}).get(opening["entity_id"], opening["entity_id"]),
                "exposure": opening.get("exposure"), "wind_side": opening.get("wind_side"),
                "open": opening["open"]})
    pairs = []
    for i, a in enumerate(candidates):
        for b in candidates[i + 1:]:
            if a["entry_id"] == b["entry_id"] or not (a["needs_cooling"] or b["needs_cooling"]):
                continue
            fa, fb = a["floor"], b["floor"]
            stack = bool(fa and fb and fa["level"] is not None and fb["level"] is not None
                         and fa["level"] != fb["level"])
            cross = (a["exposure"], b["exposure"]) in OPPOSITE or (b["exposure"], a["exposure"]) in OPPOSITE
            if not stack and not cross:
                continue
            wind = {a["wind_side"], b["wind_side"]} == {"windward", "leeward"}
            if stack and wind:
                lower, upper = sorted((a, b), key=lambda o: o["floor"]["level"])
                if lower["wind_side"] != "windward":
                    # Opposing wind: retain only a cross-facade possibility, not combined upward draft.
                    stack = False
            if not stack and not cross:
                continue
            pairs.append({"kind": "combined" if stack and cross and wind else "stack" if stack else "cross",
                          "wind_favorable": wind, "engaged": a["open"] and b["open"],
                          "openings": [a, b], "path_confirmed": False})
    return max(pairs, key=lambda p: (max(o["temperature"] for o in p["openings"]),
                                    p["wind_favorable"], p["engaged"]), default=None)
