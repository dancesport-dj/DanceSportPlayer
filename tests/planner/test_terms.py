#!/usr/bin/env python3
"""Dance and round names as the screen shows them.

Run:  py -m unittest tests.planner.test_terms -v

The data speaks German: DANCE_NAMES, the round names of a tournament and the
Standardrunde / Lateinrunde sections of a party list are what the .m3u files
carry and what the app reads back. An English screen showed them as they are,
"Langsamer Walzer" between "Artist" and "Title". In English they are now
translated on their way to the screen, unless ⚙ Settings asks for the German
words; a German screen keeps them as they are.
"""

import unittest

from planner import i18n, terms


class TermsTestBase(unittest.TestCase):

    def setUp(self):
        self.addCleanup(i18n.set_active, i18n.active_language())
        self.addCleanup(setattr, terms, "_english_terms", terms._english_terms)
        self.addCleanup(setattr, terms, "_german_kept", terms._german_kept)

    def english(self, german_terms=False):
        i18n.set_active("en")
        terms.apply_settings({"german_dance_terms": german_terms})

    def german(self):
        i18n.set_active("de")
        terms.apply_settings({})


class HallLanguageTest(TermsTestBase):
    """The language of what the hall sees and hears — the presenter screen
    and the announcements: the screen's own, unless the German dance terms
    were asked to stay."""

    def test_an_english_screen_shows_the_hall_english(self):
        self.english()
        self.assertEqual(terms.hall_language(), "en")

    def test_the_german_terms_switch_shows_the_hall_german(self):
        self.english(german_terms=True)
        self.assertEqual(terms.hall_language(), "de")

    def test_a_german_screen_shows_the_hall_german(self):
        self.german()
        self.assertEqual(terms.hall_language(), "de")


class DanceNameTest(TermsTestBase):

    def test_english_names_the_dances_in_english(self):
        self.english()
        self.assertEqual(terms.dance_name("LW"), "Slow Waltz")
        self.assertEqual(terms.dance_name("WW"), "Viennese Waltz")
        self.assertEqual(terms.dance_name("SF"), "Slowfox")
        self.assertEqual(terms.dance_name("CC"), "ChaCha")
        self.assertEqual(terms.dance_name("TANGOARG"), "Argentine Tango")
        self.assertEqual(terms.dance_name("JI"), "Jive")

    def test_the_setting_keeps_the_german_words(self):
        self.english(german_terms=True)
        self.assertEqual(terms.dance_name("LW"), "Langsamer Walzer")

    def test_nothing_is_translated_before_the_settings_are_applied(self):
        i18n.set_active("en")
        terms._english_terms = False
        self.assertEqual(terms.dance_name("LW"), "Langsamer Walzer")
        self.assertEqual(terms.round_name("Vorrunde"), "Vorrunde")

    def test_a_german_screen_keeps_them_whatever_the_setting(self):
        self.german()
        self.assertEqual(terms.dance_name("LW"), "Langsamer Walzer")
        self.assertEqual(terms.dance_name("WW"), "Wiener Walzer")

    def test_it_falls_back_like_dict_get(self):
        self.english()
        self.assertEqual(terms.dance_name("XX", "XX"), "XX")
        self.assertIsNone(terms.dance_name("XX"))
        self.assertIsNone(terms.dance_name(None))
        self.assertEqual(terms.dance_name("", "?"), "?")

    def test_every_dance_has_an_english_name(self):
        from planner.models import DANCE_NAMES
        self.english()
        for code in DANCE_NAMES:
            self.assertTrue(terms.dance_name(code), code)


class GenreNameTest(TermsTestBase):
    """The German genre labels of the non-competition tracks
    (planner.models.OTHER_GENRE_LABELS) are data like the dance names."""

    def test_english_names_the_german_genres_in_english(self):
        self.english()
        self.assertEqual(terms.genre_name("Einleitung"), "Intro")
        self.assertEqual(terms.genre_name("Einmarsch"), "Entrance")
        self.assertEqual(terms.genre_name("Marsch"), "March")
        self.assertEqual(terms.genre_name("Fanfare/Tusch"), "Fanfare")
        self.assertEqual(terms.genre_name("Weihnachten"), "Christmas")
        self.assertEqual(terms.genre_name("Sonstiges"), "Other")

    def test_a_dance_name_falls_back_to_the_translated_genre(self):
        self.english()
        self.assertEqual(terms.dance_name(None, "Einmarsch"), "Entrance")

    def test_the_setting_and_a_german_screen_keep_the_german_words(self):
        self.english(german_terms=True)
        self.assertEqual(terms.genre_name("Einmarsch"), "Einmarsch")
        self.german()
        self.assertEqual(terms.genre_name("Weihnachten"), "Weihnachten")

    def test_anything_else_passes_untouched(self):
        self.english()
        self.assertEqual(terms.genre_name("Schlager"), "Schlager")
        self.assertEqual(terms.genre_name("Discofox"), "Discofox")
        self.assertIsNone(terms.genre_name(None))
        self.assertEqual(terms.genre_name(""), "")


class RoundNameTest(TermsTestBase):

    def test_party_sections_are_translated(self):
        self.english()
        self.assertEqual(terms.round_name("Standardrunde 1"), "Standard round 1")
        self.assertEqual(terms.round_name("Lateinrunde 12"), "Latin round 12")
        self.assertEqual(terms.round_name("Socialrunde 2"), "Social round 2")
        self.assertEqual(terms.round_name("Lateinrunde"), "Latin round")

    def test_tournament_rounds_are_translated(self):
        self.english()
        # The WDSF words, short: Marcel's table. The rounds count on through
        # the intermediate ones, the redance has a name of its own.
        self.assertEqual(terms.round_name("Vorrunde"), "Round 1")
        self.assertEqual(terms.round_name("Hoffnungsrunde"), "Redance")
        self.assertEqual(terms.round_name("Zwischenrunde"), "Round 2")
        self.assertEqual(terms.round_name("1. Zwischenrunde"), "Round 2")
        self.assertEqual(terms.round_name("2. Zwischenrunde"), "Round 3")
        self.assertEqual(terms.round_name("3. Zwischenrunde"), "Round 4")
        self.assertEqual(terms.round_name("4. Zwischenrunde"), "Round 5")
        self.assertEqual(terms.round_name("Semifinale"), "Semi-Final")
        self.assertEqual(terms.round_name("Halbfinale"), "Semi-Final")
        self.assertEqual(terms.round_name("Viertelfinale"), "Quarter-Final")
        self.assertEqual(terms.round_name("Finale"), "Final")
        self.assertEqual(terms.round_name("Endrunde"), "Final")
        self.assertEqual(terms.round_name("Runde 3"), "Round 3")

    def test_a_dance_code_section_is_named_as_a_dance(self):
        """A running order whose rounds could not be derived heads its
        strips with the dance instead."""
        self.english()
        self.assertEqual(terms.round_name("LW"), "Slow Waltz")
        self.german()
        self.assertEqual(terms.round_name("LW"), "Langsamer Walzer")

    def test_anything_else_passes_untouched(self):
        self.english()
        for name in ("", None, "My own round", "Finale furioso"):
            self.assertEqual(terms.round_name(name), name)

    def test_german_words_and_a_german_screen_keep_them(self):
        self.english(german_terms=True)
        self.assertEqual(terms.round_name("Standardrunde 1"), "Standardrunde 1")
        self.assertEqual(terms.round_name("Vorrunde"), "Vorrunde")
        self.german()
        self.assertEqual(terms.round_name("Semifinale"), "Semifinale")


if __name__ == "__main__":
    unittest.main()
