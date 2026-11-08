"""Every command the panel sends carries its language (frontend/panel.ts `ws`): a command that does not accept it is
refused by Home Assistant (« not a valid option at 'language' »). « Je participe » was, 8 November: the switch moved on
screen and nothing was saved."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "hestia_comfort"


def _sent_by_panel() -> set[str]:
    found = set()
    for path in (ROOT / "frontend").glob("*.ts"):
        text = path.read_text(encoding="utf-8")
        found |= set(re.findall(r"this\.ws(?:<[^>]*>)?\(\{type:'(hestia_comfort/[a-z_/0-9]+)'", text))
    return found


def _declared() -> dict[str, str]:
    out = {}
    for path in INTEGRATION.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for schema in re.findall(r"@websocket_api\.websocket_command\((\{.*?\})\)\n", text, re.S):
            name = re.search(r'"(hestia_comfort/[^"]+)"', schema)
            if name:
                out[name.group(1)] = schema
    return out


def test_panel_commands_accept_the_language():
    sent, declared = _sent_by_panel(), _declared()
    assert "hestia_comfort/set_analysis" in sent
    refused = sorted(c for c in sent if c in declared and not re.search(r"LANGUAGE|\"language\"", declared[c]))
    assert refused == []
