"""² is a digit for str.isdigit() but not for int() (review item 42).

Typed text and stored settings reached int() after an isdigit() check, so a
"²" raised ValueError out of a text field or out of start-up.
"""
import unittest

from planner.event.competition import parse_competition_schedule
from planner.playing.play_sets import migrate_play_sets, parse_play_length
from player.presenter.timetable import Entry


class SuperscriptDigitTests(unittest.TestCase):
    def test_play_length_is_none(self):
        for text in ("²", "1:²", "²:30"):
            with self.subTest(text=text):
                self.assertIsNone(parse_play_length(text))

    def test_play_length_still_reads_ascii(self):
        self.assertEqual(parse_play_length("1:30"), 90)

    def test_timetable_length_ignores_it(self):
        self.assertIsNone(Entry(until="²").length())
        self.assertEqual(Entry(until="20 min").length(), 20)

    def test_competition_round_numbers_skip_the_line(self):
        parse_competition_schedule("Hobby Latein (CC; RB) 5-3-²")

    def test_a_garbled_settings_version_does_not_raise(self):
        for value in ("x", "²", [1]):
            with self.subTest(value=value):
                migrate_play_sets({"play_sets_version": value})


if __name__ == "__main__":
    unittest.main()
