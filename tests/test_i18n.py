"""Confort's Python words in English: every French text given to t(), N_() or a plural choice has its English words,
the dictionary keeps no word nothing shows, a translation keeps the same {names}, and a language set for one request
never leaks into the next."""
import ast
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"
sys.path.insert(0, str(ROOT))
from engine import i18n  # noqa: E402
from engine.i18n_en import EN  # noqa: E402

SOURCES = ("health.py", "panel.py", "configuration.py", "foyer.py", "websocket.py", "engine/habits.py")
# Functions whose literal arguments are French texts: t() and N_() take one, _count() a singular and a plural.
CALLS = {"t": 1, "N_": 1, "_count": 3}


def french_texts():
    found = set()
    for name in SOURCES:
        for node in ast.walk(ast.parse((ROOT / name).read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in CALLS:
                for arg in node.args[:CALLS[node.func.id]]:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        found.add(arg.value)
    return found


def names(text):
    return sorted(re.findall(r"\{(\w+)\}", text))


class EnglishWords(unittest.TestCase):
    def test_every_text_shown_has_its_english_words(self):
        texts = french_texts()
        self.assertGreater(len(texts), 150)
        self.assertEqual(sorted(x for x in texts if x not in EN), [])

    def test_the_dictionary_keeps_no_word_nothing_shows(self):
        self.assertEqual(sorted(set(EN) - french_texts()), [])

    def test_a_translation_keeps_the_same_names(self):
        self.assertEqual([fr for fr, en in EN.items() if names(fr) != names(en)], [])

    def test_the_language_holds_for_one_request_only(self):
        self.assertEqual(i18n.t("Tout est suivi"), "Tout est suivi")
        with i18n.speaking("en-GB"):
            self.assertEqual(i18n.t("{room} : calcul arrêté", room="Salon"), "Salon: computation stopped")
            with i18n.speaking("nl"):
                self.assertEqual(i18n.language(), "en")
            self.assertEqual(i18n.language(), "en")
        self.assertEqual(i18n.language(), "fr")
        self.assertEqual(i18n.t("Tout est suivi"), "Tout est suivi")


if __name__ == "__main__":
    unittest.main()
