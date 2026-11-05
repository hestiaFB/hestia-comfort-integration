"""Heat: two reservoirs per room, the air (fast) and the walls (slow), after the simple hourly model of EN ISO 13790.

    ca · dTa/dt = h_am·(Tm − Ta) + (h_ea + hv)·(Te − Ta) + heating + gains + 30 % of the sun
    cm · dTm/dt = h_am·(Ta − Tm) + h_em·(Te − Tm) + 70 % of the sun

The glazing and leaks lose the air's heat, the opaque walls the mass's; `hv` is the air coming in (leaks and open
windows, advisor/physics/vents.py). Each parameter has a physical meaning and starts from an ordinary value for the
room as declared (`ordinary`); the filter (learn.py) then adjusts it. Both reservoirs are stepped implicitly: an open
window empties the air within minutes, faster than the step, and an explicit step would diverge.
"""
from dataclasses import dataclass, replace
import math

from ..house import Room
from .vents import conductance, leak_flow, window_flow

STEP = 300.0  # seconds
# Effective mass per m² of floor and the surface it exchanges through (m² per m² of floor), EN ISO 13790 table 12.
MASS = {"light": (110_000.0, 2.5), None: (165_000.0, 2.5), "heavy": (260_000.0, 3.0)}
# Air-to-mass exchange per m² of exchange surface (W/m²K), EN ISO 13790.
H_MS = 9.1
# Air and furniture together hold several times the heat of the air alone.
FURNITURE = 5.0
# Ordinary losses of a room: walls per m² of floor, plus the glazing.
WALLS, GLAZING_U = 1.0, 2.8
# Solar factor of a double glazing, and the vertical sun on a window against the horizontal sun on the station.
G_VALUE, VERTICAL = 0.6, 0.5
# Each glazing's solar factor and U (W/m²K): ordinary values of EN 410 and EN 673, the same U as the ressenti
# (engine/feel.py). Norms, not settings; the glazing itself is declared (« Votre maison », or the window's own).
GLAZINGS = {"simple": (0.85, 5.8), "double": (G_VALUE, GLAZING_U), "triple": (0.5, 1.0)}


def glazing(kind: str | None) -> tuple[float, float]:
    """Solar factor and U of a glazing; a double one when it is not declared."""
    return GLAZINGS.get(kind or "double", GLAZINGS["double"])
# Share of the losses through the opaque walls: the rest goes through the glazing, straight from the air.
OPAQUE = 0.6
SUN_TO_AIR = 0.3
ORDINARY_GAINS = 50.0
# Ordinary heater sizing, W per m² of floor.
HEATER = 100.0
# What a closed roller shutter adds to its window's thermal resistance (m²K/W), EN ISO 10077-1 annex G, a shutter of
# average air tightness. On Chambre P's window (1.3 m²), a night at 5 °C outside: about 0.2 to 0.3 °C kept at waking up
# (1 November) — a supposed effect until nights shut and open are compared (CAHIER-MOTEUR.md § 4.1, § 6.7 ter).
SHUTTER_R = 0.15


def shutter_insulation(area: float, closed: float) -> float:
    """W/K a connected shutter takes off its windows' losses: `area` of glass behind it (m²), `closed` 0 to 1."""
    gained = GLAZING_U - 1 / (1 / GLAZING_U + SHUTTER_R)
    return gained * area * min(1.0, max(0.0, closed))


@dataclass(frozen=True)
class Params:
    h_env: float    # W/K lost through walls and glazing
    cm: float       # J/K stored in the walls
    ca: float       # J/K stored in the air and furniture
    h_am: float     # W/K between the air and the walls
    heat: float     # W at full heating power
    sun: float      # m²: W gained per W/m² of horizontal sun
    gains: float    # W, steady gains of the household
    window: float   # multiplier of the window law
    leaks: float    # m³/h through a shut room
    # The household's daily rhythm (W): people home in the evening, cooking, lights. A daily wave learned on top of
    # the steady gains, never a guess of who is home.
    rhythm_cos: float = 0.0
    rhythm_sin: float = 0.0
    # The share of the house's own heaters (a stove, a fireplace) that reaches this room: most of it where it stands,
    # some upstairs through the hall and the staircase. A room heater only heats its room; a house heater, all of them.
    share: float = 0.0
    # What the room keeps of the sun computed through its windows (curtains, a tree, the sensor's place): learned.
    glass: float = 1.0


@dataclass(frozen=True)
class Inputs:
    outdoor: float
    sun: float = 0.0                                # W/m², horizontal
    heating: float = 0.0                            # share of the full power, 0 to 1
    windows: tuple[tuple[float, float], ...] = ()   # (area, height) of each open window
    wind: float | None = None                       # m/s
    extra: float = 0.0                              # W: people, cooking…
    vent: float = 0.0                               # m³/h of outdoor air a running ventilation adds (a VMC's fast speed)
    purifier: float = 0.0                           # m³/h of clean air a running purifier gives (the particles' twin)
    hour: float | None = None                       # local time of day, for the household's rhythm
    house_heat: float = 0.0                         # W given off by the house heaters, wherever they stand
    # The share of the sun a connected shutter lets through, read on its position (0 shut, 1 open); 1 when the room has
    # none or its shutters are manual (their habit is then in the learned `sun`).
    shade: float = 1.0
    # W/K the connected shutters, closed, take off the glazing's losses (`shutter_insulation`); 0 when open or none.
    shutter: float = 0.0
    # W of sun through the room's windows, by their orientation (advisor/physics/sunlight.py), when it is declared:
    # an optional plus (CAHIER-MOTEUR.md § 6.7); without it, the horizontal sun times the learned `sun`.
    facade: float | None = None
    # The same with every window shut, and with every window open: an open sash lets in more sun than its glass, and the
    # advisor's scenarios shut or open them all (advisor/decide.py). None: `facade` holds whatever the windows do.
    # The learned `glass` weighs both: counting an open sash's sun in full, without it, made Chambre AL's forecasts worse
    # with its window open (bench of 31 October, 0.29 → 0.37 °C at one hour) and helped no other room.
    facade_shut: float | None = None
    facade_all: float | None = None
    # Windows open on two sides of the room let the air cross it: their flow is this many times what each lets in on its
    # own (advisor/decide.py `crossing`). 1: one side only.
    cross: float = 1.0


def ordinary(room: Room) -> Params:
    """The room's parameters from its declarations, ordinary values for the rest."""
    surface = room.surface
    per_m2, exchange = MASS.get(room.walls, MASS[None])
    # Each window by its own glazing: a single pane loses twice a double one's heat and lets more sun in.
    losses = sum(glazing(o.pane)[1] * o.glazing for o in room.openings) or GLAZING_U * 1.2
    gained = sum(glazing(o.pane)[0] * o.glazing for o in room.openings) or G_VALUE * 1.2
    return Params(h_env=WALLS * surface + losses, cm=per_m2 * surface, ca=1.2 * 1005 * room.air * FURNITURE,
                  h_am=H_MS * exchange * surface, heat=room.heating_power or HEATER * surface,
                  sun=max(0.2, VERTICAL * gained), gains=ORDINARY_GAINS, window=1.0, leaks=leak_flow(room.air))


def rhythm(p: Params, hour: float | None) -> float:
    """The household's gains at this time of day, above or under their steady value (W)."""
    if hour is None:
        return 0.0
    angle = 2 * math.pi * hour / 24
    return p.rhythm_cos * math.cos(angle) + p.rhythm_sin * math.sin(angle)


def flow(p: Params, ta: float, u: Inputs) -> float:
    """Outdoor air coming in (m³/h)."""
    if not u.windows:   # most steps: the nightly learning runs millions of them
        return p.leaks + u.vent
    return p.leaks + u.vent + p.window * u.cross * sum(window_flow(a, h, ta, u.outdoor, u.wind) for a, h in u.windows)


def step(p: Params, ta: float, tm: float, u: Inputs, dt: float = STEP) -> tuple[float, float]:
    """The air and the walls `dt` seconds later."""
    hv = conductance(flow(p, ta, u))
    h_em, h_ea = OPAQUE * p.h_env, max(0.0, (1 - OPAQUE) * p.h_env - u.shutter)
    entering = p.glass * u.facade if u.facade is not None else p.sun * max(0.0, u.sun)
    solar = max(0.0, entering) * min(1.0, max(0.0, u.shade))
    q_air = (p.heat * min(1.0, max(0.0, u.heating)) + min(1.0, max(0.0, p.share)) * u.house_heat
             + p.gains + u.extra + SUN_TO_AIR * solar + (rhythm(p, u.hour) if p.rhythm_cos or p.rhythm_sin else 0.0))
    q_mass = (1 - SUN_TO_AIR) * solar
    a11, a12 = p.ca / dt + p.h_am + h_ea + hv, -p.h_am
    a21, a22 = -p.h_am, p.cm / dt + p.h_am + h_em
    b1 = p.ca / dt * ta + (h_ea + hv) * u.outdoor + q_air
    b2 = p.cm / dt * tm + h_em * u.outdoor + q_mass
    det = a11 * a22 - a12 * a21
    return (b1 * a22 - a12 * b2) / det, (a11 * b2 - a21 * b1) / det


def time_constant(p: Params) -> float:
    """Hours for a shut, unheated room to cover two thirds of its way to the outdoor temperature."""
    return (p.cm + p.ca) / (p.h_env + conductance(p.leaks)) / 3600


def energy(p: Params, u: Inputs, dt: float = STEP) -> float:
    """kWh the heating spends over the step."""
    return p.heat * min(1.0, max(0.0, u.heating)) * dt / 3.6e6


def with_values(p: Params, **values) -> Params:
    return replace(p, **{k: v for k, v in values.items() if v is not None and math.isfinite(v)})
