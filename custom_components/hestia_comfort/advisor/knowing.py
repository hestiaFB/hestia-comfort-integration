"""« Bon à savoir »: passive advice, made of providers (CAHIER-MOTEUR.md § 14).

Each provider is a small function that receives the room as the advisor sees it and gives zero, one or several tips.
Adding one changes nothing elsewhere: it joins PROVIDERS. A tip holds what it says as a kind and its values; the words
(advisor/words.py) turn it into a sentence, in each language.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .physics.sunlight import bearing_name, sun_hours
from .physics.surface import misted
from .physics.water import absolute
from .pollen import Pollen
from .proof import LIVE_MINUTES, LIVE_SHARE, PROVEN, REINFORCED, SUPPOSED, WATER_GAP

# The sun is said only when it warms the room by this much over the coming hours (°C): the days it changes nothing, its
# line goes (Frank, 3 November: a room with three windows had three sun lines).
SUN_COUNTS = 0.5
# Strong sun: this much horizontal sun forecast on average over the hours the sun is on the window (W/m²); a clear
# autumn noon gives about 450, an overcast sky under 150.
STRONG_SUN = 200.0
# The significant gap of the heat (decide.SIGNIFICANT["heat"]), for a gesture seen to work now.
HEAT_GAP = 1.5


@dataclass(frozen=True)
class Tip:
    kind: str                   # sun · open_warms · open_cools · mist
    values: dict
    subject: str                # heat · light…
    importance: int             # higher first
    until: datetime | None      # shown until then
    level: str = SUPPOSED       # how sure (advisor/proof.py)


@dataclass(frozen=True)
class Window:
    entity_id: str
    bearing: float | None
    sun: tuple[datetime, datetime] | None = None    # when Adaptive Cover Pro sees the sun before it, if it drives it


@dataclass
class RoomView:
    """What the providers know of the room."""
    now: datetime                                   # aware, local
    latitude: float
    longitude: float
    windows: list[Window] = field(default_factory=list)
    sun_forecast: dict = field(default_factory=dict)    # hour (aware datetime) → horizontal sun forecast, W/m²
    air: float | None = None
    minimum: float = 20.0
    maximum: float = 24.0
    # The windows opened since then, when the room's air was this: the gesture under way.
    opened_at: datetime | None = None
    air_at_opening: float | None = None
    humidity: float | None = None                       # %
    coldest_tonight: float | None = None                # °C, the lowest outside forecast before waking up
    glazing: str | None = None                          # the room's coldest glazing (advisor/physics/surface.py), None: double
    bedtime: datetime | None = None                     # the room's next going to bed (advisor/household.py)
    asleep: bool = False
    # What the shutter closed at bedtime keeps by waking up (advisor/decide.py `shutter_tonight`), and the waking hour.
    shutter_night: dict | None = None
    wake: datetime | None = None
    # What the heating does for a room under its range: {"minutes"} until back, or {"air"} reached by the horizon's end
    # (advisor/decide.py `heating_back`).
    heating_back: dict | None = None
    # °C the room would gain by the end of the horizon with its thermostat on again, and that hour (`heating_off`).
    heating_off: float | None = None
    end_hour: int | None = None
    # The set point the room's schedule raises next (ha-chauffage, engine/schedule.py): {"at", "temperature"}.
    heating_planned: dict | None = None
    # The stove at its lowest in a room already warm enough (advisor/decide.py `stove_idle`).
    stove_idle: dict | None = None
    # °C the sun adds to the room over the coming hours (advisor/decide.py `sun_gain`); None when not known.
    sun_gain: float | None = None
    # The outside air, and whether the room's humidity is in question now: a window open, the humidity above its mark, a
    # gesture or a tip for it (`outside_water`).
    outdoor: float | None = None
    outdoor_humidity: float | None = None
    water_matters: bool = False
    # The airing on the banner for the humidity: (the outside's water when it starts, g/m³; its local start). The tip then
    # speaks of that moment, not of now (bilan of 11 November: « Aérez 30 min vers 19 h » beside « aérer n'assèche pas »).
    airing_at: tuple | None = None
    # The share of its forecast the window open now really does (advisor/opening.py), and the humidity when it was opened.
    window_share: float | None = None
    humidity_at_opening: float | None = None
    # The day's high pollens, for an allergic household (advisor/pollen.py); None otherwise.
    pollen: Pollen | None = None


def sun_on_windows(view: RoomView) -> list[Tip]:
    """When the sun is on the room's windows today, still to come or going on, in one line for the whole room, and only
    when it warms the room by SUN_COUNTS at least: supposed by their orientation, reinforced by a strong sun forecast.
    Adaptive Cover Pro's hours, when it drives the window, come before the computed ones."""
    if view.sun_gain is not None and view.sun_gain < SUN_COUNTS:
        return []
    midnight = view.now.replace(hour=0, minute=0, second=0, microsecond=0)
    spans = {}
    for w in view.windows:
        if w.sun is not None:
            stretches = [w.sun]
        elif w.bearing is not None:
            stretches = sun_hours(midnight, view.latitude, view.longitude, w.bearing)
        else:
            continue
        for start, end in stretches:
            if end > view.now:
                direction = bearing_name(w.bearing) if w.bearing is not None else None
                spans.setdefault((direction, start, end), []).append(w.entity_id)
    if not spans:
        return []
    ordered = sorted(spans.items(), key=lambda item: item[0][1])
    strong = False
    for (direction, start, end), entities in ordered:
        hours = [v for h, v in view.sun_forecast.items() if v is not None and start.replace(minute=0) <= h < end]
        strong = strong or (bool(hours) and sum(hours) / len(hours) >= STRONG_SUN)
    # The sides in the order the sun reaches them: « les fenêtres est, sud et ouest ».
    directions = list(dict.fromkeys(direction for (direction, _, _), _ in ordered if direction is not None))
    start, end = min(s for (_, s, _), _ in ordered), max(e for (_, _, e), _ in ordered)
    return [Tip("sun", {"directions": directions, "windows": sum(len(e) for _, e in ordered), "start": start, "end": end,
                        "gain": view.sun_gain}, "light", 1, end, REINFORCED if strong else SUPPOSED)]


def gesture_seen(view: RoomView) -> list[Tip]:
    """A window open for a while that brings the room back toward its range, by a clear change: proven now
    (CAHIER-MOTEUR.md § 4.1) — « Laissez ouvert »."""
    if view.opened_at is None or view.air is None or view.air_at_opening is None:
        return []
    minutes = (view.now - view.opened_at).total_seconds() / 60
    change = view.air - view.air_at_opening
    if minutes < LIVE_MINUTES or abs(change) < LIVE_SHARE * HEAT_GAP:
        return []
    if change > 0 and view.air_at_opening < view.minimum and view.air <= view.maximum:
        kind = "open_warms"
    elif change < 0 and view.air_at_opening > view.maximum and view.air >= view.minimum:
        kind = "open_cools"
    else:
        return []
    return [Tip(kind, {"change": abs(change), "since": view.opened_at}, "heat", 3, None, PROVEN)]


# Misted panes are said this long before going to bed, and during the night.
BEFORE_BED = timedelta(hours=5)


def mist_tonight(view: RoomView) -> list[Tip]:
    """Misted panes tonight: the room's air left as it is, the panes cooled by the coldest hour of the night."""
    evening = view.asleep or (view.bedtime is not None and view.now >= view.bedtime - BEFORE_BED)
    if not evening or None in (view.air, view.humidity, view.coldest_tonight):
        return []
    if not misted(view.air, view.humidity, view.coldest_tonight, view.glazing):
        return []
    return [Tip("mist", {"outdoor": view.coldest_tonight}, "humidity", 2, None, REINFORCED)]


# The shutter closed for the night is worth saying from this much kept at waking up, when the room would wake up under
# its range, or from this much heating saved (kWh): half a gesture's (decide.SIGNIFICANT « energy »). Below, it is
# « Rien à faire » for it too — 0.1 kWh said « Baissez le volet ce soir » under « Rien à faire » (Chambre P, 5 November).
SHUTTER_HEAT, SHUTTER_ENERGY = 0.3, 0.25


def shutter_at_night(view: RoomView) -> list[Tip]:
    """« Baissez le volet cette nuit » in the evening, while it is open: the twin's gain, supposed until nights shut and
    open are compared (CAHIER-MOTEUR.md § 6.7 ter)."""
    found = view.shutter_night
    # Said in the evening only: nobody gets up at night for it.
    evening = not view.asleep and view.bedtime is not None and view.now >= view.bedtime - BEFORE_BED
    if not evening or not found:
        return []
    if found["energy"] >= SHUTTER_ENERGY:
        return [Tip("shutter_night_energy", {"energy": found["energy"]}, "heat", 2, None, SUPPOSED)]
    if found["heat"] >= SHUTTER_HEAT and found["wake"] < view.minimum:
        return [Tip("shutter_night", {"change": found["heat"], "wake": view.wake}, "heat", 2, None, SUPPOSED)]
    return []


def heating_catches_up(view: RoomView) -> list[Tip]:
    """« Le chauffage ramène la pièce à 17 °C vers 12 h 30 », or « Le chauffage réchauffe la pièce : 19,7 °C prévus à
    15 h (21,5 °C visés) »: a room under its range that its heating is bringing back, its own thermostat or the house's
    stove, as the twin simulates it — nothing to do, and the household knows when (Frank, 1 November)."""
    found = view.heating_back
    if found is None:
        return []
    if "minutes" in found:
        at = view.now + timedelta(minutes=found["minutes"])
        at = at.replace(minute=at.minute - at.minute % 5, second=0, microsecond=0)
        return [Tip("heating_back", {"minimum": view.minimum, "at": at}, "heat", 2, at, REINFORCED)]
    return [Tip("heating_rising", {"air": found["air"], "minimum": view.minimum, "hour": view.end_hour}, "heat", 2, None,
                REINFORCED)]


def heating_is_off(view: RoomView) -> list[Tip]:
    """« Chauffage éteint : le rallumer donnerait 1,5 °C de plus d'ici 15 h »: never a gesture, a passive advice (Frank,
    1 November) — the household may heat the room otherwise."""
    if view.heating_off is None or view.asleep:
        return []
    return [Tip("heating_off", {"gain": view.heating_off, "hour": view.end_hour}, "heat", 2, None, REINFORCED)]


# How far ahead the schedule's next warmer slot is said (h): the coming afternoon, not tomorrow's morning at noon.
PLANNED_HOURS = 6


def heating_planned(view: RoomView) -> list[Tip]:
    """« Chauffage prévu à 17 h : 20 °C visés » (issue #42): the room's schedule (ha-chauffage) raises its set point
    soon — kept lower on purpose until then, and the household knows when it warms again. A plan, not a forecast."""
    found = view.heating_planned
    if found is None or view.asleep or not view.now <= found["at"] <= view.now + timedelta(hours=PLANNED_HOURS):
        return []
    return [Tip("heating_planned", {"at": found["at"], "temperature": found["temperature"]}, "heat", 2, found["at"], PROVEN)]


def stove_at_its_lowest(view: RoomView) -> list[Tip]:
    """« Le poêle tourne au minimum : sans lui, la pièce reste au-dessus de 20 °C jusqu'à 18 h », or « … et la pièce
    monte encore » (Frank, 1 November): the stove does not stop by itself. Passive until its share is proven; past the
    household's margin for long enough, « Coupez le poêle » is a gesture (advisor/decide.py)."""
    found = view.stove_idle
    if found is None or view.asleep:
        return []
    if "rise" in found:
        return [Tip("stove_rising", {"change": found["rise"]}, "heat", 2, None, PROVEN)]
    if found["minutes"] is None:
        return [Tip("stove_hold_long", {"minimum": view.minimum, "hour": view.end_hour}, "heat", 2, None, SUPPOSED)]
    at = view.now + timedelta(minutes=found["minutes"])
    at = at.replace(minute=at.minute - at.minute % 5, second=0, microsecond=0)
    return [Tip("stove_hold", {"minimum": view.minimum, "at": at}, "heat", 2, at, SUPPOSED)]


def outside_water(view: RoomView) -> list[Tip]:
    """The outside air in water, not in %: 78 % at 10 °C holds less water than 69 % at 18 °C, and an airing dries the room.
    Without it, the % outside says the opposite of the advice (Frank, 3 November: « sans explication je vais comparer avec
    l'humidité extérieure »). Said when the humidity is in question; a fact of physics, proven."""
    if not view.water_matters or None in (view.air, view.humidity, view.outdoor, view.outdoor_humidity):
        return []
    inside, outside = absolute(view.air, view.humidity), absolute(view.outdoor, view.outdoor_humidity)
    kind = "outside_drier" if outside <= inside - WATER_GAP else "outside_wetter" if outside >= inside + WATER_GAP else "outside_same"
    if view.airing_at is not None and kind != "outside_drier":
        later, at = view.airing_at
        if later is not None and later <= inside - WATER_GAP and at > view.now:
            return [Tip("outside_drier_later", {"at": at, "inside": inside, "outside": later}, "humidity", 3, None, PROVEN)]
        # The airing dries by the room's own water carried away (cooking, breath), not by a drier outside: the tip
        # would contradict the banner, it is left out.
        return []
    return [Tip(kind, {"outdoor": view.outdoor, "outdoor_humidity": view.outdoor_humidity, "inside": inside, "outside": outside},
                "humidity", 3, None, PROVEN)]


def window_weak(view: RoomView) -> list[Tip]:
    """The window open now renews little of the air, measured since it was opened: the reason the advice does not count on
    it (advisor/opening.py) — a leaf ajar, a tilted sash."""
    from .opening import WEAK
    if view.window_share is None or view.window_share >= WEAK or view.opened_at is None or None in (view.air, view.air_at_opening):
        return []
    values = {"since": view.opened_at, "air_then": view.air_at_opening, "air": view.air,
              "humidity_then": view.humidity_at_opening, "humidity": view.humidity}
    return [Tip("open_weak", values, "heat", 4, None, PROVEN)]


def pollen_today(view: RoomView) -> list[Tip]:
    """A day of high pollens, for an allergic household (advisor/pollen.py): airings kept short, best early in the morning;
    just after the rain, the air washed of them is said instead. Proven: Hestia Weather says the day's level."""
    found = view.pollen
    if found is None:
        return []
    if found.after_rain:
        return [Tip("pollen_rain", {}, "air", 4, None, PROVEN)]
    return [Tip("pollen", {"level": found.level, "main": found.main}, "air", 4, None, PROVEN)]


PROVIDERS = [pollen_today, window_weak, outside_water, gesture_seen, mist_tonight, heating_catches_up, heating_planned, heating_is_off, stove_at_its_lowest, shutter_at_night,
             sun_on_windows]


def tips(view: RoomView, providers=None) -> list[Tip]:
    """Every provider's tips, the most important first; a provider that fails never stops the others."""
    out = []
    for provider in providers or PROVIDERS:
        try:
            out.extend(provider(view))
        except Exception:  # noqa: BLE001 - « Bon à savoir » is a plus, never a reason to lose the advice
            continue
    return sorted(out, key=lambda t: -t.importance)
