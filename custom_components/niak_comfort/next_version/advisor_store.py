"""What the 3.0 advisor keeps on disk (niak-comfort/docs/PASSAGE-CONFORT-3.md § 2.5).

In `<config>/hestia_comfort/`: the journal of the advice changes (60 days), the replayable snapshots (10 days), the
situations the household reported with « Ce conseil ne va pas » (without limit), the opinions and the gestures followed.
Everything here is plain file work, run in the executor; the twins and each room's state go in Home Assistant's Store.
"""
from datetime import datetime, timedelta
import json
from pathlib import Path

from .advisor.feedback import followed_share
from .advisor.snapshot import dump, load as load_snapshot, replay, trace

FOLDER = "hestia_comfort"
JOURNAL_DAYS, SNAPSHOT_DAYS = 60, 10


class AdvisorFiles:
    def __init__(self, config_path: str):
        self.folder = Path(config_path) / FOLDER

    def _append(self, name: str, line: dict) -> None:
        self.folder.mkdir(exist_ok=True)
        with open(self.folder / name, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    def journal(self, line: dict) -> None:
        self._append("journal.jsonl", line)

    def feedback(self, line: dict) -> None:
        self._append("retours.jsonl", line)

    def learned(self, line: dict) -> None:
        self._append("apprentissage.jsonl", line)

    def keep(self, slug: str, now: datetime, local: datetime, snap: dict, decision, words, changed: bool) -> None:
        """The room's last snapshot, always; and each change of advice, with its trace, for SNAPSHOT_DAYS."""
        folder = self.folder / "instantanes"
        folder.mkdir(parents=True, exist_ok=True)
        dump(snap, folder / f"{slug}-dernier.json")
        if changed:
            dump({"instantane": snap, "trace": trace(snap, decision, words)}, folder / f"{slug}-{local:%Y%m%d-%H%M}.json")
            limit = now.timestamp() - SNAPSHOT_DAYS * 86400
            for old in folder.glob("*-2*.json"):
                if old.stat().st_mtime < limit:
                    old.unlink()

    def signal(self, slug: str, local: datetime, kind: str, note: str, shown: dict, snap: dict | None = None) -> str | None:
        """The room's last snapshot, with its trace and what the card showed, kept in « signales » without limit. `snap`:
        the one kept in memory (the analysis tools off, PLAN-OPTIMISATION.md point 16), else the last one written."""
        if snap is None:
            last = self.folder / "instantanes" / f"{slug}-dernier.json"
            if not last.exists():
                return None
            snap = load_snapshot(last)
        decision, words = replay(snap)
        folder = self.folder / "signales"
        folder.mkdir(parents=True, exist_ok=True)
        file = f"signale-{slug}-{local:%Y%m%d-%H%M%S}-{kind}.json"
        dump({"avis": kind, "note": note, "affiche": shown, "instantane": snap, "trace": trace(snap, decision, words)}, folder / file)
        return file

    def prune(self, now: datetime) -> None:
        """The journal kept JOURNAL_DAYS: older lines go, once a night."""
        path = self.folder / "journal.jsonl"
        if not path.exists():
            return
        since = (now - timedelta(days=JOURNAL_DAYS)).isoformat()
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and json.loads(line).get("heure", "") >= since]
        path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")

    def atelier(self, now: datetime) -> dict:
        """The Atelier's chronology: the advice changes of the last days, the snapshots kept, the opinions given and the
        share of gestures followed by room over 30 days (CAHIER-MOTEUR.md § 15, § 16 bis.3)."""
        path = self.folder / "journal.jsonl"
        lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()[-300:] if line.strip()] if path.exists() else []
        kept = sorted((p.name for p in (self.folder / "instantanes").glob("*.json")), reverse=True) if (self.folder / "instantanes").exists() else []
        path = self.folder / "retours.jsonl"
        feedback = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
        since = (now - timedelta(days=30)).isoformat()
        followed = {}
        for line in feedback:
            if line["type"] == "suivi" and line["heure"] >= since:
                followed.setdefault(line["piece"], []).append(line)
        return {"journal": lines[::-1], "instantanes": kept,
                "avis": [line for line in feedback if line["type"] == "avis"][::-1][:100],
                "suivis": {room: followed_share(records) for room, records in followed.items()},
                "derniers_suivis": [line for line in feedback if line["type"] == "suivi"][::-1][:30]}

    def trace(self, file: str) -> dict | None:
        """One decision's trace, layer by layer (CAHIER-MOTEUR.md § 16 bis.1): kept with the snapshot, or replayed from it."""
        if "/" in file or "\\" in file or file.startswith("."):
            return None
        path = self.folder / ("signales" if file.startswith("signale-") else "instantanes") / file
        if not path.exists():
            return None
        kept = load_snapshot(path)
        if "trace" in kept:
            return kept
        decision, words = replay(kept)
        return {"instantane": kept, "trace": trace(kept, decision, words)}
