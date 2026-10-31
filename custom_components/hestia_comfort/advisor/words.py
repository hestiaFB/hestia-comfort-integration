"""Layer 9: the decision in words — the banner, its gain, « Pourquoi ? » — in French, English and German.

The card composes no advice of its own: it shows these words (CAHIER-MOTEUR.md § 14). One idea per line, one advice per
card; a gain always in plain units (°C, humidity points, minutes); the conditional when the twin is not yet sure.
"""
from .decide import Decision, Gesture

TEXTS = {
    "fr": {
        "nothing": "Rien à faire", "close": "Refermez", "open": "Aérez {minutes} min", "open_long": "Ouvrez",
        "heat": "vous gardez {value} °C d'ici {hour} h", "heat_open": "{value} °C de mieux d'ici {hour} h",
        "humidity": "{value} points d'humidité en moins", "co2": "l'air redevient sain en {minutes} min",
        "particles": "les particules retombent en {minutes} min",
        "sure": "{line}", "unsure": "{line}, sans doute",
        "why": "{gesture} : {air} °C à {hour} h", "why_humidity": ", humidité {humidity} %",
        "shut": "Fermée", "open_now": "Ouverte", "aired": "Aérée {minutes} min",
        "nothing_line": "Ouverte ou fermée, la pièce restera dans votre plage",
    },
    "en": {
        "nothing": "Nothing to do", "close": "Close", "open": "Air for {minutes} min", "open_long": "Open",
        "heat": "you keep {value} °C until {hour}:00", "heat_open": "{value} °C better by {hour}:00",
        "humidity": "{value} humidity points less", "co2": "the air is fresh again in {minutes} min",
        "particles": "the particles settle in {minutes} min",
        "sure": "{line}", "unsure": "{line}, most likely",
        "why": "{gesture}: {air} °C at {hour}:00", "why_humidity": ", humidity {humidity} %",
        "shut": "Shut", "open_now": "Open", "aired": "Aired {minutes} min",
        "nothing_line": "Open or shut, the room stays in your range",
    },
    "de": {
        "nothing": "Nichts zu tun", "close": "Schließen", "open": "{minutes} Min. lüften", "open_long": "Öffnen",
        "heat": "Sie behalten {value} °C bis {hour} Uhr", "heat_open": "{value} °C besser bis {hour} Uhr",
        "humidity": "{value} Punkte weniger Feuchte", "co2": "die Luft ist in {minutes} Min. wieder frisch",
        "particles": "die Partikel setzen sich in {minutes} Min.",
        "sure": "{line}", "unsure": "{line}, voraussichtlich",
        "why": "{gesture}: {air} °C um {hour} Uhr", "why_humidity": ", Feuchte {humidity} %",
        "shut": "Geschlossen", "open_now": "Offen", "aired": "{minutes} Min. gelüftet",
        "nothing_line": "Offen oder geschlossen, der Raum bleibt in Ihrem Bereich",
    },
}
SUBJECTS = ("heat", "humidity", "co2", "particles")
STEP_MINUTES = 5


def subject_of(decision: Decision) -> str | None:
    """What the advised gesture mostly does: the cost term it lowers the most against « do nothing »."""
    if decision.gesture.kind == "nothing" or not decision.scenarios:
        return None
    nothing, best = decision.scenarios[Gesture("nothing")], decision.scenarios[decision.gesture]
    return max(SUBJECTS, key=lambda s: nothing[s] - best[s])


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


def _name(gesture: Gesture, path, words) -> str:
    """How « Pourquoi ? » names a scenario: by the state of the windows it leaves."""
    if gesture.kind == "open":
        return words["aired"].format(minutes=gesture.minutes) if gesture.minutes else words["open_now"]
    if gesture.kind == "nothing" and path.lost > 0:
        return words["open_now"]
    return words["shut"]


def phrase(decision: Decision, end_hour: int, language: str = "fr", sure: bool = True,
           marks: dict | None = None) -> dict:
    """The banner's title and line, and the lines of « Pourquoi ? »."""
    words = TEXTS[language]
    marks = marks or {"co2": 1000.0, "particles": 15.0}
    gesture, subject = decision.gesture, subject_of(decision)
    if gesture.kind == "open":
        title = words["open"].format(minutes=gesture.minutes) if gesture.minutes else words["open_long"]
    else:
        title = words[gesture.kind]
    line = words["nothing_line"] if gesture.kind == "nothing" else ""
    paths = decision.paths
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
    line = words["sure" if sure else "unsure"].format(line=line) if line else line
    why = []
    for g, path in paths.items():
        if path.air:
            text = words["why"].format(gesture=_name(g, path, words), air=_number(path.air[-1], language), hour=end_hour)
            if path.humidity:
                text += words["why_humidity"].format(humidity=round(path.humidity[-1]))
            why.append(text)
    return {"title": title, "line": line, "subject": subject, "why": why}
