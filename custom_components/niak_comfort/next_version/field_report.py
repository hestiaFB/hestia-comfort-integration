"""« Participez à l'amélioration du moteur » (niak-comfort/docs/REGLAGES-3.md § 4.1, PASSAGE-CONFORT-3.md § 7 bis).

While the advice engine is in beta (advisor/__init__.py BETA), each home can download what its engine forecast and
measured, what each room learned and the situations reported with « Ce conseil ne va pas », to share it in a GitHub
issue if the person wants to. Nothing leaves Home Assistant here: the panel shows the report, the person downloads it.

Anonymous: the rooms become « Pièce 1, Pièce 2… », every entity becomes « entité 1, entité 2… », the home's position
and the people are left out, and no raw history is in it. Beside the report, what would make it more useful
(« Ce qui le rendrait plus utile »): those lines name the rooms, they are for the person and stay out of the report.
"""
import json
from pathlib import Path
import re

from homeassistant.util import dt as dt_util

from .advisor import BETA, VERSION as ADVISOR_VERSION
from .advisor_store import FOLDER
from .const import VERSION

FORMAT = 1
# The situations reported, the most recent first: enough to see a pattern, few enough to stay readable.
SIGNALS = 20
# Days of history that would let the twins learn more than one kind of weather (the recorder keeps 10 by default).
WANTED_DAYS = 30
ENTITY = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")
# Keys whose value names a person, a place or a thing of the home: left out wherever they appear.
HIDDEN = {"entite", "entity_id", "friendly_name", "name", "area_id", "floor_id", "persons", "people", "presence",
          "latitude", "longitude", "elevation", "location", "fichier", "file", "title"}


class Anonymous:
    """The same alias for the same room or entity throughout one report, so that the report stays coherent."""

    def __init__(self, rooms: list[str]):
        self.rooms = {}
        for name in rooms:
            if name and name not in self.rooms:
                self.rooms[name] = f"Pièce {len(self.rooms) + 1}"
        # « Salon · Cuisine » also names « Salon » and « Cuisine » apart; the longest names are replaced first.
        words = dict(self.rooms)
        for name, alias in self.rooms.items():
            for part in name.split(" · "):
                words.setdefault(part, alias)
        self.words = sorted(words.items(), key=lambda kv: -len(kv[0]))
        self.entities = {}

    def room(self, name: str | None) -> str | None:
        return self.rooms.get(name) if name else None

    def _entity(self, entity_id: str) -> str:
        return self.entities.setdefault(entity_id, f"entité {len(self.entities) + 1}")

    def _text(self, text: str) -> str:
        if ENTITY.match(text):
            return self._entity(text)
        for name, alias in self.words:
            if name in text:
                text = text.replace(name, alias)
            # The room's slug, as in the snapshots' file names (room/advice.py `slug`).
            slug = name.lower().replace(" · ", "_").replace(" ", "_")
            if len(slug) > 2 and slug in text:
                text = text.replace(slug, alias.lower().replace(" ", "_"))
        return text

    def __call__(self, value):
        if isinstance(value, dict):
            return {self._text(k) if isinstance(k, str) else k: self(v) for k, v in value.items() if k not in HIDDEN}
        if isinstance(value, (list, tuple)):
            return [self(v) for v in value]
        if isinstance(value, str):
            return self._text(value)
        return value


def _room(config: dict, advisor) -> dict:
    """One room's context and what its engine knows, before it is made anonymous."""
    built = config.get("room") or {}
    openings = config.get("openings") or {}
    windows = config.get("windows") or []
    learned = dict(getattr(advisor, "learned", None) or {})
    gestures = learned.pop("gestures", None) or {}
    knowing = advisor.knowing() if advisor is not None else {}

    def sized(w):
        meta = openings.get(w) or {}
        return bool(meta.get("width") and meta.get("height"))

    return {
        "piece": config.get("name"),
        # A room that shares its air with another is advised with it: its engine is the other room's.
        "conseil_a_part": advisor is not None,
        "usage": built.get("uses"),
        "surface": built.get("surface"), "hauteur": built.get("height"),
        "murs": {k: built.get(k) for k in ("outside", "wall_material", "insulation", "partitions") if built.get(k) is not None},
        "chauffee": config.get("heated", True),
        "chauffages": sorted({h.get("kind") or "?" for h in config.get("heaters") or [] if isinstance(h, dict)}),
        "capteurs": sorted(k for k, v in (config.get("sources") or {}).items() if v),
        "equipements": sorted(config.get("equipment") or []),
        "fenetres": len(windows),
        "fenetres_sans_taille": sum(1 for w in windows if not sized(w)) if not config.get("windows_unmeasured") else 0,
        "volets": sum(1 for w in windows if (openings.get(w) or {}).get("shutter") not in (None, "none")),
        "meme_air": bool(config.get("open_to")),
        "jours": knowing.get("jours"),
        "ecart_1h": knowing.get("ecart_1h"),
        "prevu_contre_mesure": knowing.get("effets") or [],
        "appris_le": (getattr(advisor, "learned_at", None) or "")[:10] or None,
        "jumeaux": learned,
        "gestes_vus": {effect: len(cases) for effect, cases in gestures.items()},
        "derniere_nuit": getattr(advisor, "report", None),
    }


def _signals(config_path: str) -> list[dict]:
    """The last situations reported with « Ce conseil ne va pas », each with its snapshot and its trace."""
    folder = Path(config_path) / FOLDER / "signales"
    if not folder.exists():
        return []
    found = []
    for path in sorted(folder.glob("signale-*.json"), reverse=True)[:SIGNALS]:
        try:
            found.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return found


def helpful(rooms: list[dict]) -> list[dict]:
    """What would make the report more useful: the rooms are named, these lines stay in the panel. The analysis tools
    are the encart's own switch (« Je participe »), not a line here."""
    lines = []
    without = [r["piece"] for r in rooms if r["fenetres_sans_taille"]]
    if without:
        lines.append({"key": "sizes", "count": sum(r["fenetres_sans_taille"] for r in rooms), "rooms": without})
    days = max((r["jours"] or 0 for r in rooms), default=0)
    if days < WANTED_DAYS:
        lines.append({"key": "history", "days": round(days), "wanted": WANTED_DAYS})
    learning = [r["piece"] for r in rooms if r["conseil_a_part"] and not r["appris_le"]]
    if learning:
        lines.append({"key": "learning", "rooms": learning})
    return lines


def assemble(rooms: list[dict], signals: list[dict], followed: dict, home: dict, now) -> dict:
    """The report itself, anonymous: plain values in, plain values out (tests/test_field_report.py)."""
    anonymous = Anonymous([r["piece"] for r in rooms])
    return {
        "rapport": "Hestia Confort · essai terrain", "format": FORMAT,
        "date": now.date().isoformat(),
        "versions": {"confort": VERSION, "moteur": ADVISOR_VERSION, "moteur_beta": BETA},
        "maison": {
            "pieces": len(rooms),
            "chauffages": sorted({k for r in rooms for k in r["chauffages"]}),
            "hestia_meteo": bool(home.get("weather")),
            "alarme": bool(home.get("alarm")),
            "outils_analyse": bool(home.get("analysis")),
            "jours_historique": round(max((r["jours"] or 0 for r in rooms), default=0), 1),
        },
        "pieces": [{"piece": anonymous.room(r["piece"]), **anonymous({k: v for k, v in r.items() if k != "piece"})} for r in rooms],
        "gestes_suivis": anonymous(followed),
        "signalements": anonymous(signals),
    }


async def build(hass, configuration, home) -> dict:
    """The report as it would be shared, and beside it what would make it more useful (not in the report)."""
    advisors = getattr(home, "rooms", None) or {}
    analysis = bool(configuration.home.get("analysis"))
    rooms = [_room({**e.data, **e.options}, advisors.get(e.entry_id)) for e in configuration.entries()]
    signals = await hass.async_add_executor_job(_signals, hass.config.path())
    followed = {}
    if home is not None and analysis:
        followed = (await hass.async_add_executor_job(home.files.atelier, dt_util.utcnow())).get("suivis") or {}
    return {"report": assemble(rooms, signals, followed, configuration.home, dt_util.now()),
            "helpful": helpful(rooms), "beta": BETA, "analysis": analysis}
