"""The kind of heating in the advisor's scenarios (engine 3.9.5, Frank, 5 November): a radiator with a core or a heated
floor keeps giving off heat once stopped and is slow to warm again, a wood stove is not put out by a window, a heat pump
costs a third. Chambre P, 5 November at 21 h 22: « À essayer — Aérez 5 min » while its radiator was heating."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.decide import Gesture, Thermostat, decide, simulate
from advisor.physics.heaters import HEATERS, given_off, heater
from advisor.physics.thermal import STEP
from advisor.snapshot import load, restore

WINDOW = ((1.33, 0.95),)


class Kinds(unittest.TestCase):

    def test_a_convector_is_the_default(self):
        self.assertEqual(heater(None), HEATERS["radiator"])
        self.assertEqual(heater("unknown"), HEATERS["radiator"])
        self.assertEqual(given_off(0.2, 0.9, 0.0, STEP), 0.9)

    def test_a_core_gives_off_two_thirds_of_the_change_in_its_delay(self):
        given = 1.0
        for _ in range(6):   # 30 minutes
            given = given_off(given, 0.0, HEATERS["inertia"].lag, STEP)
        self.assertAlmostEqual(given, 0.368, places=2)

    def test_an_open_window_puts_out_a_pellet_stove_not_a_wood_stove(self):
        wood, pellet = Thermostat(20.0, kind="stove"), Thermostat(20.0, kind="pellet")
        self.assertGreater(wood.power(19.0, 10.0, WINDOW), 0.0)
        self.assertEqual(pellet.power(19.0, 10.0, WINDOW), 0.0)

    def test_the_kind_follows_the_schedule(self):
        self.assertEqual(Thermostat(20.0, then=17.0, at=10.0, kind="inertia").scheduled(20).kind, "inertia")


class ChambreP(unittest.TestCase):
    """The real snapshot of 21 h 22: radiator heating to 20 °C, 75 % of humidity, the walls' corners at risk of mould."""

    def setUp(self):
        self.args = restore(load(Path(__file__).parent / "fixtures" / "chambre-p-5-novembre-21h22.json"))

    def kind(self, kind):
        twins = self.args["twins"]
        return {**self.args, "twins": replace(twins, thermostat=replace(twins.thermostat, kind=kind))}

    def airing(self, kind):
        a = self.kind(kind)
        return [simulate(a["twins"], a["now"], a["coming"], g) for g in (Gesture("nothing"), Gesture("open", 5))]

    def test_a_kind_not_set_changes_nothing(self):
        before = self.args
        after = self.kind("radiator")
        for g in (Gesture("nothing"), Gesture("open", 5)):
            self.assertEqual(simulate(before["twins"], before["now"], before["coming"], g),
                             simulate(after["twins"], after["now"], after["coming"], g))
        self.assertEqual(decide(**before).passive, decide(**after).passive)

    def test_an_airing_costs_more_with_a_storage_radiator(self):
        idle, opened = self.airing(None)
        idle_core, opened_core = self.airing("inertia")
        self.assertGreater(opened_core.spent - idle_core.spent, opened.spent - idle.spent + 0.1)

    def test_with_storage_radiators_the_airing_is_still_worth_trying(self):
        # Frank's bedrooms (5 November): the mould at the cold corners still carries it, the heat it costs counted.
        decision = decide(**self.kind("inertia"))
        self.assertEqual(decision.gesture, Gesture("nothing"))
        self.assertEqual(decision.passive, Gesture("open", 5))

    def test_a_heated_floor_is_not_aired_while_it_heats(self):
        # The floor goes on giving off for hours and takes hours to warm again: the five minutes cost what they spare.
        decision = decide(**self.kind("floor"))
        self.assertEqual(decision.gesture, Gesture("nothing"))
        self.assertIsNone(decision.passive)

    def test_a_heat_pump_spends_a_third(self):
        idle, _ = self.airing(None)
        idle_pump, _ = self.airing("ac")
        self.assertAlmostEqual(idle_pump.spent, idle.spent / 3, places=6)


if __name__ == "__main__":
    unittest.main()
