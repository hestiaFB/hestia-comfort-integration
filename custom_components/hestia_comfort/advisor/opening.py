"""The window open now, seen at work: what the twin said it would do since it was opened, against what was measured.

A window barely open, or tilted, lets through a fraction of the air the twin gives it (Chambre P, 3 November: one leaf
ajar, 0.1 °C lost in twenty minutes with 10 °C outside, the humidity up from 67 to 69 % where the twin forecast −13
points). After a few minutes the measures say how much of the forecast the window really does; the rest of the airing
is judged with that share (CAHIER-MOTEUR.md § 4.1, the gesture under way).
"""
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from .notes import SETTLE_STEPS, case
from .physics.thermal import STEP
from .physics.water import absolute

# The window's work is read from this long after it was first seen open: sooner, a sensor's step is all one sees.
OBSERVE_MINUTES = 10
# The forecast change is read from this much at least (°C; g/m³ of water): smaller, the ratio is noise. The air first,
# its heat free of the room's own sources of water; the water when the air hardly changes (a mild evening).
HEAT_READ, WATER_READ = 0.3, 0.5
# The share is kept within these: a window does nothing at worst, half as much again as forecast at best.
LOWEST, HIGHEST = 0.0, 1.5
# Under this share, the window renews little of the air: said in « Bon à savoir ».
WEAK = 0.5
# Under this share of what it was advised for, an airing does not work: « Refermez », said as measured (Frank, 6 November:
# « le conseil n'est pas efficace, refermez pour ne pas empirer »). Above it, the twin goes on with the share it sees.
INEFFECTIVE = 0.3
# What each subject an airing is advised for is read on (`seen_shares`): the humidity and the mould on the air's water.
READ_ON = {"humidity": "water", "mould": "water", "heat": "heat"}


def failed(subject: str | None, shares: dict, opened: Opened, now: datetime, air: float,
           humidity: float | None, read: dict | None = None) -> dict | None:
    """The airing advised for `subject`, seen at work, when it does less than INEFFECTIVE of its forecast: what was
    measured since it was opened, for the card to say. None while it works, or when it cannot be read yet. `read`: when
    each measure was last sent (`seen_shares`), the minutes said are those of the reading."""
    key = READ_ON.get(subject or "")
    if key is None or key not in shares or shares[key] >= INEFFECTIVE:
        return None
    at = (read or {}).get("humidity" if key == "water" else "air") or now
    minutes = (min(at, now) - opened.since).total_seconds() / 60
    if key == "water":
        if humidity is None or opened.humidity is None:
            return None
        return {"subject": "humidity", "then": opened.humidity, "now": humidity, "minutes": minutes, "share": shares[key]}
    return {"subject": "heat", "then": opened.air, "now": air, "minutes": minutes, "share": shares[key]}


@dataclass(frozen=True)
class Opened:
    """The opening as first seen, with the twin's forecast for it: the windows left as they are, every step from then."""
    since: datetime
    air: float
    humidity: float | None
    forecast_air: tuple[float, ...]
    forecast_humidity: tuple[float, ...] = ()


def seen_shares(opened: Opened, now: datetime, air: float | None, humidity: float | None,
                read: dict | None = None) -> dict[str, float]:
    """The share of the forecast the open window shows since it was opened, read apart on the heat and on the water: 1 as
    forecast, 0 nothing at all. A subject is left out when too soon or when its forecast changes too little to be read.
    Apart, because the twin learns them apart: Chambre P, 6 November, the window did a sixth of the heat forecast and
    half as much water again — scaled on the heat alone, the drying vanished and the twin saw the humidity climb.
    `read`: when each measure (« air », « humidity ») was last sent, None as now. A measure is read against the forecast at
    the time it was sent, and only once sent OBSERVE_MINUTES after the opening: a sensor that reports every half hour
    still shows the room as it was opened (Chambre A, 7 November: 67 % sent at 9 h 24, the window open since 9 h 24, then
    nothing until 63 % at 9 h 56 — at 9 h 39 the airing was judged useless on the first)."""
    if not opened.forecast_air:
        return {}
    read = read or {}

    def step(kind):
        """The forecast step the measure of `kind` stands for, or None when sent too soon after the opening."""
        at = min(read.get(kind) or now, now)
        minutes = (at - opened.since).total_seconds() / 60
        k = int(round(minutes * 60 / STEP)) - 1
        if minutes < OBSERVE_MINUTES or k < 0:
            return None
        return min(k, len(opened.forecast_air) - 1)
    found = {}
    k = step("air")
    if air is not None and k is not None:
        told = opened.forecast_air[k] - opened.air
        if abs(told) >= HEAT_READ:
            found["heat"] = (air - opened.air) / told
    k = step("humidity")
    if humidity is not None and opened.humidity is not None and k is not None and len(opened.forecast_humidity) > k:
        then = absolute(opened.air, opened.humidity)
        # The water is read on both the humidity and the air; without the air, the twin's for that time.
        air_then = air if air is not None else opened.forecast_air[k]
        told = absolute(opened.forecast_air[k], opened.forecast_humidity[k]) - then
        if abs(told) >= WATER_READ:
            found["water"] = (absolute(air_then, humidity) - then) / told
    return {subject: min(HIGHEST, max(LOWEST, share)) for subject, share in found.items()}


def seen_share(opened: Opened, now: datetime, air: float, humidity: float | None) -> float | None:
    """The share of the forecast the open window shows: the heat's when it can be read, the air's water otherwise (the
    air first, its heat free of the room's own sources of water); None when neither can be read yet."""
    shares = seen_shares(opened, now, air, humidity)
    return shares.get("heat", shares.get("water"))


def scaled(twins, share: float, water: float | None = None):
    """The twins with the windows doing this share of what they learned: the heat's, and each air's — the air's by
    `water` when the water was read apart (`seen_shares`), the same air carrying the water, the CO₂ and the rest."""
    air = share if water is None else water

    def flow(pair):
        return (pair[0], pair[1] * air)
    return replace(twins, heat=replace(twins.heat, window=twins.heat.window * share), water_flow=flow(twins.water_flow),
                   air_flow=flow(twins.air_flow), particles_flow=flow(twins.particles_flow), voc_flow=flow(twins.voc_flow))


@dataclass(frozen=True)
class Closed:
    """The airing ended, waiting for the room to settle: when it opened and when it was shut, and the twin's forecasts
    from the opening, every step: for the airing as it was — open that long, then shut — and without it."""
    since: datetime
    shut: datetime
    forecast_air: tuple[float, ...]
    forecast_humidity: tuple[float, ...] = ()
    without_air: tuple[float, ...] = ()
    without_humidity: tuple[float, ...] = ()
    devices: tuple[bool, bool] = (False, False)     # the VMC's fast speed, the purifier, as the forecasts have them

    def due(self, now: datetime) -> bool:
        return now >= self.shut + SETTLE


# An airing is judged this long after it was shut, once the room settled: the walls and the furnishings give back the
# water and the heat the window took from the air (Chambre P, 3 November: the humidity back where it was, or higher,
# after shutting; Frank: « met le à 1 h, je pense que c'est mieux pour l'inertie »). As the night does (advisor/notes.py).
SETTLE = timedelta(minutes=5 * SETTLE_STEPS)


def settling(opened: Opened, shut: datetime, forecast_air, forecast_humidity=(), without_air=(), without_humidity=(),
             devices=(False, False)) -> Closed | None:
    """The airing just shut, kept until it is judged; None when it was too short to say anything, or when the forecasts
    do not reach the moment it is judged (the night's horizon ends at the waking)."""
    if (shut - opened.since).total_seconds() / 60 < OBSERVE_MINUTES:
        return None
    if _step(opened.since, shut + SETTLE) >= min(len(forecast_air), len(without_air)):
        return None
    return Closed(opened.since, shut, tuple(forecast_air), tuple(forecast_humidity), tuple(without_air),
                  tuple(without_humidity), tuple(devices))


def disturbed(closed: Closed, opened, devices, sources) -> bool:
    """Whether something else acted on the room while it settled — a window opened again, the VMC or the purifier
    switched, a shower or a cooking (a humidity source, advisor/decide.py `recent_sources`): the forecasts no longer say
    what the airing did. Nothing is noted, and the night leaves it out too (advisor/notes.py, « ecartes »)."""
    return bool(opened) or tuple(devices) != closed.devices or "humidity" in (sources or {})


def _step(since: datetime, now: datetime) -> int:
    return int(round((now - since).total_seconds() / STEP)) - 1


def closed_cases(closed: Closed, now: datetime, air: float, humidity: float | None) -> dict[str, tuple[float, float]]:
    """The airing judged, the room settled: {subject: (effect announced, effect measured)} of the air (°C) and of its
    water (g/m³), both against the twin without it (advisor/notes.py) — the night's own measures. Kept without waiting
    for the night, so that the next airing is judged on it (Frank, 3 November: « il vient d'apprendre tout seul que
    cette action n'a rien amené ? »). An effect too small to be read says nothing."""
    k = _step(closed.since, now)
    if k < 0 or k >= min(len(closed.forecast_air), len(closed.without_air)):
        return {}
    out = {}
    if (noted := case("heat", closed.since, closed.forecast_air[k], closed.without_air[k], air)):
        out["heat"] = tuple(noted[1:])
    if humidity is not None and k < min(len(closed.forecast_humidity), len(closed.without_humidity)):
        with_it = absolute(closed.forecast_air[k], closed.forecast_humidity[k])
        without = absolute(closed.without_air[k], closed.without_humidity[k])
        if (noted := case("humidity", closed.since, with_it, without, absolute(air, humidity))):
            out["humidity"] = tuple(noted[1:])
    return out
