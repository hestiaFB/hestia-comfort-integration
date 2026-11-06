"""The integration's former technical name, gathered here and nowhere else.

Hestia Confort was first published under another technical name. A home installed then keeps that name in its
configuration entries, .storage files (learning, twins, answers, the home's settings), dashboards and automations:
domain_migration.py carries all of it over to « hestia_comfort » at the first start, then removes the old entries.
These constants are only what it needs to find them, and what lets Hestia Confort keep its link with a Hestia Weather
not updated yet. No other module writes an old name.
"""
from __future__ import annotations

import re

# The former domain: its config entries, its entity platform, its device identifiers.
DOMAIN = "niak_comfort"
# Where its files were served, and its card's file.
ASSETS = "/niak_comfort-assets"
CARD_FILE = "niak-comfort-card.js"
# Who published it then: its former folder is removed only when it is this brick.
CODEOWNERS = ("@hestiaFB", "@Niakman13")
# The shared « Hestia » panel: its former address (still opened from bookmarks) and its settings file.
PANEL = "niak"
SOCLE_KEY = "niak_socle"
# The .storage files of the former domain: the home's settings, and each room's learning, twin and answers.
STORES = (f"{DOMAIN}.",)
# Values written in the entries and .storage files under the former name, with the new one.
VALUES = {"niak_home": "hestia_home", "niak_weather": "hestia_weather", "niak_air": "hestia_air", "niak_index": "hestia_index", "niak_weather_air": "hestia_weather_air"}
# Hestia Weather under its former name, until it is updated too: its entities' platform and its interface.
WEATHER_DOMAIN = "niak_weather"
WEATHER_API_KEY = "niak_weather_api"
# Started by Hestia Confort once carried over, so that Hestia Weather carries itself over too (domain_migration._start_siblings).
SIBLINGS = {"hestia_weather": WEATHER_DOMAIN}
# Former names in what the user wrote (automations, scripts, scenes, dashboards), with the new one.
# Whole words only; an entity id is never touched: ids stay as they are.
TEXT = (
    (r"(?<![\w.-])niak_comfort(?![\w.-])", "hestia_comfort"),
    (r"(?<![\w-])niak-comfort-", "hestia-comfort-"),
    (r"/niak_comfort-assets/", "/hestia_comfort-assets/"),
    (r"(?<![\w-])/niak-confort(?=/|[\"'\s]|$)", "/hestia/confort"),
    (r"(?<![\w-])/niak(?=/|[\"'\s]|$)", "/hestia"),
    (r"--niak-", "--hestia-"),
)
# An entry id: a ULID, or the 32 hexadecimal digits of older Home Assistant versions.
_ENTRY_ID = re.compile(r"^(?:[0-9A-HJKMNP-TV-Z]{26}|[0-9a-f]{32})$")


def rekey(value: str) -> str:
    """A shared air's id names its rooms' entry ids in order (volume_<id>_<id>, then its key): new ids, new order."""
    if not value.startswith("volume_"):
        return value
    parts = value[len("volume_"):].split("_")
    count = next((n for n, part in enumerate(parts) if not _ENTRY_ID.match(part)), len(parts))
    return "_".join(["volume", *sorted(parts[:count]), *parts[count:]])
