#!/usr/bin/env python3
"""A reply that is no JSON list falls back to lines, and says so in the log.

Run:  py -m unittest tests.planner.test_ai_parse_fallback_logged -v
"""

import unittest

from planner.generate.ai import parse_ai_suggestions


class ParseFallbackLoggedTest(unittest.TestCase):

    def test_a_plain_text_reply_is_read_line_by_line_and_logged(self):
        with self.assertLogs("dancesport.ai", level="DEBUG") as logs:
            got = parse_ai_suggestions("1. ABBA - Dancing Queen\n2. Toto - Africa")
        self.assertEqual(got, [{'artist': 'ABBA', 'title': 'Dancing Queen'},
                               {'artist': 'Toto', 'title': 'Africa'}])
        self.assertIn("no JSON list", logs.output[0])

    def test_a_json_reply_logs_nothing(self):
        with self.assertNoLogs("dancesport.ai", level="DEBUG"):
            got = parse_ai_suggestions('[{"artist": "ABBA", "title": "SOS"}]')
        self.assertEqual(got, [{'artist': 'ABBA', 'title': 'SOS'}])


class ParseEdgeTest(unittest.TestCase):
    """L7: the line fallback ate a name's leading digits, and the JSON list
    was cut from the first '[' to the LAST ']' of the whole reply."""

    def test_a_name_starting_with_digits_keeps_them(self):
        got = parse_ai_suggestions("1. 10cc - Dreadlock Holiday\n"
                                   "- 2Raumwohnung - Wir trafen uns\n"
                                   "99 Luftballons")
        self.assertEqual(got, [
            {'artist': '10cc', 'title': 'Dreadlock Holiday'},
            {'artist': '2Raumwohnung', 'title': 'Wir trafen uns'},
            {'artist': '', 'title': '99 Luftballons'}])

    def test_a_bracket_after_the_list_does_not_break_it(self):
        got = parse_ai_suggestions(
            'Here you go: [{"artist": "ABBA", "title": "SOS"}]\n'
            'Note: tempos are approximate [source: memory].')
        self.assertEqual(got, [{'artist': 'ABBA', 'title': 'SOS'}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
