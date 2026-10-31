"""« Bon à savoir »: passive advice, made of providers (CAHIER-MOTEUR.md § 14).

Each provider is a small function that receives the room as the advisor sees it and gives zero, one or several tips.
Adding one changes nothing elsewhere: it joins PROVIDERS. A tip holds what it says as a kind and its values; the words
(advisor/words.py) turn it into a sentence, in each language.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .physics.sunlight import bearing_name, sun_hours
from .physics.surface import misted
from .proof import LIVE_MINUTES, LIVE_SHARE, PROVEN, REINFORCED, SUPPOSED

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
    bedtime: datetime | None = None                     # the room's next going to bed (advisor/household.py)
    asleep: bool = False
    # What the shutter closed at bedtime keeps by waking up (advisor/decide.py `shutter_tonight`), and the waking hour.
    shutter_night: dict | None = None
    wake: datetime | None = None


def sun_on_windows(view: RoomView) -> list[Tip]:
    """When the sun is on the room's windows today, still to come or going on: supposed by their orientation, reinforced
    by a strong sun forecast. Adaptive Cover Pro's hours, when it drives the window, come before the computed ones."""
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
    tips = []
    for (direction, start, end), entities in sorted(spans.items(), key=lambda item: item[0][1]):
        hours = [v for h, v in view.sun_forecast.items() if v is not None and start.replace(minute=0) <= h < end]
        strong = bool(hours) and sum(hours) / len(hours) >= STRONG_SUN
        tips.append(Tip("sun", {"direction": direction, "windows": len(entities), "start": start, "end": end},
                        "light", 1, end, REINFORCED if strong else SUPPOSED))
    return tips


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
    if not misted(view.air, view.humidity, view.coldest_tonight):
        return []
    return [Tip("mist", {"outdoor": view.coldest_tonight}, "humidity", 2, None, REINFORCED)]


# The shutter closed for the night is worth saying from this much kept at waking up, when the room would wake up under
# its range, or from this much heating saved (kWh).
SHUTTER_HEAT, SHUTTER_ENERGY = 0.1, 0.05


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


PROVIDERS = [gesture_seen, mist_tonight, shutter_at_night, sun_on_windows]


def tips(view: RoomView, providers=None) -> list[Tip]:
    """Every provider's tips, the most important first; a provider that fails never stops the others."""
    out = []
    for provider in providers or PROVIDERS:
        try:
            out.extend(provider(view))
        except Exception:  # noqa: BLE001 - « Bon à savoir » is a plus, never a reason to lose the advice
            continue
    return sorted(out, key=lambda t: -t.importance)
