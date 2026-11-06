#!/usr/bin/env python3
"""The 📂 Import M3U button asks before it replaces a deck that holds tracks.

Run:  py -m unittest tests.gui.test_import_button_confirm -v

A dropped .m3u (table_dnd) and the tournament double-click both go through
`_confirm_m3u_replaces`; the button picked the file and wiped the deck without
a word. A "No" has to leave the deck alone on every replacing path: deck,
flat player list and the Eintanzen panel.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_impbtn_"))

from PySide6.QtWidgets import QApplication, QFileDialog

from planner.music.library import MusicLibrary
from tests.qt_test_support import reap_widget, stub_window_startup


class ImportButtonConfirmTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        from PySide6.QtCore import QSettings
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_impbtn_qs_"))
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_impbtn_m3u_"))
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.win._library.lib = MusicLibrary()
        self.m3u = self.dir / "incoming.m3u"
        self.m3u.write_text("#EXTM3U\n", encoding="utf-8")
        self.table = self.win._deckset.table
        # The deck "holds tracks" — the confirm only reads the count.
        self.table._row_meta.song_count = lambda: 3
        self.asked = []
        self.answer = False

        def _ask(m3u):
            self.asked.append(m3u)
            return self.answer
        self.table._confirm_m3u_replaces = _ask
        self.calls = []
        self.win._import_playlist_path = lambda p, report=True: self.calls.append(
            ("deck", p))
        self.win._load_player_list_from_m3u = lambda t, p: self.calls.append(
            ("flat", p))
        self.win._load_warmup_from_m3u = lambda t, p: self.calls.append(
            ("warmup", p))

    def _pick(self, table):
        with mock.patch.object(QFileDialog, "getOpenFileNames",
                               return_value=([str(self.m3u)], "")):
            self.win._import_m3u_into(table)

    def test_a_no_leaves_a_populated_deck_alone(self):
        self.answer = False
        self._pick(self.table)
        self.assertEqual(self.asked, [self.m3u])
        self.assertEqual(self.calls, [])

    def test_a_yes_imports_into_the_deck(self):
        self.answer = True
        self._pick(self.table)
        self.assertEqual(self.calls, [("deck", str(self.m3u))])

    def test_a_no_leaves_a_flat_player_deck_alone(self):
        self.answer = False
        self.table.plays_flat = lambda: True
        self._pick(self.table)
        self.assertEqual(self.calls, [])

    def test_a_yes_loads_the_flat_player_deck(self):
        self.answer = True
        self.table.plays_flat = lambda: True
        self._pick(self.table)
        self.assertEqual(self.calls, [("flat", str(self.m3u))])

    def test_a_no_leaves_the_warmup_panel_alone(self):
        self.answer = False
        warm = self.win._deckset.warmup_table
        warm._confirm_m3u_replaces = self.table._confirm_m3u_replaces
        warm._warmup = True
        self._pick(warm)
        self.assertEqual(self.calls, [])

    def test_a_wishlist_appends_so_it_never_asks(self):
        wish = self.win._deckset.wishlists[0]
        wish._insert_drop_files = lambda files, row: 0
        self._pick(wish)
        self.assertEqual(self.asked, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
