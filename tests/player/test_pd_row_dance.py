#!/usr/bin/env python3
"""🐂 A title played from a Paso Doble row is a Paso Doble.

Run:  .venv\\Scripts\\python.exe -m unittest tests.player.test_pd_row_dance -v

Marcel, on the Mac: "paso on with highlitgh 1 stop selected" — and the Paso
Doble neither showed its highlight nor stopped there. The player took the
dance from the file's library entry, looked up again by path, and never from
the row it was started from. A grid slot names its dance whatever the title in
it is tagged, and a path the library does not hold verbatim is rebuilt from its
file name alone. Either way the deck said PD while the player heard no Paso
Doble, and the whole 🐂 stop was skipped.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pd_row_dance_"))

from pathlib import Path

from PySide6.QtWidgets import QApplication

from gui.decks.running_order import Row
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget, stub_window_startup


class PdRowDanceTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_pd_row_dance_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.table = self.win._deckset.tableB
        self.path = Path("C:/music/Espana Cani.mp3")

    def start(self, row_dance, resolved_dance):
        """`path` is ▶ on a row of `row_dance`; looked up by path it resolves
        to an entry of `resolved_dance` (None: no dance at all)."""
        self.table.setRowCount(1)
        self.table._row_meta.append(Row(
            entry=MusicEntry(path=self.path, title="Espana Cani", dance="PD"),
            dance=row_dance))
        self.table._current_play_row = 0
        self.win._resolve_entry = lambda _p: MusicEntry(
            path=self.path, title="Espana Cani", dance=resolved_dance)
        self.win._adopt_track(self.path)

    def test_the_rows_dance_wins_over_the_resolved_entry(self):
        self.start("PD", None)
        self.assertEqual(self.win._playback.dance, "PD")

    def test_the_highlight_stop_runs_for_it(self):
        self.win._play_panel.set_pd_highlight_stop(True)
        self.start("PD", None)
        self.assertTrue(self.win._pd_runs_to_its_highlight())

    def test_a_row_of_another_title_does_not_name_this_ones_dance(self):
        """The marked row may still be the title before — a drop onto the
        card cues without one. Then the entry's own dance stands."""
        self.start("PD", "SA")
        self.table._row_meta.at(0).entry.path = Path("C:/music/other.mp3")
        self.win._adopt_track(self.path)
        self.assertEqual(self.win._playback.dance, "SA")

    def test_without_a_playing_row_the_entry_decides(self):
        self.start("PD", "SA")
        self.table._current_play_row = -1
        self.win._adopt_track(self.path)
        self.assertEqual(self.win._playback.dance, "SA")

    def test_the_mark_tools_work_only_on_a_paso_doble(self):
        """F16: 🎯 ✖ ✏️ act on the title on the deck, and only a Paso Doble
        has highlights to mark."""
        panel = self.win._play_panel
        tools = (panel.pd_learn_btn, panel.pd_clear_btn, panel.pd_edit_btn)
        self.assertFalse(any(w.isEnabled() for w in tools), "nothing loaded")
        self.start("PD", None)
        self.assertTrue(all(w.isEnabled() for w in tools))
        self.start("PD", "SA")
        self.table._current_play_row = -1
        self.win._adopt_track(self.path)
        self.assertFalse(any(w.isEnabled() for w in tools), "a samba")
        self.start("PD", None)
        self.win._unload_track(self.win._player)
        self.assertFalse(any(w.isEnabled() for w in tools), "unloaded")


if __name__ == "__main__":
    unittest.main(verbosity=2)
