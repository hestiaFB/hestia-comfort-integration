"""Layer 6's fixed rules: what safety takes away from the gestures (CAHIER-MOTEUR.md § 9.3).

The only rules of the engine. They never choose a gesture by themselves: they take « open » away, and the decision then
shuts what is open (advisor/decide.py). Reasons in order: rain now, rain soon, gusts, a red vigilance, nobody home; then
frost, which only takes the long openings away (« open_long »): a short airing still clears a shower's steam.
"""
RAIN = 0.2              # mm/h: it rains
RAIN_SOON = 20          # minutes: the rain is due before an airing would end
DRIVEN = 25.0           # km/h: from there, the rain is pushed under an overhang (engine/wind.py DRIVEN_RAIN_GUST)
WINDWARD = 60           # degrees: a wind from within this of the side an opening faces blows into it
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


def rained_on(sheltered: bool, facing: float | None, gust: float | None, wind_from: float | None) -> bool:
    """Whether the rain reaches an opening: one not sheltered, or sheltered but facing a wind that pushes the rain in. The
    side it faces or the wind's not known, gusts strong enough are taken as pushing it in."""
    if not sheltered:
        return True
    if gust is None or gust < DRIVEN:
        return False
    if facing is None or wind_from is None:
        return True
    return abs((wind_from - facing + 540) % 360 - 180) < WINDWARD


# « La pluie arrive » believed this long without a drop at the station; then no longer, until it rains or the forecast
# moves away (Frank, 5 November: Météo-France's radar said it 20 min away from 20 h 16, the station saw the first drops at
# 21 h 49 and the rain at 22 h 27 — the evening's airings were held back in five rooms).
RAIN_SOON_WAIT = 45     # minutes
RAIN_GONE = 60          # minutes: a forecast this far, or none, ends the wait
RAIN_SOON_KEPT = 40     # minutes: once said, « la pluie arrive » holds while the forecast stays this close


def rain_believed(rain_in: float | None, rain_rate: float | None, since: float | None,
                  now: float, sheltered: bool = False) -> tuple[float | None, float | None]:
    """The rain forecast as believed, and since when (seconds) it has been said due without a drop measured. Without a
    station measuring the rain, the forecast is always believed: nothing says it is wrong. Nor with a rain gauge under a
    tree or an overhang (`sheltered`, Hestia Weather's `station_trust`): its zero does not say the rain is not falling;
    the rain it does measure still forbids (`forbidden`)."""
    if rain_rate is None or sheltered:
        return rain_in, None
    if rain_rate > RAIN or rain_in is None or rain_in > RAIN_GONE:
        return rain_in, None
    if rain_in > RAIN_SOON:
        # Said due already: a forecast that slips a few minutes further does not lift it, only one that moves away
        # (6 November, Chambre A and Salon: « la pluie arrive » came and went every 5 to 20 minutes from 8 h 06).
        if since is not None and rain_in <= RAIN_SOON_KEPT and now - since <= RAIN_SOON_WAIT * 60:
            return float(RAIN_SOON), since
        return rain_in, since
    since = now if since is None else since
    return (None if now - since > RAIN_SOON_WAIT * 60 else rain_in), since


def forbidden(rain_rate: float | None = None, gust: float | None = None, rain_in: float | None = None,
              vigilance=None, alarm: str | None = None, coldest: float | None = None,
              shelter: str | None = None) -> tuple[frozenset[str], str | None]:
    """What safety takes away now, and why (the reason the card says). A value not known forbids nothing. `rain_in`: in
    minutes (`minutes`); `coldest`: the lowest outside temperature forecast over the coming hours; `shelter`: what the
    rain spares (`rained_on`) — « all » every opening of the room, « opened » those open now."""
    rain = ("rain" if rain_rate is not None and rain_rate > RAIN
            else "rain_soon" if rain_in is not None and 0 <= rain_in <= RAIN_SOON else None)
    if rain and shelter != "all":
        # A sheltered French window open under the rain stays so (Salon · Cuisine, 4 November: « Refermez, il pleut »
        # with its overhang ticked); opening the others more would let the rain in.
        return frozenset({"open_more"} if shelter == "opened" else {"open"}), rain
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
