#!/usr/bin/env python3
"""Take the grey off played titles without restarting.

Run:  py -m unittest tests.gui.test_reset_played_titles -v

Marcel's list, 6.6: "In the playlist column context menu, add a reset for played
titles (the grey ones), similar to the play counter reset. [...] The user must
be able to reset a greyed-out title without restarting the client."

The grey and the counters stay two entries: the spec allows one, but a mistaken
grey in the middle of an evening should not cost the counters.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_reset_played_"))

from PySide6.QtWidgets import QApplication

from planner.models import MusicEntry
from player.window import main_resume
from tests.qt_test_support import reap_widget, stub_window_startup

RESET = "Reset the played titles (grey)"
SONG = Path(r"C:\music\A.mp3")


def _entry(path=SONG):
    return MusicEntry(path=path, title=path.stem, dance="LW", duration=150)


class ResetPlayedTitlesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._qs_dir = tempfile.mkdtemp(prefix="dp_reset_played_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._qs_dir)
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.table, self.other = self.win._deckset.all_tables[:2]
        for t in (self.table, self.other):
            t.load_warmup([_entry(Path(r"C:\music\B.mp3")), _entry()], "Party",
                          "Standard", "S", False, lambda *_a: None, None)
            t.set_play_highlight_enabled(True)

    def action(self, table=None):
        return next(a for a in (table or self.table).build_column_menu().actions()
                    if a.text() == RESET)

    def test_nothing_played_leaves_it_greyed(self):
        self.assertFalse(self.action().isEnabled())

    def test_it_takes_the_grey_off_in_every_list(self):
        self.win._mark_path_played(SONG)
        self.assertTrue(self.table._played_saved)
        self.assertTrue(self.other._played_saved)
        self.action().trigger()
        for t in (self.table, self.other):
            self.assertFalse(t._played_saved)
            self.assertFalse(t._played_paths)

    def test_a_reset_title_greys_again_when_it_plays_again(self):
        self.win._mark_path_played(SONG)
        self.action().trigger()
        self.win._mark_path_played(SONG)
        self.assertTrue(self.table._played_saved)

    def test_the_evening_on_disk_forgets_too(self):
        """The crash note offers its titles back on the next start."""
        self.win._mark_path_played(SONG)
        with mock.patch.object(main_resume.EVENING, "write") as write:
            self.action().trigger()
        self.assertEqual(write.call_args.args[0]["played"], [])

    def test_the_counted_title_on_air_stays_played(self):
        """Past its ten seconds it would never be marked again."""
        self.win._mark_path_played(SONG)
        self.win._playback.path = SONG
        self.win._played_marked = True
        with mock.patch.object(main_resume.EVENING, "write"):
            self.action().trigger()
        self.assertEqual(self.table._played_paths, {str(SONG)})

    def test_a_title_on_air_not_counted_yet_is_forgotten(self):
        self.win._mark_path_played(SONG)
        self.win._playback.path = SONG
        self.win._played_marked = False
        with mock.patch.object(main_resume.EVENING, "write"):
            self.action().trigger()
        self.assertFalse(self.table._played_paths)

    def test_the_counters_stay(self):
        self.win._mark_path_played(SONG)
        with mock.patch.object(self.win, "_reset_play_counts") as counters:
            self.action().trigger()
        counters.assert_not_called()


if __name__ == "__main__":
    unittest.main()
