"""A decision kept as one file gives the same decision when replayed, and its trace says in which layer it was made."""
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.decide import Gesture, Now, Thermostat, decide
from advisor.proof import PROVEN, SUPPOSED
from advisor.snapshot import capture, dump, load, replay, trace, turning_point
from advisor.words import phrase
from test_advisor_decide import FRENCH, TWINS, WEST, day, night


def kept(twins, now, coming, **kw):
    """Decide, keep the snapshot in a file, read it back."""
    decision = decide(twins, now, coming, **{k: v for k, v in kw.items() if k in ("previous", "forbidden", "proof")})
    snap = capture(twins, now, coming, end_hour=kw.get("end_hour", 7), reason=kw.get("reason"),
                   **{k: v for k, v in kw.items() if k in ("previous", "forbidden", "proof")})
    with tempfile.TemporaryDirectory() as folder:
        dump(snap, Path(folder) / "instantane.json")
        return decision, load(Path(folder) / "instantane.json")


class Snapshots(unittest.TestCase):
    def test_the_night_of_30_october_replays_exactly(self):
        now = Now(air=20.6, walls=20.4, opened=(FRENCH.size,), humidity=66.0, night=True, missed=0.3)
        decision, snap = kept(replace(TWINS, thermostat=Thermostat(19.0)), now, night(), proof={"heat": PROVEN})
        again, words = replay(snap)
        self.assertEqual((again.gesture, again.rule, again.level), (decision.gesture, decision.rule, decision.level))
        self.assertEqual(again.gain, decision.gain)
        self.assertEqual(words["title"], "Refermez")

    def test_sun_shutters_and_held_back_gestures_replay_too(self):
        coming = [(replace(u, facade=250.0, facade_shut=250.0, facade_all=400.0, shade=0.5), w) for u, w in day(outdoor=14.0)]
        now = Now(air=20.2, walls=20.2, opened=(FRENCH.size, WEST.size), humidity=55.0)
        decision, snap = kept(TWINS, now, coming, proof={"heat": SUPPOSED}, end_hour=17)
        again, words = replay(snap)
        self.assertEqual((again.gesture, again.passive, again.gain), (decision.gesture, decision.passive, decision.gain))
        self.assertEqual(words["try"], phrase(decision, 17)["try"])

    def test_what_if_a_warmer_outside(self):
        now = Now(air=20.6, walls=20.6, opened=(FRENCH.size,), humidity=66.0, night=True)
        decision, snap = kept(TWINS, now, night())
        point = turning_point(snap, decision)
        self.assertIsNotNone(point)
        self.assertGreater(point["outdoor"], 0)     # only a warmer night would leave the window open

    def test_the_trace_goes_layer_by_layer(self):
        now = Now(air=20.6, walls=20.6, opened=(FRENCH.size,), humidity=66.0, night=True)
        decision, snap = kept(TWINS, now, night(), forbidden=frozenset({"open"}), reason="rain_soon")
        again, words = replay(snap)
        found = trace(snap, again, words)
        self.assertEqual(list(found), ["1_mesures", "2_jumeau", "3_gestes", "4_scenarios", "5_regle", "6_changerait", "7_phrase"])
        self.assertEqual(found["5_regle"]["regle"], "safety")
        self.assertEqual(found["7_phrase"]["line"], "la pluie arrive")
        json.dumps(found)  # plain JSON, ready for the diagnostics and the Atelier page


if __name__ == "__main__":
    unittest.main()
