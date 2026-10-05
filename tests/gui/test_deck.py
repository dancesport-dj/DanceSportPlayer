#!/usr/bin/env python3
"""Tests for the Deck module — what the window knows about one playlist deck.

Run:  py -m unittest tests.gui.test_deck -v

The eleven dicts these fields come from could never be tested on their own:
every question about a deck ("what is it called?", "was it ever generated?")
was a `.get()` in whichever module happened to ask, and the answer lived in a
built MainWindow. Deck is the interface, so it is also the test surface — no
Qt, no window.
"""
import unittest

from gui.deck import Deck, DeckContext


class DeckTitleTest(unittest.TestCase):
    """What to call a deck: the typed name wins, the default carries it, and
    there is always SOMETHING to write in a report or a file name."""

    def test_the_typed_name_is_the_title(self):
        self.assertEqual(Deck(None, name="HGR B Latein").title, "HGR B Latein")

    def test_an_unnamed_deck_falls_back_to_its_default(self):
        self.assertEqual(Deck(None, default_name="Playlist 3").title,
                         "Playlist 3")

    def test_the_typed_name_beats_the_default(self):
        d = Deck(None, name="HGR B Latein", default_name="Playlist 3")
        self.assertEqual(d.title, "HGR B Latein")

    def test_a_deck_that_was_never_named_at_all_still_has_a_title(self):
        """Reports and bundle folders are built from this — it may not be ''."""
        self.assertEqual(Deck(None).title, "Playlist")

    def test_a_cleared_name_falls_back_rather_than_going_blank(self):
        """Clearing a deck blanks `name`; the header then shows the default
        again instead of an empty title bar."""
        d = Deck(None, name="HGR B Latein", default_name="Playlist 3")
        d.name = ""
        self.assertEqual(d.title, "Playlist 3")


class DeckDefaultsTest(unittest.TestCase):
    """A deck that nobody has filled in yet answers every question — that is
    the whole point of asking one object instead of eleven dicts."""

    def test_a_fresh_deck_is_unfolded_and_unlettered(self):
        d = Deck(None)
        self.assertFalse(d.folded)
        self.assertEqual(d.letter, "")

    def test_a_fresh_deck_has_no_widgets(self):
        """The wishlists are asked about before their box is built."""
        d = Deck(None)
        for widget in (d.header, d.box, d.mode_btn, d.fold_btn,
                       d.total_lbl, d.count_lbl):
            self.assertIsNone(widget)

    def test_a_deck_that_was_never_generated_has_no_context(self):
        self.assertIsNone(Deck(None).ctx)

    def test_two_contexts_do_not_share_their_lists(self):
        """A mutable default would have every deck generated as the last one."""
        a, b = DeckContext(), DeckContext()
        a.dances.append("LW")
        self.assertEqual(b.dances, [])

    def test_the_deck_remembers_its_table(self):
        table = object()
        self.assertIs(Deck(table).table, table)


class DeckAccessorTest(unittest.TestCase):
    """`window.deck(table)` — the one way in. Built on first ask, and the SAME
    deck every time after, or a rename would be written to a throwaway."""

    def setUp(self):
        from gui.main_decks import DeckLayoutMixin

        class _Win:
            deck = DeckLayoutMixin.deck

            def __init__(self):
                self._deck_of = {}

        self.win = _Win()

    def test_asking_about_an_unknown_table_makes_its_deck(self):
        table = object()
        self.assertIsInstance(self.win.deck(table), Deck)
        self.assertIs(self.win.deck(table).table, table)

    def test_asking_twice_gives_the_same_deck(self):
        table = object()
        self.win.deck(table).name = "HGR B Latein"
        self.assertEqual(self.win.deck(table).name, "HGR B Latein")

    def test_two_tables_get_two_decks(self):
        a, b = object(), object()
        self.win.deck(a).name = "Deck A"
        self.assertEqual(self.win.deck(b).name, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
