"""Zone-local needs, opportunities and constraints, independently of commands.

Threshold defaults replay historical settings; they are not health standards.
"""
from dataclasses import asdict, dataclass, field, replace
import math
from datetime import datetime
from typing import Mapping

from .sources import Reading
from .wind import DRIVEN_RAIN_GUST, GUSTY, crossing as wind_crossing, open_first, plan as airflow_plan, side as wind_side
from .outlook import IMMINENT, rain_timing, slot as next_slot
from . import learning, schedule, shower as showers, thermostat as thermostats

# Points above the humidity threshold beyond which a useful drying gesture can be proposed.
HUMIDITY_GRACE = 3
# Water (g/m³) the room must hold above the outdoor air for its humidity to come from inside: below it,
# the humidity is the weather's, and no airing can lower it.
INDOOR_SOURCE = 0.5
# The coldest spot of an outer wall (a corner, a thermal bridge) sits at 70 % of the way from outdoors to
# indoors (EN ISO 13788's fRsi criterion); mould grows where the air touching it stays above 80 %.
WALL_FACTOR = 0.7
MOULD_RH, MOULD_FAST, MOULD_HYSTERESIS = 80.0, 85.0, 3.0
# A peak after a shower or a meal falls by itself: damp walls are said only once it has lasted this long.
MOULD_MINUTES = 60
# Water (g/m³) above the outdoor air from which a stopped ventilation is worth starting: it renews the air
# without a window, so it helps where opening would bring too little to be asked.
VENTILATION_DELTA = 0.8
# Humidity points an already open window must still take off to be worth keeping open.
OPEN_GAIN = 3.0
DRYING_HYSTERESIS = 1.0
# A room under its range with the heating off is first said in « À savoir »; « Rallumez » comes only once it has been
# below the range by more than the room's tolerance for this long, and its twin does not see it warming by itself.
HEAT_MINUTES = 30
# Degrees the twin must see the room gain within the hour for it to be warming by itself (the sun, a neighbour's heat).
WARMING = 0.3
# Reasons that only say « do not open »: with nothing open, they bring nothing and stay off the banner.
QUIET_REASONS = ("open_neutral", "humid_outdoor", "drying_unavailable", "drying_slow", "drying_night", "drying_alone", "opening_blocked", "heat_needed", "cooling_unavailable", "precool_later")
# The air against the cold wall from which « Chauffez un peu plus » is worth asking: a clear risk, not the threshold.
WARM_WALL_SURFACE = 82.0
# Reasons that leave damp walls without a remedy: « Chauffez un peu plus » may then be asked.
WARM_WALL_REASONS = ("drying_slow", "drying_unavailable", "heat_needed", "humid_outdoor", "open_neutral", "within_comfort")
LEVELS = ("calm", "benefit", "action", "urgent", "neutral")
ACTIONS = ("ok", "ouvrir", "fermer", "attendre", "unknown")
# Every reason the engine gives, for the « Raison » diagnostic sensor.
REASONS = ("within_comfort", "rain_open_windows", "opening_blocked", "verify_exterior", "air_needed", "cooling_possible", "warming_possible",
           "drying_possible", "exchange_harmful", "cooling_unavailable", "heat_needed", "drying_unavailable", "drying_later", "drying_slow",
           "drying_night", "drying_alone", "ventilation_possible", "incomplete_data", "optional_air_change", "gust_open_windows",
           "short_air_change", "sun_entering", "rain_soon", "precool_possible", "precool_later", "shared_volume", "humid_outdoor",
           "open_neutral", "rehumidification_risk", "alarm_open", "warm_walls", "voc_outdoor")


@dataclass(frozen=True)
class Settings:
    minimum: float = 20
    maximum: float = 24
    humidity_high: float = 62
    humidity_low: float = 40
    co2_potential: float = 1000
    co2_action: float = 1200
    co2_urgent: float = 1600
    temperature_hysteresis: float = 0.5
    co2_hysteresis: float = 100
    humidity_hysteresis: float = 3
    cooling_delta: float = 1.5
    drying_delta: float = 1.5
    # Many sensors only send a value when it changes: three hours of silence is still a valid reading.
    max_age_seconds: float = 10800
    gust_max: float = 45
    frost: float = 1.0
    sun_facade: float = 250
    pm25_action: float = 25
    illuminance_low: float = 100
    # Upper comfort limit once summer has settled in; `maximum` stays the winter limit.
    summer_maximum: float = 26
    # Degrees under `minimum` the room may stay before « Rallumez le chauffage » is a gesture.
    heating_tolerance: float = 1.0

    def __post_init__(self) -> None:
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
               for v in asdict(self).values()):
            raise ValueError("finite_settings_required")
        if not (5 <= self.minimum < self.maximum <= 40):
            raise ValueError("invalid_temperature_range")
        if not (0 <= self.co2_potential < self.co2_action < self.co2_urgent <= 100000):
            raise ValueError("invalid_co2_thresholds")
        if not (0 <= self.humidity_low < self.humidity_high <= 100):
            raise ValueError("invalid_humidity_threshold")
        if not (0 <= self.temperature_hysteresis < (self.maximum - self.minimum) / 2):
            raise ValueError("invalid_temperature_hysteresis")
        if not (0 <= self.co2_hysteresis < self.co2_action - self.co2_potential):
            raise ValueError("invalid_co2_hysteresis")
        if not (0 <= self.humidity_hysteresis < self.humidity_high):
            raise ValueError("invalid_humidity_hysteresis")
        if min(self.cooling_delta, self.drying_delta, self.max_age_seconds, self.gust_max, self.sun_facade, self.pm25_action, self.illuminance_low) <= 0:
            raise ValueError("positive_settings_required")
        if not -30 <= self.frost <= 15:
            raise ValueError("invalid_frost_threshold")
        if not self.minimum < self.summer_maximum <= 40:
            raise ValueError("invalid_summer_maximum")
        if not 0 <= self.heating_tolerance <= 5:
            raise ValueError("invalid_heating_tolerance")


# Seven-day mean outdoor temperature between which the comfort limit moves from winter to summer.
SEASON_FROM, SEASON_TO = 12.0, 20.0


# The upper limit by season, when the home's season is known (Hestia Weather's, or a season sensor): winter's value,
# summer's, and half-way in spring and autumn.
SEASON_WEIGHTS = {"winter": 0.0, "between": 0.5, "summer": 1.0}


def season_group(name):
    """« summer », « winter », « between » (spring, autumn) or None when the home's season is not known."""
    return None if name is None else name if name in ("summer", "winter") else "between" if name in ("spring", "autumn") else None


def seasonal(settings: "Settings", outdoor_mean: float | None, name: str | None = None) -> tuple["Settings", dict]:
    """Comfort range for the season: the upper limit follows the home's season when it is known, else the recent
    outdoor mean, smoothly.

    Without either, the saved range is kept untouched; nothing is guessed from the calendar.
    """
    summer = max(settings.summer_maximum, settings.maximum)
    group = season_group(name)
    if group:
        weight = SEASON_WEIGHTS[group]
        maximum = round(settings.maximum + weight * (summer - settings.maximum), 1)
        mean = round(outdoor_mean, 1) if outdoor_mean is not None and math.isfinite(outdoor_mean) else None
        return replace(settings, maximum=maximum), {"known": True, "weight": weight, "outdoor_mean": mean, "name": name, "group": group,
                                                    "minimum": settings.minimum, "maximum": maximum}
    if outdoor_mean is None or not math.isfinite(outdoor_mean):
        return settings, {"known": False, "weight": None, "outdoor_mean": None,
                          "minimum": settings.minimum, "maximum": settings.maximum}
    weight = min(1.0, max(0.0, (outdoor_mean - SEASON_FROM) / (SEASON_TO - SEASON_FROM)))
    maximum = round(settings.maximum + weight * (summer - settings.maximum), 1)
    return replace(settings, maximum=maximum), {"known": True, "weight": round(weight, 2),
                                                "outdoor_mean": round(outdoor_mean, 1),
                                                "minimum": settings.minimum, "maximum": maximum}


@dataclass(frozen=True)
class Opening:
    """What the user declared about one opening; nothing is guessed from its name."""
    exposure: str | None = None
    kind: str = "window"
    sheltered: bool = False
    shutter: str = "none"
    cover_entity: str | None = None
    auto_entity: str | None = None
    override_entity: str | None = None
    # The integration that drives the cover with the sun (« adaptive_cover_pro », « cover_automatic », « cover_extender »), when one is recognised.
    driver: str | None = None
    # The window's exact bearing in degrees, when the cover's driver knows it (Adaptive Cover Pro, CoverAutomatic's facade).
    azimuth: float | None = None
    width: float | None = None
    height: float | None = None
    overhang_depth: float | None = None
    overhang_gap: float | None = None


@dataclass(frozen=True)
class Sun:
    elevation: float
    azimuth: float


EXPOSURES = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SO": 225, "O": 270, "NO": 315}
KINDS = ("window", "french", "skylight", "door")
SHELTER_ATTENUATION = 3.0  # Template casquette_att: a roof overhang divides direct sun.


@dataclass(frozen=True)
class Assessment:
    action: str
    level: str
    reason: str
    needs: tuple[str, ...]
    constraints: tuple[str, ...]
    opportunities: tuple[str, ...]
    partial: bool
    missing: tuple[str, ...]
    heating_action: str
    indoor_absolute_humidity: float | None
    outdoor_absolute_humidity: float | None
    temperature_delta: float | None
    coordination: str = "not_connected"
    openings: tuple[dict, ...] = ()
    sun: dict | None = None
    unverified: tuple[str, ...] = ()
    wind_bearing: float | None = None
    crossing: str | None = None
    open_first: tuple[str, ...] = ()
    slot: dict | None = None
    rain_soon_minutes: int | None = None
    features: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def humidity_state(value, settings, previous=None, lasting=False):
    status = "unknown" if value is None else "low" if value < settings.humidity_low else "high" if value > settings.humidity_high else "normal"
    distance = 0 if value is None else max(settings.humidity_low - value, value - settings.humidity_high, 0)
    degree = 0 if distance == 0 else 1 if distance <= 3 else 2 if distance <= 10 else 3
    before = (previous.features.get("humidity") or {}).get("measured") if previous else None
    old_distance = max(settings.humidity_low - before, before - settings.humidity_high, 0) if before is not None else None
    trend = "improving" if old_distance is not None and distance < old_distance - 0.5 else "worsening" if old_distance is not None and distance > old_distance + 0.5 else "stable"
    return {"status": status, "degree": degree, "measured": value, "minimum": settings.humidity_low,
            "maximum": settings.humidity_high, "lasting": lasting if status == "high" else False,
            "trend": trend if value is not None else None}


def absolute_humidity(t: float | None, rh: float | None) -> float | None:
    if t is None or rh is None:
        return None
    return 6.112 * math.exp(17.67 * t / (t + 243.5)) * rh * 2.1674 / (273.15 + t)


def facade_share(exposure: str | None, sun: Sun | None, azimuth: float | None = None) -> float:
    """Share of the sun facing a facade, as in the template: cos(elevation)·cos(azimuth gap).
    An exact bearing, when known, replaces the eight-point exposure."""
    facing = azimuth if azimuth is not None else EXPOSURES.get(exposure)
    if facing is None or sun is None or sun.elevation <= 0:
        return 0.0
    gap = ((sun.azimuth - facing + 540) % 360) - 180
    return max(math.cos(math.radians(sun.elevation)) * math.cos(math.radians(gap)), 0.0)


def facade_irradiance(share: float, sun: Sun | None, solar: float | None) -> float | None:
    """W/m² on a vertical facade from the measured horizontal irradiance; never invented."""
    if solar is None or sun is None:
        return None
    diffuse = solar * 0.15
    direct = 0.0
    if sun.elevation > 5 and solar > 40:
        direct = min(solar / max(math.sin(math.radians(sun.elevation)), 0.09) * share, 850)
    return round(max(direct, diffuse))


# Minutes of a winter airing: short and brisk; and the humidity points it must take off to be asked for.
WINTER_AIRING, WINTER_GAIN = 10, 3.0
# Minutes of an airing on a day of high pollens, for a household that said it is allergic; and how long after the rain
# the air stays washed of them.
POLLEN_AIRING, POLLEN_RINSED = 10, 60


def _benefits(details, openings, settings, ti, hot, cold, heated, te, group=None):
    """What the sun on the windows does for the room now, worth knowing without being a gesture of its own.

    - sun_warms: a heated room in the lower half of its range, the sun on a window: shutters and curtains open;
    - sun_heats: a room above its range, or near its top with a warmer outside, the sun on a shut window whose cover is not driven:
      lowering the shutter or the blind keeps it out. An open window in the sun of a hot room is already a gesture."""
    if ti is None:
        return []
    sunny = [d for d in details if d.get("sun_wm2") is not None and d["sun_wm2"] >= settings.sun_facade]
    middle = (settings.minimum + settings.maximum) / 2
    found = []
    # By season: in winter the sun is always welcome, in summer never sought, in between when the room is cool.
    welcome = group == "winter" or (group != "summer" and (cold or ti < middle))
    if sunny and heated and not hot and welcome:
        found.append({"kind": "sun_warms", "openings": [d["entity_id"] for d in sunny], "watts": max(d["sun_wm2"] for d in sunny),
                      # Colder outside: the window stays shut, the glass lets the warmth in.
                      "keep_shut": te is not None and te < ti})
    # In-between seasons, a sunny afternoon at 24 °C stores warmth for the night: only too hot, or nearly with a warmer outside.
    near_top = group != "winter" and (hot or (ti >= settings.maximum - 1 and (group == "summer" or (te is not None and te >= ti))))
    free = [d for d in sunny if d.get("open") is not True and not getattr(openings.get(d["entity_id"]), "driver", None)]
    if near_top and free and not cold:  # in summer, as soon as the room nears the top of its range
        found.append({"kind": "sun_heats", "openings": [d["entity_id"] for d in free], "watts": max(d["sun_wm2"] for d in free)})
    return found


def assess(readings: Mapping[str, Reading], settings: Settings = Settings(),
           previous: Assessment | None = None, openings: Mapping[str, Opening] | None = None,
           sun: Sun | None = None, outlook: Mapping | None = None, now: datetime | None = None,
           context: Mapping | None = None) -> Assessment:
    def value(key: str):
        reading = readings.get(key)
        return reading.value if reading and reading.usable else None
    openings = openings or {}
    outlook = outlook or {}
    context = context or {}
    # A Versatile Thermostat (engine/thermostat.py): its comfort temperature can stand as the room's minimum.
    thermostat = context.get("thermostat") if isinstance(context.get("thermostat"), Mapping) else None
    # ha-chauffage's next change (engine/schedule.py) comes with it, alone for a heating other than Versatile Thermostat.
    planned = (thermostat or {}).get("next")
    thermostat = thermostat if thermostat and set(thermostat) - {"next"} else None
    comfort = thermostats.reference(thermostat, settings.maximum) if context.get("thermostat_reference") else None
    if comfort is not None:
        try:
            settings = replace(settings, minimum=comfort)
        except ValueError:
            # Too close to the maximum for the hysteresis: the room's own minimum stays.
            comfort = None
    # The upper comfort limit follows the season; a room declared unheated never calls for warmth.
    settings, season = seasonal(settings, context.get("outdoor_mean_7d"), context.get("season_name"))
    group = season.get("group")
    heated = context.get("heated", True) is not False
    ti, te = value("indoor_temperature"), value("outdoor_temperature")
    hi, he, co2 = value("indoor_humidity"), value("outdoor_humidity"), value("co2")
    gust, solar, bearing = value("wind_gust"), value("solar"), value("wind_bearing")
    contacts = {k[7:]: r for k, r in readings.items() if k.startswith("window:")}
    opened = any(r.usable and r.value is True for r in contacts.values())
    closed = bool(contacts) and all(r.usable and r.value is False for r in contacts.values())
    # Rain only concerns openings that are not sheltered, or sheltered but hit by a wind that pushes it in.
    def rained_on(e):
        meta = openings.get(e, Opening())
        driven = wind_side(meta.exposure, bearing) == "windward" and gust is not None and gust >= DRIVEN_RAIN_GUST
        return not meta.sheltered or driven
    exposed = [e for e in contacts if rained_on(e)]
    all_sheltered = bool(contacts) and not exposed
    rain = False if all_sheltered else value("rain")
    pollution = value("pollution")
    # Today's pollens: given by the coordinator only when someone at home said they are allergic.
    pollen = context.get("pollen") if isinstance(context.get("pollen"), Mapping) else None
    pollen_high = bool(pollen and pollen.get("high") is True)
    rinsed = False
    if pollen_high and now is not None and isinstance(context.get("rained_at"), str) and value("rain") is not True:
        try:
            rinsed = 0 <= (now - datetime.fromisoformat(context["rained_at"])).total_seconds() <= POLLEN_RINSED * 60
        except (TypeError, ValueError):
            rinsed = False
    daily_air = readings.get("pollution")
    if daily_air and daily_air.quality == "estimated" and daily_air.value is not None:
        # The daily index the person chose as precaution: above their threshold it blocks,
        # below it the precaution is checked, like an unconfigured one would not block.
        pollution = daily_air.value
    from .evolution import air_features, features, _shade
    # The VOC's own state at the last update: its margin and how long it has stood above (engine/voc.py).
    previous_air = (previous.features.get("air") or {}) if previous else {}
    air_detail = air_features(readings, settings, {**context, "now": now, "voc_was_high": previous_air.get("voc_status") == "high",
                                                   "voc_above_since": previous_air.get("voc_above_since")})
    old = previous.needs if previous else ()
    hot = ti is not None and ti > settings.maximum - (settings.temperature_hysteresis if "cool" in old else 0)
    cold = heated and ti is not None and ti < settings.minimum + (settings.temperature_hysteresis if "heat" in old else 0)
    previous_co2 = previous.features.get("air", {}).get("co2_status") if previous else None
    co2_was_high = previous_co2 == "high" if previous_co2 is not None else "air" in old
    co2_air = co2 is not None and co2 >= settings.co2_action - (settings.co2_hysteresis if co2_was_high else 0)
    air_detail["co2_status"] = ("not_configured" if "co2" not in readings else "unknown" if co2 is None
                               else "high" if co2_air else "ok")
    air = co2_air or (air_detail["pm25_status"] == "high" and not air_detail["pm25_treated"]) or air_detail["voc_status"] == "high"
    # Lasting humidity matters for the explanation and the cold-wall risk, separately from the current degree.
    lasting = context.get("humidity_floor_3h")
    lasting = isinstance(lasting, (int, float)) and not isinstance(lasting, bool) and lasting > settings.humidity_high
    # Rooms open onto each other share one air: its humidity is judged on the mean water of the volume, at its
    # mean temperature, so that the kitchen and the salon never tell two stories. A room clearly wetter than its
    # volume has a local source (steam from cooking, a shower): said, but not a need of the whole air.
    volume = context.get("volume") if isinstance(context.get("volume"), Mapping) else None
    hti, hhi, local = ti, hi, None
    if (volume and all(isinstance(volume.get(k), (int, float)) and not isinstance(volume.get(k), bool) for k in ("water", "temperature"))
            and hi is not None and ti is not None):
        hti = volume["temperature"]
        hhi = min(100.0, volume["water"] / absolute_humidity(hti, 100) * 100)
        local = round(absolute_humidity(ti, hi) - volume["water"], 1)
    humid = hhi is not None and (hhi > settings.humidity_high - settings.humidity_hysteresis if "dry" in old
                                 else hhi > settings.humidity_high + HUMIDITY_GRACE or (hhi > settings.humidity_high and lasting))
    ai, ae = absolute_humidity(hti, hhi), absolute_humidity(te, he)
    # Mould: the relative humidity of the air against the coldest spot of the outer walls, not of the room.
    surface = None
    if ai is not None and te is not None and te < hti:
        surface = min(100.0, ai / absolute_humidity(te + WALL_FACTOR * (hti - te), 100) * 100)
    previous_humidity = (previous.features.get("humidity") or {}) if previous else {}
    # A shower in a room that has one (its « Équipements »): the peak is expected, it starts no mould risk.
    shower = showers.episode(context.get("humidity_history"), now, "shower" in (context.get("equipment") or ()))
    damp = (surface is not None and surface >= MOULD_RH - (MOULD_HYSTERESIS if previous_humidity.get("damp_since") else 0)
            and (lasting or surface >= MOULD_FAST) and not (shower and not previous_humidity.get("damp_since")))
    damp_since = (previous_humidity.get("damp_since") or (now.isoformat() if now else None)) if damp else None
    # Already lasting for three hours, or damp for an hour now: a passing peak is not a mould risk.
    mould = damp and (now is None or lasting or (damp_since is not None
                                                  and (now - datetime.fromisoformat(damp_since)).total_seconds() >= MOULD_MINUTES * 60))
    # Judged on what airing can gain: humidity that comes from inside (shower, cooking, sleep) calls for a gesture;
    # the weather's own humidity does not, however high. Without the outdoor humidity, as before.
    excess = ai - ae if ai is not None and ae is not None else None
    from_inside = excess is None or excess >= INDOOR_SOURCE - (0.3 if "dry" in old else 0)
    humidity_scale = humidity_state(hi, settings, previous, lasting)
    ceiling = context.get("humidity_ceiling_3h")
    if humidity_scale["status"] == "low":
        humidity_scale["lasting"] = isinstance(ceiling, (int, float)) and not isinstance(ceiling, bool) and ceiling < settings.humidity_low
    wet = ((humid and hhi > settings.humidity_high + HUMIDITY_GRACE) or mould) and from_inside
    humid_outdoor = (humid or mould) and not from_inside
    # Pre-cooling (template « prérefroidir »): at night, when tomorrow is announced well above the comfort range.
    tomorrow_max = outlook.get("tomorrow_max")
    night = sun is not None and sun.elevation < 0
    # The season's waking hours (engine/learning.py awake): nobody is asked to open in the middle of the night.
    awake_now, morning = True, None
    if now is not None:
        start, until = learning.awake(context.get("season_name"))
        clock = now.astimezone(context["zone"]) if context.get("zone") else now
        awake_now, morning = start <= clock.hour < until, start
    # The summer evening airing that stores coolness: only until bedtime, never in the middle of the night.
    night = night and awake_now
    precool = (not hot and not cold and not wet and night and ti is not None and isinstance(tomorrow_max, (int, float))
               and tomorrow_max >= settings.maximum + 3 and ti > settings.minimum + 2)
    needs = tuple(k for k, active in (("air", air), ("cool", hot), ("heat", cold), ("dry", wet), ("precool", precool)) if active)
    delta = te - ti if te is not None and ti is not None else None
    cool = delta is not None and delta <= -settings.cooling_delta
    dry = ai is not None and ae is not None and ai - ae >= settings.drying_delta
    # What airing would really bring here, learned from the room's past openings (an ordinary room before
    # that), instead of a full replacement of its air by the outdoor one.
    drying = None
    if wet and dry and ti is not None:
        model = (volume or {}).get("drying_model") or context.get("drying_model")
        model = model if isinstance(model, Mapping) and all(isinstance(model.get(k), (int, float)) for k in ("tau", "residual", "rebound")) else {**learning.DEFAULT, "openings": 0}
        # In winter a short, brisk airing dries without chilling the walls: what ten minutes would bring.
        # A window already open keeps the airing it was given to its end: judged over the room's whole time constant.
        short = WINTER_AIRING if group == "winter" else learning.minutes(model) if opened else None
        # Otherwise until the room is back in its range, or until more minutes would bring next to nothing.
        drying = {**learning.outcome(model, hti, ai, ae, short, target=settings.humidity_high), "tau": model["tau"], "openings": model.get("openings", 0),
                  "later": learning.best_moment(model, hti, ai, ae, outlook.get("hours"), now, zone=context.get("zone"), season=context.get("season_name"),
                                                duration=short) if now and not opened else None}
    # Before opening, an airing must be worth it; once open, it must still bring something to stay open.
    # In winter ten minutes bring less, and are worth repeating: three points are enough to ask for it.
    # Judged against waiting: what the room sheds by itself, windows shut (engine/learning.py alone), is no gain.
    least = OPEN_GAIN if opened else WINTER_GAIN if group == "winter" else learning.MIN_GAIN
    # An airing already asked for is not withdrawn for a tenth of a point: one point of margin.
    if previous is not None and previous.reason == "drying_possible" and not opened:
        least -= DRYING_HYSTERESIS
    worth = drying is not None and drying["net"] >= least
    # Worth it against now, not against waiting: the room gets there by itself, at least half of the way.
    shedding = (drying is not None and not opened and not worth and drying["gain"] >= least
                and drying["gain"] - drying["net"] >= drying["gain"] / 2)
    # Drying waits for the morning: a room damp in the night (sleep, a late shower) often dries back by itself, and
    # nobody gets up to air it. An open window keeps its own advice.
    asleep = wet and not awake_now and not opened
    if asleep and drying is not None:
        drying["morning"] = morning
    windy = gust is not None and gust > settings.gust_max
    frost = te is not None and te <= settings.frost
    heating_running = value("heating") == "heating"

    details = []
    for entity_id, reading in contacts.items():
        meta = openings.get(entity_id, Opening())
        is_open = reading.usable and reading.value is True
        share = facade_share(meta.exposure, sun, meta.azimuth)
        watts = facade_irradiance(share, sun, solar)
        shade, shade_model = _shade(meta, sun)
        if watts is not None and shade_model == "geometry":
            watts = round(watts * (1 - shade))
        elif watts is not None and meta.sheltered:
            watts = round(watts / SHELTER_ATTENUATION)
        flags = []
        facing = wind_side(meta.exposure, bearing)
        if is_open and rain is True and rained_on(entity_id):
            flags.append("rain_exposed")
        if is_open and windy:
            flags.append("gust")
        if is_open and hot and watts is not None and watts >= settings.sun_facade:
            flags.append("sun_entering")
        details.append({"entity_id": entity_id, "open": is_open if reading.usable else None,
                        "exposure": meta.exposure, "kind": meta.kind, "sheltered": meta.sheltered,
                        "sun_share": round(share, 2), "sun_wm2": watts, "wind_side": facing, "flags": flags})
    exposed_open = any("rain_exposed" in d["flags"] for d in details)
    sunny_open = any("sun_entering" in d["flags"] for d in details)

    # Template veto order: rain, gusts, outdoor air, frost, heating. Frost and a running
    # heating only soften the advice: a confirmed air need still gets a short airing.
    storm = outlook.get("storm") is True
    vigilance = (outlook.get("vigilance") or 0) >= 2  # orange or red, from Hestia Weather
    # One rain for the whole home, the same for « open » and for « close »: the station says whether it rains,
    # the radar when it starts. Only a rain due shortly shuts the exposed openings and keeps them shut: within
    # twenty minutes when known to the minute, within the hour when only the hourly forecast says it and nothing
    # measures the rain here. A later rain only bounds the airing.
    soon, precise = rain_timing(outlook.get("rain"), outlook.get("rain_in_hours")) if rain is not True else (None, False)
    rain_measured = "rain" in readings and readings["rain"].usable
    imminent = (soon is not None and not all_sheltered
                and (soon <= IMMINENT if precise else not rain_measured and soon <= 60))
    # Which openings to leave shut when choosing where the air goes through: one the rain reaches (now or
    # within the hour), one facing strong gusts, one letting the sun in while the room is too hot.
    wet_hour = value("rain") is True or (soon is not None and soon <= 60)
    for d in details:
        d["avoid"] = ("rain" if wet_hour and rained_on(d["entity_id"])
                      else "gust" if d["wind_side"] == "windward" and gust is not None and gust >= GUSTY
                      else "sun" if hot and d["sun_wm2"] is not None and d["sun_wm2"] >= settings.sun_facade else None)
    # The storm and the orange vigilance are forecasts. When Hestia Weather's own station measures the rain
    # and the gusts here, it has the last word: dry, calm and no rain within the hour, they only shorten
    # the airing. Without such a station, or with a red vigilance, the forecast still keeps everything shut.
    station = outlook.get("station") or ()
    measured = ("rain_rate" in station and "wind_gust" in station and value("rain") is False
                and gust is not None and not windy and not imminent)
    forecast_only = measured and (outlook.get("vigilance") or 0) < 3
    constraints = tuple(k for k, active in (("rain", rain is True), ("rain_soon", imminent), ("storm", storm), ("vigilance", vigilance), ("gust", windy),
                                            ("pollution", pollution is True), ("frost", frost), ("heating_running", heating_running)) if active)
    hard = [c for c in constraints if c in ("rain", "rain_soon", "gust", "pollution") or (c in ("storm", "vigilance") and not forecast_only)]
    rain_coming = imminent and any(d["open"] and rained_on(d["entity_id"]) for d in details)
    soft = [c for c in constraints if c in ("frost", "heating_running") or (c in ("storm", "vigilance") and forecast_only)]
    # A configured protection that does not answer blocks the advice; one never configured does not.
    # Rain still guards an opening when its sensor stops answering. A daily outdoor-air index that is
    # down (Atmo France outage) behaves like one never configured: the advice stands, the gap is reported.
    checked = (rain is False or ("rain" not in readings and rain is None)) and pollution is not True
    thermal_known = ti is not None and te is not None
    optional_wet_exchange = ai is not None and ae is not None and ae > ai + 1
    # Drying never justifies opening a cold room to a colder outside, nor a hot one to a hotter outside.
    # A warmer outside warms a cold room while it dries: then opening helps twice. Rooms of one air are warmed
    # through their common windows: judged on the air's mean temperature, so that both rooms tell one story.
    warms = te is not None and hti is not None and te - hti > 0.5
    chill = cold and not warms
    heat_in = hot and delta is not None and delta > 0
    # In winter a room is not cooled by opening: a hot room says to turn the heating down (card, « À savoir »).
    useful = air or ((hot or precool) and cool and group != "winter" and not optional_wet_exchange) or (wet and worth and not chill and not heat_in and not asleep)
    # A cold room and a clearly milder outside, as clearly as cooling asks, while someone home is up:
    # the outdoor air warms it for free.
    warming = (cold and delta is not None and delta >= settings.cooling_delta and awake_now
               and context.get("occupied") is not False)
    useful = useful or warming
    # A constraint speaks only where opening would have helped: a cold room under the rain needs no « keep closed ».
    wants_open = air or warming or ((hot or precool) and cool) or (wet and dry and not chill and not heat_in and not asleep)
    opportunities = tuple(k for k, active in (("cool", cool and not optional_wet_exchange), ("dry", dry),
        ("air", co2 is not None and co2 >= settings.co2_potential)) if active) if not hard and not soft else ()
    missing = tuple(sorted(k for k in ({k for k, r in readings.items() if r.source and not r.usable
                                        and not (k == "pollution" and r.quality == "estimated" and r.value is not None)}
                                       | {k for k in ("indoor_temperature", "outdoor_temperature") if value(k) is None})
                           if not (k == "rain" and all_sheltered)))
    partial = bool(set(missing) - {"pollution"})
    urgent = (co2 is not None and co2 >= settings.co2_urgent) or exposed_open or (windy and opened)
    # Pre-cooling is an opportunity for tomorrow, not a problem now.
    level = "urgent" if urgent else "action" if set(needs) - {"precool"} else "benefit" if needs else "neutral" if partial else "calm"
    action, reason = "ok", "within_comfort"
    if exposed_open:
        action, reason = "fermer", "rain_open_windows"
    elif windy and opened:
        action, reason = "fermer", "gust_open_windows"
    elif opened and ("storm" in hard or "vigilance" in hard):
        action, reason, level = "fermer", "opening_blocked", "urgent" if storm else "action"
    elif rain_coming:
        action, reason, level = "fermer", "rain_soon", "action"
    elif hard and (opened or wants_open or not closed):
        # Windows not known to be shut still hear the constraint: Hestia-FB cannot tell all is well.
        # Only outdoor air reaches every opening; rain spares sheltered ones, gusts are handled above.
        action, reason = ("fermer" if opened and pollution is True else "attendre"), "opening_blocked"
        if level in ("calm", "neutral"):
            # A constraint alone, with known closed windows and no need, is not an action need.
            level = "calm" if closed and not partial else "neutral"
    elif opened and not air and delta is not None and ((hot and delta > 0.5) or (cold and delta < -0.5)):
        # A room already out of its range and an open window that pushes it further: no drying justifies it.
        action, reason, level = "fermer", "exchange_harmful", "action"
    elif soft and (air or (wet and dry and not chill and not heat_in and not asleep)):
        # Heating on or frost outside: a short airing still clears stale air or the steam of a shower or a meal.
        action, reason = ("ok" if opened else "ouvrir"), "short_air_change"
    elif soft and opened:
        action, reason, level = "fermer", "opening_blocked", "action"
    elif soft and wants_open and not chill:
        action, reason = "attendre", "opening_blocked"
    elif useful:
        if not checked or not thermal_known:
            action, reason = "unknown", "verify_exterior"
        else:
            action, reason = ("ok" if opened else "ouvrir"), ("air_needed" if air else "cooling_possible" if hot and cool and group != "winter"
                                                             else "precool_possible" if precool and cool
                                                             else "drying_possible" if wet and worth and not chill else "warming_possible")
    elif opened and delta is not None and ((ti >= (settings.minimum + settings.maximum) / 2 and delta > 0.5)
                                          or (heated and ti <= settings.minimum + 1 and delta < -0.5)):
        action, reason = "fermer", "exchange_harmful"
        level = "action"
    elif hot and sunny_open:
        action, reason, level = "fermer", "sun_entering", "action"
    elif hot:
        action, reason = "attendre", "cooling_unavailable"
    elif cold:
        # A window letting in warmer air helps a cold room: « Refermez » only when the outside is not warmer.
        action, reason = ("fermer" if opened and (delta is None or delta <= 0) else "ok"), "heat_needed"
    elif wet and drying and drying["later"]:
        action, reason = "attendre", "drying_later"
    elif asleep and worth:
        action, reason = "attendre", "drying_night"
    elif wet and shedding:
        action, reason = "attendre", "drying_alone"
    elif wet and drying:
        action, reason = "attendre", "drying_slow"
    elif wet:
        action, reason = "attendre", "drying_unavailable"
    elif humid_outdoor:
        action, reason = "ok", "humid_outdoor"
    elif precool:
        action, reason = "attendre", "precool_later"
    elif partial:
        action, reason = "unknown", "incomplete_data"
    elif opportunities and not opened and co2 is not None and co2 >= settings.co2_potential and not pollen_high:
        # Pollens high for an allergic household: an airing nothing calls for brings only pollens.
        level, reason = "benefit", "optional_air_change"
    if (opened and optional_wet_exchange and not air and not hard and not soft
            and action != "fermer" and not rain_coming):
        action, reason, level = "fermer", "rehumidification_risk", "action"
    # The VOC climbing since the window was opened: the air outside brings it in, staying open only adds to it.
    if (opened and air_detail.get("voc_rising_open") and not air and not hard and action != "fermer" and not rain_coming
            and reason in ("within_comfort", "open_neutral", "drying_slow", "drying_unavailable", "drying_later", "humid_outdoor")):
        action, reason, level = "fermer", "voc_outdoor", "action"
    # A window the person said is open on purpose at night, to let the cool air in: while it does just that (cooler
    # outside, the room not below its range), it is no oversight. A warmer outside, a room getting too cold or damp
    # still get their « Refermez »: on purpose does not mean right.
    if (context.get("intended_open") and opened and action == "fermer" and reason == "exchange_harmful"
            and delta is not None and delta < 0 and not cold):
        action, reason, level = "ok", "open_neutral", "calm"
    # An open window that neither helps nor harms is neutral: the person may keep it or close it.
    if opened and reason in ("within_comfort", "drying_slow", "drying_unavailable", "drying_later", "humid_outdoor"):
        action, reason = "ok", "open_neutral"
    # The alarm armed with a window open (engine/people.py): away or on holiday, nobody will close it; at night, unless
    # it is the window the person leaves open on purpose to sleep cool. Rain and gusts keep their own words.
    alarm = context.get("alarm") if isinstance(context.get("alarm"), Mapping) else None
    if (opened and alarm and (alarm.get("away") or (alarm.get("night") and not context.get("intended_open")))
            and reason not in ("rain_open_windows", "gust_open_windows")):
        action, reason, level = "fermer", "alarm_open", "urgent" if alarm.get("away") else "action"
    # A cold room speaks only when it points at something: someone at home and the heating switched off.
    occupied = context.get("occupied")
    if not isinstance(occupied, bool) and thermostat:
        # No presence sensor of its own: the presence or motion the thermostat follows.
        occupied = thermostat.get("occupied")
    heating_state = value("heating") if "heating" in readings else None
    # A schedule keeps sending presets to a heating switched off for the summer: nothing comes of it, nothing is said.
    off = (thermostat or {}).get("mode") == "off" if thermostat else heating_state == "off"
    planned = schedule.heard(planned, heated, off, (thermostat or {}).get("off_reason"))
    warmth = {"occupied": occupied if isinstance(occupied, bool) else None,
              "heating": None if "heating" not in readings else "off" if heating_state == "off" else "on" if heating_state in ("heating", "idle") else None}
    if thermostat:
        warmth["thermostat"] = {"name": thermostat.get("name"), "preset": thermostat.get("preset"), "target": thermostat.get("target"),
                                "off_reason": thermostat.get("off_reason"), "lowered": thermostats.lowered(thermostat),
                                "reference": comfort}
    if planned:
        warmth["next"] = planned
    heating = (value("heating") or "unknown") if "heating" in readings else "not_configured"
    flows = context.get("flows") or {}
    first = tuple(open_first(details, flows)) if action == "ouvrir" else ()
    coming = next_slot(outlook.get("hours") or [], now, ti, hot=hot or precool, cool_now=cool, margin=settings.cooling_delta) if now else None
    # A banner speaks only when it brings something: a gesture now, a gesture to undo, a likely wrong reflex
    # (opening when it is hotter outside), a precise later time, or another remedy such as the ventilation.
    # The ventilation brings outdoor air too: it helps where the outdoor air is drier but the window renews little.
    ventilation_off = (air_detail.get("ventilation") or {}).get("on") is False
    if (reason == "drying_slow" or (reason == "drying_unavailable" and excess is not None and excess >= VENTILATION_DELTA)) and ventilation_off:
        reason = "ventilation_possible"
    elif reason == "drying_later" or (reason in ("cooling_unavailable", "precool_later") and coming and coming["kind"] == "open"):
        level = "benefit"
    elif (reason in QUIET_REASONS and action != "fermer" and level != "urgent"
          and not (reason == "cooling_unavailable" and delta is not None and delta > 0)
          # Stale air or a hot room make people open by reflex: warning them off is still useful.
          and not (reason == "opening_blocked" and ("air" in needs or ("cool" in needs and cool)))):
        level = "neutral" if partial or level == "neutral" else "calm"
    if reason == "heat_needed" and action != "fermer":
        # One degree under the range is not worth switching the heating on: only a room clearly and lastingly cold.
        before = ((previous.features.get("warmth") or {}) if previous else {}).get("chilly_since")
        margin = settings.heating_tolerance - (settings.temperature_hysteresis if before else 0)
        chilly = ti is not None and ti < settings.minimum - margin
        chilly_since = (before or (now.isoformat() if now else None)) if chilly else None
        lasting = chilly and (now is None or chilly_since is None
                              or (now - datetime.fromisoformat(chilly_since)).total_seconds() >= HEAT_MINUTES * 60)
        coming = context.get("next_hour_temperature")
        slope = (thermostat or {}).get("slope")
        if not isinstance(coming, (int, float)) and isinstance(slope, (int, float)) and ti is not None:
            # A twin still learning: the slope the thermostat measures, in °C per hour.
            coming = ti + slope
        warming = (isinstance(coming, (int, float)) and not isinstance(coming, bool) and ti is not None
                   and coming >= ti + WARMING)
        warmth.update(chilly_since=chilly_since, tolerance=settings.heating_tolerance, warming=warming,
                      outdoor_warms=opened and warms)
        # Only a heating switched off by hand is the person's to switch back on: a window, the thermostat's own
        # start-stop or a central mode resume by themselves, and an eco or frost preset aims lower on purpose.
        theirs = not thermostat or (thermostat.get("off_reason") in (None, "manual") and not thermostats.lowered(thermostat))
        # Nobody known away is someone maybe home: a cold room never sits under « Rien à faire » for want of a presence sensor.
        asked = warmth["occupied"] is not False and warmth["heating"] == "off" and lasting and not warming and theirs
        level = "action" if asked else "neutral" if partial else "calm"
    # Damp walls that no airing nor running ventilation dries: one or two degrees more warm their coldest spot, and the
    # air touching it falls under the mould threshold. Heating removes no water; it only keeps the walls warm enough.
    # Asked only when it is enough to pass under the threshold, the room staying a degree under its maximum; for a
    # clear risk, not one at the threshold; in waking hours; never against a thermostat lowered on purpose.
    warm_walls = None
    if (mould and surface is not None and surface >= WARM_WALL_SURFACE and awake_now and not thermostats.lowered(thermostat) and ai is not None and te is not None and ti is not None and heated
            and "heating" in readings and occupied is not False and action != "fermer"
            and level not in ("action", "urgent", "benefit") and reason in WARM_WALL_REASONS
            and (air_detail.get("ventilation") or {}).get("on") is not True):
        for degrees in (1, 2):
            if ti + degrees > settings.maximum - 1:
                break
            after = min(100.0, ai / absolute_humidity(te + WALL_FACTOR * (hti + degrees - te), 100) * 100)
            if after < MOULD_RH:
                warm_walls = {"degrees": degrees, "target": round(ti + degrees, 1), "surface": round(surface), "after": round(after)}
                break
    if warm_walls:
        action, reason, level = "ok", "warm_walls", "action"
    # Protections never configured: the advice stands, the card says what Hestia-FB does not watch.
    unverified = tuple(k for k in ("pollution", "rain") if k not in readings and not (k == "rain" and all_sheltered))
    extended = features(readings, settings, context, openings, sun, details,
                        needs, action, reason, now, ai, ae, air_detail)
    extended["season"] = {**season, "heated": heated}
    # Where the air should go through: the card says it under the advice, only while airing is asked.
    extended["airflow"] = airflow_plan(details, flows)
    extended["drying"] = drying
    # An open window letting warmer air into a room under the middle of its range: it does something, it warms.
    extended["open_warms"] = bool(opened and warms and ti is not None and ti < (settings.minimum + settings.maximum) / 2)
    extended["warm_walls"] = warm_walls
    extended["benefits"] = _benefits(details, openings, settings, ti, hot, cold, heated, te, group)
    # Within the heating tolerance a room is « a little cool », not « too cool »: the card says it gently.
    warmth["slight"] = ti is not None and ti >= settings.minimum - settings.heating_tolerance
    extended["warmth"] = warmth if cold else None
    # The schedule's next change, cold or not: the card puts it in « À venir ».
    extended["planned"] = planned
    # The window a Versatile Thermostat saw open, worth saying when no contact of the room says it.
    # Who the room is for and what the alarm says, for the card's « À savoir » (engine/people.py).
    found = context.get("people") if isinstance(context.get("people"), Mapping) else None
    extended["people"] = {"home": list(found.get("home") or []), "away": list(found.get("away") or [])} if found else None
    extended["household"] = {
        # A window left open with nobody (of this room) at home: nobody will think of it.
        "away_open": opened and warmth["occupied"] is False and reason != "alarm_open",
        # Nobody in the room right now, someone at home: the moment for a long airing.
        "empty_room": action == "ouvrir" and (extended.get("presence") or {}).get("state") == "empty" and warmth["occupied"] is not False,
        "sleeping": bool(alarm and alarm.get("night")),
        "alarm": {"name": alarm.get("name"), "state": alarm.get("state"), "armed": alarm.get("armed")} if alarm else None}
    extended["thermostat"] = ({"name": thermostat.get("name"), "window": thermostat.get("window") is True and not opened,
                               "preset": thermostat.get("preset"), "target": thermostat.get("target"), "reference": comfort,
                               "next": planned}
                              if thermostat else None)
    if isinstance(extended.get("humidity"), dict):
        saturated = absolute_humidity(ti, 100) if ti is not None else None
        extended["humidity"].update(
            **humidity_scale,
            surface=None if surface is None else round(surface), mould=mould,
            excess=None if excess is None else round(excess, 1), source="inside" if wet else "outside" if humid_outdoor else None,
            # Water above the shared air of the volume (g/m³): a local source such as cooking steam.
            local=local if local is not None and local >= 1.0 else None, damp_since=damp_since, shower=shower,
            # Where a full airing would bring the room at best: the outdoor water, warmed to the room's temperature.
            reachable=None if ae is None or not saturated else round(min(100.0, ae / saturated * 100)))
    if reason == "drying_possible" and drying:
        extended["ventilation"]["duration_minutes"] = ({"min": 5, "max": WINTER_AIRING} if group == "winter" else
                                                       {"min": max(5, 5 * round(drying["minutes"] * .75 / 5)), "max": drying["minutes"]})
    # High pollens, for a household that said it is allergic (« Réglages généraux »): the airing stays short, best early in
    # the morning or just after the rain. It is never put off: the humidity and the CO₂ come first.
    extended["pollen"] = None
    if pollen_high:
        span = extended["ventilation"].get("duration_minutes")
        if action == "ouvrir" and isinstance(span, dict) and span.get("max", 0) > POLLEN_AIRING:
            extended["ventilation"]["duration_minutes"] = {"min": min(span.get("min", 5), 5), "max": POLLEN_AIRING}
        extended["pollen"] = {"level": pollen.get("level"), "main": pollen.get("main"), "after_rain": rinsed,
                              "airing": action == "ouvrir" or opened}
    # A later rain bounds the airing: the window is shut five minutes before it.
    extended["rain_ahead"] = {"minutes": soon, "precise": precise} if soon is not None else None
    if soon is not None and action == "ouvrir" and soon > IMMINENT:
        span = extended["ventilation"].get("duration_minutes")
        if isinstance(span, dict) and span.get("max", 0) > soon - 5:
            extended["ventilation"]["duration_minutes"] = {"min": min(span["min"], soon - 5), "max": soon - 5}
    # The last 24 hours of the room, widened by the current reading (statistics stop at the last full hour).
    day = context.get("indoor_day_range")
    if (isinstance(day, Mapping) and all(isinstance(day.get(k), (int, float)) and not isinstance(day.get(k), bool) and math.isfinite(day[k]) for k in ("min", "max"))
            and day["min"] <= day["max"]):
        low, high = (min(day["min"], ti), max(day["max"], ti)) if ti is not None else (day["min"], day["max"])
        extended["day_range"] = {"min": round(low, 1), "max": round(high, 1)}
    else:
        extended["day_range"] = None
    # A solar protection opportunity does not change the contact action. Existing
    # room needs and safety reasons retain their original priority.
    if (not constraints and reason == "within_comfort" and level == "calm"
            and any(s["advice"] for s in extended["shutters"])):
        level, reason = "benefit", "shutter_protection"
    return Assessment(action, level, reason, needs, constraints, opportunities, partial, missing,
                      heating, ai, ae, delta, openings=tuple(details), unverified=unverified, wind_bearing=bearing,
                      crossing=wind_crossing(details), open_first=first, slot=coming, rain_soon_minutes=soon,
                      sun={"elevation": round(sun.elevation, 1), "azimuth": round(sun.azimuth, 1)} if sun else None,
                      features=extended)
