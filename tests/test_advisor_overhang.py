"""The sun under an overhang: drawn by its shadow, not by a fixed share (Frank, 5 November: the Salon's French windows,
under a 1 m overhang, full of sun on a November noon)."""
from datetime import datetime
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.physics.sunlight import Overhang, lit_share, sun_position, through_windows

HOME = (43.45, 5.47)
ZONE = ZoneInfo("Europe/Paris")
SALON = Overhang(depth=1.0, gap=0.3, height=2.1)
DOOR = 1.18 * 2.1


class OverhangTest(unittest.TestCase):
    def at(self, *when):
        return sun_position(datetime(*when, tzinfo=ZONE), *HOME)

    def test_the_low_sun_of_november_passes_under_it(self):
        elevation, azimuth = self.at(2026, 11, 5, 12, 50)
        self.assertGreater(lit_share(SALON, 180, elevation, azimuth), 0.75)

    def test_the_high_sun_of_june_stays_above_the_window(self):
        elevation, azimuth = self.at(2026, 6, 21, 13, 30)
        self.assertLess(lit_share(SALON, 180, elevation, azimuth), 0.05)

    def test_more_sun_in_november_than_the_former_third(self):
        elevation, azimuth = self.at(2026, 11, 5, 12, 50)
        bare = through_windows(450, elevation, azimuth, [(DOOR, 180, False)])
        under = through_windows(450, elevation, azimuth, [(DOOR, 180, SALON)])
        self.assertGreater(under, bare / 3 * 2)
        self.assertLessEqual(under, bare)

    def test_in_june_little_more_than_the_sky(self):
        elevation, azimuth = self.at(2026, 6, 21, 13, 30)
        bare = through_windows(900, elevation, azimuth, [(DOOR, 180, False)])
        under = through_windows(900, elevation, azimuth, [(DOOR, 180, SALON)])
        self.assertLess(under, bare / 2)

    def test_ticked_only_takes_the_ordinary_overhang(self):
        elevation, azimuth = self.at(2026, 11, 5, 12, 50)
        self.assertEqual(through_windows(450, elevation, azimuth, [(DOOR, 180, True)]),
                         through_windows(450, elevation, azimuth, [(DOOR, 180, Overhang())]))

    def test_a_deeper_overhang_shades_more(self):
        elevation, azimuth = self.at(2026, 11, 5, 12, 50)
        self.assertLess(lit_share(Overhang(2.0, 0.0, 2.1), 180, elevation, azimuth),
                        lit_share(Overhang(0.5, 0.3, 2.1), 180, elevation, azimuth))


if __name__ == "__main__":
    unittest.main()
