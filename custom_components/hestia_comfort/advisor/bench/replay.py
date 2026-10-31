"""Replay a decision from its snapshot, and its trace layer by layer (CAHIER-MOTEUR.md § 16 bis.2).

    cd custom_components/hestia_comfort && python -m advisor.bench.replay instantane.json [--dehors +1.5] [--poids heat=2]

`--dehors` makes the outside warmer (or colder) all along; `--poids` changes a weight of the cost (advisor/decide.py
`Weights`): « Et si… ? », nothing saved.
"""
from dataclasses import replace
import json
import sys

from ..snapshot import _plain, load, replay, restore, trace, warmer


def main(argv):
    snap = load(argv[0])
    args, changes = restore(snap), {}
    for flag, value in zip(argv[1::2], argv[2::2]):
        if flag == "--dehors":
            changes["coming"] = warmer(args["coming"], float(value))
        elif flag == "--poids":
            name, number = value.split("=")
            changes["weights"] = replace(changes.get("weights", args["weights"]), **{name: float(number)})
    decision, words = replay(snap, **changes)
    if "coming" in changes:
        snap = {**snap, "coming": [[_plain(u), w] for u, w in changes["coming"]]}
    if "weights" in changes:
        snap = {**snap, "weights": _plain(changes["weights"])}
    print(json.dumps(trace(snap, decision, words), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
