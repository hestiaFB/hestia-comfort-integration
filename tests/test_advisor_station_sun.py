"""The forecast sun checked against the station's: its shade learned by the sun's position, the clouds of the last hours."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.physics.station_sun import cell, clouds_missed, corrected, learn_shade, share

LAT, LON = 43.45, 5.46
# A summer noon (sun high in the south) and a winter morning (sun low in the south-east), UTC hours.
NOON = datetime(2026, 6, 21, 11, tzinfo=timezone.utc)
WINTER = datetime(2026, 12, 21, 9, tzinfo=timezone.utc)


def days(start, count, forecast, measured, clouds=0.0):
    return [(start + timedelta(days=d), forecast, measured, clouds) for d in range(count)]


class Shade(unittest.TestCase):
    def test_the_low_sun_hidden_and_the_high_sun_seen(self):
        shade = learn_shade(days(NOON, 6, 900.0, 880.0) + days(WINTER, 6, 300.0, 90.0), LAT, LON)
        self.assertGreater(share(shade, cell(NOON, LAT, LON)), 0.9)
        self.assertLess(share(shade, cell(WINTER, LAT, LON)), 0.4)

    def test_cloudy_hours_teach_nothing(self):
        self.assertEqual(learn_shade(days(NOON, 6, 900.0, 200.0, clouds=80.0), LAT, LON), {})

    def test_a_cell_needs_several_clear_hours(self):
        self.assertEqual(learn_shade(days(NOON, 2, 900.0, 880.0), LAT, LON), {})

    def test_cells_learned_before_are_kept(self):
        known = {"120/10": 0.3}
        self.assertEqual(learn_shade(days(NOON, 6, 900.0, 880.0), LAT, LON, known)["120/10"], 0.3)

    def test_an_unknown_cell_borrows_from_its_neighbours(self):
        where = cell(NOON, LAT, LON)
        azimuth, elevation = (int(v) for v in where.split("/"))
        self.assertEqual(share({f"{azimuth + 10}/{elevation}": 0.8}, where), 0.8)
        self.assertIsNone(share({}, where))

    def test_night_has_no_cell(self):
        self.assertIsNone(cell(datetime(2026, 6, 21, 22, tzinfo=timezone.utc), LAT, LON))


class Clouds(unittest.TestCase):
    def setUp(self):
        self.shade = {cell(NOON - timedelta(hours=h), LAT, LON): 1.0 for h in (1, 2)}

    def test_more_clouds_than_forecast(self):
        recent = [(NOON - timedelta(hours=h), 800.0, 400.0) for h in (1, 2)]
        self.assertAlmostEqual(clouds_missed(recent, self.shade, LAT, LON), 0.5)

    def test_nothing_read_in_the_station_shade(self):
        shaded = {k: 0.3 for k in self.shade}
        recent = [(NOON - timedelta(hours=h), 800.0, 100.0) for h in (1, 2)]
        self.assertIsNone(clouds_missed(recent, shaded, LAT, LON))

    def test_nothing_read_without_a_measure_or_a_shade(self):
        self.assertIsNone(clouds_missed([(NOON, 800.0, None)], self.shade, LAT, LON))
        self.assertIsNone(clouds_missed([(NOON, 800.0, 400.0)], {}, LAT, LON))

    def test_the_gap_fades_with_the_hours(self):
        self.assertAlmostEqual(corrected(800.0, 0, 0.5), 400.0)
        self.assertGreater(corrected(800.0, 3, 0.5), corrected(800.0, 1, 0.5))
        self.assertAlmostEqual(corrected(800.0, 40, 0.5), 800.0, delta=1)
        self.assertEqual(corrected(800.0, 1, None), 800.0)


if __name__ == "__main__":
    unittest.main()
