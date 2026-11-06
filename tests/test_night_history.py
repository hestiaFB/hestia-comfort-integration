"""The nightly learning reads the history lighter (PLAN-OPTIMISATION.md, point 1): only the attributes it uses, a state
repeated as it was kept once, and every series it builds is the same as from the raw history."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.hestia_comfort.advisor_home import night_rows
from custom_components.hestia_comfort.advisor.bench.history import attribute, contacts, numbers

START = datetime(2026, 11, 1, tzinfo=timezone.utc)


def state(value, changed, updated, **attributes):
    return SimpleNamespace(state=value, attributes={"friendly_name": "x", **attributes},
                           last_changed=START + timedelta(seconds=changed), last_updated=START + timedelta(seconds=updated))


def raw(entity_id, states):
    return [{"entity_id": entity_id, "state": s.state, "attributes": dict(s.attributes),
             "last_changed": s.last_changed.isoformat(), "last_updated": s.last_updated.isoformat()} for s in states]


def light(entity_id, states, attributes, slice_size=7):
    """As night_history reads them: in slices, the last key carried from one to the next."""
    rows, last = [], None
    for i in range(0, len(states), slice_size):
        more, last = night_rows(entity_id, states[i:i + slice_size], attributes, last)
        rows.extend(more)
    return rows


def same(a, b, since=True):
    """Equal at every moment; `since` (when the value held was reported) too, but for the attributes: dated by their
    row's update, the learning only reads their value."""
    times = sorted(set(a.times) | set(b.times))
    probe = [t + d for t in times for d in (timedelta(0), timedelta(microseconds=1), timedelta(seconds=29))]
    return all(a.at(t) == b.at(t) and (not since or a.since(t) == b.since(t)) for t in probe)


class NightHistory(unittest.TestCase):
    def test_a_thermostat_keeps_its_power_and_drops_the_rest(self):
        states, changed, power = [], 0, 0
        rng = random.Random(3)
        for k in range(400):
            if rng.random() < 0.2:
                changed = k * 60
            power = rng.choice((power, power, 0, 40, 100))
            # Most rows change only an attribute the learning does not read (its current temperature).
            states.append(state("heat" if changed % 120 == 0 else "off", changed, k * 60, power_percent=power, current_temperature=19 + k % 7))
        rows = light("climate.salon", states, True)
        self.assertLess(len(rows), len(states))
        self.assertTrue(all(set(r["attributes"]) <= {"power_percent", "current_position"} for r in rows))
        before, after = {"climate.salon": raw("climate.salon", states)}, {"climate.salon": rows}
        self.assertTrue(same(attribute(before, "climate.salon", "power_percent", 0.01), attribute(after, "climate.salon", "power_percent", 0.01), since=False))

    def test_measures_and_contacts_read_the_same(self):
        rng = random.Random(7)
        # As Home Assistant writes them: a value reported again keeps the moment it changed.
        temperature, changed, value = [], 0, None
        for k in range(500):
            new = f"{20 + rng.randint(0, 3) / 10:.1f}"
            if new != value:
                changed, value = k * 30, new
            temperature.append(state(value, changed, k * 30))
        # A contact: openings, a sensor that stops answering, and repeated reports of the same state.
        contact, changed, value = [], 0, "off"
        for k in range(300):
            new = rng.choice((value, value, value, "on", "off", "unavailable"))
            if new != value:
                changed, value = k * 20, new
            contact.append(state(value, changed, k * 20))
        for entity_id, states, series in (("sensor.t", temperature, numbers), ("binary_sensor.f", contact, contacts)):
            before, after = {entity_id: raw(entity_id, states)}, {entity_id: light(entity_id, states, False)}
            self.assertTrue(same(series(before, entity_id), series(after, entity_id)), entity_id)
            self.assertEqual(series(before, entity_id).times[:1], series(after, entity_id).times[:1])
            self.assertEqual(after[entity_id][0]["attributes"], {})


if __name__ == "__main__":
    unittest.main()
