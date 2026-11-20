"""The morning of 20 November at the house (Confort 3.1.0b18, moteur 3.19.4): advice followed, then « Rien à faire ».

- Salon · Cuisine: « Aérez 5 min » for the kitchen's VOC (385) from 8 h 04. The west window, then the two French windows
  opened a few seconds each (8 h 38 to 8 h 39), the kitchen's from 8 h 40 to 8 h 56, the west one again from 8 h 41 to
  8 h 43. At 8 h 41 the card said « Rien à faire · Ouverte ou fermée : 18,3 °C à 11 h », the VOC at 268.
- Chambre A: the slot's « Aérez 20 min » (69 %) from 7 h 04, its promise sliding « vers 8 h 30 », 9 h, 9 h 15, 10 h. The
  window opened at 8 h 42: at 8 h 44 « Rien à faire · L'humidité repasse seule sous 60 % vers 8 h 55 ».
- Chambre M: the same « Aérez 20 min » (67 %), opened at 8 h 41: at 8 h 44 « Rien à faire · Humidité 63 % à 11 h ».
- The card took one to three minutes after a window moved; on a phone, its right side was cut.

What the card says now: « Aération en cours », what it is for and when to shut, until it is done or its reason sorted.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.hestia_comfort import advisor_home  # noqa: E402
from custom_components.hestia_comfort.advisor.board import OPEN_LEAST, RESUME, Board, Plan  # noqa: E402
from custom_components.hestia_comfort.advisor.decide import Decision, Gesture  # noqa: E402
from custom_components.hestia_comfort.advisor.words import airing_words, phrase  # noqa: E402
from custom_components.hestia_comfort.room.advice import airing_shown, first_windows  # noqa: E402

PARIS = timezone(timedelta(hours=1))
MARKS = {"minimum": 20.0, "maximum": 24.0, "humidity": 60.0, "co2": 1000.0, "particles": 15.0, "voc": 150.0}
NOTHING = Decision(Gesture("nothing"), 0.0, "nothing", {})


def at(hour, minute, second=0):
    """20 November, Paris time."""
    return datetime(2026, 11, 20, hour, minute, second, tzinfo=PARIS)


def local(when):
    return when.astimezone(PARIS)


class Room:
    """The steps of room/advice.py that open and shut the airing, as they run them: a window open less than OPEN_LEAST
    is someone going through, unless an airing is already under way; the reason is what was shown when it opened."""

    def __init__(self, reason=None, subject=None, minutes=None, longest=30):
        self.board, self.reason, self.subject, self.minutes, self.longest = Board(), reason, subject, minutes, longest
        self.opening = None

    def step(self, now, opened: bool, measures: dict, decision=NOTHING):
        if not opened:
            self.opening = None
            if self.board.airing is not None:
                self.board.end_airing(now, measures)
            return None
        if self.opening is None:
            self.opening = now
        young = now - self.opening < timedelta(seconds=OPEN_LEAST) and self.board.airing is None \
            and not self.board.resumable(now)
        if young:
            return None
        if self.board.airing is None:
            self.board.start_airing(self.opening, measures, self.subject, minutes=self.minutes, reason=self.reason)
        return airing_shown(self.board, decision, measures, None, MARKS, self.longest, now, local)


class SalonCuisineVOC(unittest.TestCase):
    """The kitchen's VOC urgency followed, with the bursts of openings of 8 h 38 to 8 h 41."""

    def morning(self):
        room = Room("urgence", "voc", 5)
        shown = {}
        # 8 h 38 min 44 s to 8 h 39 min 37 s: three windows opened a few seconds each, seen 10 s after each move.
        for t, opened in ((at(8, 38, 54), True), (at(8, 39, 5), True), (at(8, 39, 18), False), (at(8, 39, 30), True),
                          (at(8, 39, 37), False)):
            shown[t] = room.step(t, opened, {"voc": 270.0})
        # The kitchen's, from 8 h 40 min 03 s: seen at 8 h 40 min 13 s, an airing a minute later.
        shown[at(8, 40, 13)] = room.step(at(8, 40, 13), True, {"voc": 270.0})
        shown[at(8, 41, 18)] = room.step(at(8, 41, 18), True, {"voc": 268.0})
        shown[at(8, 41, 25)] = room.step(at(8, 41, 25), True, {"voc": 268.0})
        shown[at(8, 44, 56)] = room.step(at(8, 44, 56), True, {"voc": 69.0})
        return room, shown

    def test_the_passages_are_not_an_airing(self):
        room, shown = self.morning()
        self.assertIsNone(shown[at(8, 38, 54)])
        self.assertIsNone(shown[at(8, 39, 37)])
        self.assertIsNone(shown[at(8, 40, 13)])

    def test_the_airing_keeps_its_reason_and_its_countdown(self):
        _, shown = self.morning()
        gesture, rule, said, _ = shown[at(8, 41, 25)]
        self.assertEqual(said["title"], "Aération en cours")
        self.assertEqual(said["line"], "COV 268 · refermez vers 8 h 45")
        self.assertEqual((gesture.kind, rule), ("close", "en_cours"))
        self.assertEqual(gesture.after, 4)

    def test_never_nothing_to_do_while_open(self):
        _, shown = self.morning()
        for t in (at(8, 41, 18), at(8, 41, 25), at(8, 44, 56)):
            self.assertNotEqual(shown[t][0].kind, "nothing")

    def test_the_reason_sorted_says_close(self):
        _, shown = self.morning()
        gesture, rule, said, _ = shown[at(8, 44, 56)]
        self.assertEqual((gesture.kind, rule, said["title"]), ("close", "reglee", "Refermez"))
        self.assertEqual(said["line"], "COV 69 : c'est réglé")


class ChambresAirSlot(unittest.TestCase):
    """The slot's « Aérez 20 min » followed in Chambre A (8 h 42) and Chambre M (8 h 41)."""

    def test_chambre_a_says_when_to_shut(self):
        room = Room("creneau", "humidity", 20)
        room.step(at(8, 42, 12), True, {"humidity": 67.97})
        gesture, rule, said, _ = room.step(at(8, 44, 56), True, {"humidity": 67.93})
        self.assertEqual(said["line"], "Humidité 68 % · refermez vers 9 h 02")
        self.assertEqual((gesture.kind, rule), ("close", "en_cours"))
        # Not over because the humidity fell under 60 %: a slot's airing goes on to its end.
        gesture, rule, _, _ = room.step(at(8, 58, 0), True, {"humidity": 58.0})
        self.assertEqual(rule, "en_cours")

    def test_done_says_what_it_did(self):
        room = Room("creneau", "humidity", 20)
        room.step(at(8, 41, 57), True, {"humidity": 66.6})
        room.step(at(8, 43, 0), True, {"humidity": 66.6})
        gesture, rule, said, _ = room.step(at(9, 2, 0), True, {"humidity": 61.1})
        self.assertEqual((gesture.kind, rule, said["title"]), ("close", "finie", "Refermez"))
        self.assertEqual(said["line"], "Aérée 20 min : 67 % → 61 %")

    def test_left_open_after_the_end_still_says_close(self):
        room = Room("creneau", "humidity", 20)
        room.step(at(8, 41, 57), True, {"humidity": 66.6})
        room.step(at(8, 43, 0), True, {"humidity": 66.6})
        self.assertEqual(room.step(at(9, 30, 0), True, {"humidity": 62.0})[1], "finie")

    def test_the_engine_keeping_it_open_for_something_else_speaks(self):
        room = Room("creneau", "humidity", 20)
        room.step(at(18, 0, 0), True, {"humidity": 60.0})
        room.step(at(18, 1, 5), True, {"humidity": 60.0})
        keep = Decision(Gesture("close", after=30), 1.0, "best", {})
        self.assertIsNone(room.step(at(18, 25, 0), True, {"humidity": 55.0}, keep))
        # While it runs, the countdown stays: the household's airing is the one shown.
        self.assertEqual(room.step(at(18, 10, 0), True, {"humidity": 58.0}, keep)[1], "en_cours")


class EveryCase(unittest.TestCase):
    def test_opened_of_its_own_accord_is_the_engines(self):
        room = Room()
        room.step(at(10, 0), True, {"humidity": 70.0})
        self.assertIsNone(room.step(at(10, 2), True, {"humidity": 70.0}))

    def test_urgency_worse_at_the_end_goes_on_up_to_the_longest(self):
        room = Room("urgence", "co2", 10, longest=20)
        room.step(at(12, 0), True, {"co2": 1500.0})
        room.step(at(12, 1, 5), True, {"co2": 1500.0})
        self.assertEqual(room.step(at(12, 10, 0), True, {"co2": 1300.0})[1], "en_cours")
        self.assertEqual(room.step(at(12, 15, 0), True, {"co2": 1250.0})[1], "en_cours")
        self.assertEqual(room.step(at(12, 20, 0), True, {"co2": 1200.0})[1], "finie")
        self.assertEqual(room.board.airing["extra"], 10)

    def test_an_urgency_asked_without_a_length_says_leave_open(self):
        room = Room("urgence", "humidity", None)
        room.step(at(7, 0), True, {"humidity": 80.0})
        gesture, rule, said, _ = room.step(at(7, 1, 5), True, {"humidity": 80.0})
        self.assertEqual((gesture.kind, said["line"]), ("keep", "Humidité 80 % · laissez ouvert"))

    def test_shut_and_opened_again_soon_is_the_same_airing(self):
        room = Room("urgence", "voc", 5)
        room.step(at(8, 40, 13), True, {"voc": 300.0})
        room.step(at(8, 41, 18), True, {"voc": 290.0})
        room.step(at(8, 42, 0), False, {"voc": 280.0})
        # Opened again within RESUME minutes: the same airing at once, its countdown from 8 h 40.
        shown = room.step(at(8, 43, 0), True, {"voc": 270.0})
        self.assertEqual(shown[2]["line"], "COV 270 · refermez vers 8 h 45")
        self.assertEqual(room.board.today, [])

    def test_shut_longer_starts_again(self):
        room = Room("urgence", "voc", 5)
        room.step(at(8, 40, 13), True, {"voc": 300.0})
        room.step(at(8, 41, 18), True, {"voc": 290.0})
        room.step(at(8, 42, 0), False, {"voc": 280.0})
        later = at(8, 42) + timedelta(minutes=RESUME + 1)
        room.step(later, True, {"voc": 270.0})
        self.assertIsNone(room.step(later + timedelta(seconds=30), True, {"voc": 270.0}))

    def test_a_slot_shut_at_once_is_asked_again(self):
        board = Board()
        board.plan = Plan("matin", at(7, 4), at(10, 0), Gesture("open", 20), {"subject": "humidity"}, False, False)
        board.followed()
        board.start_airing(at(8, 42), {"humidity": 68.0}, "humidity", minutes=20, reason="creneau")
        board.end_airing(at(8, 43), {"humidity": 68.0})
        self.assertIs(board.plan_shown(at(8, 50)), board.plan)
        # Aired long enough: it was done.
        board.followed()
        board.start_airing(at(9, 0), {"humidity": 68.0}, "humidity", minutes=20, reason="creneau")
        board.end_airing(at(9, 15), {"humidity": 62.0})
        self.assertIsNone(board.plan_shown(at(9, 20)))

    def test_home_assistant_restarted_mid_airing(self):
        room = Room("creneau", "humidity", 20)
        room.step(at(8, 42, 12), True, {"humidity": 68.0})
        room.step(at(8, 44, 56), True, {"humidity": 67.9})
        kept = Board()
        kept.load(room.board.state())
        room.board, room.opening = kept, None
        # The first step after the restart sees the window « just opened »: the airing goes on, not someone going by.
        gesture, rule, said, _ = room.step(at(8, 50, 0), True, {"humidity": 64.0})
        self.assertEqual(said["line"], "Humidité 64 % · refermez vers 9 h 02")

    def test_two_rooms_a_minute_apart_keep_their_own(self):
        a, m = Room("creneau", "humidity", 20), Room("creneau", "humidity", 20)
        m.step(at(8, 41, 57), True, {"humidity": 66.6})
        a.step(at(8, 42, 12), True, {"humidity": 67.97})
        self.assertIn("9 h 01", m.step(at(8, 44, 56), True, {"humidity": 66.4})[2]["line"])
        self.assertIn("9 h 02", a.step(at(8, 44, 56), True, {"humidity": 67.93})[2]["line"])

    def test_the_rain_comes_first_then_the_countdown_goes_on(self):
        from custom_components.hestia_comfort.advisor.board import choose
        room = Room("creneau", "humidity", 20)
        room.step(at(8, 42, 12), True, {"humidity": 68.0})
        room.step(at(8, 44, 56), True, {"humidity": 67.9})
        rain = Decision(Gesture("close"), 0.0, "safety", {})
        self.assertEqual(choose(rain, True, None, None, set(), 18.5, 18.0), "securite")
        # The rain over, the window still open: the same countdown, not a new one.
        self.assertEqual(room.step(at(8, 55, 0), True, {"humidity": 63.0})[2]["line"], "Humidité 63 % · refermez vers 9 h 02")

    def test_a_summer_evening_airing_for_the_heat(self):
        room = Room("creneau", "heat", 45)
        room.step(at(21, 0), True, {"heat": 26.4})
        gesture, rule, said, _ = room.step(at(21, 1, 5), True, {"heat": 26.2})
        self.assertEqual(said["line"], "26,2 °C · refermez vers 21 h 45")

    def test_opened_at_night_with_the_heating_on_is_the_engines(self):
        # No urgency at night, no slot: a window opened then has no reason, the engine answers as before.
        room = Room()
        room.step(at(23, 30), True, {"humidity": 65.0, "heat": 19.0})
        self.assertIsNone(room.step(at(23, 35), True, {"humidity": 64.0, "heat": 18.6}))

    def test_the_words_in_english(self):
        said = airing_words({"state": "running", "end": at(9, 2), "minutes": 3}, "humidity", 68.0, 69.0, local(at(9, 2)), "en")
        self.assertNotIn("{", said["line"])


class NameTheWindow(unittest.TestCase):
    """« Aérez » opens the part where its measure is taken, one side of it; the draught comes second."""
    SALON_CUISINE = {
        "windows": {"ouest": (1.0, 1.2), "pf_d": (1.0, 2.1), "pf_g": (1.0, 2.1), "cuisine": (0.8, 1.0)},
        "orientations": {"ouest": (270.0, None), "pf_d": (180.0, None), "pf_g": (180.0, None), "cuisine": (90.0, None)},
        "parts": [{"name": "Salon", "windows": ["ouest", "pf_d", "pf_g"],
                   "sources": ["co2", "indoor_humidity", "indoor_temperature", "pm25"]},
                  {"name": "Cuisine", "windows": ["cuisine"], "sources": ["indoor_humidity", "indoor_temperature", "pm25", "voc"]}],
    }

    def test_the_kitchens_voc_opens_the_kitchen(self):
        self.assertEqual(first_windows(self.SALON_CUISINE, "voc"), (("cuisine",), "Cuisine"))

    def test_the_living_rooms_co2_opens_one_side_of_it(self):
        windows, side = first_windows(self.SALON_CUISINE, "co2")
        self.assertEqual((windows, side), (("pf_d", "pf_g"), "Salon"))

    def test_a_room_on_one_side_names_nothing(self):
        room = {"windows": {"a": (1.0, 1.2)}, "orientations": {"a": (180.0, None)}}
        self.assertEqual(first_windows(room, "humidity"), (("a",), None))

    def test_a_room_on_two_sides_names_the_side(self):
        room = {"windows": {"n": (0.6, 1.0), "s": (1.2, 1.4)}, "orientations": {"n": (0.0, None), "s": (180.0, None)}}
        self.assertEqual(first_windows(room, "humidity"), (("s",), "sud"))

    def test_the_draught_is_the_second_gesture(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from dataclasses import replace
        from advisor.decide import Gesture as G, Now, _open, candidates, one_side
        from test_advisor_decide import TWINS
        west, south = (1.18, 1.21), (1.18, 2.1)
        self.assertEqual(one_side((270.0, 180.0), (0, 1), (1.4, 2.5)), (1,))
        twins = replace(TWINS, windows=(west, south), bearings=(270.0, 180.0), first=(south,))
        shut = Now(air=21.0, walls=21.0, opened=())
        self.assertEqual(_open(G("open", 10), shut, twins, 0), (south,))
        opened = Now(air=21.0, walls=21.0, opened=(south,))
        self.assertTrue(any(g.kind == "open_more" and g.facing == "west" for g in candidates(opened, twins)))


class SlotPromiseFixed(unittest.TestCase):
    def decision(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
        from advisor.decide import Decision as D, Gesture as G, Path as P
        zero = dict.fromkeys(("heat", "co2", "particles", "voc", "energy", "mould"), 0.0)
        nothing, airing = G("nothing"), G("open", 20)
        return D(airing, 2.0, "creneau", {nothing: {**zero, "humidity": 3.0, "total": 3.0},
                                          airing: {**zero, "humidity": 1.0, "total": 1.0}},
                 {nothing: P(air=[19.0] * 30, humidity=[70.0] * 30), airing: P(air=[18.5] * 30, humidity=[55.0] * 30)})

    def test_said_without_an_hour_that_slides(self):
        from advisor.words import phrase as say
        line = say(self.decision(), 13, fixed=True)["line"]
        self.assertEqual(line, "55 % d'humidité une heure après l'aération au lieu de 70 %")
        # The same at 7 h 04 and at 8 h 34.
        self.assertEqual(line, say(self.decision(), 13, fixed=True, hour=8.5)["line"])


class WindowMoved(unittest.TestCase):
    """A window opened is advised again once it counts as an airing, not at the next five-minute step."""

    def test_advised_again_once_it_counts(self):
        home = advisor_home.AdvisorHome.__new__(advisor_home.AdvisorHome)
        home.hass, home.pending, home.aging = None, {}, {}
        advisor = SimpleNamespace(entry_id="a")
        event = SimpleNamespace(data={"old_state": SimpleNamespace(state="off"), "new_state": SimpleNamespace(state="on")})
        with mock.patch.object(advisor_home, "async_call_later", return_value=lambda: None) as later:
            home._window_moved(advisor, event)
        delays = sorted(call.args[1] for call in later.call_args_list)
        self.assertEqual(delays, [advisor_home.WINDOW_SETTLE, OPEN_LEAST + 5])

    def test_shutting_needs_no_second_look(self):
        home = advisor_home.AdvisorHome.__new__(advisor_home.AdvisorHome)
        home.hass, home.pending, home.aging = None, {}, {}
        event = SimpleNamespace(data={"old_state": SimpleNamespace(state="on"), "new_state": SimpleNamespace(state="off")})
        with mock.patch.object(advisor_home, "async_call_later", return_value=lambda: None) as later:
            home._window_moved(SimpleNamespace(entry_id="a"), event)
        self.assertEqual([c.args[1] for c in later.call_args_list], [advisor_home.WINDOW_SETTLE])


class NotAloneWhileOpen(unittest.TestCase):
    def test_back_under_its_mark_with_the_window_open(self):
        nothing, close = Gesture("nothing"), Gesture("close")
        zero = dict.fromkeys(("heat", "co2", "particles", "voc", "energy", "mould", "humidity"), 0.0)
        from custom_components.hestia_comfort.advisor.decide import Path as P
        idle = P(air=[18.8] * 30, humidity=[68.0, 66.0, 63.0, 59.0] + [56.0] * 26)
        decision = Decision(nothing, 0.0, "nothing", {nothing: {**zero, "total": 0.1}, close: {**zero, "total": 0.2}},
                            {nothing: idle, close: P(air=[18.8] * 30, humidity=[68.0] * 30)})
        line = phrase(decision, 11, marks={**MARKS, "minimum": 18.0}, hour=8.75)["line"]
        self.assertNotIn("seule", line)
        self.assertIn("fenêtre ouverte", line)


if __name__ == "__main__":
    unittest.main()
