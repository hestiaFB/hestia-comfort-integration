"""Layer 6's fixed rules: what safety takes away from the gestures (CAHIER-MOTEUR.md § 9.3).

The only rules of the engine. They never choose a gesture by themselves: they take « open » away, and the decision then
shuts what is open (advisor/decide.py). Reasons in order: rain now, rain soon, gusts, a red vigilance, nobody home.
"""
RAIN = 0.2              # mm/h: it rains
RAIN_SOON = 20          # minutes: the rain is due before an airing would end
GUSTS = 45.0            # km/h
# Hestia Weather's vigilance levels, as the 2.1 engine reads them: yellow 1, orange 2, red 3.
RED = 3
COLOURS = {"vert": 0, "green": 0, "jaune": 1, "yellow": 1, "orange": 2, "rouge": 3, "red": 3}
AWAY = ("armed_away", "armed_vacation")


def _level(vigilance) -> int | None:
    if vigilance is None:
        return None
    try:
        return int(float(vigilance))
    except (TypeError, ValueError):
        return COLOURS.get(str(vigilance).strip().lower())


def forbidden(rain_rate: float | None = None, gust: float | None = None, rain_in: float | None = None,
              vigilance=None, alarm: str | None = None) -> tuple[frozenset[str], str | None]:
    """What safety takes away now, and why (the reason the card says). A value not known forbids nothing."""
    if rain_rate is not None and rain_rate > RAIN:
        return frozenset({"open"}), "rain"
    if rain_in is not None and 0 <= rain_in <= RAIN_SOON:
        return frozenset({"open"}), "rain_soon"
    if gust is not None and gust > GUSTS:
        return frozenset({"open"}), "gusts"
    level = _level(vigilance)
    if level is not None and level >= RED:
        return frozenset({"open"}), "vigilance"
    if alarm in AWAY:
        return frozenset({"open"}), "away"
    return frozenset(), None


def holidays(alarm: str | None) -> bool:
    """The household is away for days (CAHIER-MOTEUR.md § 11, point 8): only safety and the house are watched."""
    return alarm == "armed_vacation"
