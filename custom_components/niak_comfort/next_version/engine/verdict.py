"""The card's banner, in Python: the gesture, the pill and the colour the card shows, for the entities.

A word-for-word port of advice() and slides() in card/src/views/room.ts (titles only, not the explaining line):
tests/test_verdict_parity.py replays every audited situation through both and fails on the first difference."""
import math
import re
from datetime import datetime, timedelta

LEVEL_RANK = {"calm": 0, "neutral": 1, "benefit": 2, "action": 3, "urgent": 4}
PILLS = {"calm": "Tout va bien", "benefit": "À saisir", "action": "Geste conseillé", "urgent": "Attention", "neutral": "À vérifier"}
QUIET = ("drying_unavailable", "drying_slow", "drying_night", "drying_alone", "opening_blocked", "cooling_unavailable", "precool_later")
NEED_PILLS = {"dry": "Trop humide", "heat": "Trop frais", "cool": "Trop chaud", "air": "Air à renouveler"}
NEED_DISKS = {"dry": "drop", "heat": "temp", "cool": "temp", "air": "air"}
COMPASS = ("nord", "nord-est", "est", "sud-est", "sud", "sud-ouest", "ouest", "nord-ouest")

# The pill, as a stable state for automations; its words stay in the translations.
STATES = {"Tout va bien": "calm", "Au mieux": "best", "À saisir": "benefit", "Geste conseillé": "action", "Attention": "urgent",
          "À vérifier": "neutral", "Conseil optimisé": "optimized", "Trop frais": "too_cold", "Démarrage": "starting",
          "Capteurs muets": "sensors_silent", "Un capteur muet": "sensor_silent"}
# The card's colours (hestia-charte.css, oklch converted to sRGB): blue all is well, green a benefit, orange a gesture.
COLOURS = {"calm": (170, 214, 229), "best": (170, 214, 229), "benefit": (165, 214, 174), "action": (241, 178, 119),
           "urgent": (234, 140, 143), "neutral": (177, 177, 177)}
# The same hues, saturated, for a coloured light: a pastel looks white on a LED.
HUES = {"calm": 195, "best": 195, "benefit": 131, "action": 29, "urgent": 358, "neutral": None}
GESTURES = ("none", "open", "keep_open", "close", "keep_closed", "later", "ventilation", "heat", "covers", "check_outside", "check_sensors")
# What asks the person to act now: the LED's « something to do ».
ACTING = ("open", "close", "ventilation", "heat", "covers", "check_outside")
HUMIDITY = ("normal", "slightly_humid", "humid", "very_humid", "slightly_dry", "dry", "very_dry")


def _get(d, *keys):
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def _round(x):
    """Math.round: halves go up."""
    return math.floor(x + 0.5)


def numeric(r):
    v = r.get("value") if isinstance(r, dict) else None
    return v if isinstance(r, dict) and r.get("quality") == "valid" and isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None


def _hour(iso, local):
    h = local(datetime.fromisoformat(iso)).hour
    return "minuit" if h == 0 else "midi" if h == 12 else f"{h} h"


def _rain_clock(d):
    m = d.minute // 5 * 5
    return f"{d.hour} h" + (f" {m:02d}" if m else "")


def _wind_from(bearing):
    if bearing is None or not math.isfinite(bearing):
        return ""
    name = COMPASS[_round(((bearing % 360) + 360) % 360 / 45) % 8]
    return "vent " + ("d’" + name if name in ("est", "ouest") else "du " + name if name in ("nord", "sud") else "de " + name)


def _failed(v):
    obs = v.get("observations") or {}
    return [k for k in v["assessment"].get("missing", []) if obs.get(k) and k != "pollution"]


def unreadable(v):
    failed = _failed(v)
    return "indoor_temperature" in failed or len(failed) >= 3


def cold_settled(a):
    w = _get(a, "features", "warmth")
    return (not w or bool(w.get("slight")) or w.get("heating") is not None or bool(w.get("thermostat")) or w.get("occupied") is False
            or bool(w.get("outdoor_warms")) or bool(w.get("warming")))


def humidity_label(v):
    """The room's humidity in the card's words, as a state: normal, slightly_humid … very_dry; None if unknown."""
    if numeric((v.get("observations") or {}).get("indoor_humidity")) is None:
        return None
    humidity = _get(v["assessment"], "features", "humidity")
    if not humidity or not humidity.get("status"):
        return "humid" if "dry" in v["assessment"].get("needs", []) else None
    status = humidity["status"]
    if status == "unknown":
        return None
    if status == "normal":
        return "normal"
    wet = status == "high"
    degree = humidity.get("degree")
    return ("slightly_" if degree == 1 else "very_" if degree == 3 else "") + ("humid" if wet else "dry")


def _with_learning(v, out):
    a = v["assessment"]
    learned = _get(a, "features", "learned")
    if learned and learned.get("closing") and a["action"] == "fermer":
        return {**out, "learned": "appris dans cette pièce", "pill": "Conseil optimisé"}
    if not learned or a["action"] not in ("ouvrir", "ok"):
        return out
    title = out["title"]
    if a["action"] == "ouvrir" and re.match(r"^(Aérez|Ouvrez) ", title):
        title = f"{title.split(' ')[0]} {learned['minutes']} min"
    return {**out, "title": title, "learned": f"d’après {learned['openings']} aérations", "pill": "Conseil optimisé"}


def advice(v, local=lambda d: d.astimezone()):
    """The banner of the card for this view: title, disk, cap, and the pill and level when they are not the engine's."""
    a = v["assessment"]
    out = _with_learning(v, _gesture(v, local))
    # The gesture made, the window open while it still helps: nothing better to do, in blue. « Vous pouvez refermer » is orange again.
    if gesture_key(out["title"], out["disk"]) == "keep_open" and a["level"] in ("action", "benefit"):
        return {**out, "pill": "Au mieux", "level": "calm"}
    humidity, label = _get(a, "features", "humidity"), humidity_label(v)
    if (label and humidity and humidity.get("status") and a["reason"] != "shared_volume" and a["level"] in ("calm", "neutral")
            and not unreadable(v) and a["action"] != "fermer"
            and not any(n not in ("dry", "precool") and (n != "heat" or not cold_settled(a)) for n in a.get("needs", []))):
        if humidity["status"] == "normal" and out.get("pill") == "Trop humide":
            return {**out, "pill": None, "disk": "check", "level": a["level"]}
        if humidity["status"] in ("low", "high"):
            return {**out, "pill": "Au mieux", "disk": "drop", "level": "calm"}
    if a["action"] == "fermer" and not out.get("cap"):
        names = v.get("names") or {}
        opened = [names.get(o["entity_id"], o["entity_id"]) for o in a.get("openings") or [] if o.get("open")]
        if opened:
            return {**out, "cap": f"{len(opened)} ouvertures" if len(opened) > 2 else " et ".join(opened)}
    return out


def _gesture(v, local):
    a = v["assessment"]
    features = a.get("features") or {}
    vol = features.get("volume")
    if a["reason"] == "shared_volume" and vol and vol.get("assessment"):
        lead = vol["assessment"]
        return advice({**v, "observations": vol.get("observations") or v.get("observations"),
                       "assessment": {**a, **lead, "features": {**features, **(lead.get("features") or {}), "volume": None}}}, local)
    o = v.get("observations") or {}
    names = v.get("names") or {}
    opened = any(k.startswith("window:") and r.get("quality") == "valid" and r.get("value") is True for k, r in o.items())
    first = next((names.get(e, e) for e in a.get("open_first") or []), None)
    slot = a.get("slot")
    duration = _get(features, "ventilation", "duration_minutes")
    drying = features.get("drying")
    span = f"{duration['min']} à {duration['max']} min" if duration else None
    opened_for = _get(features, "ventilation", "opened_minutes")

    def airing(verb, fallback):
        if a["action"] == "ok":
            if duration and opened_for is not None:
                left, since = _round(duration["max"] - opened_for), f"ouvert depuis {_round(opened_for)} min"
                return ({"title": f"Encore {left} min d’aération", "disk": "open", "cap": since} if left > 0
                        else {"title": "Vous pouvez refermer", "disk": "shut", "cap": since})
            return {"title": "Aération en cours", "disk": "open", "cap": f"{span} au total" if span else None}
        rain = features.get("rain_ahead")
        shut = (_rain_clock(local(datetime.fromisoformat(v["computed_at"]) + timedelta(minutes=rain["minutes"] - 5)))
                if rain and rain["minutes"] <= ((duration or {}).get("max") or 15) + 15 else None)
        return {"title": f"{verb} {span}" if span else fallback, "disk": "open", "cap": f"Refermez avant {shut}" if shut else first}

    failed = _failed(v)
    if unreadable(v) and v.get("starting"):
        return {"title": "Mesures en chargement", "disk": "clock", "pill": "Démarrage", "level": "neutral"}
    if unreadable(v):
        return {"title": "Mesures absentes", "disk": "mute", "pill": "Capteurs muets", "level": "neutral"}
    needs, reason, action = a.get("needs", []), a["reason"], a["action"]
    quiet = ((reason in QUIET and a["level"] in ("calm", "neutral")) or reason in ("humid_outdoor", "open_neutral", "drying_unavailable")
             or (reason == "drying_slow" and _get(features, "air", "ventilation", "on") is not False)
             or (reason == "heat_needed" and action != "fermer" and a["level"] != "action"))
    if quiet and action != "fermer":
        out = {"title": "Rien à faire", "disk": "open" if opened else "check", "cap": "Fenêtre ouverte" if opened else None}
        if needs:
            unsettled = "heat" in needs and not cold_settled(a)
            need = "heat" if unsettled else "dry" if "dry" in needs else needs[0]
            out.update(pill=NEED_PILLS["heat"] if unsettled else "Au mieux", level="neutral" if unsettled else "calm")
            if not opened:
                out["disk"] = NEED_DISKS.get(need, "info")
        return out
    if reason == "within_comfort":
        return {"title": "Rien à faire", "disk": "open" if opened else "check", "cap": "Fenêtre ouverte" if opened else None}
    if reason == "rain_open_windows":
        return {"title": "Fermez, il pleut", "disk": "rain"}
    if reason == "gust_open_windows":
        return {"title": "Fermez, vent fort", "disk": "shut"}
    if reason in ("alarm_open", "exchange_harmful", "rehumidification_risk", "voc_outdoor"):
        return {"title": "Refermez", "disk": "shut"}
    if reason == "rain_soon":
        return {"title": "Refermez avant la pluie", "disk": "rain"}
    if reason == "opening_blocked":
        return {"title": "Refermez", "disk": "shut"} if action == "fermer" else {"title": "Gardez fermé", "disk": "window"}
    if reason == "short_air_change":
        return {"title": "Aération en cours" if action == "ok" else "Aérez 5 minutes", "disk": "open", "cap": None if action == "ok" else "Puis refermez"}
    if reason == "air_needed":
        return airing("Aérez", "Renouvelez l’air")
    if reason == "cooling_possible":
        return airing("Ouvrez", "Ouvrez pour rafraîchir")
    if reason == "warming_possible":
        return {"title": "Laissez ouvert" if action == "ok" else "Ouvrez pour réchauffer", "disk": "open", "cap": first}
    if reason == "precool_possible":
        return {"title": "Laissez ouvert cette nuit" if action == "ok" else "Ouvrez pour la nuit", "disk": "moon", "cap": first}
    if reason in ("precool_later", "cooling_unavailable"):
        if slot and slot.get("kind") == "open":
            return {"title": f"Ouvrez vers {_hour(slot['time'], local)}", "disk": "moon",
                    "cap": _wind_from(slot["wind_bearing"]) if slot.get("wind_bearing") is not None else None}
        return {"title": "Gardez fermé", "disk": "clock"}
    if reason == "shared_volume":
        return ({"title": "Refermez", "disk": "shut", "cap": "Même air"} if action == "fermer"
                else {"title": "Laissez ouvert", "disk": "open", "cap": "Même air"} if action == "ok"
                else {"title": "Aérez", "disk": "open", "cap": first or "Même air"})
    if reason == "drying_possible":
        out = airing("Aérez", "Aérez pour assécher")
        if ((drying or {}).get("openings") or 0) >= 5 and not out.get("learned"):
            out["learned"] = f"d’après {drying['openings']} aérations"
        return out
    if reason == "drying_later":
        later = (drying or {}).get("later")
        if later:
            out = {"title": f"Aérez vers {_hour(later['time'], local)}", "disk": "clock"}
            if ((drying or {}).get("openings") or 0) >= 5:
                out["learned"] = f"d’après {drying['openings']} aérations"
            return out
        return {"title": "Aérez plus tard", "disk": "clock"}
    if reason == "drying_slow":
        return {"title": "Lancez la VMC", "disk": "vmc", "cap": "Aérer assèche peu ici"}
    if reason == "ventilation_possible":
        return {"title": "Lancez la VMC", "disk": "vmc", "cap": "Elle assèchera mieux"}
    if reason == "warm_walls":
        return {"title": "Chauffez un peu plus", "disk": "heat", "cap": "Risque de moisissure"}
    if reason == "heat_needed":
        return ({"title": "Refermez", "disk": "shut"} if action == "fermer"
                else {"title": "Rallumez le chauffage", "disk": "heat", "cap": "Le chauffage est coupé"})
    if reason == "sun_entering":
        return {"title": "Fermez côté soleil", "disk": "shut"}
    if reason == "shutter_protection":
        return {"title": "Adaptez les volets", "disk": "window"}
    if reason == "optional_air_change":
        return {"title": "Aérez si possible", "disk": "open"}
    if reason == "verify_exterior":
        title = ("Renouvelez l’air" if "air" in needs else "Ouvrez pour rafraîchir" if "cool" in needs
                 else "Aérez pour assécher" if "dry" in needs else "Vérifiez dehors")
        return {"title": title, "disk": "ask", "cap": "Si le temps le permet"}
    if reason == "incomplete_data":
        if failed:
            return {"title": "Rien à faire", "disk": "check", "pill": "Capteurs muets" if len(failed) > 1 else "Un capteur muet", "level": "neutral"}
        return {"title": "Bilan partiel", "disk": "check"}
    return ({"title": "Refermez", "disk": "shut"} if action == "fermer" else {"title": "Aérez", "disk": "open"} if action == "ouvrir"
            else {"title": "Rien à faire", "disk": "check"})


def gesture_key(title, disk):
    """The gesture as a stable state: what an automation tests, whatever the words."""
    if disk == "ask":
        return "check_outside"
    if title.startswith("Mesures"):
        return "check_sensors"
    if title in ("Rien à faire", "Bilan partiel"):
        return "none"
    if title.startswith(("Aérez vers", "Ouvrez vers")) or title == "Aérez plus tard":
        return "later"
    if title == "Lancez la VMC":
        return "ventilation"
    if title in ("Chauffez un peu plus", "Rallumez le chauffage"):
        return "heat"
    if title == "Gardez fermé":
        return "keep_closed"
    if title.startswith(("Refermez", "Fermez", "Vous pouvez refermer")):
        return "close"
    if title.startswith(("Laissez ouvert", "Encore ")) or title == "Aération en cours":
        return "keep_open"
    if title == "Adaptez les volets":
        return "covers"
    return "open"


def verdict(v, local=lambda d: d.astimezone()):
    """What the card's banner says, as states: the title, its gesture, the pill, the mood and its colour."""
    a = v["assessment"]
    main = advice(v, local)
    level = main.get("level") or a["level"]
    pill = main.get("pill") or PILLS[a["level"]]
    mood = "best" if pill == "Au mieux" else level
    rgb = COLOURS.get(mood, COLOURS["neutral"])
    return {"title": main["title"], "gesture": gesture_key(main["title"], main["disk"]), "cap": main.get("cap"),
            "learned": main.get("learned"), "disk": main["disk"], "pill": pill, "state": STATES.get(pill, level),
            "level": level, "mood": mood, "colour": "#%02x%02x%02x" % rgb, "rgb": list(rgb), "hue": HUES.get(mood),
            "humidity": humidity_label(v)}


def strongest(verdicts):
    """The verdict that weighs most among several (rooms of one air, the whole home): a gesture before a calm room."""
    return max(verdicts, key=lambda x: (x["gesture"] in ACTING, LEVEL_RANK.get(x["level"], 0)), default=None)
