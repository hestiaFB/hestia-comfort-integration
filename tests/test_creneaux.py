"""The advice by slots (moteur 3.18.0, docs/ETAT-DES-LIEUX-MOTEUR.md § 4-6): the card changes on an event,
never because a timer ran out.

Ten days of the house (6 to 16 November): 43 advices came and went within the hour with no window touched; 39 airings
of 47 taken back unfollowed, most of them half an hour after they were shown (HOLD_MINUTES), to come back five minutes
later. Chambre A, 16 November: « Aérez 15 min » 7 h 03, « Rien à faire — À essayer » 7 h 33, « Aérez 20 min » 7 h 38,
« À essayer » 8 h 13, « Aérez 25 min » 8 h 38, « Rien à faire » 9 h 43.
"""
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort"))
from advisor.board import (ASIDE, ENTER_STEPS, PATIENCE, Board, choose, thresholds,  # noqa: E402
                           urgent_decision)
from advisor.decide import Decision, Gesture, Path as Scenario  # noqa: E402
from advisor.household import Habits, Sleep  # noqa: E402
from advisor.house import Opening, Room  # noqa: E402
from advisor.identity import chronic, heat_card, normal_of, normals, opening_habits  # noqa: E402
from advisor.nightly import RoomSpec  # noqa: E402
from advisor.physics.thermal import ordinary  # noqa: E402
from advisor.slots import PLAN_EVERY, following, moments, plan_pool, slot_at  # noqa: E402
from advisor.words import aside_urgent, before_after, dwelling_lines, next_moment, normal_humidity, phrase  # noqa: E402

PARIS = ZoneInfo("Europe/Paris")
HABITS = Habits(sleep=Sleep(start=time(22, 0), end=time(7, 0)))


def at(hour, minute=0, day=16):
    return datetime(2026, 11, day, hour, minute, tzinfo=PARIS)


class SlotTests(unittest.TestCase):
    def test_the_four_slots_of_a_day(self):
        self.assertEqual(slot_at(at(7, 30), HABITS).name, "matin")
        self.assertEqual(slot_at(at(12, 0), HABITS).name, "apres_midi")
        self.assertEqual(slot_at(at(17, 59), HABITS).name, "apres_midi")
        self.assertEqual(slot_at(at(18, 0), HABITS).name, "soir")
        self.assertEqual(slot_at(at(23, 0), HABITS).name, "nuit")
        self.assertEqual(slot_at(at(6, 0), HABITS).name, "nuit")

    def test_a_slot_keeps_its_key_at_every_step(self):
        keys = {slot_at(at(12) + timedelta(minutes=5 * k), HABITS).key for k in range(72)}
        self.assertEqual(keys, {"2026-11-16/apres_midi"})
        # The night belongs to the evening it began.
        self.assertEqual(slot_at(at(2, 0, day=17), HABITS).key, "2026-11-16/nuit")

    def test_the_plan_weighs_moments_of_the_slot_every_half_hour(self):
        from advisor.decide import Comfort, Now, Twins
        room = Room("a", "Chambre A", volume=30.0, openings=(Opening("w", "window", area=1.2, height=1.2),), heating_power=0)
        twins = Twins(heat=ordinary(room), windows=((1.2, 1.2),))
        now, comfort = Now(air=19.0, walls=18.5, opened=()), Comfort(minimum=19.0, maximum=24.0)
        # At 9 °C outside, no airing longer than the household's usual 30 min (rejeu of 16 November at 7 h 02).
        cold = plan_pool(now, twins, HABITS, comfort, 180, outdoor=9.0)
        self.assertNotIn(Gesture("open", 45), cold)
        pool = plan_pool(now, twins, HABITS, comfort, 180, outdoor=14.0)
        laters = sorted({g.after for g in pool if g.kind == "open" and g.after})
        self.assertEqual(laters[0], PLAN_EVERY)
        self.assertTrue(all(a % PLAN_EVERY == 0 for a in laters))
        # No airing ends after the slot.
        self.assertTrue(all((g.after or 0) + g.minutes <= 180 for g in pool if g.kind == "open"))
        self.assertIn(Gesture("open", 60), pool)


class UrgentTests(unittest.TestCase):
    def steps(self, board, values, subject="co2", normal=None, drier=3.0, opened=False, start=None):
        start = start or at(14)
        out = []
        for k, v in enumerate(values):
            found = board.urgent_now({subject: v}, normal, drier, opened, start + timedelta(minutes=5 * k))
            out.append(found[0] if found else None)
        return out

    def test_a_measure_hovering_at_its_threshold_does_not_blink(self):
        shown = self.steps(Board(), [1380, 1420, 1390, 1420, 1430, 1390, 1300, 1150, 1120, 1050, 1150, 1390])
        changes = sum(1 for a, b in zip(shown, shown[1:]) if a != b)
        # Shown at the second step in a row above 1 400 ppm, kept down to 1 100, gone under it: two changes.
        self.assertEqual(changes, 2)
        self.assertEqual(shown[4], "co2")
        self.assertIsNone(shown[-1])

    def test_one_measure_alone_shows_nothing(self):
        self.assertEqual(self.steps(Board(), [1500, 1300, 1500, 1300]), [None] * 4)
        self.assertEqual(ENTER_STEPS, 2)

    def test_left_unfollowed_it_waits_aside_then_comes_back_only_if_worse(self):
        board = Board()
        n = PATIENCE // 5 + 3
        shown = self.steps(board, [1500] * n)
        self.assertEqual(shown[2], "co2")
        self.assertIsNone(shown[-1])
        self.assertIn("co2", board.aside(at(14) + timedelta(minutes=5 * n)))
        # Still 1 500 ppm an hour on: aside.
        later = at(14) + timedelta(minutes=5 * n + 60)
        self.assertIsNone(board.urgent_now({"co2": 1500}, None, None, False, later))
        self.assertIsNone(board.urgent_now({"co2": 1500}, None, None, False, later + timedelta(minutes=5)))
        # 300 ppm worse: back.
        board.urgent_now({"co2": 1850}, None, None, False, later + timedelta(minutes=10))
        self.assertEqual(board.urgent_now({"co2": 1850}, None, None, False, later + timedelta(minutes=15)), ("co2", 1850))
        self.assertEqual(ASIDE, 120)

    def test_followed_its_patience_starts_again(self):
        board = Board()
        self.steps(board, [1500, 1500])
        n = PATIENCE // 5 + 2
        shown = self.steps(board, [1500] * n, opened=True, start=at(14, 10))
        self.assertTrue(all(s == "co2" for s in shown))

    def test_the_humidity_on_the_room_own_normal(self):
        # The Chambre P lives at 77 %: never urgent at 80 %, urgent at 86 % when the outside is drier.
        self.assertEqual(thresholds("humidity", 77.0), (85.0, 80.0))
        self.assertEqual(self.steps(Board(), [80, 81, 82], "humidity", 77.0), [None] * 3)
        self.assertEqual(self.steps(Board(), [86, 86, 86], "humidity", 77.0)[1], "humidity")
        # The outside as humid: an airing does not dry the room.
        self.assertEqual(self.steps(Board(), [86, 86, 86], "humidity", 77.0, drier=0.5), [None] * 3)
        # A dry room is not urgent at 60 %: never under 70 %.
        self.assertEqual(thresholds("humidity", 50.0)[0], 70.0)
        # The normal not known yet: no urgency on the humidity.
        self.assertIsNone(thresholds("humidity", None))

    def test_the_gesture_an_urgency_asks(self):
        nothing, five, ten, fifteen, later = (Gesture("nothing"), Gesture("open", 5), Gesture("open", 10),
                                              Gesture("open", 15), Gesture("open", 10, after=30))
        scenarios = {nothing: {"co2": 5.0, "total": 6.0}, five: {"co2": 3.0, "total": 4.5},
                     ten: {"co2": 1.0, "total": 3.0}, fifteen: {"co2": 0.9, "total": 3.2}, later: {"co2": 0.5, "total": 2.0}}
        asked = urgent_decision(Decision(nothing, 0.0, "nothing", scenarios), "co2", 1450.0, None)
        self.assertEqual((asked.gesture, asked.rule, asked.measured), (ten, "urgent", {"co2": 1450.0}))
        # Nothing lowers it: no urgency said.
        flat = {nothing: {"co2": 5.0, "total": 6.0}, ten: {"co2": 5.0, "total": 7.0}}
        self.assertIsNone(urgent_decision(Decision(nothing, 0.0, "nothing", flat), "co2", 1450.0, None))


class PlanTests(unittest.TestCase):
    def test_a_slot_gesture_stays_until_its_moment_is_past_and_never_comes_back(self):
        board = Board()
        board.set_plan("2026-11-16/matin", at(7, 5), at(12), Gesture("open", 30, after=115),
                       {"title": "Aérez 30 min vers 9 h", "title_now": "Aérez 30 min", "line": "65 % à 11 h au lieu de 70 %"},
                       False)
        titles = []
        for k in range(60):
            now = at(7, 5) + timedelta(minutes=5 * k)
            plan = board.plan_shown(now)
            titles.append(None if plan is None else (plan.words["title"] if plan.left(now).after else plan.words["title_now"]))
        changes = [i for i, (a, b) in enumerate(zip(titles, titles[1:])) if a != b]
        # « vers 9 h » until 9 h, then « Aérez 30 min » until the slot ends at noon (bilan of 17 November: gone at 7 h 49,
        # before anyone was up), then nothing: two changes in five hours.
        self.assertEqual(len(changes), 2)
        self.assertEqual(titles[0], "Aérez 30 min vers 9 h")
        self.assertEqual(titles[-2], "Aérez 30 min")
        self.assertIsNone(titles[-1])
        self.assertEqual(board.plan.until, at(12))
        # Missed, it joins the day as « pas fait ».
        board.close_missed(at(12))
        self.assertEqual([x["genre"] for x in board.today], ["rate"])
        self.assertFalse(board.needs_plan("2026-11-16/matin"))
        self.assertTrue(board.needs_plan("2026-11-16/apres_midi"))

    def test_followed_it_is_done(self):
        board = Board()
        board.set_plan("2026-11-16/apres_midi", at(12), at(18), Gesture("open", 45, after=150), {"title": "x"}, False)
        board.followed()
        self.assertIsNone(board.plan_shown(at(14)))

    def test_kept_across_a_restart(self):
        board = Board()
        board.set_plan("2026-11-16/apres_midi", at(12), at(18), Gesture("open", 45, after=150), {"title": "x"}, True)
        board.urgent_now({"co2": 1500}, None, None, False, at(12))
        board.calm = "humidity"
        again = Board()
        again.load(board.state())
        self.assertEqual((again.plan.gesture, again.plan.trial, again.plan.until), (Gesture("open", 45, after=150), True, at(18)))
        self.assertEqual(again.urgent["co2"].above, 1)
        self.assertEqual(again.calm, "humidity")


class ChooseTests(unittest.TestCase):
    def test_the_families_in_order(self):
        nothing = Decision(Gesture("nothing"), 0.0, "nothing", {})
        close = Decision(Gesture("close"), 1.0, "best", {})
        board = Board()
        board.set_plan("k", at(12), at(18), Gesture("open", 30), {"title": "Aérez 30 min"}, False)
        plan = board.plan_shown(at(12))
        asked = Decision(Gesture("open", 10), 1.0, "urgent", {}, measured={"co2": 1500})
        self.assertEqual(choose(Decision(Gesture("close"), 0.0, "safety", {}), True, asked, plan, set(), 20, 19), "securite")
        self.assertEqual(choose(nothing, True, asked, plan, set(), 20, 19), "reponse")
        self.assertEqual(choose(close, True, None, plan, set(), 18.2, 19), "urgence")
        self.assertEqual(choose(nothing, False, asked, plan, set(), 20, 19), "urgence")
        self.assertEqual(choose(nothing, False, None, plan, set(), 20, 19), "creneau")
        self.assertEqual(choose(nothing, False, None, plan, {"open"}, 20, 19), "calme")
        self.assertEqual(choose(nothing, False, None, None, set(), 20, 19), "calme")


class CalmSubjectTests(unittest.TestCase):
    def decision(self, air, humidity):
        idle = Scenario(air=[air] * 3, humidity=[humidity] * 3)
        return Decision(Gesture("nothing"), 0.0, "nothing", {Gesture("nothing"): {"total": 1.0}}, {Gesture("nothing"): idle})

    def test_the_subject_said_stays_while_it_is_true(self):
        marks = {"minimum": 19.0, "maximum": 24.0, "humidity": 60.0}
        # 18,9 °C (near its minimum) and 72 %: the heat said first by itself, the humidity kept once said.
        first = phrase(self.decision(18.9, 72.0), 23, marks=marks)
        self.assertEqual(first["calm"], "heat")
        held = phrase(self.decision(18.9, 72.0), 23, marks=marks, calm_subject="humidity")
        self.assertEqual(held["calm"], "humidity")
        self.assertTrue(held["line"].startswith("Humidité 72 %"))
        # The humidity back under its mark: the subject changes.
        gone = phrase(self.decision(18.9, 55.0), 23, marks=marks, calm_subject="humidity")
        self.assertEqual(gone["calm"], "heat")


def history_of(entity, values, start, every=timedelta(hours=1)):
    return {entity: [{"state": str(v), "last_changed": (start + k * every).isoformat()} for k, v in enumerate(values)]}


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 16, 20, 0, tzinfo=timezone.utc)
        self.start = self.now - timedelta(days=14)
        self.spec = RoomSpec("Chambre P", "sensor.t", {"binary_sensor.w": (1.0, 1.2)}, humidity="sensor.h", habits=HABITS)

    def test_the_normal_slot_by_slot_and_what_is_chronic(self):
        hours = 14 * 24
        history = {**history_of("sensor.t", [19.0 + (k % 24) / 24 for k in range(hours)], self.start),
                   **history_of("sensor.h", [77.0 + (2 if 7 <= (self.start + timedelta(hours=k)).astimezone(PARIS).hour < 12
                                                      else 0) for k in range(hours)], self.start)}
        normal = normals(history, self.spec, self.now, PARIS, HABITS)
        self.assertEqual(normal["jour"]["humidite"][1], 77.0)
        self.assertEqual(normal_of({"normale": normal}, "humidite", "matin"), 79.0)
        self.assertEqual(chronic(normal), [{"sujet": "humidite", "mediane": 77.0, "bas": 77.0}])
        self.assertEqual(dwelling_lines({"chronique": chronic(normal)})[0][:30], "Humide en permanence : 77 % d'")
        self.assertIsNone(normal_of(None, "humidite"))

    def test_the_household_habits_from_the_windows(self):
        states = []
        for day in range(28):
            opened = datetime(2026, 10, 20, 14, 0, tzinfo=timezone.utc) + timedelta(days=day)
            if day % 2 == 0:
                states += [{"state": "on", "last_changed": opened.isoformat()},
                           {"state": "off", "last_changed": (opened + timedelta(minutes=60)).isoformat()}]
            # Someone going through, twenty seconds: not an airing.
            states += [{"state": "on", "last_changed": (opened + timedelta(hours=4)).isoformat()},
                       {"state": "off", "last_changed": (opened + timedelta(hours=4, seconds=20)).isoformat()}]
        habits = opening_habits({"binary_sensor.w": states}, self.spec, self.now, PARIS, HABITS)
        self.assertEqual(set(habits), {"apres_midi"})
        self.assertEqual(habits["apres_midi"]["duree_min"], 60)
        self.assertAlmostEqual(habits["apres_midi"]["par_semaine"], 3.5, delta=0.6)

    def test_the_heat_in_plain_figures(self):
        room = Room("p", "Chambre P", volume=51.0, openings=(Opening("w", "window", area=1.2, height=1.2),), heating_power=1000)
        card = heat_card(ordinary(room), [(1.0, 1.2)])
        self.assertGreater(card["perte_h"], 0)
        self.assertGreater(card["inertie_h"], 1)
        self.assertGreater(card["chauffage_h"], 0)
        self.assertGreater(card["aeration_20"], 0)
        self.assertLess(card["aeration_20_1h"], card["aeration_20"])


if __name__ == "__main__":
    unittest.main()


class HalfHourTests(unittest.TestCase):
    def test_the_moments_fall_on_the_half_hours(self):
        # 10 h 53 (23 minutes past the half hour): the afternoon from noon, every half hour: 12 h, 12 h 30…, never 12 h 20.
        found = moments(67, 427, 30, offset=23)
        self.assertEqual(found[:2], [67, 97])
        self.assertTrue(all((a + 23) % PLAN_EVERY == 0 for a in found))
        # Within the slot at 12 h 04: 12 h 30, 13 h…
        self.assertEqual(moments(0, 360, 30, offset=4)[0], 26)
        # On the half hour itself: the next one, not now.
        self.assertEqual(moments(0, 360, 30, offset=0)[0], 30)


class DayTests(unittest.TestCase):
    def test_an_airing_done_says_what_it_did(self):
        board = Board()
        board.new_day("2026-11-17")
        board.start_airing(at(9, 5), {"humidity": 68.0}, "humidity")
        board.end_airing(at(9, 20), {"humidity": 61.0})
        item = board.today[0]
        self.assertEqual((item["genre"], item["minutes"]), ("fait", 15))
        self.assertEqual(before_after("humidity", item["before"], item["after"]), "68 % → 61 %")
        # Someone going through: not an airing.
        board.start_airing(at(10), {"humidity": 61.0}, "humidity")
        board.end_airing(at(10, 1), {"humidity": 61.0})
        self.assertEqual(len(board.today), 1)
        # A new day starts afresh.
        board.new_day("2026-11-18")
        self.assertEqual(board.today, [])

    def test_the_later_slots_of_the_day(self):
        self.assertEqual([s.name for s in following(at(9), HABITS)], ["apres_midi", "soir"])
        self.assertEqual([s.name for s in following(at(15), HABITS)], ["soir"])
        self.assertEqual(following(at(19), HABITS), [])
        self.assertEqual(following(at(23), HABITS), [])

    def test_the_words_of_the_day(self):
        # Frank, 17 November: « « Aérez 10 min » en pause jusqu'à 10 h 45 », « on ne sait pas comment interpréter ».
        self.assertEqual(aside_urgent("voc", 387, "open", 5), "COV encore élevé (387) : aérer 5 min aiderait, quand vous pourrez")
        self.assertEqual(aside_urgent("co2", 1450, "open", 10),
                         "CO₂ encore élevé (1\u202f450 ppm) : aérer 10 min aiderait, quand vous pourrez")
        self.assertEqual(next_moment("apres_midi", at(15, 2), "open", 30), "Prochain bon moment : cet après-midi vers 15 h, aérer 30 min")
        self.assertEqual(normal_humidity(77.4), "Humidité 77 % : normal pour cette pièce")
        self.assertNotIn("aucun geste", phrase(CalmSubjectTests().decision(18.9, 72.0), 23,
                                                 marks={"minimum": 19.0, "maximum": 24.0, "humidity": 60.0})["line"])


class NoShadowTests(unittest.TestCase):
    def test_the_room_step_never_hides_a_name_it_imports(self):
        # 16 November at the lab: a plan's `within` hid advisor/physics/water.py `within` in `_advise`, which then failed
        # in every room (UnboundLocalError).
        import ast
        source = (Path(__file__).resolve().parents[1] / "custom_components" / "hestia_comfort" / "room" / "advice.py")
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imported = {(a.asname or a.name) for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
        step = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "_advise")
        assigned = {n.id for n in ast.walk(step) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
        self.assertEqual(assigned & imported, set())
