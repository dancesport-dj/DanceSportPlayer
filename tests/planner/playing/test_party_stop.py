"""⏹ The party stop rule: after this title, after N titles, at a time.

Run:  py -m unittest tests.planner.playing.test_party_stop -v
"""
import unittest
from datetime import datetime, timedelta

from planner.playing.party_stop import PartyStop, parse_stop_time, stop_time_choices

EVENING = datetime(2026, 10, 24, 22, 10)


class CountTest(unittest.TestCase):

    def test_unarmed_never_stops(self):
        stop = PartyStop()
        self.assertFalse(stop.title_ended(EVENING))
        self.assertEqual(stop.text(), "")

    def test_after_this_title_stops_at_the_first_end(self):
        stop = PartyStop()
        stop.arm_count(1)
        self.assertTrue(stop.due(EVENING))
        self.assertTrue(stop.title_ended(EVENING))
        self.assertIsNone(stop.kind)

    def test_three_titles_stop_at_the_third_end(self):
        stop = PartyStop()
        stop.arm_count(3)
        self.assertEqual(stop.text(), "⏹  Stops after 3 titles")
        self.assertFalse(stop.title_ended(EVENING))
        self.assertFalse(stop.title_ended(EVENING))
        self.assertEqual(stop.text(), "⏹  Stops after this title")
        self.assertTrue(stop.title_ended(EVENING))
        self.assertFalse(stop.title_ended(EVENING))

    def test_a_crossfaded_end_counts_but_cannot_stop(self):
        stop = PartyStop()
        stop.arm_count(1)
        self.assertFalse(stop.title_ended(EVENING, can_stop=False))
        self.assertEqual(stop.left, 1)
        self.assertTrue(stop.title_ended(EVENING))


class StopTimeChoicesTest(unittest.TestCase):
    """⏹ The "At …" list offers what is still to come tonight."""

    @staticmethod
    def hhmm(choices):
        return [at.strftime("%H:%M") for at in choices]

    def test_at_23_20_it_reaches_into_the_night(self):
        got = self.hhmm(stop_time_choices(datetime(2026, 10, 24, 23, 20)))
        self.assertEqual(got[:2], ["23:25", "23:30"])
        self.assertIn("00:00", got)
        self.assertIn("00:30", got)
        self.assertEqual(got[-1], "01:55")

    def test_in_the_afternoon_only_what_is_still_to_come(self):
        got = self.hhmm(stop_time_choices(datetime(2026, 10, 24, 14, 3)))
        self.assertEqual(got[0], "14:05")
        self.assertIn("23:00", got)
        self.assertEqual(got[-1], "01:55")
        self.assertNotIn("14:00", got)
        self.assertNotIn("09:00", got, "not tomorrow morning")

    def test_a_time_on_the_dot_is_not_offered_any_more(self):
        got = self.hhmm(stop_time_choices(datetime(2026, 10, 24, 14, 0)))
        self.assertEqual(got[0], "14:05")

    def test_the_seconds_count(self):
        got = self.hhmm(stop_time_choices(datetime(2026, 10, 24, 14, 4, 59)))
        self.assertEqual(got[0], "14:05")

    def test_a_party_past_midnight_can_still_set_one(self):
        got = self.hhmm(stop_time_choices(datetime(2026, 10, 25, 1, 40)))
        self.assertEqual(got[0], "01:45")
        self.assertEqual(got[-1], "03:45")

    def test_every_minute_of_the_day_has_a_list_that_holds(self):
        """Never empty, always ahead of the clock, no time twice, and each one
        lands on the moment it was offered as."""
        start = datetime(2026, 10, 24)
        for minute in range(24 * 60):
            now = start + timedelta(minutes=minute, seconds=30)
            choices = stop_time_choices(now)
            self.assertTrue(choices, now)
            self.assertGreater(choices[0], now)
            self.assertEqual(len(set(self.hhmm(choices))), len(choices), now)
            stop = PartyStop()
            for at in (choices[0], choices[-1]):
                stop.arm_time(at.hour, at.minute, now)
                self.assertEqual(stop.at, at, now)


class TimeTest(unittest.TestCase):

    def test_the_first_end_at_or_after_the_time_stops(self):
        stop = PartyStop()
        stop.arm_time(23, 0, EVENING)
        self.assertEqual(stop.text(), "⏹  Stops at 23:00")
        self.assertFalse(stop.title_ended(EVENING.replace(hour=22, minute=59)))
        self.assertTrue(stop.title_ended(EVENING.replace(hour=23, minute=2)))
        self.assertIsNone(stop.kind)

    def test_a_time_already_past_means_after_midnight(self):
        stop = PartyStop()
        stop.arm_time(1, 30, EVENING)
        self.assertEqual(stop.at, datetime(2026, 10, 25, 1, 30))
        self.assertFalse(stop.due(EVENING.replace(hour=23, minute=59)))
        self.assertTrue(stop.due(datetime(2026, 10, 25, 1, 31)))

    def test_a_crossfade_through_the_time_stops_at_the_next_end(self):
        stop = PartyStop()
        stop.arm_time(23, 0, EVENING)
        late = EVENING.replace(hour=23, minute=1)
        self.assertFalse(stop.title_ended(late, can_stop=False))
        self.assertTrue(stop.title_ended(late.replace(minute=4)))


class FadeAtTimeTest(unittest.TestCase):
    """The "At …" stop's mode: play to the end, fade at the time, or fade
    only a title that had played 1:30 when the time came."""

    def armed(self) -> PartyStop:
        stop = PartyStop()
        stop.arm_time(23, 0, EVENING)
        return stop

    def at(self, seconds: int) -> datetime:
        return datetime(2026, 10, 24, 23, 0, seconds)

    def test_play_to_the_end_never_fades(self):
        stop = self.armed()
        self.assertFalse(stop.fade_due(self.at(5), 200.0, "end"))

    def test_fade_mode_fades_once_the_time_is_reached(self):
        stop = self.armed()
        self.assertFalse(stop.fade_due(EVENING.replace(hour=22, minute=59),
                                       200.0, "fade"))
        self.assertTrue(stop.fade_due(self.at(0), 200.0, "fade"))

    def test_a_title_started_after_the_time_plays_out(self):
        stop = self.armed()
        self.assertFalse(stop.fade_due(self.at(30), 10.0, "fade"))

    def test_hybrid_fades_a_title_that_had_played_long_enough(self):
        stop = self.armed()
        self.assertTrue(stop.fade_due(self.at(1), 91.0, "hybrid"))

    def test_hybrid_lets_a_young_title_play_out(self):
        stop = self.armed()
        self.assertFalse(stop.fade_due(self.at(1), 60.0, "hybrid"))
        # still the same title, past 1:30 now — but it was young at the time
        self.assertFalse(stop.fade_due(self.at(40), 99.0, "hybrid"))

    def test_only_a_time_rule_fades(self):
        stop = PartyStop()
        stop.arm_count(1)
        self.assertFalse(stop.fade_due(self.at(5), 200.0, "fade"))
        self.assertFalse(PartyStop().fade_due(self.at(5), 200.0, "fade"))


if __name__ == "__main__":
    unittest.main()


class ParseStopTimeTest(unittest.TestCase):
    """The time typed into the "At …" field."""

    def test_the_usual_ways_to_write_a_time(self):
        for text, want in (("23:15", (23, 15)), ("9:05", (9, 5)), ("2315", (23, 15)),
                           ("930", (9, 30)), ("23.15", (23, 15)), ("23", (23, 0)),
                           (" 0:30 ", (0, 30)), ("00:00", (0, 0))):
            self.assertEqual(parse_stop_time(text), want, text)

    def test_what_is_no_time_is_refused(self):
        for text in ("", "abc", "24:00", "12:60", "1:2:3", "-1:00", "12:"):
            self.assertIsNone(parse_stop_time(text), text)

