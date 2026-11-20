"""The sun as a bonus of warmth (moteur 3.22.0, Frank, 20 November at 11 h 39).

« Trop de paramètres […] cela doit être un conseil passif : si la radiation est élevée, que les prévisions sont bonnes,
on peut dire que le soleil peut apporter un bonus de chaleur, sans précisions, de telle heure à telle heure, suivant
l'orientation. » The figures of 3.21 (kWh spared, °C kept at bedtime) came from the twins: Chambre A's had learned its
south window 30 times weaker than Chambre M's, the same sun warming both alike on the 19th (+0,8 and +1,0 °C), so the A
never had its line. In the heating season the line now says a bonus, from the windows' orientation and a strong sun
forecast, never a figure. A line only: the banner's gestures do not change.
"""
from datetime import datetime
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.knowing import RoomView, Window, sun_on_windows  # noqa: E402
from advisor.words import tip_text  # noqa: E402

PARIS = ZoneInfo("Europe/Paris")
HOME = (43.447, 5.470)
NOW = datetime(2026, 11, 19, 11, 0, tzinfo=PARIS)
SOUTH = [Window("binary_sensor.fenetre_a_contact", 180)]
# The station's forecast of the 19th (W/m², horizontal), and of a grey day like the 18th.
SUNNY = {datetime(2026, 11, 19, h, 0, tzinfo=PARIS): v
         for h, v in {9: 60.0, 10: 116.0, 11: 281.0, 12: 302.0, 13: 277.0, 14: 141.0, 15: 38.0, 16: 20.0}.items()}
GREY = {h: v * 0.6 for h, v in SUNNY.items()}


def view(bonus, forecast=SUNNY, manual=False, gain=None, now=NOW):
    return RoomView(now, *HOME, windows=SOUTH, sun_forecast=forecast, sun_gain=gain, sun_bonus=bonus,
                    shutters_manual=manual)


def said(bonus, forecast=SUNNY, manual=False, gain=None, now=NOW):
    tips = sun_on_windows(view(bonus, forecast, manual, gain, now))
    return tip_text(tips[0], now=now) if tips else None


class TheBonus(unittest.TestCase):
    def test_a_bonus_without_a_figure(self):
        self.assertEqual(said({"closed": False}),
                         "Grand soleil sur la fenêtre sud jusqu'à 16 h 35 : un bonus de chaleur")

    def test_from_such_an_hour_to_such_an_hour_before_it_comes(self):
        line = said({"closed": False}, now=NOW.replace(hour=8))
        self.assertRegex(line, r"^Grand soleil prévu sur la fenêtre sud de \d+ h( \d+)? à 16 h 35 : un bonus de chaleur$")

    def test_chambre_a_has_it_whatever_its_twin_learned(self):
        # 20 November: the A's twin counted 0,08 °C of sun against 0,74 for the M, both south. The bonus does not ask it.
        self.assertIsNotNone(said({"closed": False}, gain=0.08))

    def test_not_said_on_a_grey_day(self):
        self.assertIsNone(said({"closed": False}, forecast=GREY))

    def test_not_said_once_the_strong_sun_is_over(self):
        # At 14 h on the 19th only 141 and 38 W/m² remained: no more bonus to speak of.
        self.assertIsNone(said({"closed": False}, now=NOW.replace(hour=14)))

    def test_not_said_without_a_forecast(self):
        self.assertIsNone(said({"closed": False}, forecast={}))

    def test_shutters_without_a_sensor_say_if(self):
        self.assertTrue(said({"closed": False}, manual=True).endswith(": un bonus de chaleur, si les volets sont ouverts"))

    def test_a_connected_shutter_shut_says_open_it(self):
        self.assertTrue(said({"closed": True}).endswith(": ouvrez le volet pour en profiter"))

    def test_in_english_and_german(self):
        tips = sun_on_windows(view({"closed": False}))
        self.assertTrue(tip_text(tips[0], "en", now=NOW).endswith(": a bonus of warmth"))
        self.assertTrue(tip_text(tips[0], "de", now=NOW).endswith(": ein Wärmebonus"))


class OutOfTheHeatingSeason(unittest.TestCase):
    def test_the_warming_from_half_a_degree(self):
        # No bonus (summer, a room already too warm): the sun said when it warms the room by 0,5 °C, with its figure.
        self.assertIsNone(said(None, gain=0.2))
        self.assertTrue(said(None, gain=0.8).endswith(": +0,8 °C dans la pièce"))


if __name__ == "__main__":
    unittest.main()
