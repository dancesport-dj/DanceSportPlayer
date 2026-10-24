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


if __name__ == "__main__":
    unittest.main()
