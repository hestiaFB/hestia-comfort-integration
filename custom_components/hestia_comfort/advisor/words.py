"""Layer 9: the decision in words — the banner, its gain, « Pourquoi ? » — in French, English and German.

The card composes no advice of its own: it shows these words (CAHIER-MOTEUR.md § 14). One idea per line, one advice per
card; a gain always in plain units (°C, humidity points, minutes); the conditional when the twin is not yet sure.
"""
from dataclasses import replace

from .decide import SUBJECTS, Decision, Gesture, main_subject
from .knowing import Tip
from .proof import REINFORCED

TEXTS = {
    "fr": {
        "nothing": "Rien à faire", "close": "Refermez", "open": "Aérez {minutes} min", "open_long": "Ouvrez",
        "close_later": "Refermez vers {at} h", "open_later": "Aérez vers {at} h",
        "heat": "vous gardez {value} °C d'ici {hour} h", "heat_open": "{value} °C de mieux d'ici {hour} h",
        "humidity": "{value} points d'humidité en moins", "co2": "l'air redevient sain en {minutes} min",
        "particles": "les particules retombent en {minutes} min", "energy": "{value} kWh de chauffage économisés",
        "sure": "{line}", "unsure": "{line}, sans doute",
        "why": "{gesture} : {air} °C à {hour} h", "why_humidity": ", humidité {humidity} %",
        "shut": "Fermée", "open_now": "Ouverte", "aired": "Aérée {minutes} min", "later": "Dans {minutes} min",
        "nothing_line": "Ouverte ou fermée, la pièce restera dans votre plage",
        "nothing_shut": "La pièce restera dans votre plage",
        "try": "À essayer — {title} : {line}",
        "keep_shut": "Gardez fermé : {why}",
        "safety_rain": "il pleut", "safety_rain_soon": "la pluie arrive", "safety_gusts": "rafales de vent",
        "safety_vigilance": "vigilance météo", "safety_away": "la maison est en mode absence",
        "sun": "Soleil sur {window} de {start} à {end}", "sun_strong": "Grand soleil prévu sur {window} de {start} à {end}",
        "sun_now": "Soleil sur {window} jusqu'à {end}", "sun_now_strong": "Grand soleil sur {window} jusqu'à {end}",
        "window": "la fenêtre {direction}", "windows": "les fenêtres {direction}", "window_plain": "les fenêtres",
        "open_warms": "Laissez ouvert : la pièce a gagné {change} °C depuis {since}",
        "open_cools": "Laissez ouvert : la pièce a perdu {change} °C depuis {since}",
        "time": "{h} h {m:02d}", "time_hour": "{h} h",
        "north": "nord", "north_east": "nord-est", "east": "est", "south_east": "sud-est", "south": "sud",
        "south_west": "sud-ouest", "west": "ouest", "north_west": "nord-ouest",
        "nothing_out": "Ouverte ou fermée : {air} °C à {hour} h", "nothing_out_shut": "Aucun geste ne ferait vraiment mieux : {air} °C à {hour} h",
    },
    "en": {
        "nothing": "Nothing to do", "close": "Close", "open": "Air for {minutes} min", "open_long": "Open",
        "close_later": "Close around {at}:00", "open_later": "Air around {at}:00",
        "heat": "you keep {value} °C until {hour}:00", "heat_open": "{value} °C better by {hour}:00",
        "humidity": "{value} humidity points less", "co2": "the air is fresh again in {minutes} min",
        "particles": "the particles settle in {minutes} min", "energy": "{value} kWh of heating saved",
        "sure": "{line}", "unsure": "{line}, most likely",
        "why": "{gesture}: {air} °C at {hour}:00", "why_humidity": ", humidity {humidity} %",
        "shut": "Shut", "open_now": "Open", "aired": "Aired {minutes} min", "later": "In {minutes} min",
        "nothing_line": "Open or shut, the room stays in your range",
        "nothing_shut": "The room stays in your range",
        "try": "Worth a try — {title}: {line}",
        "keep_shut": "Keep it shut: {why}",
        "safety_rain": "it is raining", "safety_rain_soon": "rain is coming", "safety_gusts": "gusts of wind",
        "safety_vigilance": "weather warning", "safety_away": "the home is set to away",
        "sun": "Sun on {window} from {start} to {end}", "sun_strong": "Bright sun expected on {window} from {start} to {end}",
        "sun_now": "Sun on {window} until {end}", "sun_now_strong": "Bright sun on {window} until {end}",
        "window": "the {direction} window", "windows": "the {direction} windows", "window_plain": "the windows",
        "open_warms": "Leave it open: the room gained {change} °C since {since}",
        "open_cools": "Leave it open: the room lost {change} °C since {since}",
        "time": "{h}:{m:02d}", "time_hour": "{h}:00",
        "north": "north", "north_east": "north-east", "east": "east", "south_east": "south-east", "south": "south",
        "south_west": "south-west", "west": "west", "north_west": "north-west",
        "nothing_out": "Open or shut: {air} °C at {hour}:00", "nothing_out_shut": "No gesture would really do better: {air} °C at {hour}:00",
    },
    "de": {
        "nothing": "Nichts zu tun", "close": "Schließen", "open": "{minutes} Min. lüften", "open_long": "Öffnen",
        "close_later": "Gegen {at} Uhr schließen", "open_later": "Gegen {at} Uhr lüften",
        "heat": "Sie behalten {value} °C bis {hour} Uhr", "heat_open": "{value} °C besser bis {hour} Uhr",
        "humidity": "{value} Punkte weniger Feuchte", "co2": "die Luft ist in {minutes} Min. wieder frisch",
        "particles": "die Partikel setzen sich in {minutes} Min.", "energy": "{value} kWh Heizenergie gespart",
        "sure": "{line}", "unsure": "{line}, voraussichtlich",
        "why": "{gesture}: {air} °C um {hour} Uhr", "why_humidity": ", Feuchte {humidity} %",
        "shut": "Geschlossen", "open_now": "Offen", "aired": "{minutes} Min. gelüftet", "later": "In {minutes} Min.",
        "nothing_line": "Offen oder geschlossen, der Raum bleibt in Ihrem Bereich",
        "nothing_shut": "Der Raum bleibt in Ihrem Bereich",
        "try": "Einen Versuch wert — {title}: {line}",
        "keep_shut": "Geschlossen lassen: {why}",
        "safety_rain": "es regnet", "safety_rain_soon": "Regen kommt", "safety_gusts": "Windböen",
        "safety_vigilance": "Unwetterwarnung", "safety_away": "das Haus ist auf Abwesenheit gestellt",
        "sun": "Sonne auf {window} von {start} bis {end}", "sun_strong": "Viel Sonne erwartet auf {window} von {start} bis {end}",
        "sun_now": "Sonne auf {window} bis {end}", "sun_now_strong": "Viel Sonne auf {window} bis {end}",
        "window": "dem Fenster nach {direction}", "windows": "den Fenstern nach {direction}", "window_plain": "den Fenstern",
        "open_warms": "Offen lassen: der Raum hat seit {since} {change} °C gewonnen",
        "open_cools": "Offen lassen: der Raum hat seit {since} {change} °C verloren",
        "time": "{h}:{m:02d} Uhr", "time_hour": "{h} Uhr",
        "north": "Norden", "north_east": "Nordosten", "east": "Osten", "south_east": "Südosten", "south": "Süden",
        "south_west": "Südwesten", "west": "Westen", "north_west": "Nordwesten",
        "nothing_out": "Offen oder geschlossen: {air} °C um {hour} Uhr", "nothing_out_shut": "Keine Geste wäre wirklich besser: {air} °C um {hour} Uhr",
    },
}
STEP_MINUTES = 5


def subject_of(decision: Decision) -> str | None:
    """What the advised gesture mostly does: the cost term it lowers the most against « do nothing »."""
    return main_subject(decision.scenarios, decision.gesture)


def _number(value: float, language: str) -> str:
    """One decimal, as the card shows temperatures, with the language's decimal mark."""
    text = f"{value:.1f}"
    return text.replace(".", ",") if language in ("fr", "de") else text


def _back_under(values: list[float], mark: float) -> int | None:
    """Minutes until a series comes back under a mark."""
    for k, v in enumerate(values):
        if v <= mark:
            return (k + 1) * STEP_MINUTES
    return None


def _name(gesture: Gesture, path, words, opened: bool) -> str:
    """How « Pourquoi ? » names a scenario: by the state of the windows it leaves."""
    if gesture.after:
        return words["later"].format(minutes=gesture.after)
    if gesture.kind == "open":
        return words["aired"].format(minutes=gesture.minutes) if gesture.minutes else words["open_now"]
    if gesture.kind == "nothing" and opened:
        return words["open_now"]
    return words["shut"]


def phrase(decision: Decision, end_hour: int, language: str = "fr", sure: bool = True,
           marks: dict | None = None, hour: float | None = None, reason: str | None = None) -> dict:
    """The banner's title and line, and the lines of « Pourquoi ? »; `hour`: the local time now, for a later gesture;
    `marks`: the room's range and marks, as `Comfort` holds them; `reason`: the safety rule that shuts, if one does
    (advisor/safety.py)."""
    words = TEXTS[language]
    # A reinforced effect is said in the conditional (CAHIER-MOTEUR.md § 4.1).
    sure = sure and decision.level != REINFORCED
    marks = {"minimum": 20.0, "maximum": 24.0, "co2": 1000.0, "particles": 15.0, **(marks or {})}
    # Something is open when closing is one of the scenarios.
    opened = any(g.kind == "close" for g in decision.scenarios)
    gesture, subject = decision.gesture, subject_of(decision)
    if gesture.after and hour is not None:
        title = words[f"{gesture.kind}_later"].format(at=int(hour + gesture.after / 60 + 0.5) % 24)
    elif gesture.kind == "open":
        title = words["open"].format(minutes=gesture.minutes) if gesture.minutes else words["open_long"]
    else:
        title = words[gesture.kind]
    paths = decision.paths
    line = ""
    if gesture.kind == "nothing":
        # « Open or shut » only when something is open; « in your range » only when it is true (31 October, Chambre P at
        # 18 °C, its window open: « la pièce restera dans votre plage » was not).
        idle = paths.get(Gesture("nothing"))
        if idle is not None and idle.air and not marks["minimum"] <= idle.air[-1] <= marks["maximum"]:
            line = words["nothing_out" if opened else "nothing_out_shut"].format(air=_number(idle.air[-1], language), hour=end_hour)
        else:
            line = words["nothing_line" if opened else "nothing_shut"]
    if subject and paths:
        chosen, idle = paths[gesture], paths[Gesture("nothing")]
        if subject == "heat":
            gain = chosen.air[-1] - idle.air[-1]
            line = words["heat" if gesture.kind == "close" else "heat_open"].format(value=_number(abs(gain), language), hour=end_hour)
        elif subject == "humidity" and chosen.humidity and idle.humidity:
            line = words["humidity"].format(value=_number(max(i - c for i, c in zip(idle.humidity, chosen.humidity)), language))
        elif subject in ("co2", "particles"):
            series = chosen.co2 if subject == "co2" else chosen.particles
            minutes = _back_under(series, marks[subject]) if series else None
            if minutes:
                line = words[subject].format(minutes=minutes)
        elif subject == "energy":
            line = words["energy"].format(value=_number(idle.spent - chosen.spent, language))
    if decision.rule == "safety" and reason and f"safety_{reason}" in words:
        line = words[f"safety_{reason}"]
    elif gesture.kind == "nothing" and not opened and reason and f"safety_{reason}" in words:
        # A shut room whose openings a safety rule took away: that is why nothing is to do.
        line = words["keep_shut"].format(why=words[f"safety_{reason}"])
    line = words["sure" if sure else "unsure"].format(line=line) if line else line
    # « Pourquoi ? » compares two or three scenarios (CAHIER-MOTEUR.md § 14): doing nothing, the advice, and the best
    # other one when it differs.
    shown = [Gesture("nothing"), gesture]
    others = sorted((g for g in decision.scenarios if g not in shown), key=lambda g: decision.scenarios[g]["total"])
    shown += others[:1]
    why = []
    for g in dict.fromkeys(shown):
        path = paths.get(g)
        if path is not None and path.air:
            text = words["why"].format(gesture=_name(g, path, words, opened), air=_number(path.air[-1], language), hour=end_hour)
            if path.humidity:
                text += words["why_humidity"].format(humidity=round(path.humidity[-1]))
            why.append(text)
    out = {"title": title, "line": line, "subject": subject, "why": why, "try": None}
    if decision.passive is not None:
        # Held back for want of proof: said as a passive advice, to try.
        tried = phrase(replace(decision, gesture=decision.passive, passive=None, rule="best"), end_hour, language,
                       sure=False, marks=marks, hour=hour)
        out["try"] = words["try"].format(title=tried["title"], line=tried["line"]) if tried["line"] else tried["title"]
    return out


def _time(when, words) -> str:
    return words["time_hour"].format(h=when.hour) if when.minute == 0 else words["time"].format(h=when.hour, m=when.minute)


def tip_text(tip: Tip, language: str = "fr", now=None) -> str:
    """A « Bon à savoir » tip in words."""
    words = TEXTS[language]
    v = tip.values
    if tip.kind == "sun":
        if v["direction"] is None:
            window = words["window_plain"]
        else:
            window = words["windows" if v["windows"] > 1 else "window"].format(direction=words[v["direction"]])
        going = now is not None and v["start"] <= now
        key = ("sun_now" if going else "sun") + ("_strong" if tip.level == REINFORCED else "")
        return words[key].format(window=window, start=_time(v["start"], words), end=_time(v["end"], words))
    if tip.kind in ("open_warms", "open_cools"):
        return words[tip.kind].format(change=_number(v["change"], language), since=_time(v["since"], words))
    return ""
