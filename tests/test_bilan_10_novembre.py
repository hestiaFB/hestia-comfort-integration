"""The house's day of 10 November (moteur 3.14.0), read with Frank: what the engine got wrong.

- The Salon's stove asked 100 % at 6 h and 17 h but waited for its lighting to be confirmed, never lit: every room
  forecast it burning (« 21,7 °C à 20 h » for a Salon at 19 °C, Chambre M « 23,1 °C » at 19,9 °C).
- The stove's shares learned by the rooms added up to 128 %.
- 19 hours of « Rien à faire » left no word in the journal of what the banner's line said.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.hestia_comfort.advisor_home import share_caps  # noqa: E402
from custom_components.hestia_comfort.advisor.bench.history import lit_power  # noqa: E402
from custom_components.hestia_comfort.advisor.physics.fit import FREE, params_of  # noqa: E402
from custom_components.hestia_comfort.advisor.physics.thermal import Params  # noqa: E402
from custom_components.hestia_comfort.room.advice import house_power_now, phrase_subject, stove_waiting  # noqa: E402

NOW = datetime(2026, 11, 10, 16, 0, tzinfo=timezone.utc)


def hass_with(**states):
    return SimpleNamespace(states=SimpleNamespace(get=lambda e: states.get(e)))


def poele(action, power, mode="heat"):
    return SimpleNamespace(state=mode, attributes={"hvac_action": action, "power_percent": power})


class StoveWaitingTests(unittest.TestCase):
    def test_asked_but_idle_it_waits_and_gives_nothing(self):
        hass = hass_with(**{"climate.poele": poele("idle", 100)})
        self.assertTrue(stove_waiting(hass, "climate.poele"))
        self.assertEqual(house_power_now(hass, "climate.poele"), 0.0)

    def test_lit_it_gives_what_it_is_asked(self):
        hass = hass_with(**{"climate.poele": poele("heating", 60)})
        self.assertFalse(stove_waiting(hass, "climate.poele"))
        self.assertAlmostEqual(house_power_now(hass, "climate.poele"), 0.6)

    def test_at_rest_on_frost_it_does_not_wait(self):
        """Not asked (frost, 0 %): still simulated, its schedule may light it at 17 h."""
        hass = hass_with(**{"climate.poele": poele("idle", 0)})
        self.assertFalse(stove_waiting(hass, "climate.poele"))
        self.assertFalse(stove_waiting(hass_with(), "climate.poele"))
        self.assertFalse(stove_waiting(hass_with(**{"climate.poele": poele("off", 100, mode="off")}), "climate.poele"))


class LitPowerTests(unittest.TestCase):
    def test_the_night_counts_the_stove_only_while_it_burns(self):
        def row(minutes, action, power):
            at = (NOW + timedelta(minutes=minutes)).isoformat()
            return {"state": "heat", "last_changed": at, "last_updated": at, "attributes": {"hvac_action": action, "power_percent": power}}
        history = {"climate.poele": [row(0, "idle", 0), row(60, "idle", 100), row(75, "idle", 0), row(120, "heating", 80)]}
        series = lit_power(history, "climate.poele")
        self.assertEqual(series.at(NOW + timedelta(minutes=65)), 0.0)
        self.assertAlmostEqual(series.at(NOW + timedelta(minutes=130)), 0.8)

    def test_a_history_without_the_action_keeps_the_power(self):
        at = NOW.isoformat()
        history = {"climate.poele": [{"state": "heat", "last_changed": at, "last_updated": at, "attributes": {"power_percent": 50}}]}
        self.assertAlmostEqual(lit_power(history, "climate.poele").at(NOW + timedelta(minutes=5)), 0.5)


class ShareTests(unittest.TestCase):
    def test_shares_over_the_whole_keep_their_part_of_it(self):
        found = share_caps({"salon": 0.55, "sdb": 0.27, "al": 0.15, "m": 0.15, "a": 0.09, "p": 0.07, "b": 0.0})
        self.assertAlmostEqual(sum(found.values()), 1.0)
        self.assertAlmostEqual(found["salon"], 0.55 / 1.28)

    def test_under_the_whole_each_may_grow_by_what_is_left(self):
        found = share_caps({"salon": 0.5, "p": 0.1, "new": None})
        self.assertAlmostEqual(found["salon"], 0.9)
        self.assertAlmostEqual(found["new"], 0.4)

    def test_the_search_never_goes_above_the_cap(self):
        base = Params(h_env=50.0, cm=1e7, ca=5e5, h_am=3e5, heat=1000.0, sun=5.0, gains=50.0, window=0.1, leaks=10.0)
        x = [0.0 if log else (0.9 if name == "share" else getattr(base, name)) for name, log, _ in FREE]
        self.assertAlmostEqual(params_of(base, x, 0.3).share, 0.3)
        self.assertAlmostEqual(params_of(base, x).share, 0.9)


class JournalTests(unittest.TestCase):
    def test_the_subject_of_a_line_leaves_its_figures_aside(self):
        self.assertEqual(phrase_subject("Humidité 73 % à 7 h : aucun geste ne ferait vraiment mieux"),
                         phrase_subject("Humidité 72 % à 8 h : aucun geste ne ferait vraiment mieux"))
        self.assertNotEqual(phrase_subject("Aucun geste ne ferait vraiment mieux : 21,7 °C à 20 h"),
                            phrase_subject("Humidité 75 % à 20 h : aucun geste ne ferait vraiment mieux"))


if __name__ == "__main__":
    unittest.main()
