"""The house's day of 11 November (moteur 3.14.1), read with Frank: what the engine got wrong.

1. The outside's humidity was the forecast's, never pulled toward the station: 91 % for 78 % measured at 15 h 47, and
   « Refermez » for nothing in the Salon.
2. A gesture left aside said « aucun geste ne ferait vraiment mieux » (Chambres P, M and AL at 20 h 36).
3. « Dehors, l'air est aussi humide qu'ici : aérer n'assèche pas » beside « Aérez 30 min vers 19 h ».
4. The stove just lit at 100 % was held at full power two hours in the other rooms: Chambre M 24,8 °C foreseen, 21,8 °C.
5. The twins of the water were never scored over a night: Chambre P 89 % foreseen at 7 h, 82 % measured.
6. « À essayer » said « le COV devrait retomber en 15, 30, 45, 75 min » by turns.
7. « Aérez 15 min vers 19 h 45 », « 20 min vers 19 h 50 », « 20 min vers 20 h 10 » in ten minutes.
8. « Aérez 20 min » counted as followed for a window open two minutes.
9. The line's subject took turns under the same « Rien à faire ».
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.hestia_comfort.advisor_home import AdvisorHome  # noqa: E402
from custom_components.hestia_comfort.advisor.decide import Gesture, Now  # noqa: E402
from custom_components.hestia_comfort.advisor.feedback import follow  # noqa: E402
from custom_components.hestia_comfort.advisor.knowing import RoomView, outside_water  # noqa: E402
from custom_components.hestia_comfort.advisor.physics import airfit  # noqa: E402
from custom_components.hestia_comfort.advisor.physics.water import absolute, relative  # noqa: E402
from custom_components.hestia_comfort.advisor.words import aside_line, tip_text  # noqa: E402

PARIS = timezone(timedelta(hours=1))
NOW = datetime(2026, 11, 11, 14, 47, tzinfo=timezone.utc)


def home_with(forecast, houses=None, states=None, stove_paths=None):
    home = AdvisorHome.__new__(AdvisorHome)
    home.forecast, home.sun_missed = forecast, None
    home.houses, home.stove_paths = houses or {}, stove_paths or {}
    states = states or {}
    home.hass = SimpleNamespace(config=SimpleNamespace(latitude=43.45, longitude=5.47),
                                states=SimpleNamespace(get=lambda e: states.get(e)))
    return home


class OutsideWaterTests(unittest.TestCase):
    def test_the_forecast_humidity_is_pulled_toward_the_station(self):
        # 15 h 47: the forecast said 21,8 °C and 80 % (15,4 g/m³ once moved to 19,6 °C), the station 19,6 °C and 78 %.
        hour = NOW.replace(minute=0)
        forecast = {hour + timedelta(hours=h): (21.8, 80.0, 0.0) for h in range(-1, 4)}
        coming = home_with(forecast).coming(NOW, 3, 19.6, 78.0, 0.0, 1.0)
        self.assertAlmostEqual(coming[0][1], absolute(19.6, 78.0), places=2)
        self.assertLess(relative(coming[0][0].outdoor, coming[0][1]), 80.0)

    def test_the_gap_fades_like_the_temperature_one(self):
        hour = NOW.replace(minute=0)
        forecast = {hour + timedelta(hours=h): (15.0, 90.0, 0.0) for h in range(-1, 14)}
        coming = home_with(forecast).coming(NOW, 144, 15.0, 70.0, 0.0, 1.0)
        start, later = coming[0][1], coming[-1][1]
        self.assertAlmostEqual(start, absolute(15.0, 70.0), places=2)
        # Twelve hours on, back most of the way to the forecast, never above saturation.
        self.assertGreater(later, start + 0.5 * (absolute(15.0, 90.0) - start))
        self.assertLessEqual(later, absolute(coming[-1][0].outdoor, 100.0))

    def test_without_a_forecast_humidity_the_station_is_kept(self):
        hour = NOW.replace(minute=0)
        coming = home_with({hour: (19.6, None, 0.0)}).coming(NOW, 2, 19.6, 78.0, 0.0, 1.0)
        self.assertAlmostEqual(coming[0][1], absolute(19.6, 78.0), places=2)


class AsideTests(unittest.TestCase):
    def test_a_gesture_put_aside_is_said_waiting(self):
        line = aside_line({"title": "Ouvrez", "line": "75 % d'humidité à 23 h au lieu de 80 %"},
                          datetime(2026, 11, 11, 22, 36, tzinfo=PARIS))
        self.assertEqual(line, "« Ouvrez » en pause jusqu'à 22 h 35 : 75 % d'humidité à 23 h au lieu de 80 %")
        self.assertNotIn("aucun geste", line)


class GoodToKnowTests(unittest.TestCase):
    def view(self, airing_at=None):
        return RoomView(datetime(2026, 11, 11, 18, 17, tzinfo=PARIS), 43.45, 5.47, air=20.6, humidity=72.0,
                        outdoor=16.2, outdoor_humidity=91.0, water_matters=True, airing_at=airing_at)

    def test_alone_the_outside_as_humid_is_said(self):
        self.assertEqual([t.kind for t in outside_water(self.view())], ["outside_same"])

    def test_an_airing_later_in_a_drier_air_says_its_moment(self):
        at = datetime(2026, 11, 11, 19, 2, tzinfo=PARIS)
        tips = outside_water(self.view((11.4, at)))
        self.assertEqual([t.kind for t in tips], ["outside_drier_later"])
        self.assertEqual(tip_text(tips[0]), "Vers 19 h, l'air dehors sera plus sec qu'ici : le bon moment pour aérer")

    def test_an_airing_for_the_room_own_water_is_not_contradicted(self):
        at = datetime(2026, 11, 11, 19, 2, tzinfo=PARIS)
        self.assertEqual(outside_water(self.view((13.0, at))), [])


class StovePathTests(unittest.TestCase):
    def test_the_other_rooms_follow_the_stove_as_its_room_simulates_it(self):
        stove = SimpleNamespace(state="heat", attributes={"hvac_action": "heating", "power_percent": 100})
        path = [1.0, 0.8, 0.5, 0.2, 0.0, 0.0]
        home = home_with({}, houses={"climate.poele": 8500.0}, states={"climate.poele": stove},
                         stove_paths={"climate.poele": (NOW - timedelta(minutes=5), path)})
        given = home.house_heat_steps(NOW, 8)
        self.assertEqual(given[:5], [8500.0 * s for s in path[1:]])
        self.assertEqual(given[-1], 0.0)

    def test_without_a_fresh_path_the_power_of_the_moment_is_kept(self):
        stove = SimpleNamespace(state="heat", attributes={"hvac_action": "heating", "power_percent": 40})
        home = home_with({}, houses={"climate.poele": 8500.0}, states={"climate.poele": stove},
                         stove_paths={"climate.poele": (NOW - timedelta(minutes=40), [1.0])})
        self.assertEqual(home.house_heat_steps(NOW, 3), [3400.0] * 3)


class NightScoreTests(unittest.TestCase):
    def test_a_slow_drift_over_eight_hours_costs_in_the_score(self):
        when = datetime(2026, 11, 10, 18, 0, tzinfo=timezone.utc)
        rows = []
        for i in range(airfit.NIGHT + airfit.THREE + 12):
            inputs = SimpleNamespace(windows=(), cross=1.0, vent=0.0, purifier=0.0, outdoor=10.0, wind=None, hour=None)
            sample = SimpleNamespace(when=when + timedelta(minutes=5 * i), inputs=inputs, measured=20.0)
            rows.append((sample, 10.0, 10.0))
        x = airfit.first("water")
        wet = list(x)
        wet[4] = 20.0
        drifting = airfit._run("water", wet, 40.0, rows, rows[0][0].when, rows[-1][0].when)
        self.assertTrue(drifting["night"])
        self.assertGreater(abs(drifting["night"][0]), abs(drifting["three"][0]))
        without = sum(abs(v) for v in drifting["hour"]) / len(drifting["hour"]) \
            + sum(abs(v) for v in drifting["three"]) / len(drifting["three"])
        self.assertGreater(airfit.score("water", wet, 40.0, rows, rows[0][0].when, rows[-1][0].when), without)


class FollowedTests(unittest.TestCase):
    def test_two_minutes_open_is_not_a_twenty_minute_airing(self):
        shut, opened = Now(air=20.0, walls=19.0, opened=()), Now(air=20.0, walls=19.0, opened=((1.8, 2.1),))
        asked, _ = follow(None, Gesture("open", 20), "Aérez 20 min", False, shut, NOW)
        asked, out = follow(asked, Gesture("close", after=20), "Laissez ouvert encore 20 min", False, opened,
                            NOW + timedelta(minutes=1))
        self.assertEqual(out, [])
        asked, out = follow(asked, Gesture("open", 20), "Aérez 20 min", False, shut, NOW + timedelta(minutes=3))
        self.assertFalse(out[0]["suivi"])


if __name__ == "__main__":
    unittest.main()
