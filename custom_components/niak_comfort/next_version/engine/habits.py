"""Habits: what comes back at the same time, found in the twin's half hours. They never name a cause by themselves.

A habit becomes a question (Oui / Non / Je ne sais pas) in the hub's « Apprentissage » box. Only a « yes » lets the
card name the cause; a « no » or « don't know » only stops the question. Two kinds for now:

- humidity that rises at the same hour, windows shut (a shower, cooking, laundry drying… or something else);
- a window open at night, night after night (on purpose, or forgotten).
"""
from datetime import datetime
import math
import unicodedata

from .i18n import N_, t

# Water (g/m³) gained in half an hour, windows shut, that counts as a rise.
RISE = 1.0
# A habit: on at least this share of the days, and at least this many times.
SHARE, TIMES = 0.4, 4
NIGHT = (0, 1, 2, 3, 4, 5)


def _water(t, rh):
    return 6.112 * math.exp(17.67 * t / (t + 243.5)) * rh * 2.1674 / (273.15 + t)


def detect(rows, zone):
    """The habits of a room from its half-hour samples; `zone` is the home's time zone."""
    days = {"weekdays": set(), "weekend": set()}
    rises = {}
    nights, open_nights = set(), set()
    for first, second in zip(rows, rows[1:]):
        when = datetime.fromisoformat(first[0]).astimezone(zone)
        kind = "weekend" if when.weekday() >= 5 else "weekdays"
        days[kind].add(when.date())
        if when.hour in NIGHT:
            nights.add(when.date())
            if first[6] >= 0.5:
                open_nights.add(when.date())
        if (datetime.fromisoformat(second[0]) - datetime.fromisoformat(first[0])).total_seconds() != 1800 or first[6] > 0:
            continue
        if _water(second[1], second[2]) - _water(first[1], first[2]) >= RISE:
            rises.setdefault((kind, when.hour), set()).add(when.date())
    found = []
    # A shower is not taken at the same minute every day: a rise counts within an hour of the habit's hour.
    def around(kinds, hour):
        return {d for (k, h), dates in rises.items() if k in kinds and abs((h - hour + 12) % 24 - 12) <= 1 for d in dates}
    def best(kinds):
        total = sum(len(days[k]) for k in kinds)
        hour, count = max(((h, len(around(kinds, h))) for h in range(24)), key=lambda x: x[1])
        return (hour, count, round(count / total, 2)) if total and count >= TIMES and count / total >= SHARE else None
    every = best(("weekdays", "weekend"))
    if every:
        found.append({"key": f"humidity:all:{every[0]}", "kind": "humidity", "days": "all", "hour": every[0], "share": every[2]})
    else:
        for kind in ("weekdays", "weekend"):
            if one := best((kind,)):
                found.append({"key": f"humidity:{kind}:{one[0]}", "kind": "humidity", "days": kind, "hour": one[0], "share": one[2]})
    if len(open_nights) >= TIMES and len(open_nights) / max(1, len(nights)) >= 0.5:
        found.append({"key": "night_open", "kind": "night_open", "share": round(len(open_nights) / len(nights), 2)})
    return found


def cause(title, area=None, equipment=()):
    """The cause a question may ask about: a shower the room declares, else what its name says; None when nothing fits."""
    if "shower" in (equipment or ()):
        return N_("la douche")
    name = unicodedata.normalize("NFD", f"{title} {area or ''}".lower())
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    if any(w in name for w in ("salle de bain", "salle d'eau", "salle d’eau", "sdb", "douche")):
        return N_("la douche")
    if "cuisine" in name:
        return N_("la cuisine")
    if any(w in name for w in ("buanderie", "lingerie", "cellier")):
        return N_("le linge qui sèche")
    return None


def season_group(name):
    """« summer », « winter » or « between » (spring, autumn, or no season known): an answer holds for one of them."""
    return name if name in ("summer", "winter") else "between"


SEASON_WORDS = {"summer": N_("cet été"), "winter": N_("cet hiver"), "between": N_("en cette saison")}


def night_key(season):
    """The answer about a window open at night holds for the season it was given in: asked again in the next."""
    return f"night_open:{season_group(season)}"


def questions(title, area, habits, answers, season=None, equipment=()):
    """The questions still to ask for this room: one per habit not answered yet (per season for a night window)."""
    out = []
    for habit in habits:
        key = night_key(season) if habit["kind"] == "night_open" else habit["key"]
        # In winter a window open at night is always said: asking whether it is on purpose would change nothing.
        if key in (answers or {}) or key == "night_open:winter":
            continue
        if habit["kind"] == "humidity":
            rises = {"weekdays": N_("L’humidité de la pièce « {room} » monte souvent vers {hour} h en semaine."),
                     "weekend": N_("L’humidité de la pièce « {room} » monte souvent vers {hour} h le week-end.")}.get(
                habit["days"], N_("L’humidité de la pièce « {room} » monte souvent vers {hour} h."))
            guess = cause(title, area, equipment)
            text = t(rises, room=title, hour=habit["hour"]) + " " + (
                t("Est-ce {cause} ?", cause=t(guess)) if guess else t("Est-ce une habitude de la maison ?"))
            hint = t("Votre réponse précise la cause ; sans elle, aucune cause n’est affichée.")
        else:
            text = t("Une fenêtre de la pièce « {room} » est souvent ouverte la nuit {season}. Est-ce voulu, pour l’air frais ?",
                     room=title, season=t(SEASON_WORDS[season_group(season)]))
            hint = t("Si oui, elle ne sera plus signalée comme un oubli tant qu’elle rafraîchit la pièce. Si l’air du dehors "
                     "la réchauffe, la refroidit trop ou l’humidifie, Confort conseillera toujours de fermer. Question reposée à chaque saison.")
        out.append({"key": key, "text": text, "hint": hint})
    return out


def now_habit(habits, answers, when, title, area=None, equipment=()):
    """A confirmed humidity habit going on now (its hour and the two after): the words for « À savoir », or None."""
    kind = "weekend" if when.weekday() >= 5 else "weekdays"
    for habit in habits:
        if (habit["kind"] == "humidity" and habit["days"] in (kind, "all") and (answers or {}).get(habit["key"]) == "yes"
                and -1 <= when.hour - habit["hour"] <= 2):
            guess = cause(title, area, equipment)
            return f"habituelle à cette heure : {guess}, elle retombe d’elle-même" if guess else "habituelle à cette heure, elle retombe d’elle-même"
    return None
