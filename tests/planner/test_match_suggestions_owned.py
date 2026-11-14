"""Review 6.B: "do I own it" for an AI suggestion counted any containment of
the normalised strings as a 0.9 match, inside words and for two-letter titles,
and never looked at the artist.

Run:  .venv/Scripts/python.exe -m unittest tests.planner.test_match_suggestions_owned -v
"""
import unittest
from types import SimpleNamespace

from planner.generate.ai import match_suggestions_to_library


def _lib(*pairs):
    return SimpleNamespace(entries=[SimpleNamespace(title=t, tag_artist=a)
                                    for t, a in pairs])


def _match(lib, title, artist=""):
    return match_suggestions_to_library(lib, [{"title": title, "artist": artist}])[0]


class OwnedTitleMatchTest(unittest.TestCase):

    def test_a_two_letter_library_title_owns_no_longer_wish(self):
        got = _match(_lib(("Si", "Zaz")), "Besame Mucho Si Quieres")
        self.assertIsNone(got["entry"])
        self.assertLess(got["ratio"], 0.9)

    def test_letters_inside_a_word_are_no_containment(self):
        got = _match(_lib(("Go", "Moby")), "Tango Argentino")
        self.assertIsNone(got["entry"])

    def test_a_whole_word_part_still_counts(self):
        lib = _lib(("Hello (Radio Edit)", "Adele"))
        got = _match(lib, "Hello", "Adele")
        self.assertIs(got["entry"], lib.entries[0])
        self.assertGreaterEqual(got["ratio"], 0.9)

    def test_the_same_title_by_another_artist_scores_lower(self):
        got = _match(_lib(("Hello", "Adele")), "Hello", "Lionel Richie")
        self.assertLess(got["ratio"], 1.0)

    def test_the_artist_breaks_a_tie_between_two_same_titles(self):
        lib = _lib(("Hello", "Adele"), ("Hello", "Lionel Richie"))
        got = _match(lib, "Hello", "Lionel Richie")
        self.assertIs(got["entry"], lib.entries[1])
        self.assertEqual(got["ratio"], 1.0)

    def test_an_unknown_artist_costs_nothing(self):
        lib = _lib(("Hello", None))
        self.assertEqual(_match(lib, "Hello", "Adele")["ratio"], 1.0)
        self.assertEqual(_match(_lib(("Hello", "Adele")), "Hello")["ratio"], 1.0)

    def test_no_overlap_is_no_match(self):
        got = _match(_lib(("Moon River", "Mancini")), "Cha Cha Royale")
        self.assertIsNone(got["entry"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
