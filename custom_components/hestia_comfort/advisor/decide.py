"""Layers 6 to 8: the gestures a room allows, what each one costs over the coming hours, and the one advised.

Every gesture is simulated on the room's twins with the weather to come; its cost adds up, in readable units, the
discomfort it leaves (degrees out of the range × hours, humidity points × hours, CO₂ and particles above their marks),
the heat it lets out (kWh) and the bother of doing it (more at night). The cheapest is advised only when it beats « do
nothing » by a clear gain, and a gesture already shown stays until another beats it by a margin: one hysteresis, on the
cost, instead of one per threshold (CAHIER-MOTEUR.md § 10, § 11). Safety rules only take gestures away.
"""
from dataclasses import dataclass, field, replace

from .household import Habits
from .physics.air import AirParams, ParticleParams, air_step, particles_step
from .physics.fit import DEFAULT_RECENT, correction
from .physics.sunlight import bearing_name
from .physics.surface import mould_excess
from .physics.thermal import STEP, Inputs, Params, shutter_insulation, step
from .physics.vents import conductance, leak_flow, window_flow
from .physics.water import WaterParams, absolute, relative, water_step
from .proof import PROVEN, REINFORCED, SUPPOSED

HOURS = STEP / 3600
# A gesture is advised only when it saves at least this much (in the cost's unit, about one degree out of the range for
# one hour), and a gesture shown is replaced only by one cheaper by this share of its cost.
GAIN, MARGIN = 0.5, 0.2


@dataclass(frozen=True)
class Gesture:
    kind: str                   # nothing | close | open
    minutes: int | None = None  # how long an opening lasts; None: until the end of the horizon
    after: int | None = None    # minutes before the gesture: « Refermez vers 16 h », « Aérez vers 14 h »
    target: float | None = None # °C the heating is set back to: « Remettez le chauffage à 19 °C »
    facing: str | None = None   # « open_more »: the side of the windows opened as well (« south »), None if several


@dataclass(frozen=True)
class Comfort:
    """The room's range and marks (SEUILS.md), the person's own."""
    minimum: float = 20.0
    maximum: float = 24.0
    humidity: float = 60.0      # %
    co2: float = 1000.0         # ppm
    particles: float = 15.0     # µg/m³
    voc: float = 150.0          # Sensirion VOC index: 100 is the room's usual air, 150 a worse one, 250 a bad one


# The upper limit moves from winter's to summer's with the home's season, when it is known (the same rule as Confort 2.1,
# engine/assessment.py `seasonal`): half-way in spring and autumn. Without a season, the range is kept as set.
SEASON_WEIGHTS = {"winter": 0.0, "spring": 0.5, "autumn": 0.5, "summer": 1.0}


def for_season(minimum: float, maximum: float, summer_maximum: float | None = None, season: str | None = None,
               **marks) -> Comfort:
    """The room's range as set in Confort, its upper limit for the season; `marks`: humidity, co2, particles."""
    weight = SEASON_WEIGHTS.get(season or "")
    if weight is not None and summer_maximum is not None:
        maximum = round(maximum + weight * (max(summer_maximum, maximum) - maximum), 1)
    return Comfort(minimum=minimum, maximum=maximum, **marks)


def from_thermostat(comfort: Comfort, target: float | None, preset: str | None, comfort_temperature: float | None) -> Comfort:
    """The room's minimum is its thermostat's set point when it has one (CAHIER-MOTEUR.md § 6.8, Confort 2.1's
    `thermostat_reference`): eco lowers it on purpose, the room is then expected cooler. Frost protection is a safeguard,
    not a comfort: the comfort temperature stands instead. Kept only between 5 °C and the range's maximum."""
    found = comfort_temperature if "frost" in (preset or "") or target is None else target
    if found is None or not 5 <= found < comfort.maximum:
        return comfort
    # A thermostat may report 19.00000000000001.
    return replace(comfort, minimum=round(found, 1))


def heating_off(twins: "Twins", now: "Now", coming, comfort: Comfort, tolerance: float = 1.0) -> float | None:
    """°C the room would gain by the end of the horizon with its thermostat on again, when that gain is one a gesture
    would need (`significant`); None otherwise. A passive advice only (CAHIER-MOTEUR.md § 9.1 bis, Frank, 1 November):
    a room heated by something else is never pushed to turn its own heating on."""
    if twins.idle_thermostat is None or twins.thermostat is not None or now.night:
        return None
    # A house heater warming the room (the Salon's stove): it is heated, its own heating is not missed.
    if twins.house_thermostat is not None or (coming and coming[0][0].house_heat * twins.heat.share > 0):
        return None
    idle = simulate(twins, now, coming, Gesture("nothing"))
    on = simulate(twins, now, coming, Gesture("heat_on"))
    if not idle.air or "heat" not in significant(idle, on, comfort, tolerance=tolerance):
        return None
    return on.air[-1] - idle.air[-1]


# A room the heating warms by this much over the horizon is said to be warming up, even short of its range (°C).
WARMING = 0.5


# The stove's flame at its lowest: its thermostat asks this share of the power or less (0 to 1).
STOVE_LOW = 0.1
# The room still warming by this much over the last half hour, the stove at its lowest, is worth saying (°C).
STOVE_RISE = 0.3


def stove_idle(twins: "Twins", now: "Now", coming, minimum: float, hold_hours: float) -> dict | None:
    """The stove burning at its lowest in a room already at its set point (Frank, 1 November: it does not stop by
    itself): {"minutes"} the room stays in its range once it is stopped — None when beyond the horizon — when that is
    at least `hold_hours`; else {"rise"} °C the room still gained over the last half hour, measured. None otherwise.
    A passive advice: the stove's share is learned, and lighting it again has a cost."""
    stove = twins.house_thermostat
    if stove is None or not now.house_running or now.night or now.air < stove.target or twins.house_now > STOVE_LOW:
        return None
    stopped = simulate(twins, now, coming, Gesture("heat_stop"))
    below = next((k for k, air in enumerate(stopped.air) if air < minimum), None)
    minutes = None if below is None else below * STEP / 60
    # Held through the whole horizon counts only when the horizon is as long as the household's hours.
    held = len(stopped.air) * STEP / 60 if minutes is None else minutes
    if stopped.air and held >= hold_hours * 60:
        return {"minutes": minutes}
    if now.house_rise is not None and now.house_rise >= STOVE_RISE:
        return {"rise": now.house_rise}
    return None


def sun_gain(twins: "Twins", now: "Now", coming) -> float:
    """°C the sun adds to the room over the coming steps, at most: the room left as it is, with and without the sun
    (« Bon à savoir » speaks of the sun only when it counts, Frank, 3 November)."""
    if not coming:
        return 0.0
    lit = simulate(twins, now, coming, Gesture("nothing"))
    dark = simulate(twins, now, [(replace(u, sun=0.0, facade=0.0 if u.facade is not None else None,
                                          facade_shut=0.0 if u.facade_shut is not None else None,
                                          facade_all=0.0 if u.facade_all is not None else None), w) for u, w in coming],
                    Gesture("nothing"))
    return max((a - b for a, b in zip(lit.air, dark.air)), default=0.0)


def heating_back(twins: "Twins", idle: "Path", now: "Now", minimum: float, coming=(),
                 step_minutes: float = STEP / 60) -> dict | None:
    """What the heating does for a room under its range, left as it is: {"minutes"} until it is back to its minimum, or,
    short of it by the end of the horizon, {"air"} it will have reached. The room's own thermostat, or a house heater
    warming it (the Salon's stove, `coming` holds its heat). None when the room is not under its range, nothing heats
    it, or it hardly warms."""
    house = twins.house_thermostat is not None or (bool(coming) and coming[0][0].house_heat * twins.heat.share > 0)
    if (twins.thermostat is None and not house) or now.air >= minimum or not idle.air:
        return None
    for k, air in enumerate(idle.air):
        if air >= minimum:
            return {"minutes": (k + 1) * step_minutes}
    if idle.air[-1] - now.air >= WARMING:
        return {"air": idle.air[-1]}
    return None


@dataclass(frozen=True)
class Weights:
    """What one unit of each discomfort costs, in degrees·hours: the three sliders of § 10.3 move them, within bounds."""
    heat: float = 1.0           # per °C·h out of the range
    humidity: float = 0.05      # per point·h above the mark
    co2: float = 0.002          # per ppm·h above the mark
    particles: float = 0.02     # per µg/m³·h above the mark
    voc: float = 0.008          # per index point·h above the mark: 50 points for an hour weigh as 200 ppm of CO₂
    mould: float = 0.1          # per point·h above 80 % at the coldest wall corner (advisor/physics/surface.py)
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


# How many times more air crosses a room open on two sides than its windows let in each on its own (CIBSE AM10: two to
# three times in a moderate wind). The learning counts it too, so the windows' learned effect stays a one-side one.
CROSS = 2.0
# Windows facing sides this far apart (°) let the air cross the room.
CROSS_ANGLE = 60.0


def sides_apart(bearings) -> bool:
    """Whether windows facing these sides (°, None unknown) let the air cross the room."""
    sides = {b for b in bearings if b is not None}
    return any(abs((a - b + 180) % 360 - 180) >= CROSS_ANGLE for a in sides for b in sides)


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
    # The VOC index follows the particles' law: made indoors, let out by the windows, and back toward the room's usual
    # air by itself (the sensor's own 24-hour baseline). Bench of 31 October, kitchen, 10 days: 3-hour error 54 points
    # against 89 for « nothing changes »; 33 airings, −81 measured for −154 forecast in an hour.
    voc: ParticleParams | None = None
    voc_flow: tuple[float, float] = (1.0, 1.0)
    # The room's devices (CAHIER-MOTEUR.md § 9.1): m³/h of outdoor air the VMC's fast speed adds, m³/h of clean air the
    # purifier gives (its filter takes the particles, not the VOC). 0: the room has none.
    boost: float = 0.0
    purifier: float = 0.0
    # With a thermostat, its heating is simulated in every scenario; without, the heating stays as the inputs say.
    thermostat: Thermostat | None = None
    # m² of glass behind the room's connected shutter (CAHIER-MOTEUR.md § 6.7 ter); 0: none.
    shutter_area: float = 0.0
    # The room's thermostat as it would run once turned on again, when it is off with no reason of its own
    # (CAHIER-MOTEUR.md § 9.1 bis): « Rallumez le chauffage ».
    idle_thermostat: Thermostat | None = None
    # The room's main heating when it is a house heater (the Salon's stove, CAHIER-MOTEUR.md § 6.8): its thermostat, its
    # full power (W) and the share of it running now. Simulated as a thermostat in every scenario — it starts again when
    # the room cools — instead of held at the power it had when the advisor looked.
    house_thermostat: Thermostat | None = None
    house_power: float = 0.0
    house_now: float = 0.0
    # The side each window faces (°, in the order of `windows`; None when not declared), and how many times more air
    # crosses the room when windows on two sides are open (CAHIER-MOTEUR.md § 9.1, « ouvrir ici et là »): CIBSE AM10
    # gives two to three times a single-sided opening in a moderate wind. Supposed until the room shows it.
    bearings: tuple = ()
    cross: float = CROSS


@dataclass(frozen=True)
class Now:
    air: float                                  # °C
    walls: float                                # °C, as the twin follows them
    opened: tuple[tuple[float, float], ...]     # the windows open now
    humidity: float | None = None               # %
    reserve: float | None = None                # g/m³, the walls' water
    co2: float | None = None                    # ppm
    particles: float | None = None              # µg/m³
    voc: float | None = None                    # VOC index
    boosting: bool = False                      # the VMC runs at its fast speed
    purifying: bool = False                     # the purifier runs
    night: bool = False
    # What the twin missed over the last hour (°C, measured minus forecast with what really came): the room's trend
    # the twin did not see, carried into every scenario and fading over two hours (advisor/physics/fit.py). Bench of
    # 31 October, 10 days, windows left as they were: it brings the one-hour error down by a fifth to two fifths —
    # Chambre AL open 0.38 → 0.29 °C, salon open 0.23 → 0.13 °C; carried as a slope instead, it does no better.
    missed: float | None = None
    # The connected shutter's position, 0 shut to 1 open, when the household moves it; None: no shutter, or one an
    # automation drives (Adaptive Cover Pro's automatic control): the advisor then proposes nothing on it.
    cover: float | None = None
    # The room's thermostat: heating (on) or not, and the set point it aims at — what « Rallumez » and « Remettez le
    # chauffage à 19 °C » are followed with (advisor/feedback.py).
    heating: bool | None = None
    heating_target: float | None = None
    # The room's main house heater (the Salon's stove): whether it burns — it does not stop by itself, its thermostat
    # only lowers the flame —, °C the room gained over the last half hour, measured, and minutes the room has stayed
    # above its set point by the household's margin (`Habits.overheat`).
    house_running: bool = False
    house_rise: float | None = None
    overheated: float | None = None
    # A source running now that the twin's usual one does not explain (a cooking, a shower, guests, the stove): for each
    # subject, what it adds per hour — ppm of CO₂, µg/m³, VOC index points, g/m³ of water — measured over the last half
    # hour (`recent_sources`), carried into every scenario and fading over SOURCE_HOURS (Frank, 1 November: a cooking
    # going on, the window open, keeps the VOC level; shut, it would climb — « Refermez » was wrong).
    sources: dict | None = None


@dataclass
class Path:
    """A scenario, step by step, and what it lets out."""
    air: list[float] = field(default_factory=list)
    humidity: list[float] = field(default_factory=list)
    co2: list[float] = field(default_factory=list)
    particles: list[float] = field(default_factory=list)
    voc: list[float] = field(default_factory=list)
    mould: float = 0.0          # points·h above the mould's 80 % at the coldest wall corner
    lost: float = 0.0           # kWh of heat let out through open windows
    heating: float = 0.0        # kWh the simulated thermostat spends
    heated: bool = False        # a thermostat was simulated: `heating` is what the gesture really costs

    @property
    def spent(self) -> float:
        """kWh the scenario costs: what the thermostat spends when it is simulated — heat let out of a room the heating
        would not have warmed anyway costs nothing —, otherwise the heat the windows let out."""
        return self.heating if self.heated else self.lost


# The airings, later moments and devices' durations proposed are the household's (advisor/household.py `Habits`).


DEVICES = ("boost", "purify")


def candidates(now: Now, twins: Twins | None = None, habits: Habits = Habits(), comfort: Comfort | None = None) -> list[Gesture]:
    """What the room allows: shut what is open, or open what is shut, for a few minutes or for good; now or later; start
    or stop its devices; set its heating back to the room's minimum (`comfort`). Turning it on again is only a passive
    advice (`heating_off`)."""
    if now.opened:
        # Shut now, in a few minutes (« Laissez ouvert encore 5 min »), or later on.
        afters = sorted(set(habits.airings) | {a for a in habits.later if a > habits.airing_max})
        out = [Gesture("nothing"), Gesture("close")] + [Gesture("close", after=a) for a in afters]
        # The other side opened as well, for the air to cross the room (« Ouvrez aussi la porte-fenêtre »).
        if twins and crossing(twins, twins.windows) > crossing(twins, now.opened):
            shut = [twins.bearings[i] for i, w in enumerate(twins.windows)
                    if w not in now.opened and i < len(twins.bearings) and twins.bearings[i] is not None]
            names = {bearing_name(b) for b in shut}
            facing = names.pop() if len(names) == 1 else None
            out += [Gesture("open_more", m, facing=facing) for m in habits.airings]
    else:
        out = ([Gesture("nothing")] + [Gesture("open", m) for m in habits.airings] + [Gesture("open")]
               + [Gesture("open", m, after=a) for a in habits.later for m in habits.airings])
    for device, running, has in (("boost", now.boosting, twins and twins.boost), ("purify", now.purifying, twins and twins.purifier)):
        if has:
            out += [Gesture(f"{device}_off")] if running else [Gesture(device, m) for m in habits.devices]
    if twins and twins.shutter_area and now.cover is not None:
        out += [Gesture("shutter_close")] if now.cover > SHUTTER_SHUT else []
        out += [Gesture("shutter_open")] if now.cover < SHUTTER_OPEN else []
    if twins and twins.thermostat is not None and comfort is not None and comfort.minimum > twins.thermostat.target + HEAT_STEP:
        out.append(Gesture("heat_to", target=comfort.minimum))
    return out


# A set point this much under the room's minimum is worth setting back (°C): a thermostat's own step is half a degree.
HEAT_STEP = 0.25


def _thermostat(gesture: Gesture, twins: Twins, k: int) -> Thermostat | None:
    """The thermostat that runs at step `k` of the scenario: turned on again, set back, or as it is."""
    if gesture.kind == "heat_on" and twins.idle_thermostat is not None and k * STEP / 60 >= (gesture.after or 0):
        return twins.idle_thermostat
    if gesture.kind == "heat_to" and twins.thermostat is not None:
        return replace(twins.thermostat, target=gesture.target)
    return twins.thermostat


# A shutter under this position is shut, above that one open (0 to 1); shut, it still lets a little light through.
SHUTTER_SHUT, SHUTTER_OPEN, SHUT_SHADE = 0.05, 0.95, 0.05


def _shutter(gesture: Gesture, twins: Twins, u: Inputs, k: int) -> Inputs:
    """The inputs of step `k` under a shutter gesture: its sun and its insulation, from the gesture's moment on."""
    if not gesture.kind.startswith("shutter_") or k * STEP / 60 < (gesture.after or 0):
        return u
    closed = gesture.kind == "shutter_close"
    return replace(u, shade=SHUT_SHADE if closed else 1.0, shutter=shutter_insulation(twins.shutter_area, 1.0 if closed else 0.0))


def _running(gesture: Gesture, device: str, now_on: bool, k: int) -> bool:
    """Whether a device runs at step `k` of the scenario."""
    if gesture.kind == device:
        return k * STEP / 60 < gesture.minutes
    return False if gesture.kind == f"{device}_off" else now_on


def crossing(twins: Twins, windows) -> float:
    """How many times more air the open `windows` let in for crossing the room: `twins.cross` when two of them face
    sides at least CROSS_ANGLE apart, 1 otherwise."""
    sides = [twins.bearings[i] for i, w in enumerate(twins.windows) if i < len(twins.bearings) and w in windows]
    return twins.cross if sides_apart(sides) else 1.0


def _open(gesture: Gesture, now: Now, twins: Twins, k: int):
    if gesture.kind == "open_more":
        # The other windows opened as well for a while, those open now staying open.
        return twins.windows if k * STEP / 60 < gesture.minutes else now.opened
    if gesture.kind not in ("open", "close", "nothing"):
        return now.opened
    waited = k * STEP / 60 - (gesture.after or 0)
    if gesture.kind == "nothing" or waited < 0:
        return now.opened if gesture.kind != "open" else ()
    if gesture.kind == "close":
        return ()
    return twins.windows if gesture.minutes is None or waited < gesture.minutes else ()


def _flow(learned, volume, windows, air, outdoor, wind, cross=1.0):
    return learned[0] * leak_flow(volume) + learned[1] * cross * sum(window_flow(a, h, air, outdoor, wind) for a, h in windows)


# How long a source seen now is carried into the scenarios, fading to nothing (h): a cooking, a shower, a visit. To be
# learned from the sources the room shows (CAHIER-MOTEUR.md § 8).
SOURCE_HOURS = {"co2": 1.5, "voc": 0.75, "particles": 0.5, "humidity": 0.5}


def _extra(now: Now, subject: str, k: int, fade: bool = True) -> float:
    """What the source seen now adds over step `k`."""
    rate = (now.sources or {}).get(subject)
    if not rate:
        return 0.0
    left = max(0.0, 1.0 - k * HOURS / SOURCE_HOURS[subject]) if fade else 1.0
    return rate * HOURS * left


def simulate(twins: Twins, now: Now, coming: list[tuple[Inputs, float | None]], gesture: Gesture,
             fade: bool = True) -> Path:
    """The room under `gesture`, over the coming steps: (inputs, outdoor water g/m³ or None)."""
    path = Path(heated=twins.thermostat is not None or (gesture.kind == "heat_on" and twins.idle_thermostat is not None))
    air, walls = now.air, now.walls
    water = reserve = None
    if twins.water and now.humidity is not None:
        water = absolute(now.air, now.humidity)
        reserve = now.reserve if now.reserve is not None else water
    co2, particles, voc = now.co2, now.particles, now.voc
    for k, (u, outdoor_water) in enumerate(coming):
        windows = _open(gesture, now, twins, k)
        boost = twins.boost if _running(gesture, "boost", now.boosting, k) else 0.0
        purify = twins.purifier if _running(gesture, "purify", now.purifying, k) else 0.0
        # The sun of the scenario's windows: through the glass when shut, more of it through an open sash.
        facade = u.facade_shut if not windows else u.facade_all if windows == twins.windows else None
        cross = crossing(twins, windows) if len(windows) > 1 else 1.0
        u = _shutter(gesture, twins, replace(u, windows=windows, facade=u.facade if facade is None else facade, vent=boost,
                                             cross=cross), k)
        felt = path.air[-1] if path.air else now.air
        if (thermostat := _thermostat(gesture, twins, k)) is not None:
            # The thermostat reads the room as it is, the twin's trend included.
            u = replace(u, heating=thermostat.power(felt, u.outdoor, windows))
            path.heating += twins.heat.heat * u.heating * HOURS / 1000
        if twins.house_thermostat is not None:
            # The stove follows the room too; the other house heaters stay as they are.
            running = 0.0 if gesture.kind == "heat_stop" else twins.house_thermostat.power(felt, u.outdoor, windows)
            u = replace(u, house_heat=max(0.0, u.house_heat + twins.house_power * (running - twins.house_now)))
        before = air
        air, walls = step(twins.heat, air, walls, u)
        path.air.append(air + correction(DEFAULT_RECENT, now.missed, k))
        if windows or boost:
            out = sum(window_flow(a, h, before, u.outdoor, u.wind) for a, h in windows) * twins.heat.window * cross + boost
            path.lost += max(0.0, conductance(out) * (before - u.outdoor)) * HOURS / 1000
        if water is not None and outdoor_water is not None:
            flow = _flow(twins.water_flow, twins.water.volume, windows, before, u.outdoor, u.wind, cross) + boost
            water, reserve = water_step(twins.water, water, reserve, outdoor_water, flow, u.hour)
            water += _extra(now, "humidity", k, fade)
            path.humidity.append(relative(path.air[-1], water))
            path.mould += mould_excess(path.air[-1], path.humidity[-1], u.outdoor) * HOURS
        if twins.air and co2 is not None:
            co2 = air_step(twins.air, co2, _flow(twins.air_flow, twins.air.volume, windows, before, u.outdoor, u.wind, cross) + boost,
                           u.hour) + _extra(now, "co2", k, fade)
            path.co2.append(co2)
        if twins.particles and particles is not None:
            flow = _flow(twins.particles_flow, twins.particles.volume, windows, before, u.outdoor, u.wind, cross) + boost
            particles = particles_step(twins.particles, particles, flow, u.hour, purifier=purify) + _extra(now, "particles", k, fade)
            path.particles.append(particles)
        if twins.voc and voc is not None:
            flow = _flow(twins.voc_flow, twins.voc.volume, windows, before, u.outdoor, u.wind, cross) + boost
            voc = particles_step(twins.voc, voc, flow, u.hour) + _extra(now, "voc", k, fade)
            path.voc.append(voc)
    return path


# A source is said to run when the measure stands this far above what the twin foresaw over the last half hour, with
# what really acted on the room: about twice each sensor's noise (ppm, VOC points, µg/m³, g/m³ of water).
SOURCE_GAP = {"co2": 60.0, "voc": 20.0, "particles": 4.0, "humidity": 0.4}


def recent_sources(twins: Twins, before: Now, acted: list[tuple[Inputs, float | None]], now: Now) -> dict:
    """The sources running now that the twin's usual ones do not explain: from the room as it was (`before`), the
    twin replayed with what acted since (`acted`, one entry per step), set against what is measured `now`. Each is the
    rate that closes the gap, found with the room's own dilution — a window open takes part of a cooking out as it goes.
    Nothing when the windows or the devices changed meanwhile: the gesture, not a source, would explain the gap."""
    if not acted or (before.opened, before.boosting, before.purifying) != (now.opened, now.boosting, now.purifying):
        return {}
    plain = replace(twins, thermostat=None, house_thermostat=None)
    start = replace(before, missed=None, sources=None)
    idle = simulate(plain, start, acted, Gesture("nothing"))
    unit = simulate(plain, replace(start, sources=dict.fromkeys(SOURCE_GAP, 1.0)), acted, Gesture("nothing"), fade=False)
    found = {}
    for subject in ("co2", "voc", "particles"):
        measured, foreseen, moved = getattr(now, subject), getattr(idle, subject), getattr(unit, subject)
        if measured is None or not foreseen or not moved:
            continue
        gap, per_unit = measured - foreseen[-1], moved[-1] - foreseen[-1]
        if gap >= SOURCE_GAP[subject] and per_unit > 0:
            found[subject] = gap / per_unit
    if now.humidity is not None and idle.humidity and unit.humidity:
        # In water (g/m³): the twin's back at its own air, the measure at the air measured — a heat error stays out.
        foreseen = absolute(idle.air[-1], idle.humidity[-1])
        gap = absolute(now.air, now.humidity) - foreseen
        per_unit = absolute(unit.air[-1], unit.humidity[-1]) - foreseen
        if gap >= SOURCE_GAP["humidity"] and per_unit > 0:
            found["humidity"] = gap / per_unit
    return found


# A gesture must be significant (CAHIER-MOTEUR.md § 10.2 bis): a gap one feels at the end of the horizon, or that gap
# spared for two hours (AVOIDED_HOURS). At night the gaps double.
SIGNIFICANT = {"heat": 1.5, "humidity": 5.0, "co2": 200.0, "particles": 5.0, "voc": 50.0, "mould": 5.0, "energy": 0.5}
MARKS = {"humidity": (60.0, 70.0), "co2": (1000.0, 1500.0), "particles": (15.0, 25.0), "voc": (150.0, 250.0)}
NIGHT_STRICTER = 2.0
# A gesture also counts when it spares the room this felt gap for two hours, all along the horizon (°C·h, points·h…):
# a bedroom kept 2.5 °C warmer all night though under its range both ways, a kitchen's VOC kept under its mark for an
# hour after cooking. « Refermez, vous gardez 0,5 °C » for a room just under its range (1.5 °C·h) is still not one.
AVOIDED_HOURS = 2.0


def _beyond_mark(values, low, high) -> float:
    """How far a scenario stays out of [low, high], summed over its steps (°C·h, points·h…)."""
    return sum(max(low - v, 0.0, v - high) for v in values) * HOURS


# An effect only reinforced must be this much clearer (CAHIER-MOTEUR.md § 4.1); it does not add up with the night's.
REINFORCED_STRICTER = 2.0


def significant(idle: Path, chosen: Path, comfort: Comfort, night: bool = False, stricter: float = 1.0,
                tolerance: float = 1.0) -> list[str]:
    """The subjects on which `chosen` makes a difference worth a gesture, against doing nothing; `stricter` multiplies the
    gaps, unless the night already does more; `tolerance`, the household's (`Habits`), multiplies them all."""
    scale = max(NIGHT_STRICTER if night else 1.0, stricter) * tolerance
    found = []
    if idle.air and chosen.air:
        gap = abs(chosen.air[-1] - idle.air[-1])
        spared = (_beyond_mark(idle.air, comfort.minimum, comfort.maximum)
                  - _beyond_mark(chosen.air, comfort.minimum, comfort.maximum))
        if gap >= SIGNIFICANT["heat"] * scale or spared >= AVOIDED_HOURS * SIGNIFICANT["heat"] * scale:
            found.append("heat")
    for subject in ("humidity", "co2", "particles", "voc"):
        before, after = getattr(idle, subject), getattr(chosen, subject)
        if before and after:
            mark = MARKS[subject][0]
            gap = before[-1] - after[-1]
            spared = _beyond_mark(before, float("-inf"), mark) - _beyond_mark(after, float("-inf"), mark)
            if gap >= SIGNIFICANT[subject] * scale or spared >= AVOIDED_HOURS * SIGNIFICANT[subject] * scale:
                found.append(subject)
    # The mould: 5 points of humidity spared at the coldest corner for two hours, night or day (the dwelling does not
    # sleep). Counted in hours of risk, a corner hovering at 80 % made one point of humidity look like hours spared:
    # « Aérez 20 min » at night in the bedrooms, rejeu of 10 days.
    if idle.mould - chosen.mould >= AVOIDED_HOURS * SIGNIFICANT["mould"]:
        found.append("mould")
    # Energy is a subject only where the heating is simulated: without, the heat a window lets out shows as the room's
    # own cooling, already counted on the heat.
    if idle.heated and idle.spent - chosen.spent >= SIGNIFICANT["energy"] * scale:
        found.append("energy")
    return found


def cost(path: Path, comfort: Comfort, weights: Weights, gesture: Gesture, night: bool) -> dict[str, float]:
    """Each term of a scenario's cost, and their total."""
    terms = {
        "heat": weights.heat * sum(max(comfort.minimum - t, 0.0, t - comfort.maximum) for t in path.air) * HOURS,
        "humidity": weights.humidity * sum(max(0.0, h - comfort.humidity) for h in path.humidity) * HOURS,
        "co2": weights.co2 * sum(max(0.0, c - comfort.co2) for c in path.co2) * HOURS,
        "particles": weights.particles * sum(max(0.0, p - comfort.particles) for p in path.particles) * HOURS,
        "voc": weights.voc * sum(max(0.0, v - comfort.voc) for v in path.voc) * HOURS,
        "mould": weights.mould * path.mould,
        "energy": weights.energy * path.spent,
        "bother": 0.0 if gesture.kind == "nothing" else weights.bother * (weights.night if night else 1.0),
    }
    terms["total"] = sum(terms.values())
    return terms


SUBJECTS = ("heat", "humidity", "co2", "particles", "voc", "mould", "energy")


def effect(gesture: Gesture, subject: str) -> str:
    """The effect a gesture rests on, as the proof names it (advisor/proof.py): the windows' on a subject (« heat »), a
    device's (« boost:humidity », « purify:particles »). The energy a gesture saves rests on its heat."""
    # The energy a gesture saves rests on its heat, the mould it spares on its humidity.
    subject = {"energy": "heat", "mould": "humidity"}.get(subject, subject)
    if gesture.kind.startswith("shutter_"):
        return f"shutter:{subject}"
    if gesture.kind.startswith("heat_"):
        return f"heating:{subject}"
    if gesture.kind == "open_more":
        # The crossing air is its own effect: supposed until the room shows it.
        return f"cross:{subject}"
    device = gesture.kind.removesuffix("_off")
    return f"{device}:{subject}" if device in DEVICES else subject


def reference(scenarios: dict, gesture: Gesture) -> Gesture:
    """What a gesture is said against: « do nothing », but « Laissez ouvert encore 10 min » against shutting now. Against
    leaving the window open for hours, it « saved » the heating that shutting saves (Chambre P, 3 November: « 2,4 kWh de
    chauffage économisés » to dry the room, Frank: « pourquoi une économie de chauffage ? »)."""
    if gesture.kind == "close" and gesture.after and Gesture("close") in scenarios:
        return Gesture("close")
    return Gesture("nothing")


def main_subject(scenarios: dict, gesture: Gesture) -> str | None:
    """What a gesture mostly does: the cost term it lowers the most against its `reference`."""
    nothing, chosen = scenarios.get(reference(scenarios, gesture)), scenarios.get(gesture)
    if gesture.kind == "nothing" or nothing is None or chosen is None:
        return None
    return max(SUBJECTS, key=lambda s: nothing[s] - chosen[s])


@dataclass(frozen=True)
class Decision:
    gesture: Gesture
    gain: float                             # what it saves against « do nothing », in the cost's unit
    rule: str                               # best | nothing | insignificant | kept | safety | unproven | overheat
    scenarios: dict                         # gesture → its cost terms, for « Pourquoi ? » and the trace
    paths: dict = field(default_factory=dict, repr=False)
    level: str = PROVEN                     # how sure the effect it rests on is (advisor/proof.py)
    # The gesture the twin found worth it, held back because its effect is not proven enough: a passive advice, to try.
    passive: Gesture | None = None
    # What a rule read on the measures rests on, said as such: « 22,7 °C pour 21,5 °C visés, depuis 35 min ».
    measured: dict | None = None


def aged(gesture: Gesture | None, minutes: float) -> Gesture | None:
    """The gesture shown `minutes` ago, as it stands now: « Laissez ouvert encore 10 min » five minutes later is « encore
    5 min », then « Refermez » — what the hysteresis keeps must count down, not stay at ten."""
    if gesture is None or not gesture.after:
        return gesture
    left = int(round((gesture.after - minutes) / 5) * 5)
    return replace(gesture, after=left if left > 0 else None)


# A gesture shown stays at least this long while it still helps (CAHIER-MOTEUR.md § 18.3: one change per half hour).
HOLD_MINUTES = 30


# Among gestures of one kind, one costing this share more than the best (of its cost, or of GAIN) still counts as enough.
ENOUGH = 0.1


def _shortest(best: Gesture, worth: list[Gesture], costs: dict) -> Gesture:
    """The least of `best`'s kind that is enough: the shortest airing or device run, the soonest shutting or moment —
    not ten minutes when five do (Frank, 1 November)."""
    if best.kind == "nothing":
        return best
    limit = costs[best]["total"] + ENOUGH * max(costs[best]["total"], GAIN)
    # Now or later stays as the best said it; only how long changes, and for a window open, how soon it is shut.
    same = [g for g in worth if g.kind == best.kind and costs[g]["total"] <= limit
            and (g.kind == "close" or (g.after is None) == (best.after is None))]
    return min(same, key=lambda g: (g.minutes is None, g.minutes or 0, g.after or 0)) if same else best


def _outside_held(coming):
    """The coming steps with the outside held as it is now: its temperature, water, wind and sun."""
    if not coming:
        return coming
    u0, w0 = coming[0]
    return [(replace(u, outdoor=u0.outdoor, sun=u0.sun, wind=u0.wind, facade=u0.facade, facade_shut=u0.facade_shut,
                     facade_all=u0.facade_all), w0) for u, _ in coming]


def _for_the_outside(later: Gesture, twins: Twins, now: Now, coming, comfort: Comfort, weights: Weights, costs: dict,
                     night: bool) -> bool:
    """Whether a later airing owes its edge over the same one now to what the outside brings (cooler, drier, the sun gone)
    more than to the room alone. The forecast ends three hours from now: an airing later leaves the room's own CO₂ less
    time to grow back by then, and so always looks better, a moment that recedes at every step and never comes (Salon ·
    Cuisine, 3 November, 15 h to 18 h; Frank: « plus tard » only for what changes outside)."""
    soon = Gesture(later.kind, later.minutes)
    real = (costs[soon]["total"] if soon in costs else cost(simulate(twins, now, coming, soon), comfort, weights, soon, night)["total"]) \
        - costs[later]["total"]
    held = _outside_held(coming)
    own = cost(simulate(twins, now, held, soon), comfort, weights, soon, night)["total"] \
        - cost(simulate(twins, now, held, later), comfort, weights, later, night)["total"]
    return real - own > own


def decide(twins: Twins, now: Now, coming, comfort: Comfort = Comfort(), weights: Weights = Weights(),
           previous: Gesture | None = None, forbidden: frozenset[str] = frozenset(),
           proof: dict[str, str] | None = None, holidays: bool = False, habits: Habits = Habits(),
           held: float | None = None) -> Decision:
    """The gesture to advise. `forbidden`: kinds a safety rule takes away (« open » under the rain, in gusts…).
    `proof`: the level of the windows' effect on each subject (advisor/proof.py); None, all taken as proven.
    `held`: minutes `previous` has been on the card (HOLD_MINUTES)."""
    if "open" in forbidden and now.opened:
        # The rain or the gusts: what is open is shut, whatever it costs.
        return Decision(Gesture("close"), 0.0, "safety", {})
    if holidays:
        # Away for days (CAHIER-MOTEUR.md § 11, point 8): only the dwelling counts — frost, humidity, mould.
        comfort = replace(comfort, minimum=habits.frost_guard, maximum=HOLIDAY_MAXIMUM)
    # While the household sleeps, nobody gets up to open a window, unless it says it would (Frank, 31 October: « en plein
    # hiver, il y a très peu de chance que je laisse ouvert, même 20 min pour aérer en pleine nuit »): the night keeps
    # closing what was left open and the devices; a window for the night is said in the evening (`tonight`).
    pool = candidates(now, twins, habits, comfort)
    # The moment said before, counted down (`aged`), is weighed as it stands: the moments compared are a quarter of an
    # hour apart from now, so « vers 17 h 30 » was never among them and the best moment slid an hour ahead at every step,
    # never to come (Salon · Cuisine, 3 November, 15 h to 18 h).
    if previous is not None and previous.after and previous not in pool:
        pool.append(previous)
    gestures = [g for g in pool if g.kind not in forbidden
                and not (g.kind == "open" and g.minutes is None and "open_long" in forbidden)
                and not (g.kind in ("open", "open_more") and now.night and not habits.open_at_night)
                and not (g.kind == "open_more" and "open" in forbidden)
                # Nobody gets up to see to the heating either (CAHIER-MOTEUR.md § 9.1 bis), nor comes back in ten minutes.
                and not (g.kind.startswith("heat_") and now.night) and not (g.after and now.night)
                # Nor starts or stops a device: the VMC's fast speed was asked all night long (2 November, Chambre P).
                and not (g.kind.removesuffix("_off") in DEVICES and now.night)]
    paths = {g: simulate(twins, now, coming, g) for g in gestures}
    costs = {g: cost(paths[g], comfort, weights, g, now.night) for g in gestures}
    nothing = costs[Gesture("nothing")]["total"]
    idle = paths[Gesture("nothing")]

    def order(g):
        # Between two gestures that cost the same, doing nothing first, then the sooner.
        return round(costs[g]["total"], 3), g.kind != "nothing", g.after or 0
    # A gesture is worth it when it beats doing nothing by a clear gain and makes a difference one feels (§ 10.2 bis); the
    # cheapest of those is advised, not the cheapest of all, which may change nothing one feels (a kitchen's VOC fed by a
    # long cooking: a 10-minute airing hardly shows, opening does).
    worth = [g for g in gestures if g.kind != "nothing" and nothing - costs[g]["total"] >= GAIN
             and significant(idle, paths[g], comfort, now.night, tolerance=habits.tolerance)]
    # An airing later only for what the outside brings: otherwise « Aérez » comes when it is worth it now.
    later = min((g for g in [*worth, previous] if g is not None and g.kind == "open" and g.after and g in costs),
                key=lambda g: costs[g]["total"], default=None)
    if later is not None and not _for_the_outside(later, twins, now, coming, comfort, weights, costs, now.night):
        worth = [g for g in worth if not (g.kind == "open" and g.after)]
        if previous is not None and previous.kind == "open" and previous.after:
            previous = None
    best = min(worth, key=order) if worth else Gesture("nothing")
    best = _shortest(best, worth, costs)
    # Only how long changed (« Aérez 30 → 20 → 25 min » in twelve minutes, 2 November): the duration shown stays while it
    # is about as good, even if, on its own, it no longer makes the difference that would put it forward.
    longer = (previous is not None and previous in costs and best.kind != "nothing" and previous.kind == best.kind
              and previous.after == best.after)
    if ((previous in worth or previous == Gesture("nothing") or longer) and previous != best
            and costs[previous]["total"] - costs[best]["total"] < MARGIN * max(costs[previous]["total"], GAIN)):
        best, rule = previous, "kept"
    elif best.kind != "nothing":
        rule = "best"
    else:
        cheapest = min(gestures, key=order)
        rule = "nothing" if cheapest.kind == "nothing" or nothing - costs[cheapest]["total"] < GAIN else "insignificant"
    gain = nothing - costs[best]["total"]
    stove = twins.house_thermostat
    if (stove is not None and now.house_running and not now.night and "heat_stop" not in forbidden
            # Half a step of slack: the steps are not exactly five minutes apart (1 November, 29 min 44 s at 21 h 13).
            and now.overheated is not None and now.overheated >= habits.overheat_minutes - STEP / 120):
        # The stove does not stop by itself (Frank, 1 November): the room measured above its set point by the household's
        # margin for long enough asks to stop it, before any gesture of the twin. A fact measured, not a forecast.
        stop = Gesture("heat_stop")
        paths[stop] = simulate(twins, now, coming, stop)
        costs[stop] = cost(paths[stop], comfort, weights, stop, now.night)
        return Decision(stop, nothing - costs[stop]["total"], "overheat", costs, paths,
                        measured={"air": now.air, "target": stove.target, "minutes": now.overheated})
    # A gesture on the card stays HOLD_MINUTES while it still helps: it neither leaves for « Rien à faire » nor drops to
    # « À essayer » at the next step, to come back at the one after (Chambre P, 2 November: four times in an hour).
    hold = (previous is not None and previous.kind != "nothing" and held is not None and held < HOLD_MINUTES
            and previous in costs and nothing - costs[previous]["total"] >= GAIN / 2)
    if best.kind == "nothing" and hold:
        best, rule, gain = previous, "kept", nothing - costs[previous]["total"]
    if best.kind == "nothing" or proof is None:
        return Decision(best, gain, rule, costs, paths)
    # Only a proven effect sends a gesture to the banner as soon as it is significant; a reinforced one must be clear-cut;
    # a supposed one stays a passive advice (CAHIER-MOTEUR.md § 4.1). The energy a window saves rests on its heat.
    subject = main_subject(costs, best)
    found = proof.get(effect(best, subject), SUPPOSED)
    if found == PROVEN or (found == REINFORCED and significant(paths[Gesture("nothing")], paths[best], comfort, now.night,
                                                                stricter=REINFORCED_STRICTER, tolerance=habits.tolerance)):
        return Decision(best, gain, rule, costs, paths, level=found)
    if hold and best == previous:
        return Decision(best, gain, "kept", costs, paths, level=found)
    return Decision(Gesture("nothing"), gain, "unproven", costs, paths, level=found, passive=best)


def shutter_tonight(twins: Twins, now: Now, coming, bedtime_minutes: int) -> dict | None:
    """What the shutter closed at bedtime keeps by waking up, against leaving it open (`coming` runs until then): °C of
    the room, kWh of its simulated heating, and the room's air at waking up left as it is. Too small for a gesture at
    night (0.2 to 0.3 °C), it is a passive advice (advisor/knowing.py). None without a shutter the household moves, or
    one already shut."""
    if not twins.shutter_area or now.cover is None or now.cover <= SHUTTER_SHUT or not coming:
        return None
    at_night = replace(now, night=True)
    idle = simulate(twins, at_night, coming, Gesture("nothing"))
    shut = simulate(twins, at_night, coming, Gesture("shutter_close", after=bedtime_minutes))
    return {"heat": shut.air[-1] - idle.air[-1], "energy": idle.spent - shut.spent if idle.heated else 0.0,
            "wake": idle.air[-1]}


# Away for days, the range becomes the frost guard's (`Habits.frost_guard`, 7 °C by default), never overheated.
HOLIDAY_MAXIMUM = 30.0


# « Cette nuit, pensez à… » (CAHIER-MOTEUR.md § 4, § 13): said in the evening, about the windows at bedtime — the
# room's own, a setting (advisor/household.py).
def _from(path: Path, k: int) -> Path:
    """The scenario from its `k`-th step on."""
    return Path(path.air[k:], path.humidity[k:], path.co2[k:], path.particles[k:], path.voc[k:], path.mould, path.lost,
                path.heating, path.heated)


def tonight(twins: Twins, now: Now, coming, bedtime_minutes: int, comfort: Comfort = Comfort(),
            weights: Weights = Weights(), proof: dict[str, str] | None = None,
            forbidden: frozenset[str] = frozenset(), habits: Habits = Habits()) -> Decision | None:
    """What to do with the windows at bedtime, judged over the whole night: `coming` runs from now until waking up,
    `bedtime_minutes` from now. Only the gesture at bedtime is compared with leaving the windows as they are; None when
    there is nothing worth saying. The night's stricter gaps apply (`significant`)."""
    at_night = replace(now, night=True)
    later = Gesture("close", after=bedtime_minutes) if now.opened else Gesture("open", after=bedtime_minutes)
    if later.kind == "open" and forbidden & {"open", "open_long"}:
        return None
    gestures = [Gesture("nothing"), later]
    paths = {g: simulate(twins, at_night, coming, g) for g in gestures}
    costs = {g: cost(paths[g], comfort, weights, g, night=True) for g in gestures}
    gain = costs[Gesture("nothing")]["total"] - costs[later]["total"]
    # Both scenarios are the same until bedtime: what matters is judged from there.
    start = bedtime_minutes * 60 // int(STEP)
    if gain < GAIN or not significant(_from(paths[Gesture("nothing")], start), _from(paths[later], start), comfort, night=True,
                                      tolerance=habits.tolerance):
        return None
    subject = main_subject(costs, later)
    found = PROVEN if proof is None else proof.get("heat" if subject == "energy" else subject, SUPPOSED)
    return Decision(later, gain, "tonight", costs, paths, level=found)
