"""Layers 6 to 8: the gestures a room allows, what each one costs over the coming hours, and the one advised.

Every gesture is simulated on the room's twins with the weather to come; its cost adds up, in readable units, the
discomfort it leaves (degrees out of the range × hours, humidity points × hours, CO₂ and particles above their marks),
the heat it lets out (kWh) and the bother of doing it (more at night). The cheapest is advised only when it beats « do
nothing » by a clear gain, and a gesture already shown stays until another beats it by a margin: one hysteresis, on the
cost, instead of one per threshold (CAHIER-MOTEUR.md § 10, § 11). Safety rules only take gestures away.
"""
from dataclasses import dataclass, field, replace

from .physics.air import AirParams, ParticleParams, air_step, particles_step
from .physics.fit import DEFAULT_RECENT, correction
from .physics.surface import mould_excess
from .physics.thermal import STEP, Inputs, Params, step
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


# Later moments compared with « now »: a gesture an hour or two away is advised as « vers 16 h ».
LATER = (60, 120)


# A device is started for this long (minutes).
DEVICE_MINUTES = (30, 60)
DEVICES = ("boost", "purify")


def candidates(now: Now, twins: Twins | None = None) -> list[Gesture]:
    """What the room allows: shut what is open, or open what is shut, for a few minutes or for good; now or later; and
    start or stop its devices."""
    if now.opened:
        out = [Gesture("nothing"), Gesture("close")] + [Gesture("close", after=a) for a in LATER]
    else:
        out = ([Gesture("nothing"), Gesture("open", 10), Gesture("open", 20), Gesture("open")]
               + [Gesture("open", 10, after=a) for a in LATER])
    for device, running, has in (("boost", now.boosting, twins and twins.boost), ("purify", now.purifying, twins and twins.purifier)):
        if has:
            out += [Gesture(f"{device}_off")] if running else [Gesture(device, m) for m in DEVICE_MINUTES]
    return out


def _running(gesture: Gesture, device: str, now_on: bool, k: int) -> bool:
    """Whether a device runs at step `k` of the scenario."""
    if gesture.kind == device:
        return k * STEP / 60 < gesture.minutes
    return False if gesture.kind == f"{device}_off" else now_on


def _open(gesture: Gesture, now: Now, twins: Twins, k: int):
    if gesture.kind not in ("open", "close", "nothing"):
        return now.opened
    waited = k * STEP / 60 - (gesture.after or 0)
    if gesture.kind == "nothing" or waited < 0:
        return now.opened if gesture.kind != "open" else ()
    if gesture.kind == "close":
        return ()
    return twins.windows if gesture.minutes is None or waited < gesture.minutes else ()


def _flow(learned, volume, windows, air, outdoor, wind):
    return learned[0] * leak_flow(volume) + learned[1] * sum(window_flow(a, h, air, outdoor, wind) for a, h in windows)


def simulate(twins: Twins, now: Now, coming: list[tuple[Inputs, float | None]], gesture: Gesture) -> Path:
    """The room under `gesture`, over the coming steps: (inputs, outdoor water g/m³ or None)."""
    path = Path(heated=twins.thermostat is not None)
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
        u = replace(u, windows=windows, facade=u.facade if facade is None else facade, vent=boost)
        if twins.thermostat:
            # The thermostat reads the room as it is, the twin's trend included.
            felt = path.air[-1] if path.air else now.air
            u = replace(u, heating=twins.thermostat.power(felt, u.outdoor, windows))
            path.heating += twins.heat.heat * u.heating * HOURS / 1000
        before = air
        air, walls = step(twins.heat, air, walls, u)
        path.air.append(air + correction(DEFAULT_RECENT, now.missed, k))
        if windows or boost:
            out = sum(window_flow(a, h, before, u.outdoor, u.wind) for a, h in windows) * twins.heat.window + boost
            path.lost += max(0.0, conductance(out) * (before - u.outdoor)) * HOURS / 1000
        if water is not None and outdoor_water is not None:
            flow = _flow(twins.water_flow, twins.water.volume, windows, before, u.outdoor, u.wind) + boost
            water, reserve = water_step(twins.water, water, reserve, outdoor_water, flow, u.hour)
            path.humidity.append(relative(path.air[-1], water))
            path.mould += mould_excess(path.air[-1], path.humidity[-1], u.outdoor) * HOURS
        if twins.air and co2 is not None:
            co2 = air_step(twins.air, co2, _flow(twins.air_flow, twins.air.volume, windows, before, u.outdoor, u.wind) + boost,
                           u.hour)
            path.co2.append(co2)
        if twins.particles and particles is not None:
            flow = _flow(twins.particles_flow, twins.particles.volume, windows, before, u.outdoor, u.wind) + boost
            particles = particles_step(twins.particles, particles, flow, u.hour, purifier=purify)
            path.particles.append(particles)
        if twins.voc and voc is not None:
            flow = _flow(twins.voc_flow, twins.voc.volume, windows, before, u.outdoor, u.wind) + boost
            voc = particles_step(twins.voc, voc, flow, u.hour)
            path.voc.append(voc)
    return path


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


def significant(idle: Path, chosen: Path, comfort: Comfort, night: bool = False, stricter: float = 1.0) -> list[str]:
    """The subjects on which `chosen` makes a difference worth a gesture, against doing nothing; `stricter` multiplies the
    gaps, unless the night already does more."""
    scale = max(NIGHT_STRICTER if night else 1.0, stricter)
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
    device = gesture.kind.removesuffix("_off")
    return f"{device}:{subject}" if device in DEVICES else subject


def main_subject(scenarios: dict, gesture: Gesture) -> str | None:
    """What a gesture mostly does: the cost term it lowers the most against « do nothing »."""
    nothing, chosen = scenarios.get(Gesture("nothing")), scenarios.get(gesture)
    if gesture.kind == "nothing" or nothing is None or chosen is None:
        return None
    return max(SUBJECTS, key=lambda s: nothing[s] - chosen[s])


@dataclass(frozen=True)
class Decision:
    gesture: Gesture
    gain: float                             # what it saves against « do nothing », in the cost's unit
    rule: str                               # best | nothing | insignificant | kept | safety | unproven
    scenarios: dict                         # gesture → its cost terms, for « Pourquoi ? » and the trace
    paths: dict = field(default_factory=dict, repr=False)
    level: str = PROVEN                     # how sure the effect it rests on is (advisor/proof.py)
    # The gesture the twin found worth it, held back because its effect is not proven enough: a passive advice, to try.
    passive: Gesture | None = None


def decide(twins: Twins, now: Now, coming, comfort: Comfort = Comfort(), weights: Weights = Weights(),
           previous: Gesture | None = None, forbidden: frozenset[str] = frozenset(),
           proof: dict[str, str] | None = None, holidays: bool = False) -> Decision:
    """The gesture to advise. `forbidden`: kinds a safety rule takes away (« open » under the rain, in gusts…).
    `proof`: the level of the windows' effect on each subject (advisor/proof.py); None, all taken as proven."""
    if "open" in forbidden and now.opened:
        # The rain or the gusts: what is open is shut, whatever it costs.
        return Decision(Gesture("close"), 0.0, "safety", {})
    if holidays:
        # Away for days (CAHIER-MOTEUR.md § 11, point 8): only the dwelling counts — frost, humidity, mould.
        comfort = replace(comfort, minimum=FROST_GUARD, maximum=HOLIDAY_MAXIMUM)
    # While the household sleeps, nobody gets up to open a window (Frank, 31 October: « en plein hiver, il y a très peu
    # de chance que je laisse ouvert, même 20 min pour aérer en pleine nuit »; Confort 2.1 had learned it too): the night
    # keeps closing what was left open and the devices; a window for the night is said in the evening (`tonight`).
    gestures = [g for g in candidates(now, twins) if g.kind not in forbidden
                and not (g.kind == "open" and g.minutes is None and "open_long" in forbidden)
                and not (g.kind == "open" and now.night)]
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
             and significant(idle, paths[g], comfort, now.night)]
    best = min(worth, key=order) if worth else Gesture("nothing")
    if ((previous in worth or previous == Gesture("nothing")) and previous != best
            and costs[previous]["total"] - costs[best]["total"] < MARGIN * max(costs[previous]["total"], GAIN)):
        best, rule = previous, "kept"
    elif best.kind != "nothing":
        rule = "best"
    else:
        cheapest = min(gestures, key=order)
        rule = "nothing" if cheapest.kind == "nothing" or nothing - costs[cheapest]["total"] < GAIN else "insignificant"
    gain = nothing - costs[best]["total"]
    if best.kind == "nothing" or proof is None:
        return Decision(best, gain, rule, costs, paths)
    # Only a proven effect sends a gesture to the banner as soon as it is significant; a reinforced one must be clear-cut;
    # a supposed one stays a passive advice (CAHIER-MOTEUR.md § 4.1). The energy a window saves rests on its heat.
    subject = main_subject(costs, best)
    found = proof.get(effect(best, subject), SUPPOSED)
    if found == PROVEN or (found == REINFORCED and significant(paths[Gesture("nothing")], paths[best], comfort, now.night,
                                                                stricter=REINFORCED_STRICTER)):
        return Decision(best, gain, rule, costs, paths, level=found)
    return Decision(Gesture("nothing"), gain, "unproven", costs, paths, level=found, passive=best)


# Away for days, the range becomes the frost guard's: the house kept above 7 °C, never overheated.
FROST_GUARD, HOLIDAY_MAXIMUM = 7.0, 30.0


# « Cette nuit, pensez à… » (CAHIER-MOTEUR.md § 4, § 13): said in the evening, about the windows at bedtime — the
# room's own, a setting (advisor/household.py).
def _from(path: Path, k: int) -> Path:
    """The scenario from its `k`-th step on."""
    return Path(path.air[k:], path.humidity[k:], path.co2[k:], path.particles[k:], path.voc[k:], path.mould, path.lost,
                path.heating, path.heated)


def tonight(twins: Twins, now: Now, coming, bedtime_minutes: int, comfort: Comfort = Comfort(),
            weights: Weights = Weights(), proof: dict[str, str] | None = None,
            forbidden: frozenset[str] = frozenset()) -> Decision | None:
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
    if gain < GAIN or not significant(_from(paths[Gesture("nothing")], start), _from(paths[later], start), comfort, night=True):
        return None
    subject = main_subject(costs, later)
    found = PROVEN if proof is None else proof.get("heat" if subject == "energy" else subject, SUPPOSED)
    return Decision(later, gain, "tonight", costs, paths, level=found)
