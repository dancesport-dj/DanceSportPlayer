#!/usr/bin/env python3
"""📂 Import M3U with several files picked: the playlists after the clicked one.

Run:  py -m unittest tests.gui.test_import_m3u_alongside -v

Several files picked in a deck's Import M3U went into whatever playlists were
empty, wherever they were, without a word, and on a player-only deck every file
after the first was dropped. Now the app asks: Yes puts the first file into the
clicked playlist and the others into the playlists after it, one each. A
playlist that holds tracks asks before it is replaced; kept, it passes its file
on to the next playlist (Marcel, 2026-11-14). No imports only the first file.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_impside_"))

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from planner.music.library import MusicLibrary
from tests.qt_test_support import reap_widget, stub_window_startup

YES = QMessageBox.StandardButton.Yes
NO = QMessageBox.StandardButton.No
CANCEL = QMessageBox.StandardButton.Cancel


class ImportAlongsideTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        from PySide6.QtCore import QSettings
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_impside_qs_"))
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_impside_m3u_"))
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.win._library.lib = MusicLibrary()
        self.win._max_decks = lambda: 4
        self.decks = self.win._deckset.decks[:4]
        self.files = []
        for name in "ABCDE":
            p = self.dir / f"{name}.m3u"
            p.write_text("#EXTM3U\n", encoding="utf-8")
            self.files.append(str(p))
        # Which playlists hold tracks, and what their replace question answers.
        self.holds = {}
        self.asked = []
        for i, deck in enumerate(self.decks):
            deck._confirm_m3u_replaces = (
                lambda m3u, i=i: self.asked.append((i + 1, m3u.stem))
                or self.holds.get(i + 1, True))
        self.loaded = []
        self.active = None
        self.win._set_active_table = lambda t: setattr(self, "active", t)
        self.win._import_playlist_path = lambda p, report=True: self.loaded.append(
            (self.decks.index(self.active) + 1, Path(p).stem))
        self.win._load_player_list_from_m3u = lambda t, p: self.loaded.append(
            (self.decks.index(t) + 1, Path(p).stem, "flat"))
        self.win._autosave_playlist = lambda: None
        self.questions = []
        self.notes = []

    def pick(self, deck_no, names, answer=YES):
        picked = [self.files["ABCDE".index(n)] for n in names]

        def question(_parent, _title, text, *_a, **_k):
            self.questions.append(text)
            return answer
        with mock.patch.object(QFileDialog, "getOpenFileNames", return_value=(picked, "")), \
                mock.patch("gui.window.main_import.QMessageBox.question", side_effect=question), \
                mock.patch("gui.window.main_import.QMessageBox.information",
                           side_effect=lambda _p, _t, text: self.notes.append(text)), \
                mock.patch("gui.window.main_import.show_toast"):
            self.win._import_m3u_into(self.decks[deck_no - 1])

    def test_yes_fills_the_clicked_playlist_and_the_ones_after_it(self):
        self.pick(1, "ABC")
        self.assertEqual(len(self.questions), 1)
        self.assertEqual(self.loaded, [(1, "A"), (2, "B"), (3, "C")])

    def test_it_starts_at_the_clicked_playlist_not_the_first_free_one(self):
        self.pick(2, "AB")
        self.assertEqual(self.loaded, [(2, "A"), (3, "B")])

    def test_no_imports_only_the_first_file_here(self):
        self.pick(2, "ABC", answer=NO)
        self.assertEqual(self.loaded, [(2, "A")])

    def test_cancel_imports_nothing(self):
        self.pick(1, "ABC", answer=CANCEL)
        self.assertEqual(self.loaded, [])
        self.assertEqual(self.asked, [])

    def test_a_full_playlist_asks_and_a_yes_replaces_it(self):
        self.holds = {2: True}
        self.pick(1, "ABC")
        self.assertIn((2, "B"), self.asked)
        self.assertEqual(self.loaded, [(1, "A"), (2, "B"), (3, "C")])

    def test_a_kept_playlist_passes_its_file_to_the_next_one(self):
        self.holds = {2: False}
        self.pick(1, "ABC")
        self.assertEqual(self.loaded, [(1, "A"), (3, "B"), (4, "C")])

    def test_the_files_past_the_last_playlist_are_named(self):
        self.pick(3, "ABC")
        self.assertEqual(self.loaded, [(3, "A"), (4, "B")])
        self.assertEqual(len(self.notes), 1)
        self.assertIn("C.m3u", self.notes[0])

    def test_nothing_is_imported_before_every_question_is_answered(self):
        """A kept playlist is asked about while nothing has loaded yet."""
        def ask(m3u, i=1):
            self.asked.append((i + 1, m3u.stem, list(self.loaded)))
            return False
        self.decks[1]._confirm_m3u_replaces = ask
        self.pick(1, "AB")
        self.assertIn((2, "B", []), self.asked)
        self.assertEqual(self.loaded, [(1, "A"), (3, "B")])

    def test_a_player_only_deck_loads_every_file_flat(self):
        for deck in self.decks:
            deck.plays_flat = lambda: True
        self.pick(1, "AB")
        self.assertEqual(self.loaded, [(1, "A", "flat"), (2, "B", "flat")])

    def test_one_file_asks_nothing_extra(self):
        self.pick(1, "A")
        self.assertEqual(self.questions, [])
        self.assertEqual(self.loaded, [(1, "A")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
