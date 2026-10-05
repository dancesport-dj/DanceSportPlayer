#!/usr/bin/env python3
"""The three counting buttons on the right of the toolbar, in German.

Run:  py -m unittest tests.gui.test_toolbar_counts_i18n -v

"The right texts for the buttons are remain in english." The rest of the row
is German, and these three are not, because they are the ones that do not
keep a fixed caption: ⧉ counts the playlists, ⭐ counts the wishlist panes,
and 🗜 names the header view it is about to cycle to. Every one of their
captions is written somewhere other than the button's constructor, which is
the only spelling the catalog had ever been given.

Nothing is looked up here that the running app does not look up: the window
is real and the captions are put on by the production calls, so a caption
added to a cycle later fails this file instead of quietly staying English.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tbcount_i18n_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui import dialogs  # noqa: E402
from planner import i18n  # noqa: E402
from gui.main_persist import layout_settings  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)


class _Counts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        layout_settings().clear()
        dialogs.AUTOSAVE.remove()

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def win(self, language):
        """A real window under one language, wide enough to keep its labels.

        The width comes from what the row itself measured, so nothing here
        depends on the font the host happens to have — an icon-only toolbar
        would hide exactly the captions this file is about."""
        i18n.set_active(language)
        i18n.install_text_hook()
        win = self.gui.MainWindow()
        win._loading_dlg.accept()          # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, win)
        win.resize(win._toolbar_full_width * 2, 900)
        self.app.processEvents()
        self.assertEqual(0, win._toolbar_compact,
                         "the row compacted and the captions are gone")
        return win

    def decks(self, win, n):
        win._deck_count = n
        win._apply_deck_view()
        return win._dual_btn.text()

    def compact(self, win, state):
        win._compact_state = state
        win._apply_compact_label()
        return win._compact_btn.text()


class GermanTest(_Counts):

    def test_the_playlist_count(self):
        win = self.win("de")
        self.assertEqual("1 Playlist", self.decks(win, 1))
        self.assertEqual("2 Playlists", self.decks(win, 2))
        self.assertEqual("Keine Playlist", self.decks(win, 0))

    def test_the_wishlist_count(self):
        win = self.win("de")
        for state, want in ((0, "Keine Wunschliste"),
                            (1, "1 Wunschliste"),
                            (2, "2 Wunschlisten"),
                            (4, "4 Wunschlisten")):
            win._set_wish_state(state)
            self.assertEqual(want, win._dual_wish_btn.text())

    def test_the_four_wishlists_stacked_two_by_two(self):
        win = self.win("de")
        win._set_wish_state(4, grid=True)
        self.assertEqual("4 Wunschlisten (2×2)", win._dual_wish_btn.text())

    def test_the_header_view_cycle(self):
        win = self.win("de")
        self.assertEqual("🗜  Kompakt", self.compact(win, 0))
        self.assertEqual("🚫  Keine Gruppen", self.compact(win, 2))
        self.assertEqual("🔢  Nummern", self.compact(win, 3))


class EnglishIsUnchangedTest(_Counts):
    """The catalog is a lookup on the English string, so English has to come
    back byte for byte — the counts most of all, since they are the ones that
    changed shape to become translatable."""

    def test_the_captions_read_the_way_they_did(self):
        win = self.win("en")
        self.assertEqual("1 playlist", self.decks(win, 1))
        self.assertEqual("2 playlists", self.decks(win, 2))
        self.assertEqual("No playlist", self.decks(win, 0))
        win._set_wish_state(2)
        self.assertEqual("2 wishlists", win._dual_wish_btn.text())
        win._set_wish_state(4, grid=True)
        self.assertEqual("4 wishlists (2×2)", win._dual_wish_btn.text())
        self.assertEqual("🚫  No groups", self.compact(win, 2))
        self.assertEqual("🔢  Numbers", self.compact(win, 3))


if __name__ == "__main__":
    unittest.main()
