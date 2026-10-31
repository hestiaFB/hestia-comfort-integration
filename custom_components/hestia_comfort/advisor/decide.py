"""Layers 6 to 8: the gestures a room allows, what each one costs over the coming hours, and the one advised.

Every gesture is simulated on the room's twins with the weather to come; its cost adds up, in readable units, the
discomfort it leaves (degrees out of the range × hours, humidity points × hours, CO₂ and particles above their marks),
the heat it lets out (kWh) and the bother of doing it (more at night). The cheapest is advised only when it beats « do
nothing » by a clear gain, and a gesture already shown stays until another beats it by a margin: one hysteresis, on the
cost, instead of one per threshold (CAHIER-MOTEUR.md § 10, § 11). Safety rules only take gestures away.
"""
from dataclasses import dataclass, field, replace

from .physics.air import AirParams, ParticleParams, air_step, particles_step
from .physics.thermal import STEP, Inputs, Params, step
from .physics.vents import conductance, leak_flow, window_flow
from .physics.water import WaterParams, absolute, relative, water_step

HOURS = STEP / 3600
# A gesture is advised only when it saves at least this much (in the cost's unit, about one degree out of the range for
# one hour), and a gesture shown is replaced only by one cheaper by this share of its cost.
GAIN, MARGIN = 0.5, 0.2


@dataclass(frozen=True)
class Gesture:
    kind: str                   # nothing | close | open
    minutes: int | None = None  # how long an opening lasts; None: until the end of the horizon


@dataclass(frozen=True)
class Comfort:
    """The room's range and marks (SEUILS.md), the person's own."""
    minimum: float = 20.0
    maximum: float = 24.0
    humidity: float = 60.0      # %
    co2: float = 1000.0         # ppm
    particles: float = 15.0     # µg/m³


@dataclass(frozen=True)
class Weights:
    """What one unit of each discomfort costs, in degrees·hours: the three sliders of § 10.3 move them, within bounds."""
    heat: float = 1.0           # per °C·h out of the range
    humidity: float = 0.05      # per point·h above the mark
    co2: float = 0.002          # per ppm·h above the mark
    particles: float = 0.02     # per µg/m³·h above the mark
    energy: float = 0.5         # per kWh of heat let out
    bother: float = 0.1         # per gesture
    night: float = 3.0          # a gesture at night bothers this much more


@dataclass(frozen=True)
class Thermostat:
    """The room's Versatile Thermostat, as its attributes describe it (CAHIER-MOTEUR.md § 6.8): it heats in proportion to
    the gap to its target and to the outside (its TPI regulation), and stops while a window it follows is open."""
    target: float                   # °C, `current_state.target_temperature`
    inside: float = 0.6             # `tpi_coef_int`
    outside: float = 0.01           # `tpi_coef_ext`
    window_off: bool = True         # `window_manager.window_action` is « window_turn_off »

    def power(self, air: float, outdoor: float, windows) -> float:
        """Share of the full power over the next cycle, 0 to 1."""
        if windows and self.window_off:
            return 0.0
        return min(1.0, max(0.0, self.inside * (self.target - air) + self.outside * (self.target - outdoor)))


@dataclass(frozen=True)
class Twins:
    """The room's twins, each with the window effect its own sensor learned (CONCEPTION-MOTEUR.md § 1 bis)."""
    heat: Params
    windows: tuple[tuple[float, float], ...]            # (area, height) of each of the room's windows
    water: WaterParams | None = None
    water_flow: tuple[float, float] = (1.0, 1.0)        # learned multipliers of the leaks and of the windows
    air: AirParams | None = None
    air_flow: tuple[float, float] = (1.0, 1.0)
    particles: ParticleParams | None = None
    particles_flow: tuple[float, float] = (1.0, 1.0)
    # With a thermostat, its heating is simulated in every scenario; without, the heating stays as the inputs say.
    thermostat: Thermostat | None = None


@dataclass(frozen=True)
class Now:
    air: float                                  # °C
    walls: float                                # °C, as the twin follows them
    opened: tuple[tuple[float, float], ...]     # the windows open now
    humidity: float | None = None               # %
    reserve: float | None = None                # g/m³, the walls' water
    co2: float | None = None                    # ppm
    particles: float | None = None              # µg/m³
    night: bool = False


@dataclass
class Path:
    """A scenario, step by step, and what it lets out."""
    air: list[float] = field(default_factory=list)
    humidity: list[float] = field(default_factory=list)
    co2: list[float] = field(default_factory=list)
    particles: list[float] = field(default_factory=list)
    lost: float = 0.0           # kWh of heat let out through open windows
    heating: float = 0.0        # kWh the simulated thermostat spends


def candidates(now: Now) -> list[Gesture]:
    """What the room allows: shut what is open, or open what is shut, for a few minutes or for good."""
    if now.opened:
        return [Gesture("nothing"), Gesture("close")]
    return [Gesture("nothing"), Gesture("open", 10), Gesture("open", 20), Gesture("open")]


def _open(gesture: Gesture, now: Now, twins: Twins, k: int):
    if gesture.kind == "nothing":
        return now.opened
    if gesture.kind == "close":
        return ()
    return twins.windows if gesture.minutes is None or k * STEP < gesture.minutes * 60 else ()


def _flow(learned, volume, windows, air, outdoor, wind):
    return learned[0] * leak_flow(volume) + learned[1] * sum(window_flow(a, h, air, outdoor, wind) for a, h in windows)


def simulate(twins: Twins, now: Now, coming: list[tuple[Inputs, float | None]], gesture: Gesture) -> Path:
    """The room under `gesture`, over the coming steps: (inputs, outdoor water g/m³ or None)."""
    path = Path()
    air, walls = now.air, now.walls
    water = reserve = None
    if twins.water and now.humidity is not None:
        water = absolute(now.air, now.humidity)
        reserve = now.reserve if now.reserve is not None else water
    co2, particles = now.co2, now.particles
    for k, (u, outdoor_water) in enumerate(coming):
        windows = _open(gesture, now, twins, k)
        u = replace(u, windows=windows)
        if twins.thermostat:
            u = replace(u, heating=twins.thermostat.power(air, u.outdoor, windows))
            path.heating += twins.heat.heat * u.heating * HOURS / 1000
        before = air
        air, walls = step(twins.heat, air, walls, u)
        path.air.append(air)
        if windows:
            out = sum(window_flow(a, h, before, u.outdoor, u.wind) for a, h in windows) * twins.heat.window
            path.lost += max(0.0, conductance(out) * (before - u.outdoor)) * HOURS / 1000
        if water is not None and outdoor_water is not None:
            flow = _flow(twins.water_flow, twins.water.volume, windows, before, u.outdoor, u.wind)
            water, reserve = water_step(twins.water, water, reserve, outdoor_water, flow, u.hour)
            path.humidity.append(relative(air, water))
        if twins.air and co2 is not None:
            co2 = air_step(twins.air, co2, _flow(twins.air_flow, twins.air.volume, windows, before, u.outdoor, u.wind), u.hour)
            path.co2.append(co2)
        if twins.particles and particles is not None:
            flow = _flow(twins.particles_flow, twins.particles.volume, windows, before, u.outdoor, u.wind)
            particles = particles_step(twins.particles, particles, flow, u.hour)
            path.particles.append(particles)
    return path


def cost(path: Path, comfort: Comfort, weights: Weights, gesture: Gesture, night: bool) -> dict[str, float]:
    """Each term of a scenario's cost, and their total."""
    terms = {
        "heat": weights.heat * sum(max(comfort.minimum - t, 0.0, t - comfort.maximum) for t in path.air) * HOURS,
        "humidity": weights.humidity * sum(max(0.0, h - comfort.humidity) for h in path.humidity) * HOURS,
        "co2": weights.co2 * sum(max(0.0, c - comfort.co2) for c in path.co2) * HOURS,
        "particles": weights.particles * sum(max(0.0, p - comfort.particles) for p in path.particles) * HOURS,
        # With a thermostat simulated, what the heating really spends; without, the heat the windows let out.
        "energy": weights.energy * (path.heating if path.heating else path.lost),
        "bother": 0.0 if gesture.kind == "nothing" else weights.bother * (weights.night if night else 1.0),
    }
    terms["total"] = sum(terms.values())
    return terms


@dataclass(frozen=True)
class Decision:
    gesture: Gesture
    gain: float                             # what it saves against « do nothing », in the cost's unit
    rule: str                               # best | nothing | kept | safety
    scenarios: dict                         # gesture → its cost terms, for « Pourquoi ? » and the trace
    paths: dict = field(default_factory=dict, repr=False)


def decide(twins: Twins, now: Now, coming, comfort: Comfort = Comfort(), weights: Weights = Weights(),
           previous: Gesture | None = None, forbidden: frozenset[str] = frozenset()) -> Decision:
    """The gesture to advise. `forbidden`: kinds a safety rule takes away (« open » under the rain, in gusts…)."""
    if "open" in forbidden and now.opened:
        # The rain or the gusts: what is open is shut, whatever it costs.
        return Decision(Gesture("close"), 0.0, "safety", {})
    gestures = [g for g in candidates(now) if g.kind not in forbidden]
    paths = {g: simulate(twins, now, coming, g) for g in gestures}
    costs = {g: cost(paths[g], comfort, weights, g, now.night) for g in gestures}
    nothing = costs[Gesture("nothing")]["total"]
    best = min(gestures, key=lambda g: (costs[g]["total"], g.kind != "nothing"))
    if (previous in costs and previous != best
            and costs[previous]["total"] - costs[best]["total"] < MARGIN * max(costs[previous]["total"], GAIN)):
        best, rule = previous, "kept"
    elif best.kind == "nothing" or nothing - costs[best]["total"] < GAIN:
        best, rule = Gesture("nothing"), "nothing"
    else:
        rule = "best"
    return Decision(best, nothing - costs[best]["total"], rule, costs, paths)
