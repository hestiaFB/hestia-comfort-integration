"""Rooms open onto each other share one air: their openings are common and they never give opposite gestures.

Each room still reads its own sensors and finds its own needs. When two rooms of one volume disagree
(one says close, the other open or keep open), the weightier reason speaks for the whole volume; the
other room says whom it follows instead of contradicting it.
"""

# Weather on the shared openings, then a need for air, then comfort reasons to close, then the rest.
SAFETY = ("rain_open_windows", "gust_open_windows", "rain_soon")
HARD = {"storm", "vigilance", "pollution", "rain", "rain_soon"}
AIR = ("air_needed", "short_air_change")
COMFORT_CLOSE = ("exchange_harmful", "rehumidification_risk", "heat_needed", "sun_entering", "opening_blocked", "voc_outdoor")
OPEN = ("cooling_possible", "drying_possible", "precool_possible", "warming_possible")


def weight(assessment: dict) -> int:
    reason, action = assessment.get("reason"), assessment.get("action")
    if reason in SAFETY or (reason == "opening_blocked" and action == "fermer" and HARD & set(assessment.get("constraints", ()))):
        return 4
    if reason in AIR:
        return 3
    if reason in COMFORT_CLOSE and action == "fermer":
        return 2
    if reason in OPEN:
        return 1
    return 0


def _side(assessment: dict) -> str | None:
    """« shut », « open » (keeping an open window open counts), or None when the room asks no window gesture."""
    action = assessment.get("action")
    if action == "fermer":
        return "shut"
    if action == "ouvrir" or (action == "ok" and assessment.get("reason") in AIR + OPEN):
        return "open"
    return None


SEVERITY = {"urgent": 4, "action": 3, "benefit": 2, "neutral": 1, "calm": 0}


def rank(assessment: dict) -> tuple:
    """What makes a room speak for its volume: the weight of its reason, a gesture, then its level."""
    return (weight(assessment), _side(assessment) is not None, SEVERITY.get(assessment.get("level"), 0))


def arbitrate(own: dict, partners: list[tuple[str, dict]]) -> dict:
    """`own` and each partner's assessment as computed alone; returns the volume's one verdict as this room shows it.

    The room whose advice weighs most speaks for the whole volume; the others show the same advice and say
    whose it is. On a tie, each room keeps its own words."""
    lead = max(partners, key=lambda p: rank(p[1]), default=None)
    if lead is None or rank(lead[1]) <= rank(own):
        return own
    title, other = lead
    # Each room keeps its own needs: its tiles show what its own sensors measure.
    keep = ("action", "level", "constraints", "rain_soon_minutes", "temperature_delta", "slot", "open_first")
    shared = {k: other[k] for k in keep if k in other}
    picked = {k: other.get("features", {}).get(k) for k in ("drying", "ventilation", "rain_ahead", "humidity", "air", "warmth", "learned", "horizon")}
    features = {**own.get("features", {}), "volume": {"lead": title, "reason": other["reason"], "action": other["action"],
                                                      "assessment": {**shared, "reason": other["reason"], "features": picked}}}
    return {**own, **shared, "reason": "shared_volume", "features": features}
