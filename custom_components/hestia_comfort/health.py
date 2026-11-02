"""The technical state of the home, for the home page of the « Confort » tab: what works, what needs the user, what could be set better.

Same shape as Hestia Weather's (engine/health.py there): orange (`bad`) only for what stops something from working, a better setting
is a tip, grey (`none`) is what is not used. Read from this brick's own settings and Home Assistant only.
"""
from dataclasses import dataclass, field

from homeassistant.util import dt as dt_util

from . import cover_link, weather_link
from .socle import SOCLE_VERSION
from .engine import people, thermostat as thermostats
from .engine.i18n import N_, language, t
from .configuration import get_configuration
from homeassistant.helpers import entity_registry as er

from .discovery import INDOOR, catalog, effective_area, overview, suggestions

GONE = ("unavailable", "unknown")
COLUMNS = (("indoor_temperature", N_("Température")), ("indoor_humidity", N_("Humidité")), ("co2", N_("CO₂")), ("windows", N_("Ouvrants")), ("heating", N_("Chauffage")))
# « Cuisine : le CO₂ ne répond pas »
SUBJECTS = {"indoor_temperature": N_("la température"), "indoor_humidity": N_("l’humidité"), "co2": N_("le CO₂"), "windows": N_("un ouvrant"), "heating": N_("le chauffage"), "illuminance": N_("la luminosité"), "pm25": N_("les PM2.5"), "voc": N_("les COV"), "purifier": N_("le purificateur"), "ventilation": N_("la ventilation"), "ventilation_boost": N_("la grande vitesse de la ventilation"), "presence": N_("la présence"), "covers": N_("le volet"), "shutter_auto": N_("l’automatisation du volet"), "shutter_override": N_("la dérogation du volet"),
            "outdoor_temperature": N_("la température"), "outdoor_humidity": N_("l’humidité"), "rain": N_("la pluie"), "wind_gust": N_("les rafales"),
            "wind_bearing": N_("la direction du vent"), "solar": N_("l’ensoleillement"), "pollution": N_("la pollution"), "season": N_("la saison")}
LOSS = {"indoor_temperature": N_("Le confort de la pièce n’est plus évalué."), "indoor_humidity": N_("L’humidité de la pièce est inconnue."),
        "co2": N_("Le conseil d’aération est en pause."), "windows": N_("On ne sait plus s’il est ouvert."), "heating": N_("On ne sait plus si le chauffage tourne.")}
LOSS.update({"illuminance": N_("La lumière intérieure est inconnue."), "pm25": N_("Les particules intérieures ne sont plus mesurées."), "voc": N_("Les COV ne sont plus mesurés."), "purifier": N_("Le fonctionnement du purificateur est inconnu."), "ventilation": N_("Le fonctionnement de la ventilation est inconnu."), "ventilation_boost": N_("La grande vitesse de la ventilation est inconnue."), "presence": N_("La présence reste inconnue."), "covers": N_("La position du volet est inconnue."), "shutter_auto": N_("L’automatisation est inconnue."), "shutter_override": N_("La dérogation est inconnue.")})
GAINS = {"indoor_humidity": N_("repérer un air trop humide et savoir si aérer l’assèche"),
         "co2": N_("savoir quand renouveler l’air"), "heating": N_("ne pas conseiller d’ouvrir pendant que le chauffage tourne")}


@dataclass
class Sensor:
    key: str
    name: str
    status: str
    """« ok », « silent », « stale » (Home Assistant has it, the advice cannot use it) or « missing »."""
    age: float | None = None
    entity_id: str = ""


@dataclass
class Room:
    entry_id: str
    title: str
    loaded: bool = True
    sensors: list = field(default_factory=list)
    available: dict = field(default_factory=dict)
    """Sensors Home Assistant has in this room for what is not chosen: key → name."""
    shared: dict = field(default_factory=dict)
    """Sources read from the room it shares its air with: key → that room's name."""
    thermostat: bool = False
    """Its heating is a Versatile Thermostat (engine/thermostat.py)."""
    better: bool = False
    """Its heating is a Better Thermostat (engine/thermostat.py)."""
    driven_covers: int = 0
    """Its covers driven with the sun (cover_link.py)."""
    drivers: frozenset = frozenset()
    """The integrations driving them: « adaptive_cover_pro », « cover_automatic », « cover_extender »."""
    windows_intended: bool = False
    """No contact on its windows, on purpose: not suggested again."""


@dataclass
class Facts:
    rooms: list = field(default_factory=list)
    exterior: list = field(default_factory=list)
    """The home's exterior sensors (Sensor)."""
    configured: bool = False
    weather: str = ""
    """The Hestia Weather place the exterior comes from, "" when not linked."""
    weather_installed: bool = False
    free_areas: list = field(default_factory=list)
    """Home Assistant rooms with a thermometer that no Hestia room follows: (area_id, name)."""
    wled: list = field(default_factory=list)
    """Who the WLED lights show, as « Notifications lumineuses » sets them: « Tout le logement » or room names."""
    version: str = ""
    alarm: str = ""
    """The home's alarm as read: « Alarmo · désarmée », "" without one."""
    installed: frozenset = frozenset()
    """The integrations of EXTENSIONS and OTHERS that Home Assistant has loaded."""
    disabled: frozenset = frozenset()
    """The extensions turned off in the general settings."""


def _duration(minutes):
    """« 5 min », « 3 h », « 2 j »."""
    if minutes < 60:
        return t("{n} min", n=round(minutes))
    return t("{n} h", n=round(minutes / 60)) if minutes < 48 * 60 else t("{n} j", n=round(minutes / 1440))


def ago(minutes):
    if minutes is None:
        return ""
    return t("à l’instant") if minutes < 1.5 else t("il y a {duration}", duration=_duration(minutes))


def _count(n, one, many):
    """One of two French texts with {n}, chosen by n: « 0 pièce », « 3 pièces » (« 0 rooms » in English)."""
    return t(one, n=n) if n == 1 or n == 0 and language() == "fr" else t(many, n=n)


def _line(level, text, why="", target=None):
    return {"level": level, "text": text, "why": why, "target": target}


def _since(age):
    return t("Depuis {duration}.", duration=_duration(age)) + " " if age is not None and age >= 1.5 else ""


def _broken(s):
    return {"missing": t("n’existe plus"), "stale": t("ne donne pas de mesure exploitable")}.get(s.status, t("ne répond pas"))


def report(f):
    todo, tips = [], []
    for room in f.rooms:
        target = {"kind": "room", "entry_id": room.entry_id, "label": room.title}
        if not room.loaded:
            todo.append(_line("bad", t("{room} : calcul arrêté", room=room.title),
                              t("Home Assistant n’a pas pu démarrer cette pièce : vérifiez ses capteurs ou les journaux (cherchez « comfort »)."), target))
        for s in room.sensors:
            if s.status != "ok":
                todo.append(_line("bad", t("{room} : {subject} {broken}", room=room.title, subject=t(SUBJECTS[s.key]), broken=_broken(s)),
                                  f"{_since(s.age)}{s.name} · {t(LOSS[s.key])}", target))
        chosen = {s.key for s in room.sensors}
        for key in ("indoor_humidity", "co2", "heating"):
            if key not in chosen and key not in room.shared and key in room.available:
                tips.append(_line("tip", t("{room} : ajouter {subject}", room=room.title, subject=t(SUBJECTS[key])),
                                  t("« {name} » est disponible : {gain}.", name=room.available[key], gain=t(GAINS[key])), target))
        if "windows" not in chosen and not room.windows_intended:
            found = room.available.get("windows")
            tips.append(_line("tip", t("{room} : ouvrants non mesurés", room=room.title), (t("« {name} » est disponible.", name=found) + " " if found else "")
                              + t("Un contact sur la fenêtre dirait si elle est ouverte : le conseil d’ouvrir ne viserait plus une fenêtre déjà ouverte.")
                              + " " + t("Pas de contact voulu ici : Modifier → Ouvertures."), target))
    exterior_target = {"kind": "exterior", "label": t("Extérieur")}
    if not f.configured:
        todo.append(_line("bad", t("Extérieur à configurer"), t("Sans l’extérieur, impossible de dire s’il vaut mieux ouvrir ou fermer."), exterior_target))
    for s in f.exterior:
        if s.status != "ok":
            todo.append(_line("bad", t("Extérieur : {subject} {broken}", subject=t(SUBJECTS[s.key]), broken=_broken(s)),
                              f"{_since(s.age)}{s.name} · {t('toutes les pièces sont concernées.')}", exterior_target))
    for area_id, name in f.free_areas:
        tips.append(_line("tip", t("{room} pas encore suivie", room=name), t("Pièce Home Assistant avec un thermomètre : elle peut être suivie."),
                          {"kind": "area", "area_id": area_id, "label": t("Ajouter")}))
    if f.weather_installed and not f.weather:
        tips.append(_line("tip", t("Reprendre l’extérieur de Hestia Weather"), t("Sa station, ses alertes et ses prévisions, sans rien choisir à nouveau."), exterior_target))

    # ---- Sources ----
    bad = [s for s in f.exterior if s.status != "ok"]
    silent = " · " + _count(len(bad), "{n} capteur ne répond pas", "{n} capteurs ne répondent pas") if bad else ""
    if f.weather:
        exterior = {"label": t("Extérieur"), "level": "bad" if bad else "ok", "text": f"Hestia Weather · {f.weather}{silent}"}
    elif f.configured:
        exterior = {"label": t("Extérieur"), "level": "bad" if bad else "ok",
                    "text": _count(len(f.exterior), "{n} capteur", "{n} capteurs") + (silent or (t(", tous répondent") if f.exterior else ""))}
    else:
        exterior = {"label": t("Extérieur"), "level": "bad", "text": t("pas encore configuré")}
    pollution = next((s for s in f.exterior if s.key == "pollution"), None)
    heated = [r for r in f.rooms if any(s.key == "heating" for s in r.sensors)]
    sources = [exterior,
               {"label": t("Pollution"), "level": "none" if not pollution else "ok" if pollution.status == "ok" else "bad",
                "text": t("aucune source") if not pollution else pollution.name + ("" if pollution.status == "ok" else " · " + t("ne répond pas"))},
               {"label": t("Chauffage"), "level": "ok" if heated else "none",
                "text": _count(len(heated), "suivi dans {n} pièce · rien n’est commandé", "suivi dans {n} pièces · rien n’est commandé") if heated else t("non suivi")}]

    # ---- Sensors by room ----
    rooms = []
    for room in f.rooms:
        cells = []
        for key, _ in COLUMNS:
            mine = [s for s in room.sensors if s.key == key]
            broken = [s for s in mine if s.status != "ok"]
            if not mine and key in room.shared:
                # Heated by the living room it opens onto, breathing the air its sensor measures.
                cells.append({"level": "shared", "text": room.shared[key]})
            elif not mine:
                cells.append({"level": "none", "text": t("non mesurés") if key == "windows" else "—"})
            elif broken:
                cells.append({"level": "bad", "text": t("{n} sur {total} ne répondent pas", n=len(broken), total=len(mine)) if len(mine) > 1 else t("ne répond pas")})
            else:
                cells.append({"level": "ok", "text": _count(len(mine), "{n} contact", "{n} contacts") if key == "windows" else t("répond")})
        rooms.append({"entry_id": room.entry_id, "title": room.title, "cells": cells})

    # Extensions: Hestia's own bricks, then other integrations Hestia reads by itself, each making the advice better where it is used.
    vt = [r.title for r in f.rooms if r.thermostat]
    bt = [r.title for r in f.rooms if r.better]
    linked = {"hestia_weather": [f.weather] if f.weather else [], thermostats.PLATFORM: vt, thermostats.BETTER: bt, people.PLATFORM: [f.alarm] if f.alarm else [],
              **{key: [r.title for r in f.rooms if key in r.drivers] for key in cover_link.ADAPTERS}, "wled": f.wled}
    installed = {"hestia_weather": f.weather_installed}
    extensions = []
    for ext in EXTENSIONS:
        found = linked[ext["key"]]
        state = "off" if ext["key"] in f.disabled else "linked" if found else "found" if installed.get(ext["key"], ext["key"] in f.installed) else "missing"
        text = (t("relié · {place}", place=f.weather) if ext["key"] == "hestia_weather" else f.alarm if ext["key"] == people.PLATFORM
                else _count(len(found), "{n} pièce", "{n} pièces") + " · " + ", ".join(found)) if found and state != "off" else t("désactivée") if state == "off" else t(ext[state])
        extensions.append({**{k: ext[k] for k in ("key", "name", "official", "url")}, **{k: t(ext[k]) for k in ("role", "use", "without")},
                           "state": state, "level": "ok" if found else "none", "text": text, "rooms": found if ext["key"] in (thermostats.PLATFORM, thermostats.BETTER, "wled") or ext["key"] in cover_link.ADAPTERS else []})
    # Installed integrations Confort does not read yet: shown so that the person can ask for them.
    others = [{**o, "use": t(o["use"])} for o in OTHERS if o["key"] in f.installed]
    versions = [{"level": "ok", "text": t("Intégration {version}", version=f.version), "why": t("avec sa carte")},
                {"level": "ok", "text": t("Relié à Hestia Weather · {place}", place=f.weather), "why": t("l’extérieur vient de sa station et de ses prévisions")} if f.weather else
                {"level": "none", "text": t("Pas relié à Hestia Weather"), "why": t("installé : il peut remplir l’extérieur") if f.weather_installed else t("non installé")}]
    # One count everywhere: every sensor checked here, in the rooms (a shared one once) and outside.
    checked = [s for r in f.rooms for s in r.sensors] + list(f.exterior)
    sensors = {"answering": sum(1 for s in checked if s.status == "ok"), "total": len(checked)}
    return {"level": "action" if todo else "ok", "sensors": sensors,
            "summary": _count(len(todo), "{n} point à régler", "{n} points à régler") if todo else t("Tout est suivi"),
            "tips_summary": _count(len(tips), "{n} réglage à améliorer", "{n} réglages à améliorer") if tips else "",
            "rooms_summary": _count(len(f.rooms), "{n} pièce suivie", "{n} pièces suivies"),
            "todo": todo, "tips": tips, "sources": sources, "extensions": extensions, "others": others, "socle": ".".join(map(str, SOCLE_VERSION)),
            # The columns by key for the panel, by name for people: a translated name is never compared.
            "column_keys": [key for key, _ in COLUMNS], "columns": [t(label) for _, label in COLUMNS], "rooms": rooms, "versions": versions, "version": f.version}


EXTENSIONS = (
    {"key": "hestia_weather", "name": "Hestia Weather", "official": True, "url": "https://github.com/hestiaFB/hestia-weather-integration",
     "role": N_("Extérieur, prévisions, pluie, vigilances"),
     "use": N_("Le dehors pour toutes les pièces : température, humidité, pluie, vent, soleil, saison, pollution, alertes et prévisions."),
     "without": N_("Sans lui : vos propres capteurs, sans prévisions ni alertes."),
     "found": N_("installé, pas relié"), "missing": N_("non installé")},
    {"key": thermostats.PLATFORM, "name": thermostats.NAME, "official": False, "url": "https://github.com/jmcollin78/versatile_thermostat",
     "role": N_("Consigne confort, raison d’un arrêt, présets, pente"),
     "use": N_("Consigne de confort, raison d’un arrêt (fenêtre, absence), préréglage et pente de chauffe : plus de conseil de chauffer quand le thermostat s’en charge."),
     "without": N_("Sans lui : le chauffage est lu sur le thermostat de Home Assistant seulement."),
     "found": N_("installé, aucun chauffage choisi dans une pièce"), "missing": N_("non installé")},
    {"key": thermostats.BETTER, "name": "Better Thermostat", "official": False, "url": "https://github.com/KartoffelToby/better_thermostat",
     "role": N_("Consigne en cours, arrêt fenêtre, préréglages, pente"),
     "use": N_("La consigne en cours sert de minimum : plus de conseil de chauffer quand Better Thermostat vise déjà cette température. Éco, absence et veille visent plus bas. Une fenêtre qu’il a vue est signalée, et un arrêt fenêtre reprend seul."),
     "without": N_("Sans lui : le chauffage est lu sur le thermostat de Home Assistant seulement."),
     "found": N_("installé, aucun chauffage choisi dans une pièce"), "missing": N_("non installé")},
    {"key": "adaptive_cover_pro", "name": cover_link.NAME, "official": False, "url": "https://github.com/jrhubott/adaptive-cover-pro",
     "role": N_("Volets pilotés avec le soleil"),
     "use": N_("Volets pilotés avec le soleil : Confort sait quand ils se ferment et nomme les volets à fermer avant la chaleur."),
     "without": N_("Sans lui : le soleil est estimé par la façade de chaque ouvrant."),
     "found": N_("installé, aucun volet relié à un ouvrant"), "missing": N_("non installé")},
    {"key": "cover_automatic", "name": "CoverAutomatic", "official": False, "url": "https://github.com/crandler/CoverAutomatic",
     "role": N_("Volets pilotés par façade, règles et scénarios"),
     "use": N_("Volets pilotés par façade : Confort sait s’il est en pause après un geste à la main, la position qu’il vise, et à quelle heure le soleil arrive sur la façade."),
     "without": N_("Sans lui : le soleil est estimé par la façade de chaque ouvrant."),
     "found": N_("installé, aucun volet relié à un ouvrant"), "missing": N_("non installé")},
    {"key": "cover_extender", "name": "Cover Extender", "official": False, "url": "https://github.com/Pulpyyyy/cover-extender",
     "role": N_("Modes, verrou et ombrage des volets"),
     "use": N_("Modes, verrou et ombrage automatique : Confort sait quand le volet se ferme seul au soleil, et ne demande rien sur un volet verrouillé."),
     "without": N_("Sans lui : le soleil est estimé par la façade de chaque ouvrant."),
     "found": N_("installé, aucun volet relié à un ouvrant"), "missing": N_("non installé")},
    {"key": "wled", "name": "WLED", "official": False, "url": "https://github.com/wled/WLED",
     "role": N_("Bandeaux LED, effets et segments"),
     "use": N_("Bandeaux LED : leurs effets (respiration, vague…) et leurs segments sont proposés dans les notifications lumineuses, un segment par pièce."),
     "without": N_("Sans lui : les notifications lumineuses utilisent les ampoules couleur, sans effets."),
     "found": N_("installé, aucune notification lumineuse"), "missing": N_("non installé")},
    {"key": people.PLATFORM, "name": people.NAME, "official": False, "url": "https://github.com/nielsfaber/alarmo",
     "role": N_("Maison vide, nuit, fenêtre ouverte alarme armée"),
     "use": N_("Maison vide, nuit, vacances : pas d’aération conseillée quand personne n’est là, et un avertissement si une fenêtre reste ouverte alarme armée."),
     "without": N_("Sans elle : l’absence est lue sur les personnes de la maison."),
     "found": N_("installée, pas utilisée"), "missing": N_("non installée")},
)
# Integrations Confort could read one day: listed only when Home Assistant has them.
OTHERS = (
    {"key": "smartir", "name": "SmartIR", "use": N_("Pourrait dire si la climatisation tourne, et dans quel mode.")},
    {"key": "scheduler", "name": "Scheduler", "use": N_("Pourrait dire quand le chauffage va reprendre.")},
)
DOMAINS = frozenset(e["key"] for e in EXTENSIONS + OTHERS) | set(cover_link.PLATFORMS)


def _weather_air(spec):
    return Sensor("pollution", f"Hestia Weather · {spec.get('provider') or t('qualité de l’air')}", "ok" if spec.get("index") else "silent")


def _sensor(hass, key, entity_id, now):
    state = hass.states.get(entity_id)
    if state is None:
        return Sensor(key, entity_id, "missing", entity_id=entity_id)
    name = str(state.attributes.get("friendly_name") or entity_id)
    if state.state in GONE:
        return Sensor(key, name, "silent", (now - state.last_changed).total_seconds() / 60, entity_id)
    seen = getattr(state, "last_reported", None) or state.last_updated
    return Sensor(key, name, "ok", (now - seen).total_seconds() / 60, entity_id)


def _unusable(coordinator):
    """Entities whose reading the room's last advice could not use: listed in its `missing`."""
    data = getattr(coordinator, "data", None)
    if not isinstance(data, dict):
        return set()
    assessment, observations = data.get("assessment") or {}, data.get("observations") or {}
    found = set()
    for key in assessment.get("missing") or ():
        source = (observations.get(key) or {}).get("source") if isinstance(observations.get(key), dict) else None
        if isinstance(source, str):
            found.add(source)
    return found


async def facts(hass, version):
    service, now = await get_configuration(hass), dt_util.utcnow()
    rooms, used, stale = [], set(), set()
    indoor_ids = {{**e.data, **e.options}.get("sources", {}).get(k) for e in service.entries() for k in ("indoor_temperature", "indoor_humidity")} - {None}
    # Only local, unselected suggestions are used here. Index the registry once,
    # rather than scanning every entity for every role for every configured room.
    local_entries = {}
    for entity in er.async_get(hass).entities.values():
        local_entries.setdefault(effective_area(hass, entity), []).append(entity)
    # Alarmo off is no alarm; the others are listed by key.
    disabled = set(service.home.get("disabled") or []) | ({people.PLATFORM} if service.home.get("alarm") == "" else set())
    for entry in service.entries():
        config = {**entry.data, **entry.options}
        sources, windows = config.get("sources", {}), config.get("windows", [])
        room = Room(entry.entry_id, entry.title, entry.state.value == "loaded")
        coordinator = getattr(entry, "runtime_data", None)
        room.shared = coordinator.inherited() if hasattr(coordinator, "inherited") else {}
        heating = er.async_get(hass).async_get(sources["heating"]) if sources.get("heating") else None
        room.thermostat = bool(heating and heating.platform == thermostats.PLATFORM and thermostats.PLATFORM not in disabled)
        room.better = bool(heating and heating.platform == thermostats.BETTER and thermostats.BETTER not in disabled)
        driven = {w: r for w, r in (getattr(coordinator, "drivers", None) or {}).items() if w in windows}
        room.driven_covers = len(driven)
        room.drivers = frozenset(r.get("driver", "adaptive_cover_pro") for r in driven.values())
        room.windows_intended = config.get("windows_unmeasured") is True
        room.sensors = [_sensor(hass, key, sources[key], now) for key in ("indoor_temperature", "indoor_humidity", "co2", "heating", "illuminance", "pm25", "voc", "purifier", "ventilation", "ventilation_boost") if sources.get(key)]
        room.sensors += [_sensor(hass, "windows", w, now) for w in windows]
        room.sensors += [_sensor(hass, "presence", e, now) for e in config.get("presence", [])]
        for meta in config.get("openings", {}).values():
            if meta.get("shutter") == "connected":
                for field, role in (("cover_entity", "covers"), ("auto_entity", "shutter_auto"), ("override_entity", "shutter_override")):
                    if meta.get(field):
                        room.sensors.append(_sensor(hass, role, meta[field], now))
        if area_id := config.get("area_id"):
            used.add(area_id)
            selected = {**sources, "windows": windows}
            candidates = {key: [] for key in INDOOR}
            candidates.update(catalog(hass, area_id, selected, indoor_ids,
                                      keys=("indoor_humidity", "co2", "heating", "windows"),
                                      entries=local_entries.get(area_id, ())))
            for key, value in suggestions(candidates, area_id).items():
                entity_id = value[0] if isinstance(value, list) and value else value
                if isinstance(entity_id, str) and not selected.get(key):
                    state = hass.states.get(entity_id)
                    room.available[key] = str(state.attributes.get("friendly_name") or entity_id) if state else entity_id
        # What Home Assistant still shows but the advice cannot use (too old, wrong unit): the same as the room's card says.
        unusable = _unusable(coordinator)
        stale |= unusable
        for sensor in room.sensors:
            if sensor.status == "ok" and sensor.entity_id in unusable:
                sensor.status = "stale"
        rooms.append(room)
    home = service.live_sources()
    exterior = [_weather_air(spec) if spec.get("adapter") == "hestia_air" else _sensor(hass, key, spec["entity_id"], now)
                for key, spec in home.items() if spec.get("entity_id")]
    for sensor in exterior:
        if sensor.status == "ok" and sensor.entity_id and sensor.entity_id in stale:
            sensor.status = "stale"
    link = weather_link.status(hass)
    weather = next((p["title"] for p in link.get("places", []) if p["entry_id"] == service.home.get("weather")), "")
    free = [(a["area_id"], a["name"]) for a in overview(hass, used) if isinstance(a["suggestions"].get("indoor_temperature"), str)]
    # The alarm as the rooms read it (engine/people.py): the one chosen in the general settings, else Alarmo.
    coordinator = next((c for e in service.entries() if (c := getattr(e, "runtime_data", None)) is not None and hasattr(c, "_alarm")), None)
    found = coordinator._alarm() if coordinator is not None else None
    states = {"disarmed": N_("désarmée"), "armed_away": N_("absence"), "armed_home": N_("à la maison"), "armed_night": N_("nuit"),
              "armed_vacation": N_("vacances"), "armed_custom_bypass": N_("personnalisée"), "triggered": N_("déclenchée")}
    alarm = f"{found['name']} · {t(states[found['state']]) if found['state'] in states else found['state']}" if found else ""
    loaded = getattr(getattr(hass, "config", None), "components", None) or set()
    # The original Adaptive Cover is read like the Pro one.
    installed = {d for d in DOMAINS if d in loaded} | ({"adaptive_cover_pro"} if any(p in loaded for p in cover_link.AdaptiveCoverPro.PLATFORMS) else set())
    # The WLED lights the light notifications drive: for the whole home, or by room.
    registry, lights = er.async_get(hass), service.home.get("lights") or {}
    is_wled = lambda rule: bool(rule) and getattr(registry.async_get(rule["entity_id"]), "platform", None) == "wled"
    titles = {e.entry_id: e.title for e in service.entries()}
    wled = ([t("Tout le logement")] if is_wled(lights.get("home")) else []) if lights.get("mode") != "rooms" else \
        [titles.get(k, k) for k, rule in (lights.get("rooms") or {}).items() if is_wled(rule)]
    return Facts(alarm=alarm, installed=frozenset(installed), disabled=frozenset(disabled), rooms=rooms, exterior=exterior, configured=bool(service.home.get("configured")), weather=weather, wled=wled,
                 weather_installed=bool(link.get("installed") and link.get("places")), free_areas=free, version=version)
