#!/usr/bin/env python3
"""A party list that was built or opened gets the room.

Run:  py -m unittest tests.gui.test_party_list_alone -v

The 🤸 panel sits between the decks and the wishlists, and a list arriving there
stayed at the panel's small share of that column, so it looked collapsed. It now
comes up at full size with the playlists off and one wishlist left.

A real MainWindow on screen offscreen, so the heights are the splitter's own.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_alone_"))

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication

from planner.models import MusicEntry
from planner.music.library import MusicLibrary
from tests.qt_test_support import reap_widget, stub_window_startup


class PartyListAloneTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._qs_dir = tempfile.mkdtemp(prefix="dp_alone_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._qs_dir)
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls)
        cls.dir = Path(tempfile.mkdtemp(prefix="dp_alone_m3u_"))

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.lib = MusicLibrary()
        self.win._library.lib = self.lib
        self.win.resize(1600, 1000)
        self.win.show()
        self.app.processEvents()
        self.entries = self._entries("party", ("SA", "CC", "RB", "LW", "TG", "WW"))

    def _entries(self, name, dances):
        out = [MusicEntry(path=self.dir / f"{name}_{i}_{d}.mp3", title=f"{d} {i}",
                          dance=d, duration=180)
               for i, d in enumerate(dances)]
        self.lib.entries.extend(out)
        return out

    def _open(self):
        """The list opened from a file: an .m3u dropped on the panel."""
        table = self.win._deckset.warmup_table
        self.win._ensure_empty_warmup()
        m3u = self.dir / "opened.m3u"
        m3u.write_text("#EXTM3U\n" + "\n".join(str(e.path) for e in self.entries),
                       encoding="utf-8")
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(m3u))])
        table.dropEvent(QDropEvent(
            QPointF(2, 2), Qt.DropAction.CopyAction, mime,
            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        self.app.processEvents()

    def _build(self):
        self.win._on_warmup_done(self.entries)
        self.app.processEvents()

    def _shown_wishlists(self):
        return [t for t in self.win._deckset.wishlists if self.win._box_shown(t)]

    def _assert_alone(self):
        grid = self.win._grid
        self.assertFalse(grid.deck_tabs.isVisible(), "the playlists are still on screen")
        self.assertEqual(self.win._deckset.deck_count, 0)
        self.assertEqual(self._shown_wishlists(), [self.win._deckset.wishlist])
        self.assertTrue(self.win._deckset.warmup_table.isVisible())
        panel = grid.warmup_box.height()
        self.assertGreater(panel, grid.wish_split.height())
        self.assertGreater(panel, grid.right_split.height() * 0.45,
                           f"{panel} of {grid.right_split.height()} px")

    def test_a_built_list_comes_up_alone_and_at_full_size(self):
        self._build()
        self._assert_alone()

    def test_an_opened_list_comes_up_alone_and_at_full_size(self):
        self._open()
        self._assert_alone()

    def test_it_also_clears_four_decks_and_the_four_wishlist_grid(self):
        self.win._deckset.deck_count = 4
        self.win._apply_deck_view()
        self.win._set_wish_state(4, grid=True)
        self._build()
        self._assert_alone()
        self.assertFalse(self.win._wish_grid_on())

    def test_a_list_that_was_folded_opens(self):
        self._build()
        self.win._toggle_warmup_fold(True)
        self.win._deckset.deck_count = 1
        self.win._apply_deck_view()
        self._build()
        self._assert_alone()
        self.assertFalse(self.win._warmup_folded)

    def test_the_party_list_stays_the_active_list(self):
        self._build()
        self.assertIs(self.win._focused_table, self.win._deckset.warmup_table)

    def test_the_playlists_come_back_with_the_view_button(self):
        self._build()
        self.win._cycle_deck_view()
        self.app.processEvents()
        self.assertEqual(self.win._deckset.deck_count, 1)
        self.assertTrue(self.win._grid.deck_tabs.isVisible())
        self.assertGreater(self.win._grid.deck_tabs.height(), 100)

    def test_no_tracks_leaves_the_view_alone(self):
        from unittest import mock
        self.win._deckset.deck_count = 2
        self.win._apply_deck_view()
        with mock.patch.object(self.gui.QMessageBox, "information"):
            self.win._on_warmup_done([])
        self.assertEqual(self.win._deckset.deck_count, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
