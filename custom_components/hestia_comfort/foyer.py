"""The household's settings (« Réglages du foyer », niak-comfort/docs/REGLAGES-3.md § 4.3 and § 6), checked as saved.

The keys are the ones the advisor reads (advisor/household.py `Habits.of`): for the house in the home store, and for a
room only where it differs. Nothing is written for what the person left at its default: a missing key takes its default
when read. The physics and the norms are not here.
"""
import math

from .engine.i18n import t

# Each number: (lowest, highest, step). The steps are those the panel offers; a value between them is refused.
NUMBERS = {
    "aeration_max_min": (10, 60, 5),       # the longest airing
    "plus_tard_max_min": (30, 240, 15),    # the furthest « vers 16 h »
    "appareils_max_min": (15, 120, 5),     # the longest run of the VMC's fast speed or the purifier
    "cette_nuit_avant_h": (1, 8, 1),       # « Cette nuit, pensez à… », hours before bedtime
    "buee_avant_h": (1, 8, 1),             # misted panes, hours before bedtime
    "hors_gel": (5, 12, 0.5),              # °C kept while away for days
    "pas_maintenant_min": (15, 240, 15),   # how long « Pas maintenant » puts a gesture aside
    "poele_tient_h": (1, 12, 0.5),         # « Coupez le poêle » when the room would hold this long without it
    "depassement": (0.5, 3, 0.5),          # °C above its set point…
    "depassement_min": (10, 120, 5),       # …for this long
}
TOLERANCES = (0.5, 0.75, 1, 1.5, 2)
# The house itself, for the ressenti (engine/feel.py): how well its walls are insulated, which glazing it has.
CHOICES = {"isolation": ("bien", "moyenne", "peu"), "vitrage": ("simple", "double", "triple")}
# The household's habits (niak-comfort/docs/HABITUDES-FOYER.md): its manual shutters away, at night and on summer's hot
# hours; « variable » keeps what the advisor learned on average.
SHUTTER_HABITS = ("fermes", "ouverts", "variable")
HABITS = ("volets_absence", "volets_nuit", "volets_ete")
# The questions already answered (« Vos habitudes », even by « Je ne sais pas »): never asked twice.
QUESTIONS = ("vitrage", *HABITS, "journee_vide", "linge_pieces", "fin_weekend")
# « Votre maison » (§ 3 bis): what each window and each room takes when it does not set its own.
HOUSE = {"volet": ("none", "manual", "connected"), "murs": ("heavy", "wood")}
CEILING = (1.8, 8.0)
# What a room may set apart from the house (« Différent du foyer pour cette pièce »).
ROOM_KEYS = ("sommeil", "ouvrir_la_nuit", "tolerance", *HABITS)
SHORTEST_NIGHT, LONGEST_NIGHT = 4 * 60, 14 * 60


def _minutes(text):
    if not isinstance(text, str) or len(text) != 5 or text[2] != ":":
        raise ValueError
    hours, minutes = int(text[:2]), int(text[3:])
    if not (0 <= hours < 24 and 0 <= minutes < 60):
        raise ValueError
    return hours * 60 + minutes


def _sleep(value):
    try:
        if set(value) - {"debut", "fin", "fin_weekend"}:
            raise ValueError
        start, end = _minutes(value.get("debut")), _minutes(value.get("fin"))
        ends = [end] + ([_minutes(value["fin_weekend"])] if value.get("fin_weekend") is not None else [])
    except (AttributeError, ValueError, TypeError):
        raise ValueError(t("Heures de sommeil invalides : coucher et lever en heures et minutes.")) from None
    if not all(SHORTEST_NIGHT <= (e - start) % (24 * 60) <= LONGEST_NIGHT for e in ends):
        raise ValueError(t("La nuit va de 4 à 14 heures : vérifiez le coucher et le lever."))
    cleaned = {"debut": value["debut"], "fin": value["fin"]}
    if len(ends) > 1:
        cleaned["fin_weekend"] = value["fin_weekend"]
    return cleaned


def _number(value, low, high):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and low <= value <= high


def _house(value, cleaned):
    """« Votre maison »: the shutter and the walls each window or room takes, the ceiling's height, the house's range."""
    for key, values in HOUSE.items():
        if key in value:
            if value[key] not in values:
                raise ValueError(t("Valeur hors des bornes : {name}", name=key))
            cleaned[key] = value[key]
    if "hauteur" in value:
        if not _number(value["hauteur"], *CEILING):
            raise ValueError(t("Valeur hors des bornes : {name}", name="hauteur"))
        cleaned["hauteur"] = value["hauteur"]
    if "plage" in value:
        plage = value["plage"]
        if not isinstance(plage, dict) or set(plage) - {"minimum", "maximum", "summer_maximum"} \
                or not all(_number(v, 5, 40) for v in plage.values()):
            raise ValueError(t("Plage de confort invalide."))
        full = {"minimum": 20.0, "maximum": 24.0, "summer_maximum": 26.0, **plage}
        if not (full["minimum"] < full["maximum"] and full["minimum"] < full["summer_maximum"]):
            raise ValueError(t("Plage de confort invalide."))
        cleaned["plage"] = dict(plage)


def _habits(value, cleaned):
    """The household's habits (HABITUDES-FOYER.md): the manual shutters, the empty weekdays, where the laundry dries."""
    for key in HABITS:
        if key in value:
            if value[key] not in SHUTTER_HABITS:
                raise ValueError(t("Valeur hors des bornes : {name}", name=key))
            cleaned[key] = value[key]
    if "journee_vide" in value:
        empty = value["journee_vide"]
        if empty is not None:
            try:
                if set(empty) != {"de", "a"} or _minutes(empty["de"]) >= _minutes(empty["a"]):
                    raise ValueError
            except (AttributeError, ValueError, TypeError):
                raise ValueError(t("Heures de la journée invalides : le départ avant le retour.")) from None
            empty = {"de": empty["de"], "a": empty["a"]}
        cleaned["journee_vide"] = empty
    if "repondu" in value:
        seen = value["repondu"]
        if not isinstance(seen, list) or not set(seen) <= set(QUESTIONS):
            raise ValueError(t("Valeur hors des bornes : {name}", name="repondu"))
        cleaned["repondu"] = [q for q in QUESTIONS if q in seen]
    if "linge_pieces" in value:
        rooms = value["linge_pieces"]
        if not isinstance(rooms, list) or len(rooms) > 40 or not all(isinstance(r, str) and r for r in rooms):
            raise ValueError(t("Pièces du linge invalides."))
        cleaned["linge_pieces"] = list(dict.fromkeys(rooms))
    # « Les deux, selon le temps »: the laundry dries inside only some days, in those rooms.
    if "linge_parfois" in value:
        if not isinstance(value["linge_parfois"], bool):
            raise ValueError(t("Pièces du linge invalides."))
        if value["linge_parfois"]:
            cleaned["linge_parfois"] = True


def clean_foyer(value, *, room=False):
    """The household's settings as saved; `room`: only what a room may set apart from the house."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(t("Réglages du foyer invalides."))
    allowed = ROOM_KEYS if room else ("sommeil", "ouvrir_la_nuit", "tolerance", *NUMBERS, *CHOICES, *HABITS, "journee_vide",
                                      "linge_pieces", "linge_parfois", "repondu", *HOUSE, "hauteur", "plage")
    if set(value) - set(allowed):
        raise ValueError(t("Réglages du foyer invalides."))
    cleaned = {}
    if "sommeil" in value:
        cleaned["sommeil"] = _sleep(value["sommeil"])
    if "ouvrir_la_nuit" in value:
        if not isinstance(value["ouvrir_la_nuit"], bool):
            raise ValueError(t("« Ouvrir une fenêtre la nuit » doit être oui ou non."))
        cleaned["ouvrir_la_nuit"] = value["ouvrir_la_nuit"]
    if "tolerance" in value:
        if value["tolerance"] not in TOLERANCES or isinstance(value["tolerance"], bool):
            raise ValueError(t("« Combien de conseils » invalide."))
        cleaned["tolerance"] = value["tolerance"]
    _habits(value, cleaned)
    if not room:
        _house(value, cleaned)
    for key, values in CHOICES.items():
        if key in value:
            if value[key] not in values:
                raise ValueError(t("Valeur hors des bornes : {name}", name=key))
            cleaned[key] = value[key]
    for key, (low, high, step) in NUMBERS.items():
        if key not in value:
            continue
        number = value[key]
        if (isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number)
                or not low <= number <= high or abs(round((number - low) / step) * step + low - number) > 1e-9):
            raise ValueError(t("Valeur hors des bornes : {name}", name=key))
        cleaned[key] = number
    return cleaned
