"""The room's « Ressenti »: the temperature the body feels, not only the air the thermometer measures.

Indoors the body feels the air and, as much, what surrounds it: the walls and the panes, colder than the air when it is
cold outside, the sun through a window, a stove's radiant heat. That half-and-half is the operative temperature (ISO 7726):
the ressenti takes half of every surface's gap to the air. A draught (an open window, colder air moving) and, in summer,
damp air come on top. The CO₂ changes nothing to the warmth: the card shows it beside, never in the figure.

The walls are estimated, not measured: their inner surface is colder the larger the gap with outside and the less the
house is insulated. How well the walls are insulated and which glazing the house has are settings of the house
(« Réglages du foyer », foyer.py), each with its default. Shown only for now (maquettes/maquette-ressenti-piece.html): the
advice keeps judging the air until the ressenti has been compared with the real house.
"""
import math

# The inner surface resistance of a wall (m²·K/W, EN ISO 6946): how far the inner face sits from the air.
SURFACE_RESISTANCE = 0.13
# U-values (W/m²·K) by setting: the walls, the panes; a closed shutter keeps this share of a pane's losses.
WALLS = {"bien": 0.3, "moyenne": 0.6, "peu": 1.4}
GLAZING = {"simple": 5.8, "double": 2.8, "triple": 1.0}
SHUTTER_KEEPS = 0.65
# What a body in the room sees of its outer walls and of its panes; the rest (inner walls, floor, ceiling) sits at the air.
OUTER_WALLS, PANES = 0.35, 0.12
# A cover at or below this position (0 = closed) hides its pane.
COVER_SHUT = 20
# The sun through a pane, on the surfaces the body sees: four tenths of a degree per hundred W/m², three degrees at most
# (halved in the ressenti): the body is seldom in the sun's patch itself.
SUN_GAIN, SUN_MOST = 0.004, 3.0
# A running heating warms the surfaces around: a stove radiates, a floor and a radiant panel too, a radiator with a core
# a little more than a convector, air conditioning not.
RADIANT = {"stove": 2.4, "pellet": 1.8, "floor": 1.2, "radiant": 1.2, "inertia": 0.9, "radiator": 0.6, "ac": 0.0}
# A draught: colder air moving past the body. Fuller with the gusts (km/h) and the gap to outside, 2.5 °C at most.
DRAUGHT_BASE, DRAUGHT_GUST, DRAUGHT_MOST, DRAUGHT_GAP = 0.3, 0.04, 2.5, 8.0
# Damp air only weighs once it is warm: from 24 °C, above 55 %, three tenths of a degree per ten points.
HUMID_FROM, HUMID_ABOVE, HUMID_STEP = 24.0, 55.0, 0.3


def dew_point(temperature, humidity):
    """The dew point (Magnus), °C."""
    a, b = 17.62, 243.12
    g = math.log(max(humidity, 1) / 100) + a * temperature / (b + temperature)
    return b * g / (a - g)


def _round(value):
    return round(value, 1) + 0.0


def feel(air, outside=None, humidity=None, gust=None, openings=(), covers=None, heating=None, night=False,
         walls="moyenne", glazing="double"):
    """The ressenti of a room, with what plays on it, or None without the air's temperature.

    `openings`: the assessment's details of the room's openings ({"entity_id", "open", "kind", "sun_wm2"}); `covers`: the
    position of each opening's connected shutter (0 closed, 100 open); `heating`: {"on", "kind", "power"} of the heating the
    room's range follows, or None without one. `walls` and `glazing`: the house's settings."""
    if air is None:
        return None
    covers = covers or {}
    panes = [o for o in openings if o.get("kind") != "door"]
    hidden = [o for o in panes if (p := covers.get(o.get("entity_id"))) is not None and p <= COVER_SHUT]
    share_shut = len(hidden) / len(panes) if panes else 0.0

    # The walls and the panes: their inner face, colder (or warmer) than the air by a share of the gap with outside.
    gap = None if outside is None else air - outside
    wall_u, pane_u = WALLS.get(walls, WALLS["moyenne"]), GLAZING.get(glazing, GLAZING["double"])
    pane_u *= 1 - share_shut * (1 - SHUTTER_KEEPS)
    wall_face = None if gap is None else air - gap * wall_u * SURFACE_RESISTANCE
    pane_face = None if gap is None else air - gap * pane_u * SURFACE_RESISTANCE
    surfaces = 0.0 if gap is None else 0.5 * (OUTER_WALLS * (wall_face - air) + PANES * (pane_face - air))

    # The sun through the panes no shutter hides: the strongest one.
    seen = [o["sun_wm2"] for o in panes if o not in hidden and isinstance(o.get("sun_wm2"), (int, float))]
    watts = max(seen) if seen and not night else None
    sun = 0.0 if not watts else 0.5 * min(SUN_MOST, SUN_GAIN * watts)

    # The heating the range follows, while it runs: its radiant part, at the power it reports.
    # A heating whose kind is not set counts as a radiator, and is named only « Chauffage ». A power of 0 % while it heats
    # (a stove's thermostat that only switches it) says nothing: the heating runs fully.
    kind = (heating or {}).get("kind")
    running = bool(heating and heating.get("on"))
    power = (heating or {}).get("power")
    share = min(power / 100, 1.0) if isinstance(power, (int, float)) and not isinstance(power, bool) and power > 0 else 1.0
    radiant = 0.5 * RADIANT.get(kind or "radiator", RADIANT["radiator"]) * share if running else 0.0

    # A draught: a window open on colder air.
    opened = any(o.get("open") is True for o in openings)
    draught = 0.0
    if opened and gap is not None and gap > 0:
        draught = -min(DRAUGHT_MOST, DRAUGHT_BASE + DRAUGHT_GUST * (gust or 0)) * min(1.0, gap / DRAUGHT_GAP)

    # Damp warm air.
    damp = 0.0
    if humidity is not None and air >= HUMID_FROM and humidity > HUMID_ABOVE:
        damp = (humidity - HUMID_ABOVE) / 10 * HUMID_STEP

    feels = air + surfaces + sun + radiant + draught + damp
    return {
        "feels": _round(feels), "air": _round(air), "outdoor": None if outside is None else _round(outside),
        "walls": walls, "glazing": glazing,
        "factors": {
            "walls": {"delta": _round(surfaces), "gap": None if gap is None else _round(gap),
                      "wall": None if wall_face is None else _round(wall_face), "pane": None if pane_face is None else _round(pane_face),
                      "shutters": share_shut > 0},
            "sun": {"delta": _round(sun), "wm2": None if watts is None else round(watts), "night": bool(night),
                    "hidden": bool(panes) and share_shut == 1.0},
            "heating": None if heating is None else {"delta": _round(radiant), "kind": kind, "on": running},
            "draught": {"delta": _round(draught), "open": opened, "gust": None if gust is None else round(gust)},
            "humidity": None if humidity is None else {"delta": _round(damp), "value": round(humidity),
                                                         "dew": _round(dew_point(air, humidity))},
        },
    }
