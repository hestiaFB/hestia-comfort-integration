"""Layer 9: the decision in words — the banner, its gain, « Pourquoi ? » — in French, English and German.

The card composes no advice of its own: it shows these words (CAHIER-MOTEUR.md § 14). One idea per line, one advice per
card; a gain always in plain units (°C, humidity points, minutes); the conditional when the twin is not yet sure.
"""
from dataclasses import replace
from datetime import time

from .decide import SUBJECTS, Decision, Gesture, main_subject, reference
from .knowing import Tip
from .proof import PROVEN, REINFORCED

TEXTS = {
    "fr": {
        "boost": "Lancez la VMC rapide {minutes} min", "boost_off": "Remettez la VMC en vitesse normale",
        "purify": "Lancez le purificateur {minutes} min", "purify_off": "Arrêtez le purificateur",
        "boosted": "VMC rapide {minutes} min", "purified": "Purificateur {minutes} min", "device_off": "Appareil arrêté",
        "nothing": "Rien à faire", "close": "Refermez", "open": "Aérez {minutes} min", "open_long": "Ouvrez",
        "close_later": "Refermez vers {at}", "open_later": "Aérez {minutes} min vers {at}", "close_soon": "Laissez ouvert encore {after} min", "open_more": "Ouvrez aussi {which} {minutes} min", "open_more_plain": "les autres fenêtres", "opened_more": "Ouvertes des deux côtés {minutes} min", "instead": "{line} au lieu de {minutes}",
        "heat": "vous gardez {value} °C d'ici {hour} h", "heat_open": "{value} °C de mieux d'ici {hour} h",
        "humidity": "{chosen} % d'humidité au lieu de {idle} %", "humidity_at": "{chosen} % d'humidité à {at} au lieu de {idle} %", "humidity_brief": "l'humidité baisse pendant l'aération, puis revient", "co2": "l'air redevient sain en {minutes} min",
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
        "window": "la fenêtre {direction}", "windows": "les fenêtres {direction}", "window_plain": "les fenêtres", "and": " et ", "sun_gain": "{line} : +{gain} °C dans la pièce",
        "heat_on": "Rallumez le chauffage", "heat_to": "Remettez le chauffage à {target} °C",
        "heated": "Chauffage rallumé", "heated_to": "Chauffage à {target} °C",
        "shutter_close": "Baissez le volet", "shutter_open": "Ouvrez le volet", "shuttered": "Volet baissé", "unshuttered": "Volet ouvert",
        "shutter_night": "Baissez le volet ce soir : environ {change} °C de plus au réveil",
        "shutter_night_energy": "Baissez le volet ce soir : environ {energy} kWh de chauffage en moins",
        "heating_back": "Le chauffage ramène la pièce à {minimum} °C vers {at}",
        "heating_planned": "Chauffage prévu à {at} : {temperature} °C visés",
        "heating_off": "Chauffage éteint : le rallumer donnerait {gain} °C de plus d'ici {hour} h",
        "heating_rising": "Le chauffage réchauffe la pièce : {air} °C prévus à {hour} h ({minimum} °C visés)",
        "heat_stop": "Coupez le poêle",
        "stove_off": "Poêle coupé",
        "overheat": "{air} °C pour {target} °C visés, depuis {minutes} min",
        "stove_hold": "Le poêle tourne au minimum : sans lui, la pièce reste au-dessus de {minimum} °C jusqu'à {at}",
        "stove_hold_long": "Le poêle tourne au minimum : sans lui, la pièce reste au-dessus de {minimum} °C au moins jusqu'à {hour} h",
        "stove_rising": "Le poêle tourne au minimum et la pièce monte encore : {change} °C de plus en 30 min",
        "doubtful": "Mesure douteuse", "doubtful_air": "La température semble fausse ({why}) : pas de conseil tant qu'elle l'est",
        "doubtful_aside": "Mesure douteuse, laissée de côté : {what}", "doubt": "{measure} ({why})",
        "doubt_range": "{value} : valeur impossible", "doubt_jump": "saut soudain à {value}", "doubt_frozen": "figée depuis {since}",
        "m_temperature": "température", "m_humidity": "humidité", "m_co2": "CO₂", "m_particles": "particules", "m_voc": "COV",
        "mist": "Buée probable sur les vitres cette nuit ({outdoor} °C dehors)",
        "open_weak": "Ouverte depuis {since} : {air_then} → {air} °C, {humidity_then} → {humidity} % : elle renouvelle peu l'air",
        "open_weak_air": "Ouverte depuis {since} : {air_then} → {air} °C : elle renouvelle peu l'air",
        "outside_drier": "Dehors, l'air est plus sec qu'ici : aérer assèche",
        "outside_wetter": "Dehors, l'air est plus humide qu'ici : aérer ferait monter l'humidité",
        "outside_same": "Dehors, l'air est aussi humide qu'ici : aérer n'assèche pas",
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
        "close_later": "Close around {at}", "open_later": "Air {minutes} min around {at}", "close_soon": "Leave it open {after} more min", "open_more": "Open {which} too for {minutes} min", "open_more_plain": "the other windows", "opened_more": "Open on both sides {minutes} min", "instead": "{line} instead of {minutes}",
        "heat": "you keep {value} °C until {hour}:00", "heat_open": "{value} °C better by {hour}:00",
        "humidity": "{chosen}% humidity instead of {idle}%", "humidity_at": "{chosen}% humidity at {at} instead of {idle}%", "humidity_brief": "the humidity drops while airing, then comes back", "co2": "the air is fresh again in {minutes} min",
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
        "window": "the {direction} window", "windows": "the {direction} windows", "window_plain": "the windows", "and": " and ", "sun_gain": "{line}: +{gain} °C in the room",
        "heat_on": "Turn the heating back on", "heat_to": "Set the heating back to {target} °C",
        "heated": "Heating on", "heated_to": "Heating at {target} °C",
        "shutter_close": "Lower the shutter", "shutter_open": "Open the shutter", "shuttered": "Shutter down", "unshuttered": "Shutter open",
        "shutter_night": "Lower the shutter tonight: about {change} °C more at waking up",
        "shutter_night_energy": "Lower the shutter tonight: about {energy} kWh of heating saved",
        "heating_back": "The heating brings the room back to {minimum} °C around {at}",
        "heating_planned": "Heating planned at {at}: {temperature} °C aimed at",
        "heating_off": "Heating off: turning it back on would give {gain} °C more by {hour}:00",
        "heating_rising": "The heating is warming the room: {air} °C expected at {hour}:00 ({minimum} °C aimed at)",
        "heat_stop": "Turn the stove off",
        "stove_off": "Stove off",
        "overheat": "{air} °C for {target} °C aimed at, for {minutes} min",
        "stove_hold": "The stove runs at its lowest: without it, the room stays above {minimum} °C until {at}",
        "stove_hold_long": "The stove runs at its lowest: without it, the room stays above {minimum} °C until {hour}:00 at least",
        "stove_rising": "The stove runs at its lowest and the room is still warming: {change} °C more in 30 min",
        "doubtful": "Doubtful measure", "doubtful_air": "The temperature looks wrong ({why}): no advice while it does",
        "doubtful_aside": "Doubtful measure, left aside: {what}", "doubt": "{measure} ({why})",
        "doubt_range": "{value}: impossible value", "doubt_jump": "sudden jump to {value}", "doubt_frozen": "frozen since {since}",
        "m_temperature": "temperature", "m_humidity": "humidity", "m_co2": "CO₂", "m_particles": "particles", "m_voc": "VOC",
        "mist": "Misted panes likely tonight ({outdoor} °C outside)",
        "open_weak": "Open since {since}: {air_then} → {air} °C, {humidity_then} → {humidity}%: it renews little air",
        "open_weak_air": "Open since {since}: {air_then} → {air} °C: it renews little air",
        "outside_drier": "The air outside is drier than in here: airing dries the room",
        "outside_wetter": "The air outside is more humid than in here: airing would raise the humidity",
        "outside_same": "The air outside is as humid as in here: airing does not dry the room",
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
        "close_later": "Gegen {at} schließen", "open_later": "Gegen {at} {minutes} Min. lüften", "close_soon": "Noch {after} Min. offen lassen", "open_more": "Auch {which} {minutes} Min. öffnen", "open_more_plain": "die anderen Fenster", "opened_more": "Auf beiden Seiten offen {minutes} Min.", "instead": "{line} statt in {minutes}",
        "heat": "Sie behalten {value} °C bis {hour} Uhr", "heat_open": "{value} °C besser bis {hour} Uhr",
        "humidity": "{chosen} % Feuchte statt {idle} %", "humidity_at": "{chosen} % Feuchte um {at} statt {idle} %", "humidity_brief": "die Feuchte sinkt beim Lüften und steigt danach wieder", "co2": "die Luft ist in {minutes} Min. wieder frisch",
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
        "window": "dem Fenster nach {direction}", "windows": "den Fenstern nach {direction}", "window_plain": "den Fenstern", "and": " und ", "sun_gain": "{line}: +{gain} °C im Raum",
        "heat_on": "Heizung wieder einschalten", "heat_to": "Heizung wieder auf {target} °C stellen",
        "heated": "Heizung an", "heated_to": "Heizung auf {target} °C",
        "shutter_close": "Rollladen herunterlassen", "shutter_open": "Rollladen öffnen", "shuttered": "Rollladen unten", "unshuttered": "Rollladen offen",
        "shutter_night": "Heute Abend Rollladen herunterlassen: etwa {change} °C mehr beim Aufstehen",
        "shutter_night_energy": "Heute Abend Rollladen herunterlassen: etwa {energy} kWh Heizenergie gespart",
        "heating_back": "Die Heizung bringt den Raum gegen {at} wieder auf {minimum} °C",
        "heating_planned": "Heizung geplant um {at}: {temperature} °C angestrebt",
        "heating_off": "Heizung aus: wieder eingeschaltet brächte sie bis {hour} Uhr {gain} °C mehr",
        "heating_rising": "Die Heizung wärmt den Raum: {air} °C erwartet um {hour} Uhr ({minimum} °C angestrebt)",
        "heat_stop": "Ofen ausschalten",
        "stove_off": "Ofen aus",
        "overheat": "{air} °C bei {target} °C Ziel, seit {minutes} min",
        "stove_hold": "Der Ofen läuft auf kleinster Stufe: ohne ihn bleibt der Raum bis {at} über {minimum} °C",
        "stove_hold_long": "Der Ofen läuft auf kleinster Stufe: ohne ihn bleibt der Raum mindestens bis {hour} Uhr über {minimum} °C",
        "stove_rising": "Der Ofen läuft auf kleinster Stufe und der Raum wird weiter wärmer: {change} °C mehr in 30 min",
        "doubtful": "Zweifelhafter Messwert", "doubtful_air": "Die Temperatur scheint falsch ({why}): kein Rat, solange sie es ist",
        "doubtful_aside": "Zweifelhafter Messwert, beiseitegelassen: {what}", "doubt": "{measure} ({why})",
        "doubt_range": "{value}: unmöglicher Wert", "doubt_jump": "plötzlicher Sprung auf {value}", "doubt_frozen": "unverändert seit {since}",
        "m_temperature": "Temperatur", "m_humidity": "Feuchte", "m_co2": "CO₂", "m_particles": "Partikel", "m_voc": "VOC",
        "mist": "Heute Nacht wahrscheinlich beschlagene Scheiben ({outdoor} °C draußen)",
        "open_weak": "Offen seit {since}: {air_then} → {air} °C, {humidity_then} → {humidity} %: es kommt wenig frische Luft",
        "open_weak_air": "Offen seit {since}: {air_then} → {air} °C: es kommt wenig frische Luft",
        "outside_drier": "Draußen ist die Luft trockener als hier: Lüften trocknet",
        "outside_wetter": "Draußen ist die Luft feuchter als hier: Lüften würde die Feuchte erhöhen",
        "outside_same": "Draußen ist die Luft so feucht wie hier: Lüften trocknet nicht",
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
# A window shut within this many minutes is « Laissez ouvert encore 10 min »; later, « Refermez vers 16 h ».
SOON = 60


def _lasting(gesture: Gesture, steps: int) -> int:
    """The step an hour after the gesture ends (the window shut again), within the forecast."""
    if gesture.kind == "close":
        end = gesture.after or 0
    elif gesture.minutes:
        end = (gesture.after or 0) + gesture.minutes
    else:
        return steps - 1
    return max(0, min(steps - 1, (end + 60) // STEP_MINUTES - 1))


def subject_of(decision: Decision) -> str | None:
    """What the advised gesture mostly does: the cost term it lowers the most against its reference (advisor/decide.py)."""
    return main_subject(decision.scenarios, decision.gesture)


def _degrees(value: float | None, language: str) -> str:
    """A set point as one says it: « 19 », « 19,5 »."""
    if value is None:
        return ""
    return _number(value, language).removesuffix(",0").removesuffix(".0")


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
    if gesture.kind == "open_more":
        return words["opened_more"].format(minutes=gesture.minutes)
    if gesture.kind.startswith("shutter_"):
        return words["shuttered" if gesture.kind == "shutter_close" else "unshuttered"]
    if gesture.kind == "heat_stop":
        return words["stove_off"]
    if gesture.kind.startswith("heat_"):
        return words["heated"] if gesture.kind == "heat_on" else words["heated_to"].format(target=_degrees(gesture.target, "fr"))
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
    # A supposed one too, when the card keeps it a while (an airing under way, advisor/decide.py `under_way`).
    sure = sure and decision.level == PROVEN
    marks = {"minimum": 20.0, "maximum": 24.0, "humidity": 60.0, "co2": 1000.0, "particles": 15.0, "voc": 150.0, **(marks or {})}
    # Something is open when closing is one of the scenarios.
    opened = any(g.kind == "close" for g in decision.scenarios)
    gesture, subject = decision.gesture, subject_of(decision)
    if gesture.kind == "close" and gesture.after and gesture.after < SOON:
        # Shut in a few minutes: how long is left, said again at each step until « Refermez » (Frank, 1 November).
        title = words["close_soon"].format(after=gesture.after)
    elif gesture.after and hour is not None:
        # Said to the five minutes: « Aérez 10 min vers 16 h 15 ».
        at = round((hour * 60 + gesture.after) / 5) * 5 % (24 * 60)
        title = words[f"{gesture.kind}_later"].format(at=_time(time(at // 60, at % 60), words), minutes=gesture.minutes)
    elif gesture.kind == "open":
        title = words["open"].format(minutes=gesture.minutes) if gesture.minutes else words["open_long"]
    elif gesture.kind == "open_more":
        which = words["windows"].format(direction=words[gesture.facing]) if gesture.facing else words["open_more_plain"]
        title = words["open_more"].format(which=which, minutes=gesture.minutes)
    else:
        title = words[gesture.kind].format(minutes=gesture.minutes, target=_degrees(gesture.target, language))
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
        chosen, idle = paths[gesture], paths[reference(paths, gesture)]
        if subject == "heat":
            gain = chosen.air[-1] - idle.air[-1]
            line = words["heat" if gesture.kind in ("close", "shutter_close") else "heat_open"].format(value=_number(abs(gain), language), hour=end_hour)
        elif subject == "humidity" and chosen.humidity and idle.humidity:
            # What the card will show an hour after the window is shut again: what stays, not the airing's own low, which
            # the walls and the bedding fill back within minutes (Chambre P, 3 November: 66 % open, 69 % ten minutes
            # after shutting), nor a difference to work out (« 13,6 points en moins »).
            k = _lasting(gesture, min(len(idle.humidity), len(chosen.humidity)))
            values = {"chosen": round(chosen.humidity[k]), "idle": round(idle.humidity[k])}
            if values["idle"] - values["chosen"] < 1:
                line = words["humidity_brief"]
            elif hour is not None:
                # Said to the quarter of an hour, or at the forecast's end for a window left open: a time that moved five
                # minutes at every step changed the line each time (Chambre AL, 4 November).
                if gesture.kind in ("open", "open_more") and not gesture.minutes:
                    at = end_hour * 60 % (24 * 60)
                else:
                    at = round((hour * 60 + (k + 1) * STEP_MINUTES) / 15) * 15 % (24 * 60)
                line = words["humidity_at"].format(at=_time(time(at // 60, at % 60), words), **values)
            else:
                line = words["humidity"].format(**values)
        elif subject in ("co2", "particles", "voc"):
            series = getattr(chosen, subject)
            minutes = _back_under(series, marks[subject]) if series else None
            if minutes:
                line = words[subject].format(minutes=minutes)
                # Opened on both sides: how much sooner than with the windows open now (« en 5 min au lieu de 15 »).
                without = _back_under(getattr(idle, subject), marks[subject]) if gesture.kind == "open_more" else None
                if without and without > minutes:
                    line = words["instead"].format(line=line, minutes=without)
        elif subject == "mould":
            line = words["mould"]
        elif subject == "energy":
            line = words["energy"].format(value=_number(idle.spent - chosen.spent, language))
    if decision.rule == "overheat" and decision.measured:
        # A fact measured, said as such: no forecast behind it.
        m = decision.measured
        line = words["overheat"].format(air=_number(m["air"], language), target=_degrees(m["target"], language),
                                        minutes=round(m["minutes"]))
    elif decision.rule == "safety" and reason and f"safety_{reason}" in words:
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
        sides = [words[d] for d in v.get("directions") or ([v["direction"]] if v.get("direction") else [])]
        if not sides:
            window = words["window_plain"]
        else:
            listed = sides[0] if len(sides) == 1 else ", ".join(sides[:-1]) + words["and"] + sides[-1]
            window = words["windows" if v["windows"] > 1 else "window"].format(direction=listed)
        going = now is not None and v["start"] <= now
        key = ("sun_now" if going else "sun") + ("_strong" if tip.level == REINFORCED else "")
        line = words[key].format(window=window, start=_time(v["start"], words), end=_time(v["end"], words))
        # What it does to the room, when known: the reason the line is there.
        return words["sun_gain"].format(line=line, gain=_number(v["gain"], language)) if v.get("gain") is not None else line
    if tip.kind == "mist":
        return words["mist"].format(outdoor=_number(v["outdoor"], language))
    if tip.kind == "open_weak":
        key = "open_weak" if None not in (v["humidity_then"], v["humidity"]) else "open_weak_air"
        return words[key].format(since=_time(v["since"], words), air_then=_number(v["air_then"], language),
                                 air=_number(v["air"], language), humidity_then=round(v["humidity_then"] or 0),
                                 humidity=round(v["humidity"] or 0))
    if tip.kind.startswith("outside_"):
        return words[tip.kind].format(rh=round(v["outdoor_humidity"]), outdoor=_number(v["outdoor"], language),
                                      outside=_number(v["outside"], language), inside=_number(v["inside"], language))
    if tip.kind == "heating_rising":
        return words["heating_rising"].format(air=_number(v["air"], language), hour=v["hour"], minimum=_degrees(v["minimum"], language))
    if tip.kind == "stove_rising":
        return words["stove_rising"].format(change=_number(v["change"], language))
    if tip.kind == "stove_hold":
        return words["stove_hold"].format(minimum=_degrees(v["minimum"], language), at=_time(v["at"], words))
    if tip.kind == "stove_hold_long":
        return words["stove_hold_long"].format(minimum=_degrees(v["minimum"], language), hour=v["hour"])
    if tip.kind == "heating_off":
        return words["heating_off"].format(gain=_number(v["gain"], language), hour=v["hour"])
    if tip.kind == "heating_planned":
        return words["heating_planned"].format(at=_time(v["at"], words), temperature=_degrees(v["temperature"], language))
    if tip.kind == "heating_back":
        return words["heating_back"].format(minimum=_degrees(v["minimum"], language), at=_time(v["at"], words))
    if tip.kind == "shutter_night":
        return words["shutter_night"].format(change=_number(v["change"], language))
    if tip.kind == "shutter_night_energy":
        return words["shutter_night_energy"].format(energy=_number(v["energy"], language))
    if tip.kind in ("open_warms", "open_cools"):
        return words[tip.kind].format(change=_number(v["change"], language), since=_time(v["since"], words))
    return ""


# The units a doubtful value is said in (advisor/checks.py).
UNITS = {"temperature": "°C", "humidity": "%", "co2": "ppm", "particles": "µg/m³", "voc": ""}


def doubt_text(doubts: list[dict], language: str = "fr") -> str | None:
    """The measures left aside, in words: « Mesure douteuse, laissée de côté : CO₂ (0 ppm : valeur impossible) »;
    `doubts`: {"mesure", "raison", "valeur", "depuis"} as the engine keeps them. The temperature's is the banner's."""
    words = TEXTS[language]
    parts = [_doubt(d, words, language) for d in doubts if d["mesure"] != "temperature"]
    return words["doubtful_aside"].format(what=", ".join(parts)) if parts else None


def doubtful_air(doubt: dict, language: str = "fr") -> dict:
    """The banner when the room's temperature itself is doubtful: no advice."""
    words = TEXTS[language]
    return {"title": words["doubtful"], "line": words["doubtful_air"].format(why=_why(doubt, words, language))}


def _why(d: dict, words: dict, language: str) -> str:
    if d["raison"] == "frozen":
        return words["doubt_frozen"].format(since=_time(d["depuis"], words))
    value = f"{_number(d['valeur'], language) if d['mesure'] == 'temperature' else round(d['valeur'])} {UNITS[d['mesure']]}".strip()
    return words[f"doubt_{d['raison']}"].format(value=value)


def _doubt(d: dict, words: dict, language: str) -> str:
    return words["doubt"].format(measure=words[f"m_{d['mesure']}"], why=_why(d, words, language))
