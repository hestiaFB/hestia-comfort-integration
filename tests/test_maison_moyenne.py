"""« 1,8 °C sous la moyenne de la maison » (Frank, 12 November): the template chauffage said it of Antoine's room, the
stove burning; the room's card said nothing."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.hestia_comfort.advisor.household import Habits  # noqa: E402
from custom_components.hestia_comfort.advisor.knowing import RoomView, below_house  # noqa: E402
from custom_components.hestia_comfort.advisor.words import tip_text  # noqa: E402

PARIS = timezone(timedelta(hours=1))


def view(air, house, asleep=False):
    return RoomView(datetime(2026, 11, 12, 9, 0, tzinfo=PARIS), 43.45, 5.47, air=air, house=house, asleep=asleep)


class BelowHouseTests(unittest.TestCase):
    def test_a_room_the_stove_warms_little_says_why(self):
        tips = below_house(view(19.4, (21.2, 0.09)))
        self.assertEqual(tip_text(tips[0]), "1,8 °C sous la moyenne de la maison (21,2 °C) : le poêle chauffe peu cette pièce")

    def test_otherwise_the_template_questions(self):
        tips = below_house(view(19.4, (21.2, 0.3)))
        self.assertIn("porte fermée, radiateur dégagé, sonde bien placée ?", tip_text(tips[0]))
        self.assertEqual(below_house(view(19.4, (21.2, None)))[0].kind, "below_house")

    def test_nothing_under_the_threshold_without_the_stove_or_at_night(self):
        self.assertEqual(below_house(view(20.0, (21.2, 0.09))), [])
        self.assertEqual(below_house(view(19.4, None)), [])
        self.assertEqual(below_house(view(19.4, (21.2, 0.09), asleep=True)), [])

    def test_the_threshold_is_a_household_setting(self):
        self.assertEqual(Habits().house_gap, 1.5)
        self.assertEqual(Habits.KEYS["ecart_maison"], "house_gap")


if __name__ == "__main__":
    unittest.main()
