"""Print what the automatic release needs for the version in manifest.json.

Used by .github/workflows/publier.yml. Writes `version`, `tag`, `title` and
`prerelease` to $GITHUB_OUTPUT (or stdout) and the release notes, taken from
CHANGELOG.md, to the file given as first argument.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "custom_components" / "hestia_comfort" / "manifest.json"
CHANGELOG = ROOT / "CHANGELOG.md"
PRODUCT = "Hestia Confort"


def section(changelog: str, version: str) -> tuple[str, str]:
    """Return (subtitle, body) of the `## <version> — <subtitle>` section."""
    lines = changelog.splitlines()
    head = re.compile(rf"^## {re.escape(version)}(?:\s+[—-]\s+(.*))?\s*$")
    for i, line in enumerate(lines):
        match = head.match(line)
        if not match:
            continue
        body: list[str] = []
        for nxt in lines[i + 1 :]:
            if nxt.startswith("## "):
                break
            body.append(nxt)
        return (match.group(1) or "").strip(), "\n".join(body).strip() + "\n"
    raise SystemExit(
        f"CHANGELOG.md n'a pas de section « ## {version} — … ». "
        "Ajoutez-la avant de publier."
    )


def main() -> None:
    version = json.loads(MANIFEST.read_text(encoding="utf-8"))["version"]
    subtitle, body = section(CHANGELOG.read_text(encoding="utf-8"), version)
    if not body.strip():
        raise SystemExit(f"La section {version} du CHANGELOG est vide.")
    title = f"{PRODUCT} {version}" + (f" — {subtitle}" if subtitle else "")
    # A letter in the number means a beta (RELEASES.md): published as a pre-release.
    prerelease = "true" if re.search(r"[a-z]", version) else "false"

    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(body, encoding="utf-8")
    out = os.environ.get("GITHUB_OUTPUT")
    values = {"version": version, "tag": f"v{version}", "title": title, "prerelease": prerelease}
    text = "".join(f"{k}={v}\n" for k, v in values.items())
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
