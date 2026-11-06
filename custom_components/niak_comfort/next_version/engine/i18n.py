"""Confort's words follow the language of the person reading them. French is the source: each text is written in French in
the code, and `t()` gives it in the language set for the current request, French when that language's dictionary lacks it.

The panel sends its language with each command (`language` in the message); `speaking()` sets it for that command only.
A context variable, not a global: two people reading the panel in two languages at once never mix their words.
Only words shown to people go through t(): entity states, read by automations, never change.
Another language: add its dictionary (same keys as i18n_en.py) to DICTIONARIES; tests/test_i18n.py checks none is missing.
"""
from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from .i18n_en import EN

DICTIONARIES: dict[str, dict[str, str]] = {"en": EN}
_LANGUAGE: ContextVar[str] = ContextVar("hestia_comfort_language", default="fr")
_NAME = re.compile(r"\{(\w+)\}")


def code(language: str | None) -> str:
    """French in French, a language's own dictionary when there is one, English otherwise."""
    short = (language or "").lower().replace("_", "-").split("-")[0]
    return "fr" if short == "fr" or not short else short if short in DICTIONARIES else "en"


@contextmanager
def speaking(language: str | None) -> Iterator[None]:
    """The words of one request in `language`, put back as they were afterwards."""
    token = _LANGUAGE.set(code(language))
    try:
        yield
    finally:
        _LANGUAGE.reset(token)


def language() -> str:
    return _LANGUAGE.get()


def t(french: str, **values: object) -> str:
    """A French text in the language set; `{name}` takes `values[name]`."""
    lang = _LANGUAGE.get()
    text = french if lang == "fr" else DICTIONARIES.get(lang, {}).get(french, french)
    return _NAME.sub(lambda m: str(values[m.group(1)]) if m.group(1) in values else m.group(0), text) if values else text


def N_(french: str) -> str:
    """Marks a French text kept in a table and translated where it is shown, with t(): the dictionary test finds it there too."""
    return french
