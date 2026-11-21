"""The advice engine stands apart from the integration (advisor/__init__.py, CHANGELOG-MOTEUR.md).

Its modules import neither Home Assistant nor the rest of Confort, so that any decision can be replayed on the bench and
the engine can move on its own number; and that number is the one its two histories start with.
"""
import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ADVISOR = ROOT / "custom_components" / "hestia_comfort" / "advisor"
# The bench's tools compare with the old engine and use scipy: they are run by hand, never by Home Assistant.
BENCH = ADVISOR / "bench"


def engine_modules():
    return sorted(p for p in ADVISOR.rglob("*.py") if BENCH not in p.parents)


def outside_imports(path):
    """The imports of one engine module that reach out of the engine, as « line: name »."""
    package = path.relative_to(ADVISOR).parent.parts  # where the module sits, inside advisor/
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            names = [node.module or ""]
        elif isinstance(node, ast.ImportFrom):
            # A relative import may climb up to advisor/ itself, never above it.
            if node.level - 1 > len(package):
                found.append(f"{node.lineno}: {'.' * node.level}{node.module or ''}")
            continue
        else:
            continue
        found += [f"{node.lineno}: {name}" for name in names
                  if name.split(".")[0] in ("homeassistant", "custom_components")]
    return found


class TheEngineStandsApart(unittest.TestCase):
    def test_no_home_assistant_and_nothing_of_confort_in_the_engine(self):
        self.assertGreater(len(engine_modules()), 20)
        for path in engine_modules():
            with self.subTest(module=str(path.relative_to(ADVISOR))):
                self.assertEqual(outside_imports(path), [])

    def test_the_changelog_starts_with_the_engines_version(self):
        from custom_components.hestia_comfort.advisor import VERSION  # noqa: PLC0415
        changelog = (ROOT / "CHANGELOG-MOTEUR.md").read_text(encoding="utf-8")
        self.assertEqual(changelog.split("\n## ")[1].split(" ")[0], VERSION)


if __name__ == "__main__":
    unittest.main()
