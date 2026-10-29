"""⏹ The party stop rule: after this title, after N titles, at a time.

Run:  py -m unittest tests.planner.playing.test_party_stop -v
"""
import unittest
from datetime import datetime

from planner.playing.party_stop import PartyStop

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
