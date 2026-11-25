"""Why a room's learning does not start, and what to set for it to start (forum, 25 November: « bloqué à 0 % »).

Both learnings read Home Assistant's history: the twin of each room (room/learning.py) needs the room's temperature and
humidity and the outdoor ones, the nightly learning (advisor_home.py) the room's temperature and the outdoor one, over
three days at least (advisor/nightly.py MIN_DAYS). Without one of them nothing was learned, without a word: the room
stayed at 0 %. Since engine 3.23.0 a missing outdoor measure is taken from Open-Meteo's past hours (forecast_past.py):
the room learns, less finely, and is told so as a tip. Each cause found here is said in the « Confort » home, the room's « Apprentissage » page, its card, and
in one of Home Assistant's repairs."""
from __future__ import annotations

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .engine.i18n import N_, speaking, t

ISSUE = "learning_blocked"
# The nightly learning reads at least this many days (advisor/nightly.py MIN_DAYS).
MIN_KEPT_DAYS = 3
# Measures without which nothing is learned; without the others, only the temperature is.
NEEDED = ("indoor_temperature", "outdoor_temperature")
HUMIDITY = ("indoor_humidity", "outdoor_humidity")
OUTDOOR = ("outdoor_temperature", "outdoor_humidity")
NAMES = {"indoor_temperature": N_("la température de la pièce"), "outdoor_temperature": N_("la température du dehors"),
         "indoor_humidity": N_("l’humidité de la pièce"), "outdoor_humidity": N_("l’humidité du dehors")}


def _recorded(hass, entity_id):
    """Whether the recorder keeps this entity's history (its `exclude`, or an `include` that leaves it out)."""
    try:
        from homeassistant.components.recorder import is_entity_recorded
        return is_entity_recorded(hass, entity_id)
    except Exception:  # noqa: BLE001 - unknown is not said to be a fault
        return True


def _kept_days(hass):
    try:
        from homeassistant.components.recorder import get_instance
        days = get_instance(hass).keep_days
        return days if isinstance(days, int) else None
    except Exception:  # noqa: BLE001
        return None


def blocks(hass: HomeAssistant, sources: dict, weather_linked: bool = False, unread: bool = False,
           forecast: bool = False) -> list[dict]:
    """What stops a room's learning: {"cause", "scope", "key"?, "entity_id"?, "days"?}, the causes stopping everything
    (scope « all ») first, then those that only keep the humidity from being learned (scope « part »).

    `sources`: the room's measures as the learning reads them ({key: entity_id or None}); `weather_linked`: the home's
    outside comes from Hestia Weather (a place without a station then gives no outdoor measure); `unread`: the last
    reading of the history failed; `forecast`: Open-Meteo's past hours stand in for a missing outdoor measure
    (forecast_past.py, engine 3.23.0), the room then learns, less precisely."""
    found = []
    if "recorder" not in hass.config.components:
        return [{"cause": "recorder", "scope": "all"}]
    if (days := _kept_days(hass)) is not None and days < MIN_KEPT_DAYS:
        found.append({"cause": "short_history", "scope": "all", "days": days})
    for key in (*NEEDED, *HUMIDITY):
        scope = "all" if key in NEEDED else "part"
        entity_id = sources.get(key)
        if not entity_id and forecast and key in OUTDOOR:
            found.append({"cause": "forecast", "scope": "part", "key": key})
        elif not entity_id:
            cause = "no_station" if key == "outdoor_temperature" and weather_linked else "missing"
            found.append({"cause": cause, "scope": scope, "key": key})
        elif not _recorded(hass, entity_id):
            state = hass.states.get(entity_id)
            found.append({"cause": "not_recorded", "scope": scope, "key": key, "entity_id": entity_id,
                          "name": str(state.attributes.get("friendly_name") or entity_id) if state else entity_id})
    # The outdoor humidity is missing because the station is: one cause, said once.
    if any(b["cause"] == "no_station" for b in found):
        found = [b for b in found if not (b["cause"] == "missing" and b["key"] == "outdoor_humidity")]
    if any(b["cause"] == "forecast" and b["key"] == "outdoor_temperature" for b in found):
        found = [b for b in found if not (b["cause"] == "forecast" and b["key"] == "outdoor_humidity")]
    if unread and not any(b["scope"] == "all" for b in found):
        found.append({"cause": "unread", "scope": "all"})
    found.sort(key=lambda b: b["scope"] != "all")
    return found


def text(block: dict) -> str:
    """The cause in a few words, then what to set, in the language of the request."""
    cause, key = block["cause"], block.get("key")
    if cause == "recorder":
        return t("L’historique de Home Assistant (recorder) n’est pas chargé : rien ne peut être appris. Remettez « recorder: » ou « default_config: » dans configuration.yaml.")
    if cause == "short_history":
        return t("L’historique de Home Assistant ne garde que {days} j (purge_keep_days) : il en faut au moins 3. Montez-le à 10, la valeur par défaut.", days=block["days"])
    if cause == "forecast" and key == "outdoor_temperature":
        return t("Le dehors est pris des prévisions, faute de capteur extérieur : la pièce apprend, mais moins finement. Pour mieux, choisissez une température et une humidité extérieures dans Extérieur.")
    if cause == "forecast":
        return t("L’humidité du dehors est prise des prévisions, faute de capteur : pour mieux, choisissez-la dans Extérieur.")
    if cause == "no_station":
        return t("Le lieu Hestia Weather n’a pas de station : ses prévisions servent aux conseils, mais l’apprentissage a besoin d’un vrai capteur du dehors. Choisissez une température et une humidité extérieures dans Extérieur.")
    if cause == "missing" and key == "outdoor_temperature":
        return t("Pas de température du dehors : choisissez-la dans Extérieur.")
    if cause == "missing" and key == "indoor_temperature":
        return t("Pas de température dans la pièce : choisissez-la dans la pièce, Modifier.")
    if cause == "missing" and key == "outdoor_humidity":
        return t("Pas d’humidité du dehors : seule la température est apprise. Choisissez-la dans Extérieur.")
    if cause == "missing":
        return t("Pas d’humidité dans la pièce : seule la température est apprise.")
    if cause == "not_recorded":
        return t("« {name} » ({subject}) n’est pas gardé par l’historique de Home Assistant : retirez-le des exclusions du recorder dans configuration.yaml.",
                 name=block.get("name") or block.get("entity_id"), subject=t(NAMES[key]))
    return t("L’historique n’a pas pu être lu : voyez le journal de Home Assistant (cherchez « comfort »).")


def described(found: list[dict]) -> list[dict]:
    """The causes with their text, for the panel and the card."""
    return [{**b, "text": text(b)} for b in found]


@callback
def async_update_issue(hass: HomeAssistant) -> None:
    """One repair for the whole home while a room learns nothing: what stops it, and which rooms. Removed once every room
    learns again."""
    stopped = {}
    for entry in hass.config_entries.async_entries(DOMAIN):
        coordinator = getattr(entry, "runtime_data", None)
        if entry.data.get("home") or not hasattr(coordinator, "learning_blocked"):
            continue
        for block in coordinator.learning_blocked():
            if block["scope"] == "all":
                stopped.setdefault(_signature(block), (block, []))[1].append(entry.title)
    if not stopped:
        ir.async_delete_issue(hass, DOMAIN, ISSUE)
        return
    with speaking(hass.config.language):
        items = "\n".join(f"- {text(block)} ({', '.join(sorted(rooms))})" for block, rooms in stopped.values())
    ir.async_create_issue(hass, DOMAIN, ISSUE, is_fixable=False, is_persistent=False, severity=ir.IssueSeverity.WARNING,
                          translation_key=ISSUE, translation_placeholders={"items": items})


def _signature(block):
    return (block["cause"], block.get("key"), block.get("entity_id"))
