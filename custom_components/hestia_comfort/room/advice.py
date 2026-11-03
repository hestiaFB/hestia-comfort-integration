"""The 3.0 advisor for one room, or for one shared air (niak-comfort/docs/PASSAGE-CONFORT-3.md § 2).

The room as the advisor sees it is read from Confort's own settings (`spec`): its sensors, its openings and their sizes,
its heatings, its devices and their flows, its range and its household settings. Rooms sharing one air (« Salon ·
Cuisine ») are one room for the advisor, advised by the best equipped of them (`leads`); the others show its decision.

Every five minutes the house's advisor (advisor_home.py) asks the room for its decision: measures checked, twins,
safety, scenarios compared, words. Between two steps a window moved only decides again: the twin's trail does not move.
Taken over from the test Home Assistant's `hestia_advisor_dev` (Engine._advise and its helpers).
"""
from collections import deque
from dataclasses import asdict, replace
from datetime import timedelta
import logging
import re

from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from ..advisor.checks import GOOD, KINDS, Checker
from ..advisor.decide import (SIGNIFICANT, Gesture, Now, Twins, aged, decide, for_season, from_thermostat, heating_back,
                              heating_off, main_subject, recent_sources, shutter_tonight, stove_idle, sun_gain, tonight)
from ..advisor.feedback import declined, follow, pause_until
from ..advisor.household import Habits
from ..advisor.house import Opening as Declared, Room
from ..advisor.knowing import RoomView, Window, tips
from ..advisor.nightly import RoomSpec
from ..advisor.physics.air import AirParams, ParticleParams
from ..advisor.physics.airfit import TWINS, first, values
from ..advisor.physics.fit import HOUR
from ..advisor.physics.thermal import STEP, Params, ordinary, shutter_insulation, step
from ..advisor.physics.water import WaterParams, absolute
from ..advisor.proof import CASES, ORDER, PROVEN, level, live, window_reinforced
from ..advisor.safety import forbidden, holidays
from ..advisor.snapshot import capture
from ..advisor.words import doubt_text, doubtful_air, phrase, tip_text, tonight_text
from ..const import DOMAIN
from ..engine.verdict import COLOURS, HUES, STATES, humidity_label

_LOGGER = logging.getLogger(__name__)

# The facade's bearing from the exposure chosen in Confort.
EXPOSURES = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SO": 225, "SW": 225, "O": 270, "W": 270, "NO": 315, "NW": 315}
# m³/h when the person does not know the flow (« Pour aller plus loin »): the fast speed's real share is learned
# (advisor/nightly.py `boost_scale`).
FLOWS = {"ventilation_boost": 60.0, "purifier": 150.0}
# The share of a house heater (a stove) a room receives before anything is learned.
HOUSE_SHARE = 0.2
# The walls' temperature is kept over a restart this long; older, it is taken back from the air of the last hours (a
# restart just after the stove took the air for the walls: the Salon was forecast 1.5 °C too warm for five hours).
WALLS_KEPT = timedelta(hours=1)
WALLS_HOURS = 6
# By day the advice looks three hours ahead; at night, until waking up.
DAY_STEPS = 36
# A step closer to the last one than this decides without moving the trail (a restart's retries, a tick come early).
STEP_AT_LEAST = timedelta(minutes=4)
VERSION = 1


def _number(hass, entity_id, attribute=None):
    state = hass.states.get(entity_id) if entity_id else None
    if state is None:
        return None
    try:
        return float(state.attributes.get(attribute) if attribute else state.state)
    except (TypeError, ValueError):
        return None


# The gesture as the entities' stable state (engine/verdict.py GESTURES), from the 3.0 advisor's gesture.
GESTURE_KEYS = {"nothing": "none", "open": "open", "open_more": "open", "close": "close", "boost": "ventilation",
                "boost_off": "ventilation", "purify": "ventilation", "purify_off": "ventilation", "shutter_close": "covers",
                "shutter_open": "covers", "heat_on": "heat", "heat_to": "heat", "heat_stop": "heat"}
# « Rien à faire » while a measure stays out of its range or mark (advisor/words.py): « Au mieux », as the card says.
BEYOND = re.compile(r"aucun geste ne ferait vraiment mieux|^(Ouverte ou fermée|Ouverte|Fermée) :", re.IGNORECASE)


def banner_level(result: dict) -> tuple[str, str]:
    """(level, pill) of a 3.0 decision, as the card's banner shows it (card/src/views/advisor3.ts `level3`): orange for a
    gesture, red for safety, green for one to try, blue otherwise (PASSAGE-CONFORT-3.md § 6.4)."""
    rule, gesture = result.get("regle"), result.get("geste") or "nothing"
    if rule == "doubtful":
        return "neutral", "À vérifier"
    if rule == "waiting":
        return "neutral", "Démarrage"
    if rule == "safety":
        return "urgent", "Attention"
    if gesture != "nothing":
        return "action", "Geste conseillé"
    if result.get("a_essayer"):
        return "benefit", "À saisir"
    quiet = rule in ("insignificant", "unproven") or bool(BEYOND.search(result.get("phrase") or ""))
    return "calm", "Au mieux" if quiet else "Tout va bien"


def verdict(result: dict, view: dict) -> dict:
    """The 3.0 decision in the shape the entities and the lights read (engine/verdict.py `verdict`): the card, the
    entities, the lights and the event say the same decision (PASSAGE-CONFORT-3.md principle 3)."""
    found, pill = banner_level(result)
    kind = result.get("geste") or "nothing"
    gesture = "check_sensors" if result.get("regle") == "doubtful" else GESTURE_KEYS.get(kind, "none")
    if result.get("apres") and kind in ("open", "open_more"):
        gesture = "later"
    elif result.get("apres") and kind == "close":
        gesture = "keep_open"
    mood = "best" if pill == "Au mieux" else found
    rgb = COLOURS.get(mood, COLOURS["neutral"])
    try:
        humidity = humidity_label(view)
    except (KeyError, TypeError, ValueError):
        humidity = None
    return {"title": result.get("title") or "", "gesture": gesture, "cap": None, "learned": result.get("preuve"),
            "disk": kind, "pill": pill, "state": STATES.get(pill, found), "level": found, "mood": mood,
            "colour": "#%02x%02x%02x" % rgb, "rgb": list(rgb), "hue": HUES.get(mood), "humidity": humidity}


def leads(coordinator) -> bool:
    """Whether this room advises its shared air: the best equipped of the rooms sharing it, as « Salon · Cuisine » is named."""
    rooms = [(-len(coordinator.config.get("sources", {})), (coordinator.config.get("name") or "").casefold(), coordinator.entry_id),
             *((-p["sources"], p["title"].casefold(), p["entry_id"]) for p in coordinator.partners)]
    return min(rooms)[2] == coordinator.entry_id


def heater_power(hass, entity_id, declared=None):
    """W at full power: declared in Confort, or Versatile Thermostat's own (`power_manager.device_power`)."""
    if declared:
        return float(declared)
    state = hass.states.get(entity_id)
    power = ((state.attributes.get("power_manager") or {}).get("device_power")) if state else None
    return float(power) if isinstance(power, (int, float)) and power > 0 else None


def house_heaters(hass) -> dict:
    """{thermostat: W} of the heaters set « chauffe toute la maison » in any room (a stove), whose power is known."""
    found = {}
    for entry in hass.config_entries.async_entries(DOMAIN):
        for heater in {**entry.data, **entry.options}.get("heaters") or ():
            if isinstance(heater, dict) and heater.get("scope") == "house" and heater.get("entity_id"):
                if power := heater_power(hass, heater["entity_id"], heater.get("power")):
                    found[heater["entity_id"]] = power
    return found


def spec(coordinator, houses: dict) -> dict:
    """The room as the advisor reads it, from Confort's settings: the room's own, then those of the rooms sharing its air."""
    hass = coordinator.hass
    configs = [coordinator.config]
    for partner in coordinator.partners:
        if entry := hass.config_entries.async_get_entry(partner["entry_id"]):
            configs.append({**entry.data, **entry.options})
    own = coordinator.config
    sources = coordinator.sources
    windows, kinds, orientations = {}, {}, {}
    for config in configs:
        sheltered = config.get("rain_exposed") is False
        for entity_id in config.get("windows", []):
            meta = (config.get("openings") or {}).get(entity_id) or {}
            width, height = meta.get("width"), meta.get("height")
            declared = Declared(entity_id, meta.get("kind") or "window", area=width * height if width and height else None, height=height)
            area, high = declared.size
            windows[entity_id], kinds[entity_id] = (area / high, high), declared.kind
            bearing = meta.get("azimuth")
            if bearing is None:
                bearing = EXPOSURES.get(str(meta.get("exposure") or "").upper())
            if bearing is not None:
                orientations[entity_id] = (float(bearing), bool(meta.get("sheltered", sheltered)))
    # The connected shutter of the room's own windows, and whatever drives it with the sun (Adaptive Cover Pro…).
    cover = cover_auto = None
    acp = {}
    drivers = getattr(coordinator, "drivers", None) or {}
    for entity_id, meta in (own.get("openings") or {}).items():
        if meta.get("shutter") != "connected" or not meta.get("cover_entity"):
            continue
        roles = drivers.get(entity_id) or {}
        if cover is None:
            cover, cover_auto = meta["cover_entity"], meta.get("auto_entity") or roles.get("auto")
        if roles.get("sun_start") and roles.get("sun_end"):
            acp[entity_id] = (roles["sun_start"], roles["sun_end"])
    flows = {}
    for config in reversed(configs):
        flows.update({k: v for k, v in (config.get("flows") or {}).items() if v})
    devices = {key: (sources[key], float(flows.get(key) or FLOWS[key])) for key in FLOWS if sources.get(key)}
    # The room's own heating, and the one its range follows when it is a house heater (the Salon follows the stove).
    heaters = [h for config in configs for h in config.get("heaters") or () if isinstance(h, dict) and h.get("entity_id")]
    thermostat = next((h["entity_id"] for h in heaters if h.get("scope") != "house"), None)
    if thermostat is None and sources.get("heating") and sources["heating"] not in houses:
        thermostat = sources["heating"]
    plage = next((c.get("thermostat_plage") for c in configs if c.get("thermostat_plage")), None)
    voc = sources.get("voc")
    # The advisor's VOC twin reads an index (1 to 500, Sensirion's); a sensor in ppb or µg/m³ is left to the 2.1 reading.
    state = hass.states.get(voc) if voc else None
    if state is not None and state.attributes.get("unit_of_measurement") not in (None, ""):
        voc = None
    settings = own.get("settings") or {}
    threshold = ((own.get("evolution") or {}).get("voc_threshold") or {})
    comfort = {"minimum": settings.get("minimum", 20.0), "maximum": settings.get("maximum", 24.0),
               "summer_maximum": settings.get("summer_maximum", 26.0), "humidity": settings.get("humidity_high", 60.0),
               "co2": settings.get("co2_action", 1000.0), "particles": settings.get("pm25_action", 15.0)}
    if voc:
        comfort["voc"] = threshold.get("value") if threshold.get("unit") in (None, "") and threshold.get("value") else 150.0
    built = own.get("room") or {}
    return {"name": coordinator.volume_name or own.get("name") or coordinator.config_entry.title,
            "members": [coordinator.entry_id, *(p["entry_id"] for p in coordinator.partners)],
            "temperature": sources.get("indoor_temperature"), "humidity": sources.get("indoor_humidity"),
            "co2": sources.get("co2"), "particles": sources.get("pm25"), "voc": voc,
            "windows": windows, "kinds": kinds, "orientations": orientations, "cover": cover, "cover_auto": cover_auto, "acp": acp,
            "boost": devices.get("ventilation_boost"), "purifier": devices.get("purifier"),
            "thermostat": thermostat, "thermostat_plage": plage, "thermostat_reference": own.get("thermostat_reference", True) is not False,
            "comfort": comfort, "foyer": own.get("foyer") or {},
            "volume": built["surface"] * built.get("height", 2.5) if built.get("surface") else None,
            "walls": {"heavy": "heavy", "wood": "light"}.get(built.get("wall_material"))}


def first_twins(room: dict, hass, houses: dict) -> dict:
    """The room's twins before anything is learned: ordinary values from what it declares (advisor/house.py); the first
    night relearns them from the recorder's days."""
    declared = Room(room["name"], room["name"], volume=room["volume"], walls=room["walls"],
                    openings=tuple(Declared(e, room["kinds"][e], area=w * h, height=h) for e, (w, h) in room["windows"].items()),
                    heating_power=heater_power(hass, room["thermostat"]) if room["thermostat"] else None)
    heat = ordinary(declared)
    if houses:
        heat = replace(heat, share=HOUSE_SHARE)
    entry = {"heat": asdict(heat), "gestures": {}}
    sensors = {"water": room["humidity"], "air": room["co2"], "particles": room["particles"], "voc": room["voc"]}
    for key, kind, _ in TWINS:
        if sensors[key]:
            entry[key], entry[f"{key}_flow"] = values(kind, first(kind), declared.air)
    return entry


def room_spec(room: dict) -> RoomSpec:
    """The room as the nightly learning reads it."""
    return RoomSpec(room["name"], room["temperature"], dict(room["windows"]), room["humidity"], room["thermostat"],
                    dict(room["orientations"]), room["cover"], room["co2"], room["particles"], room["voc"],
                    room["boost"], room["purifier"])


class RoomAdvisor:
    """One room's (or one shared air's) advisor: its twins, what it remembers between two steps, its decision."""

    def __init__(self, coordinator, home):
        self.coordinator, self.home, self.hass = coordinator, home, coordinator.hass
        self.entry_id = coordinator.entry_id
        self.store = Store(self.hass, VERSION, f"{DOMAIN}.advisor.{self.entry_id}")
        self.room = None
        self.learned, self.learned_at, self.earlier, self.report = None, None, [], None
        self.walls, self.hot_since = None, None
        # The last hour, five minutes at a time: (when, air, walls, what acted on it), for the twin's trend; the last
        # half hour: (when, the room as measured, what acted on it, outdoor water), for the sources running now.
        self.trail, self.air_trail = deque(maxlen=HOUR), deque(maxlen=8)
        # When the windows were opened, and the air and humidity then: the gesture under way (proof.live).
        self.opening = None
        # The gesture shown last: (gesture, when, since when it has been on the card).
        self.previous = None
        # The gesture the card asks for, followed until done or replaced; the gestures put aside by « Pas maintenant ».
        self.asked, self.paused = None, {}
        self.checker, self.sensors = Checker(), {}
        self.shown = None
        self.result = None

    @property
    def slug(self):
        return (self.room or {}).get("name", self.entry_id).lower().replace(" · ", "_").replace(" ", "_")

    def refresh_spec(self):
        self.room = spec(self.coordinator, self.home.houses)
        return self.room

    async def async_load(self):
        """The twins learned and the room's state before the restart (walls, gesture shown), or a fresh start."""
        self.refresh_spec()
        kept = await self.store.async_load() or {}
        self.learned = kept.get("twins") or first_twins(self.room, self.hass, self.home.houses)
        self.learned_at, self.earlier, self.report = kept.get("learned_at"), kept.get("earlier") or [], kept.get("report")
        state = kept.get("state") or {}
        at = dt_util.parse_datetime(state["at"]) if state.get("at") else None
        now = dt_util.utcnow()
        if at and now - at < WALLS_KEPT:
            self.walls = state.get("walls")
            self.hot_since = dt_util.parse_datetime(state["hot_since"]) if state.get("hot_since") else None
            if shown := state.get("shown"):
                self.previous = (Gesture(**shown["gesture"]), dt_util.parse_datetime(shown["at"]), dt_util.parse_datetime(shown["since"]))
            self.paused = {k: until for k, v in (state.get("paused") or {}).items() if (until := dt_util.parse_datetime(v)) and until > now}
        if self.walls is None and self.room["temperature"]:
            self.walls = await self.home.mean_air(self.room["temperature"], now - timedelta(hours=WALLS_HOURS), now)

    def _state(self, now):
        state = {"at": now.isoformat(), "walls": self.walls, "hot_since": self.hot_since.isoformat() if self.hot_since else None,
                 "paused": {k: v.isoformat() for k, v in self.paused.items()}}
        if self.previous:
            gesture, at, since = self.previous
            state["shown"] = {"gesture": asdict(gesture), "at": at.isoformat(), "since": since.isoformat()}
        return state

    async def async_save(self, now):
        await self.store.async_save({"twins": self.learned, "learned_at": self.learned_at, "earlier": self.earlier[-7:],
                                     "report": self.report, "state": self._state(now)})

    async def learned_now(self, entry, now, report):
        """A night's twins: kept, the previous ones remembered a week (PASSAGE-CONFORT-3.md § 2.5)."""
        if self.learned_at:
            self.earlier = [*self.earlier, {"at": self.learned_at, "twins": self.learned}][-7:]
        # Learned for real once a night had enough days to fit the twins (advisor/nightly.py MIN_DAYS), and from then on.
        entry = {**entry, "fitted": bool(entry.get("fitted") or report.get("appris"))}
        self.learned, self.learned_at, self.report = entry, now.isoformat(), report
        await self.async_save(now)

    def knowing(self):
        """What Hestia knows of the room (« Ce que Hestia sait de votre maison », CAHIER-HUB.md § 5.3): each effect it can
        have, with its level of proof, the gestures seen and what is still missing; the share proven; how far the twin
        missed the last hour. The devices' effects are listed before any of their starts was seen."""
        levels = (self.result or {}).get("preuves") or {}
        seen = dict(self.learned.get("gestures") or {}) if self.learned else {}
        if self.room and self.room["boost"]:
            seen.setdefault("boost:humidity", [])
        if self.room and self.room["purifier"]:
            seen.setdefault("purify:particles", [])
        # The heating's effect, learned with the heat twin, for a room with a heating.
        if self.room and (self.room["thermostat"] or self.room["thermostat_plage"]):
            seen.setdefault("heating:heat", [])
        effects = []
        for effect, cases in sorted(seen.items()):
            # The level of the last decision (the moment may reinforce it); before the first one, the gestures seen alone.
            found = levels.get(effect) or (PROVEN if effect == "heating:heat" and self.learned.get("fitted")
                                           else level([(c[-2], c[-1]) for c in cases]))
            forecast = sum(c[-2] for c in cases) / len(cases) if cases else None
            measured = sum(c[-1] for c in cases) / len(cases) if cases else None
            if found == PROVEN:
                missing = None
            elif effect != "heating:heat" and len(cases) < CASES:
                missing = {"gestes": CASES - len(cases)}
            elif effect == "heating:heat":
                missing = {"nuit": True}            # learned with the twin, at the first night with enough days
            else:
                missing = {"ecart": True}           # enough gestures, the twin is not yet right on their size
            effects.append({"effet": effect, "niveau": found, "gestes": len(cases),
                            "prevu": None if forecast is None else round(forecast, 2),
                            "mesure": None if measured is None else round(measured, 2), "manque": missing})
        effects.sort(key=lambda e: (-ORDER.index(e["niveau"]) if e["niveau"] in ORDER else 0, e["effet"]))
        proven = sum(e["niveau"] == PROVEN for e in effects)
        report = self.report or {}
        return {"piece": (self.room or {}).get("name"), "effets": effects,
                "pourcent": round(100 * proven / len(effects)) if effects else 0,
                "ecart_1h": (self.result or {}).get("ecart_1h"), "appris_le": self.learned_at,
                "jours": report.get("jours"), "capteurs": self.sensors}

    def _measures(self, now):
        """The room's measures, each checked (advisor/checks.py): a doubtful one is None, and noted with why."""
        found, doubts, seen = {}, [], {}
        for kind in KINDS:
            entity = self.room.get(kind)
            state = self.hass.states.get(entity) if entity else None
            value = _number(self.hass, entity)
            verdict = self.checker.check(entity, kind, value, state.last_changed if state else None, now) if entity else GOOD
            found[kind] = value if verdict.ok else None
            if entity:
                seen[kind] = {"entite": entity, "valeur": value, "fiable": verdict.ok, "raison": verdict.reason,
                              "depuis": verdict.since.isoformat() if verdict.since else None}
            if not verdict.ok:
                doubts.append({"mesure": kind, "raison": verdict.reason, "valeur": value,
                               "depuis": dt_util.as_local(verdict.since) if verdict.since else None})
        self.sensors = seen
        # The temperature first: without it, no advice.
        doubts.sort(key=lambda d: d["mesure"] != "temperature")
        return found, doubts

    def _on(self, device):
        """Whether a declared device (entity, flow) runs now."""
        state = self.hass.states.get(device[0]) if device else None
        return bool(state and state.state == "on")

    def _missed(self, heat, now, air):
        """What the twin missed over the last hour: the air measured now, minus the twin's forecast from an hour ago
        with what really acted on the room since. None until a whole hour is known (after a restart, a gap)."""
        if len(self.trail) < HOUR or abs((now - self.trail[0][0]).total_seconds() - 3600) > STEP:
            return None
        _, guessed, walls, _ = self.trail[0]
        for *_, acting in self.trail:
            guessed, walls = step(heat, guessed, walls, acting)
        return air - guessed

    def _opening(self, now, opened, air, humidity):
        """(since, air, humidity) of the opening under way, as this step first saw it; None when shut or not seen."""
        if not opened:
            self.opening = None
            return None
        if self.opening is None:
            self.opening = (now, air, humidity)
        return self.opening

    def _proof(self, current, outdoor, outdoor_water):
        """The level of the windows' effect on each subject: learned from the gestures seen, reinforced by the measures of
        the moment (advisor/proof.py)."""
        cases = {s: [(g[-2], g[-1]) for g in found] for s, found in (self.learned.get("gestures") or {}).items()}
        water = absolute(current.air, current.humidity) if current.humidity is not None else None
        measured = {"co2": current.co2 is not None, "particles": current.particles is not None, "voc": current.voc is not None}
        found = {}
        for subject in ("heat", "humidity", "co2", "particles", "voc"):
            moment = window_reinforced(subject, current.air, outdoor, water, outdoor_water, measured.get(subject, True))
            found[subject] = level(cases.get(subject, ()), moment)
            for device in ("boost", "purify"):
                found[f"{device}:{subject}"] = level(cases.get(f"{device}:{subject}", ()), moment)
        # The heating's effect is the heat twin's own, learned each night from its real heating (CAHIER-MOTEUR.md § 9.1 bis):
        # proven once a night has fitted it, not from the ordinary values of a fresh start.
        if self.learned.get("fitted") and self.learned.get("heat"):
            found["heating:heat"] = PROVEN
        return found

    def _seen(self, subject, decision, opening, now, air, humidity):
        """Whether the window open now shows the effect the twin gives it, since it was opened."""
        since, air_then, humidity_then = opening
        idle, chosen = decision.paths[Gesture("nothing")], decision.paths[decision.passive]
        minutes = (now - since).total_seconds() / 60
        if subject == "heat":
            return live(air - air_then, idle.air[-1] - chosen.air[-1], SIGNIFICANT["heat"], minutes)
        if subject == "humidity" and idle.humidity and chosen.humidity and humidity is not None and humidity_then is not None:
            return live(humidity - humidity_then, idle.humidity[-1] - chosen.humidity[-1], SIGNIFICANT["humidity"], minutes)
        return False

    def _good_to_know(self, now, air, opening, comfort, humidity=None, coldest=None, bedtime=None, asleep=False,
                      shutter_night=None, wake=None, back=None, off=None, end_hour=None, stove=None, sun_warms=None):
        """« Bon à savoir »: the sun on the windows (Adaptive Cover Pro's hours first), a gesture seen to work."""
        local = dt_util.as_local(now)
        acp = {}
        for entity, (start_id, end_id) in self.room["acp"].items():
            start, end = (self.hass.states.get(e) for e in (start_id, end_id))
            start, end = (dt_util.parse_datetime(x.state) if x else None for x in (start, end))
            if start and end and dt_util.as_local(start).date() == local.date():
                acp[entity] = (dt_util.as_local(start), dt_util.as_local(end))
        windows = [Window(e, (self.room["orientations"].get(e) or (None,))[0], acp.get(e)) for e in self.room["windows"]]
        sun = {dt_util.as_local(h): v[2] for h, v in self.home.forecast.items()}
        view = RoomView(local, self.hass.config.latitude, self.hass.config.longitude, windows, sun, air,
                        minimum=comfort.minimum, maximum=comfort.maximum,
                        opened_at=dt_util.as_local(opening[0]) if opening else None,
                        air_at_opening=opening[1] if opening else None, humidity=humidity, coldest_tonight=coldest,
                        bedtime=bedtime, asleep=asleep, shutter_night=shutter_night, wake=wake, heating_back=back,
                        heating_off=off, end_hour=end_hour, stove_idle=stove, sun_gain=sun_warms)
        return tips(view)

    def _tonight(self, twins, current, local, bedtime, wake, coming, comfort, proof, marks, taken, habits):
        """« Cette nuit, pensez à… »: in the evening, the windows at the room's bedtime judged over the whole night."""
        found = tonight(twins, current, coming, int((bedtime - local).total_seconds() // 60), comfort, proof=proof,
                        forbidden=taken, habits=habits)
        return tonight_text(found, wake.hour, marks=marks) if found else None

    async def advise(self, now, stepping=True):
        """The room's decision now, kept in `self.result`; `stepping`: a five-minute step (the twin's trail moves), or a
        window that moved in between (it decides again only). False when the room cannot be advised yet."""
        room, home, hass = self.room, self.home, self.hass
        # The twin's trail moves five minutes at a time, whatever asks for a decision in between.
        if stepping and self.trail and now - self.trail[-1][0] < STEP_AT_LEAST:
            stepping = False
        outdoor, outdoor_rh = home.outdoor
        if outdoor is None or not room["temperature"]:
            return False
        alarm_entity = self.coordinator._alarm_entity()
        alarm = (s.state if (s := hass.states.get(alarm_entity)) else None) if alarm_entity else None
        habits = Habits.of(home.foyer(), room["foyer"])
        local = dt_util.as_local(now)
        # The room's own night: its sleeping hours, or the alarm armed for the night (CAHIER-MOTEUR.md § 11, point 6).
        night, wake, bedtime = habits.sleep.asleep(local, alarm), habits.sleep.wake(local), habits.sleep.bedtime(local)
        steps = max(12, int((wake - local).total_seconds() // STEP)) if night else DAY_STEPS
        end_hour = wake.hour if night else (local + timedelta(seconds=STEP * steps)).hour
        # Each measure checked first (CAHIER-MOTEUR.md § 7.3): a doubtful one is left aside, never advised on.
        measures, doubts = self._measures(now)
        air = measures["temperature"]
        name = room["name"]
        if air is None and doubts and doubts[0]["mesure"] == "temperature":
            banner = doubtful_air(doubts[0])
            self.result = {"title": banner["title"], "phrase": banner["line"], "piece": name, "geste": "nothing", "regle": "doubtful",
                           "douteuses": [dict(d, depuis=d["depuis"].isoformat() if d["depuis"] else None) for d in doubts],
                           "calcule_a": now.isoformat()}
            return True
        if air is None:
            return False
        learned = self.learned
        sizes = {e: (w * h, h) for e, (w, h) in room["windows"].items()}
        opened = tuple(size for e, size in sizes.items() if (s := hass.states.get(e)) and s.state == "on")
        position = _number(hass, room["cover"], "current_position")
        shade = 1.0 if position is None else max(0.05, position / 100)
        # The connected shutter covers the room's windows: shut, it keeps their heat in. Its gestures are proposed only
        # while no automation drives it (Adaptive Cover Pro's automatic control, CAHIER-MOTEUR.md § 6.7 ter).
        glass = sum(a for a, _ in sizes.values()) if room["cover"] else 0.0
        shutter = 0.0 if position is None else shutter_insulation(glass, 1 - position / 100)
        driven = (s := hass.states.get(room["cover_auto"] or "")) is not None and s.state == "on"
        heat = Params(**learned["heat"])
        houses = home.houses
        # The room's main heating when it is a house heater (the Salon's stove): simulated as its thermostat.
        main = room["thermostat_plage"]
        house_power = houses.get(main, 0.0) if main else 0.0
        house_stat = home.thermostat(main) if house_power else None
        house_heat = home.house_heat()
        twins = Twins(
            heat=heat, windows=tuple(sizes.values()),
            water=WaterParams(**learned["water"]) if "water" in learned else None, water_flow=tuple(learned.get("water_flow", (1, 1))),
            air=AirParams(**learned["air"]) if "air" in learned else None, air_flow=tuple(learned.get("air_flow", (1, 1))),
            particles=ParticleParams(**learned["particles"]) if "particles" in learned else None,
            particles_flow=tuple(learned.get("particles_flow", (1, 1))),
            voc=ParticleParams(**learned["voc"]) if "voc" in learned and room["voc"] else None,
            voc_flow=tuple(learned.get("voc_flow", (1, 1))),
            # The fast speed at the share of its declared flow the room showed (advisor/nightly.py `boost_scale`).
            boost=(room["boost"] or (None, 0.0))[1] * learned.get("boost_scale", 1.0), purifier=(room["purifier"] or (None, 0.0))[1],
            thermostat=home.thermostat(room["thermostat"]), shutter_area=glass,
            idle_thermostat=home.thermostat(room["thermostat"], "off"),
            # The side each window faces, for the air crossing the room (« Ouvrez aussi la porte-fenêtre »).
            bearings=tuple((room["orientations"].get(e) or (None,))[0] for e in sizes),
            house_thermostat=house_stat, house_power=float(house_power) if house_stat else 0.0,
            house_now=(_number(hass, main, "power_percent") or 0.0) / 100 if house_stat else 0.0)
        orientations = room["orientations"]
        glazing = [(sizes[e][0], *orientations[e]) for e in sizes if e in orientations] if orientations else None
        opened_index = {i for i, e in enumerate(sizes) if (s := hass.states.get(e)) and s.state == "on"}
        coming = home.coming(now, steps, outdoor, outdoor_rh, house_heat, shade, glazing, opened_index, shutter)
        walls = self.walls if self.walls is not None else air
        # What acts on the room now, its own heating included: what the twin's trend is measured with.
        power = _number(hass, room["thermostat"], "power_percent")
        acting = replace(coming[0][0], windows=opened, heating=(power or 0.0) / 100)
        missed = self._missed(heat, now, air)
        # The stove burns while its thermostat says it heats, even at 0 %: it does not stop by itself (Frank, 1 November).
        main_state = hass.states.get(main) if house_stat else None
        burning = main_state is not None and main_state.attributes.get("hvac_action") == "heating"
        if burning and air >= house_stat.target + habits.overheat:
            self.hot_since = self.hot_since or now
        else:
            self.hot_since = None
        overheated = (now - self.hot_since).total_seconds() / 60 if self.hot_since else None
        # °C the room gained over the last half hour, measured.
        earlier = [a for t, a, *_ in self.trail if now - t >= timedelta(minutes=27.5)]
        rise = air - earlier[-1] if earlier else None
        current = Now(air=air, walls=walls, opened=opened, humidity=measures["humidity"], co2=measures["co2"],
                      particles=measures["particles"], voc=measures["voc"],
                      boosting=self._on(room["boost"]), purifying=self._on(room["purifier"]),
                      night=night, missed=missed,
                      cover=None if position is None or driven else position / 100,
                      heating=None if twins.thermostat is None and twins.idle_thermostat is None else twins.thermostat is not None,
                      heating_target=twins.thermostat.target if twins.thermostat else None,
                      house_running=burning, house_rise=rise, overheated=overheated)
        rain_rate, gust, rain_in, vigilance = home.safety()
        taken, reason = forbidden(rain_rate, gust, rain_in, vigilance, alarm, coldest=min(u.outdoor for u, _ in coming))
        # The gestures answered « Pas maintenant », put aside for a while (CAHIER-MOTEUR.md § 15).
        aside = declined(self.paused, current, now)
        taken = taken | aside
        away = holidays(alarm)
        # The room's range as set in Confort, for the home's season (CAHIER-MOTEUR.md § 10.3).
        comfort = for_season(**room["comfort"], season=self.coordinator.season_name)
        # The thermostat's set point stands as the room's minimum, eco included (CAHIER-MOTEUR.md § 6.8), unless the
        # room says otherwise; the room's main thermostat when it is not its own (the Salon follows the stove).
        main = room["thermostat_plage"] or room["thermostat"]
        stat = hass.states.get(main) if main else None
        if stat is not None and stat.state in ("heat", "off") and room["thermostat_reference"]:
            aimed = stat.attributes.get("current_state") or {}
            comfort = from_thermostat(comfort, aimed.get("target_temperature", stat.attributes.get("temperature")),
                                      aimed.get("preset", stat.attributes.get("preset_mode")),
                                      (stat.attributes.get("preset_temperatures") or {}).get("comfort_temp"))
        opening = self._opening(now, opened, air, current.humidity)
        proof = self._proof(current, outdoor, coming[0][1])
        # A source running now (a cooking, a shower…): the last half hour replayed on the twin against the measures.
        rows = list(self.air_trail)
        start = max((i for i, row in enumerate(rows) if now - row[0] >= timedelta(minutes=27.5)), default=None)
        measured_now = current
        if start is not None:
            try:
                found = recent_sources(twins, rows[start][1], [(row[2], row[3]) for row in rows[start:]], current)
            except Exception:  # noqa: BLE001 - the sources are a plus
                _LOGGER.exception("Hestia Comfort: sources for %s", name)
                found = {}
            if found:
                current = replace(current, sources=found)
        # The gesture shown last, counted down to now (« encore 10 min » five minutes on is « encore 5 min »).
        shown_before, shown_at, shown_since = self.previous or (None, now, now)
        previous = aged(shown_before, (now - shown_at).total_seconds() / 60)
        # How long it has been on the card: held half an hour while it still helps (advisor/decide.py HOLD_MINUTES).
        held = (now - shown_since).total_seconds() / 60
        decision = decide(twins, current, coming, comfort, previous=previous, forbidden=taken, proof=proof,
                          holidays=away, habits=habits, held=held)
        if decision.rule == "unproven" and opened and opening:
            # The gesture under way may show its effect now (CAHIER-MOTEUR.md § 4.1).
            subject = main_subject(decision.scenarios, decision.passive)
            if self._seen(subject, decision, opening, now, air, current.humidity):
                proof[subject] = PROVEN
                decision = decide(twins, current, coming, comfort, previous=previous, forbidden=taken, proof=proof,
                                  holidays=away, habits=habits, held=held)
        snap = capture(twins, current, coming, comfort, previous=previous, forbidden=taken, proof=proof,
                       holidays=away, habits=habits, reason=reason, held=held, end_hour=end_hour, hour=local.hour + local.minute / 60,
                       room=name, when=now.isoformat(), version=home.version)
        snap["pas_maintenant"] = sorted(aside)
        same = shown_before is not None and (shown_before.kind, shown_before.after is None) == (decision.gesture.kind, decision.gesture.after is None)
        self.previous = (decision.gesture, now, shown_since if same else now)
        if stepping:
            # The walls follow the measured air, five minutes at a time.
            self.trail.append((now, air, walls, acting))
            self.air_trail.append((now, measured_now, acting, coming[0][1]))
            _, self.walls = step(heat, air, walls, acting)
        marks = {"minimum": comfort.minimum, "maximum": comfort.maximum, "humidity": comfort.humidity, "co2": comfort.co2,
                 "particles": comfort.particles, "voc": comfort.voc}
        # The local time now: a later gesture says its hour (« Aérez 5 min vers 13 h 50 »), never only its length.
        words = phrase(decision, end_hour, marks=marks, hour=local.hour + local.minute / 60, reason=reason)
        # The coming night, from the evening on: « Cette nuit, pensez à… », misted panes.
        night_coming = None
        if night or local >= bedtime - timedelta(hours=habits.mist_before):
            night_coming = home.coming(now, int((wake - local).total_seconds() // STEP), outdoor, outdoor_rh, house_heat,
                                       shade, glazing, opened_index, shutter)
        coldest = min(u.outdoor for u, _ in night_coming) if night_coming else None
        # What the shutter closed at bedtime would keep by waking up: a passive advice (advisor/knowing.py).
        shutter_night = shutter_tonight(twins, current, night_coming, 0 if night else int((bedtime - local).total_seconds() // 60)) \
            if night_coming else None
        # A room under its range that its thermostat brings back: when (advisor/knowing.py).
        idle = decision.paths.get(Gesture("nothing"))
        back = heating_back(twins, idle, current, comfort.minimum, coming) if idle is not None else None
        # Its heating off: what turning it on again would give, said as a passive advice only (§ 9.1 bis).
        off = heating_off(twins, current, coming, comfort, habits.tolerance)
        # The stove at its lowest in a room warm enough: worth stopping, or the room still warming (passive).
        stove = stove_idle(twins, current, coming, comfort.minimum, habits.stove_hold) if decision.rule != "overheat" else None
        good = self._good_to_know(now, air, opening, comfort, current.humidity, coldest, bedtime, night, shutter_night, wake,
                                  back, off, end_hour, stove, sun_gain(twins, current, coming))
        good_words = [tip_text(t, now=local) for t in good]
        night_text = None
        if night_coming and not night and local >= bedtime - timedelta(hours=habits.tonight_before):
            night_text = self._tonight(twins, current, local, bedtime, wake, night_coming, comfort, proof, marks, taken, habits)
        # « Cette nuit, pensez à refermer » says nothing more than a banner already saying « Refermez ».
        if night_text and decision.gesture.kind != "close":
            good_words.insert(0, night_text)
        if decision.gesture.kind == "nothing" and good and good[0].kind in ("open_warms", "open_cools"):
            words["line"] = good_words[0]
        # The gesture the card asks for, followed: done while shown, or replaced before (CAHIER-MOTEUR.md § 15).
        trial = decision.gesture.kind == "nothing" and decision.passive is not None and bool(words["try"])
        shown = decision.passive if trial else decision.gesture
        self.asked, followed = follow(self.asked, shown, words["try"] if trial else words["title"], trial, current, now)
        for record in followed:
            if record["suivi"]:
                self.paused.pop(record["geste"], None)
            await hass.async_add_executor_job(home.files.feedback, {"heure": now.isoformat(), "piece": name, "type": "suivi", **record})
        self.result = {"title": words["title"], "phrase": words["line"], "pourquoi": words["why"],
                       "sujet": words["subject"], "regle": decision.rule, "gain": round(decision.gain, 2),
                       "geste": decision.gesture.kind, "minutes": decision.gesture.minutes, "apres": decision.gesture.after,
                       "sources": {k: round(v, 2) for k, v in (current.sources or {}).items()} or None,
                       # When to shut, for the card's « encore 4 min » between two steps.
                       "refermer_a": (now + timedelta(minutes=decision.gesture.after)).isoformat()
                       if decision.gesture.kind == "close" and decision.gesture.after and decision.gesture.after < 60 else None,
                       "nuit": night, "interdit": reason, "vacances": away,
                       "ecart_1h": None if missed is None else round(missed, 2), "piece": name,
                       "mesures": {"air": air, "humidite": current.humidity, "co2": current.co2, "particules": current.particles,
                                   "cov": current.voc, "dehors": outdoor, "fenetres": len(opened)},
                       "plage": [comfort.minimum, comfort.maximum], "cette_nuit": night_text, "preuve": decision.level,
                       "preuves": proof, "a_essayer": words["try"], "bon_a_savoir": good_words,
                       "pas_maintenant": {k: dt_util.as_local(until).strftime("%H h %M") for k, until in self.paused.items() if k in aside},
                       "douteuses": doubt_text(doubts), "calcule_a": now.isoformat(), "moteur": home.version}
        changed = self.shown != (words["title"], words["try"])
        await hass.async_add_executor_job(home.files.keep, self.slug, now, local, snap, decision, words, changed)
        if changed:
            self.shown = (words["title"], words["try"])
            await hass.async_add_executor_job(home.files.journal, {
                "heure": now.isoformat(), "moteur": home.version, "piece": name, "conseil": words["title"], "phrase": words["line"],
                "pourquoi": words["why"], "a_essayer": words["try"], "preuve": decision.level, "bon_a_savoir": good_words,
                "gain": round(decision.gain, 2), "ecart_1h": None if missed is None else round(missed, 2),
                "mesures": {"air": air, "dehors": outdoor, "fenetres_ouvertes": len(opened), "humidite": current.humidity,
                            "co2": current.co2, "particules": current.particles, "cov": current.voc}})
        return True

    async def opinion(self, kind, note):
        """« Ce conseil ne va pas » (CAHIER-MOTEUR.md § 15): the situation kept without limit, with its trace, to be
        replayed; « Pas maintenant » also puts the gesture aside for the household's time. Until when, if it does."""
        now = dt_util.utcnow()
        a = self.result or {}
        shown = {"conseil": a.get("title"), "phrase": a.get("phrase"), "pourquoi": a.get("pourquoi"),
                 "a_essayer": a.get("a_essayer"), "bon_a_savoir": a.get("bon_a_savoir"), "mesures": a.get("mesures")}
        until = None
        gesture = self.asked.kind if self.asked else a.get("geste")
        if kind == "pas_maintenant" and gesture and gesture != "nothing":
            habits = Habits.of(self.home.foyer(), self.room["foyer"])
            until = pause_until(now, habits.not_now)
            self.paused[gesture] = until
        file = await self.hass.async_add_executor_job(self.home.files.signal, self.slug, dt_util.as_local(now), kind, note, shown)
        await self.hass.async_add_executor_job(self.home.files.feedback, {
            "heure": now.isoformat(), "moteur": self.home.version, "piece": self.room["name"], "type": "avis", "avis": kind, "note": note, "geste": gesture,
            "conseil": shown["conseil"], "phrase": shown["phrase"], "fichier": file})
        return dt_util.as_local(until).strftime("%H h %M") if until else None
