"""The sun as a bonus of warmth (moteur 3.22.0, Frank, 20 November at 11 h 39), under a sky that lets it through (3.22.1, 3.22.2).

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
from engine.sunlight import CONDITIONS, sky_factor  # noqa: E402

PARIS = ZoneInfo("Europe/Paris")
HOME = (43.447, 5.470)
NOW = datetime(2026, 11, 19, 11, 0, tzinfo=PARIS)
SOUTH = [Window("binary_sensor.fenetre_a_contact", 180)]
# The station's forecast of the 19th (W/m², horizontal), and of a grey day like the 18th.
SUNNY = {datetime(2026, 11, 19, h, 0, tzinfo=PARIS): v
         for h, v in {9: 60.0, 10: 116.0, 11: 281.0, 12: 302.0, 13: 277.0, 14: 141.0, 15: 38.0, 16: 20.0}.items()}
GREY = {h: v * 0.6 for h, v in SUNNY.items()}


def view(bonus, forecast=SUNNY, manual=False, gain=None, now=NOW, sky=None):
    return RoomView(now, *HOME, windows=SOUTH, sun_forecast=forecast, sun_gain=gain, sun_bonus=bonus,
                    shutters_manual=manual, sky=sky or {})


def said(bonus, forecast=SUNNY, manual=False, gain=None, now=NOW, sky=None):
    tips = sun_on_windows(view(bonus, forecast, manual, gain, now, sky))
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

    def test_not_said_when_the_weather_says_cloudy(self):
        # Labo, 20 November at 13 h 12: Open-Meteo foresaw 320 to 395 W/m², Météo-France « nuageux », grey outside, and
        # the card said « Grand soleil ». Hestia Weather's sky now has the last word on the strong sun.
        cloudy = {h: sky_factor({"condition": "cloudy"}) for h in SUNNY}
        self.assertIsNone(said({"closed": False}, sky=cloudy))
        # The darker of the cover and the condition (advisor_home.py `_from_weather`): « nuageux » at 50 % is cloudy.
        cloudy_half = {h: min(sky_factor({"cloud_coverage": 50}), CONDITIONS["cloudy"]) for h in SUNNY}
        self.assertIsNone(said({"closed": False}, sky=cloudy_half))
        overcast = {h: sky_factor({"cloud_coverage": 90}) for h in SUNNY}
        self.assertIsNone(said({"closed": False}, sky=overcast))
        # Out of the heating season, never « Grand soleil » under such a sky either.
        tips = sun_on_windows(view(None, gain=0.8, sky=cloudy))
        self.assertTrue(tip_text(tips[0], now=NOW).startswith("Soleil sur la fenêtre sud"))

    def test_a_few_clouds_leave_it(self):
        fair = {h: sky_factor({"cloud_coverage": 40}) for h in SUNNY}
        self.assertIsNotNone(said({"closed": False}, sky=fair))
        self.assertIsNotNone(said({"closed": False}, sky={h: sky_factor({"condition": "sunny"}) for h in SUNNY}))

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


class TheSkyNow(unittest.TestCase):
    """Labo, 20 November at 13 h 19: every hourly forecast said « sunny » from 14 h to 16 h, Hestia Weather's sky now
    « cloudy », 100 to 150 W/m² at the station. The sky seen now holds for this hour and the next two (3.22.2)."""

    def home(self, seen, sky=None):
        from datetime import timezone
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from custom_components.hestia_comfort import advisor_home
        home = advisor_home.AdvisorHome.__new__(advisor_home.AdvisorHome)
        hours = [datetime(2026, 11, 20, h, 0, tzinfo=timezone.utc) for h in range(12, 17)]
        home.forecast = {h: (12.0, 70.0, 350.0) for h in hours}
        home.sky, home.sun_missed = sky or {}, None
        home._sky_now = lambda: seen
        return home, hours

    def test_a_grey_sky_now_holds_two_hours(self):
        home, hours = self.home(sky_factor({"condition": "cloudy"}))
        today = home.sun_today(hours[0].replace(minute=19))
        self.assertEqual([today[h][1] for h in hours[:3]], [0.25] * 3)
        self.assertIsNone(today[hours[3]][1])  # then the forecast's own sky

    def test_the_darker_of_the_two(self):
        home, hours = self.home(1.0)
        home.sky = {hours[1]: 0.25}
        today = home.sun_today(hours[0])
        self.assertEqual(today[hours[1]][1], 0.25)
        self.assertEqual(today[hours[0]][1], 1.0)

    def test_an_older_hestia_weather_changes_nothing(self):
        home, hours = self.home(None)
        self.assertTrue(all(v == (350.0, None) for v in home.sun_today(hours[0]).values()))


class OutOfTheHeatingSeason(unittest.TestCase):
    def test_the_warming_from_half_a_degree(self):
        # No bonus (summer, a room already too warm): the sun said when it warms the room by 0,5 °C, with its figure.
        self.assertIsNone(said(None, gain=0.2))
        self.assertTrue(said(None, gain=0.8).endswith(": +0,8 °C dans la pièce"))


if __name__ == "__main__":
    unittest.main()
