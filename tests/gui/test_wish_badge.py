#!/usr/bin/env python3
"""Tests for the title-count badge under a wishlist.

Run:  py -m unittest tests.gui.test_wish_badge -v

The badge counts what is in a wishlist and how much of it the library has
never seen played — "🎵 7 titles  ·  ✦ 2 new". It was assembled with
f-strings, which is the one shape the translation hook can never reach: the
catalog is keyed by the English string, and a string that only exists once the
count is known is at no call site to be keyed by. So the bar stayed English in
German mode no matter how complete the catalog got.

It is built from templates now, translated before the count goes in. These
tests pin both halves of that: the German bar says Titel and neu, and the
English bar reads exactly as it always did — including the singular, which is
the case a careless `%d titles` would have quietly broken.
"""

import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication exists (see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_wish_"))

from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from gui.deck import Deck  # noqa: E402
from gui.main_wish import WishlistMixin  # noqa: E402
from planner import i18n  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class _Entry:
    """Only what the badge asks an entry: has anybody played this before."""

    def __init__(self, popularity=0):
        self.popularity = popularity


class _Table:
    def __init__(self, entries):
        self._entries = entries

    def wishlist_entries(self):
        return self._entries


class _Host(WishlistMixin):
    """One wishlist and the parts of the window the badge refresh touches."""

    def __init__(self, entries):
        self.lbl = QLabel()
        deck = Deck(table=_Table(entries), count_lbl=self.lbl)
        self._deck_of = {deck.table: deck}

    def _update_deck_totals(self):
        """Lives in DeckLayoutMixin; the badge only piggybacks on it."""


class WishCountBadgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def badge(self, entries):
        host = _Host(entries)
        self.addCleanup(reap_widget, host.lbl)
        host._update_wish_counts()
        return host.lbl.text()

    def test_english_reads_exactly_as_it_always_did(self):
        self.assertEqual(self.badge([]), "🎵 0 titles")
        self.assertEqual(self.badge([_Entry(5)]), "🎵 1 title")
        self.assertEqual(self.badge([_Entry(5), _Entry(3)]), "🎵 2 titles")
        self.assertEqual(self.badge([_Entry(5), _Entry()]),
                         "🎵 2 titles  ·  ✦ 1 new")

    def test_the_german_bar_counts_in_german(self):
        i18n.set_active("de")
        self.assertEqual(self.badge([]), "🎵 0 Titel")
        self.assertEqual(self.badge([_Entry(5)]), "🎵 1 Titel")
        self.assertEqual(self.badge([_Entry(5), _Entry(3)]), "🎵 2 Titel")

    def test_the_fresh_count_is_german_too(self):
        """The half Marcel actually saw: the bar still said "new"."""
        i18n.set_active("de")
        text = self.badge([_Entry(5), _Entry(), _Entry()])
        self.assertNotIn("new", text)
        self.assertIn("neu", text)
        self.assertIn("2", text)

    def test_the_count_still_reaches_the_bar_in_german(self):
        """A template whose placeholder the catalog dropped would read
        "🎵 Titel" — translated, and useless."""
        i18n.set_active("de")
        self.assertIn("17", self.badge([_Entry(5)] * 17))


if __name__ == "__main__":
    unittest.main()
