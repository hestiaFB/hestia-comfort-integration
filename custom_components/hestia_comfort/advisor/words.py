"""Layer 9: the decision in words — the banner, its gain, « Pourquoi ? » — in French, English and German.

The card composes no advice of its own: it shows these words (CAHIER-MOTEUR.md § 14). One idea per line, one advice per
card; a gain always in plain units (°C, humidity points, minutes); the conditional when the twin is not yet sure.
"""
from dataclasses import replace

from .decide import SUBJECTS, Decision, Gesture, main_subject
from .knowing import Tip
from .proof import PROVEN, REINFORCED

TEXTS = {
    "fr": {
        "boost": "Lancez la VMC rapide {minutes} min", "boost_off": "Remettez la VMC en vitesse normale",
        "purify": "Lancez le purificateur {minutes} min", "purify_off": "Arrêtez le purificateur",
        "boosted": "VMC rapide {minutes} min", "purified": "Purificateur {minutes} min", "device_off": "Appareil arrêté",
        "nothing": "Rien à faire", "close": "Refermez", "open": "Aérez {minutes} min", "open_long": "Ouvrez",
        "close_later": "Refermez vers {at} h", "open_later": "Aérez vers {at} h",
        "heat": "vous gardez {value} °C d'ici {hour} h", "heat_open": "{value} °C de mieux d'ici {hour} h",
        "humidity": "{value} points d'humidité en moins", "co2": "l'air redevient sain en {minutes} min",
        "particles": "les particules retombent en {minutes} min", "voc": "le COV retombe en {minutes} min", "energy": "{value} kWh de chauffage économisés",
        "mould": "moins de risque de moisissure sur les murs froids",
        "sure": "{line}", "unsure": "{line}, sans doute",
        "why": "{gesture} : {air} °C à {hour} h", "why_humidity": ", humidité {humidity} %",
        "shut": "Fermée", "open_now": "Ouverte", "aired": "Aérée {minutes} min", "later": "Dans {minutes} min",
        "nothing_line": "Ouverte ou fermée, la pièce restera dans votre plage",
        "nothing_shut": "La pièce restera dans votre plage",
        "try": "À essayer — {title} : {line}",
        "keep_shut": "Gardez fermé : {why}",
        "tonight_close": "Cette nuit, pensez à refermer : {line}", "tonight_open": "Cette nuit, pensez à ouvrir : {line}",
        "safety_rain": "il pleut", "safety_rain_soon": "la pluie arrive", "safety_gusts": "rafales de vent",
        "safety_vigilance": "vigilance météo", "safety_away": "la maison est en mode absence", "safety_frost": "le gel est annoncé",
        "sun": "Soleil sur {window} de {start} à {end}", "sun_strong": "Grand soleil prévu sur {window} de {start} à {end}",
        "sun_now": "Soleil sur {window} jusqu'à {end}", "sun_now_strong": "Grand soleil sur {window} jusqu'à {end}",
        "window": "la fenêtre {direction}", "windows": "les fenêtres {direction}", "window_plain": "les fenêtres",
        "mist": "Buée probable sur les vitres cette nuit ({outdoor} °C dehors)",
        "open_warms": "Laissez ouvert : la pièce a gagné {change} °C depuis {since}",
        "open_cools": "Laissez ouvert : la pièce a perdu {change} °C depuis {since}",
        "time": "{h} h {m:02d}", "time_hour": "{h} h",
        "north": "nord", "north_east": "nord-est", "east": "est", "south_east": "sud-est", "south": "sud",
        "south_west": "sud-ouest", "west": "ouest", "north_west": "nord-ouest",
        "out_humidity": "Humidité {value} % à {hour} h", "out_co2": "CO₂ {value} ppm à {hour} h",
        "out_particles": "Particules {value} µg/m³ à {hour} h", "out_voc": "COV {value} à {hour} h", "out_nothing": "{what} : aucun geste ne ferait vraiment mieux",
        "held_open": "Ouverte : {air} °C à {hour} h", "held_shut": "Fermée : {air} °C à {hour} h",
        "nothing_out": "Ouverte ou fermée : {air} °C à {hour} h", "nothing_out_shut": "Aucun geste ne ferait vraiment mieux : {air} °C à {hour} h",
    },
    "en": {
        "boost": "Run the ventilation fast for {minutes} min", "boost_off": "Set the ventilation back to normal",
        "purify": "Run the purifier for {minutes} min", "purify_off": "Stop the purifier",
        "boosted": "Fast ventilation {minutes} min", "purified": "Purifier {minutes} min", "device_off": "Device stopped",
        "nothing": "Nothing to do", "close": "Close", "open": "Air for {minutes} min", "open_long": "Open",
        "close_later": "Close around {at}:00", "open_later": "Air around {at}:00",
        "heat": "you keep {value} °C until {hour}:00", "heat_open": "{value} °C better by {hour}:00",
        "humidity": "{value} humidity points less", "co2": "the air is fresh again in {minutes} min",
        "particles": "the particles settle in {minutes} min", "voc": "the VOC falls back in {minutes} min", "energy": "{value} kWh of heating saved",
        "mould": "less risk of mould on the cold walls",
        "sure": "{line}", "unsure": "{line}, most likely",
        "why": "{gesture}: {air} °C at {hour}:00", "why_humidity": ", humidity {humidity} %",
        "shut": "Shut", "open_now": "Open", "aired": "Aired {minutes} min", "later": "In {minutes} min",
        "nothing_line": "Open or shut, the room stays in your range",
        "nothing_shut": "The room stays in your range",
        "try": "Worth a try — {title}: {line}",
        "keep_shut": "Keep it shut: {why}",
        "tonight_close": "Tonight, remember to close: {line}", "tonight_open": "Tonight, remember to open: {line}",
        "safety_rain": "it is raining", "safety_rain_soon": "rain is coming", "safety_gusts": "gusts of wind",
        "safety_vigilance": "weather warning", "safety_away": "the home is set to away", "safety_frost": "frost is forecast",
        "sun": "Sun on {window} from {start} to {end}", "sun_strong": "Bright sun expected on {window} from {start} to {end}",
        "sun_now": "Sun on {window} until {end}", "sun_now_strong": "Bright sun on {window} until {end}",
        "window": "the {direction} window", "windows": "the {direction} windows", "window_plain": "the windows",
        "mist": "Misted panes likely tonight ({outdoor} °C outside)",
        "open_warms": "Leave it open: the room gained {change} °C since {since}",
        "open_cools": "Leave it open: the room lost {change} °C since {since}",
        "time": "{h}:{m:02d}", "time_hour": "{h}:00",
        "north": "north", "north_east": "north-east", "east": "east", "south_east": "south-east", "south": "south",
        "south_west": "south-west", "west": "west", "north_west": "north-west",
        "out_humidity": "Humidity {value} % at {hour}:00", "out_co2": "CO₂ {value} ppm at {hour}:00",
        "out_particles": "Particles {value} µg/m³ at {hour}:00", "out_voc": "VOC {value} at {hour}:00", "out_nothing": "{what}: no gesture would really do better",
        "held_open": "Open: {air} °C at {hour}:00", "held_shut": "Shut: {air} °C at {hour}:00",
        "nothing_out": "Open or shut: {air} °C at {hour}:00", "nothing_out_shut": "No gesture would really do better: {air} °C at {hour}:00",
    },
    "de": {
        "boost": "Lüftung {minutes} Min. auf hohe Stufe", "boost_off": "Lüftung zurück auf normale Stufe",
        "purify": "Luftreiniger {minutes} Min. einschalten", "purify_off": "Luftreiniger ausschalten",
        "boosted": "Lüftung hoch {minutes} Min.", "purified": "Luftreiniger {minutes} Min.", "device_off": "Gerät aus",
        "nothing": "Nichts zu tun", "close": "Schließen", "open": "{minutes} Min. lüften", "open_long": "Öffnen",
        "close_later": "Gegen {at} Uhr schließen", "open_later": "Gegen {at} Uhr lüften",
        "heat": "Sie behalten {value} °C bis {hour} Uhr", "heat_open": "{value} °C besser bis {hour} Uhr",
        "humidity": "{value} Punkte weniger Feuchte", "co2": "die Luft ist in {minutes} Min. wieder frisch",
        "particles": "die Partikel setzen sich in {minutes} Min.", "voc": "die VOC sinken in {minutes} Min.", "energy": "{value} kWh Heizenergie gespart",
        "mould": "weniger Schimmelgefahr an kalten Wänden",
        "sure": "{line}", "unsure": "{line}, voraussichtlich",
        "why": "{gesture}: {air} °C um {hour} Uhr", "why_humidity": ", Feuchte {humidity} %",
        "shut": "Geschlossen", "open_now": "Offen", "aired": "{minutes} Min. gelüftet", "later": "In {minutes} Min.",
        "nothing_line": "Offen oder geschlossen, der Raum bleibt in Ihrem Bereich",
        "nothing_shut": "Der Raum bleibt in Ihrem Bereich",
        "try": "Einen Versuch wert — {title}: {line}",
        "keep_shut": "Geschlossen lassen: {why}",
        "tonight_close": "Heute Nacht schließen: {line}", "tonight_open": "Heute Nacht öffnen: {line}",
        "safety_rain": "es regnet", "safety_rain_soon": "Regen kommt", "safety_gusts": "Windböen",
        "safety_vigilance": "Unwetterwarnung", "safety_away": "das Haus ist auf Abwesenheit gestellt", "safety_frost": "Frost ist angesagt",
        "sun": "Sonne auf {window} von {start} bis {end}", "sun_strong": "Viel Sonne erwartet auf {window} von {start} bis {end}",
        "sun_now": "Sonne auf {window} bis {end}", "sun_now_strong": "Viel Sonne auf {window} bis {end}",
        "window": "dem Fenster nach {direction}", "windows": "den Fenstern nach {direction}", "window_plain": "den Fenstern",
        "mist": "Heute Nacht wahrscheinlich beschlagene Scheiben ({outdoor} °C draußen)",
        "open_warms": "Offen lassen: der Raum hat seit {since} {change} °C gewonnen",
        "open_cools": "Offen lassen: der Raum hat seit {since} {change} °C verloren",
        "time": "{h}:{m:02d} Uhr", "time_hour": "{h} Uhr",
        "north": "Norden", "north_east": "Nordosten", "east": "Osten", "south_east": "Südosten", "south": "Süden",
        "south_west": "Südwesten", "west": "Westen", "north_west": "Nordwesten",
        "out_humidity": "Feuchte {value} % um {hour} Uhr", "out_co2": "CO₂ {value} ppm um {hour} Uhr",
        "out_particles": "Partikel {value} µg/m³ um {hour} Uhr", "out_voc": "VOC {value} um {hour} Uhr", "out_nothing": "{what}: keine Geste wäre wirklich besser",
        "held_open": "Offen: {air} °C um {hour} Uhr", "held_shut": "Geschlossen: {air} °C um {hour} Uhr",
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
    if gesture.kind in ("boost", "purify"):
        return words["boosted" if gesture.kind == "boost" else "purified"].format(minutes=gesture.minutes)
    if gesture.kind.endswith("_off"):
        return words["device_off"]
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
    marks = {"minimum": 20.0, "maximum": 24.0, "humidity": 60.0, "co2": 1000.0, "particles": 15.0, "voc": 150.0, **(marks or {})}
    # Something is open when closing is one of the scenarios.
    opened = any(g.kind == "close" for g in decision.scenarios)
    gesture, subject = decision.gesture, subject_of(decision)
    if gesture.after and hour is not None:
        title = words[f"{gesture.kind}_later"].format(at=int(hour + gesture.after / 60 + 0.5) % 24)
    elif gesture.kind == "open":
        title = words["open"].format(minutes=gesture.minutes) if gesture.minutes else words["open_long"]
    else:
        title = words[gesture.kind].format(minutes=gesture.minutes)
    paths = decision.paths
    line = ""
    if gesture.kind == "nothing":
        # « Open or shut » only when something is open; « in your range » only when it is true (31 October, Chambre P at
        # 18 °C, its window open: « la pièce restera dans votre plage » was not).
        idle = paths.get(Gesture("nothing"))
        if decision.passive is not None and idle is not None and idle.air:
            # A gesture held back for want of proof: « open or shut » would say it changes nothing, which is untrue.
            line = words["held_open" if opened else "held_shut"].format(air=_number(idle.air[-1], language), hour=end_hour)
        elif idle is not None and idle.air and not marks["minimum"] <= idle.air[-1] <= marks["maximum"]:
            line = words["nothing_out" if opened else "nothing_out_shut"].format(air=_number(idle.air[-1], language), hour=end_hour)
        elif idle is not None and (beyond := _beyond(idle, marks)):
            # The heat in its range, not the rest (rejeu of 10 days: « dans votre plage » at 77 % of humidity).
            measure, value = beyond
            what = words[f"out_{measure}"].format(value=round(value), hour=end_hour)
            line = words["out_nothing"].format(what=what)
        else:
            line = words["nothing_line" if opened else "nothing_shut"]
    if subject and paths:
        chosen, idle = paths[gesture], paths[Gesture("nothing")]
        if subject == "heat":
            gain = chosen.air[-1] - idle.air[-1]
            line = words["heat" if gesture.kind == "close" else "heat_open"].format(value=_number(abs(gain), language), hour=end_hour)
        elif subject == "humidity" and chosen.humidity and idle.humidity:
            line = words["humidity"].format(value=_number(max(i - c for i, c in zip(idle.humidity, chosen.humidity)), language))
        elif subject in ("co2", "particles", "voc"):
            series = getattr(chosen, subject)
            minutes = _back_under(series, marks[subject]) if series else None
            if minutes:
                line = words[subject].format(minutes=minutes)
        elif subject == "mould":
            line = words["mould"]
        elif subject == "energy":
            line = words["energy"].format(value=_number(idle.spent - chosen.spent, language))
    if decision.rule == "safety" and reason and f"safety_{reason}" in words:
        line = words[f"safety_{reason}"]
    elif gesture.kind == "nothing" and not opened and reason and f"safety_{reason}" in words:
        # A shut room whose openings a safety rule took away: that is why nothing is to do.
        line = words["keep_shut"].format(why=words[f"safety_{reason}"])
    # The conditional is for a gesture's gain, never for « Rien à faire ».
    if line and gesture.kind != "nothing":
        line = words["sure" if sure else "unsure"].format(line=line)
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


def _beyond(path, marks) -> tuple[str, float] | None:
    """The first subject the room ends above its mark: humidity, CO₂, particles."""
    for subject, values in (("humidity", path.humidity), ("co2", path.co2), ("particles", path.particles), ("voc", path.voc)):
        if values and values[-1] > marks[subject]:
            return subject, values[-1]
    return None


def tonight_text(decision: Decision, wake_hour: int, language: str = "fr", marks: dict | None = None) -> str:
    """« Cette nuit, pensez à… » in words (advisor/decide.py `tonight`): the conditional unless the effect is proven."""
    words = TEXTS[language]
    line = phrase(decision, wake_hour, language, sure=decision.level == PROVEN, marks=marks)["line"]
    return words[f"tonight_{decision.gesture.kind}"].format(line=line)


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
    if tip.kind == "mist":
        return words["mist"].format(outdoor=_number(v["outdoor"], language))
    if tip.kind in ("open_warms", "open_cools"):
        return words[tip.kind].format(change=_number(v["change"], language), since=_time(v["since"], words))
    return ""
