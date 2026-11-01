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
# What a room may set apart from the house (« Différent du foyer pour cette pièce »).
ROOM_KEYS = ("sommeil", "ouvrir_la_nuit", "tolerance")
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
        start, end = _minutes(value.get("debut")), _minutes(value.get("fin"))
    except (AttributeError, ValueError, TypeError):
        raise ValueError(t("Heures de sommeil invalides : coucher et lever en heures et minutes.")) from None
    night = (end - start) % (24 * 60)
    if not SHORTEST_NIGHT <= night <= LONGEST_NIGHT:
        raise ValueError(t("La nuit va de 4 à 14 heures : vérifiez le coucher et le lever."))
    return {"debut": value["debut"], "fin": value["fin"]}


def clean_foyer(value, *, room=False):
    """The household's settings as saved; `room`: only what a room may set apart from the house."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(t("Réglages du foyer invalides."))
    allowed = ROOM_KEYS if room else ("sommeil", "ouvrir_la_nuit", "tolerance", *NUMBERS)
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
    for key, (low, high, step) in NUMBERS.items():
        if key not in value:
            continue
        number = value[key]
        if (isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number)
                or not low <= number <= high or abs(round((number - low) / step) * step + low - number) > 1e-9):
            raise ValueError(t("Valeur hors des bornes : {name}", name=key))
        cleaned[key] = number
    return cleaned
