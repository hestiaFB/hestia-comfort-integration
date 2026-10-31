"""Layer 6's fixed rules: what safety takes away from the gestures (CAHIER-MOTEUR.md § 9.3).

The only rules of the engine. They never choose a gesture by themselves: they take « open » away, and the decision then
shuts what is open (advisor/decide.py). Reasons in order: rain now, rain soon, gusts, a red vigilance, nobody home; then
frost, which only takes the long openings away (« open_long »): a short airing still clears a shower's steam.
"""
RAIN = 0.2              # mm/h: it rains
RAIN_SOON = 20          # minutes: the rain is due before an airing would end
GUSTS = 45.0            # km/h
# Hestia Weather's vigilance levels, as the 2.1 engine reads them: yellow 1, orange 2, red 3.
RED = 3
COLOURS = {"vert": 0, "verte": 0, "green": 0, "jaune": 1, "yellow": 1, "orange": 2, "rouge": 3, "red": 3}
# A duration sensor's units (Home Assistant's `duration` class), in minutes. Hestia Weather's « Pluie dans » is in hours:
# read as minutes, 18.4 h made « la pluie arrive » all of 31 October's evening, the rain being due the next afternoon.
UNITS = {"d": 1440.0, "h": 60.0, "min": 1.0, "s": 1 / 60, "ms": 1 / 60000}


def minutes(value: float | None, unit: str | None) -> float | None:
    """A duration in minutes, from its value and its unit; None when the unit is unknown — never a guess."""
    if value is None:
        return None
    factor = UNITS.get(unit or "min")
    return None if factor is None else value * factor
AWAY = ("armed_away", "armed_vacation")
FROST = 1.0             # °C forecast outside: no long opening (Confort 2.1's `frost`)


def _level(vigilance) -> int | None:
    if vigilance is None:
        return None
    try:
        return int(float(vigilance))
    except (TypeError, ValueError):
        return COLOURS.get(str(vigilance).strip().lower())


def forbidden(rain_rate: float | None = None, gust: float | None = None, rain_in: float | None = None,
              vigilance=None, alarm: str | None = None, coldest: float | None = None) -> tuple[frozenset[str], str | None]:
    """What safety takes away now, and why (the reason the card says). A value not known forbids nothing. `rain_in`: in
    minutes (`minutes`); `coldest`: the lowest outside temperature forecast over the coming hours."""
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
    if coldest is not None and coldest <= FROST:
        return frozenset({"open_long"}), "frost"
    return frozenset(), None


def holidays(alarm: str | None) -> bool:
    """The household is away for days (CAHIER-MOTEUR.md § 11, point 8): only safety and the house are watched."""
    return alarm == "armed_vacation"
