#!/usr/bin/env python3
"""↺ on a row puts a different title in the slot whenever the library has one.

Run:  py -m unittest tests.gui.test_reroll_new_title -v

Found by the click-through scenarios (tests/gui/test_monkey.py): the row's ↺
dropped the slot's own song from the exclude set so it stayed a fallback when
no alternative exists, but that made it a full candidate of the weighted draw.
With three titles of a dance, every third ↺ or so handed back the very title
it was asked to replace, and the click looked like it did nothing.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_reroll_"))

from dancesport_planner import (
    MusicEntry,
    MusicLibrary,
    PlaylistSuggester,
    RoundConfig,
)
from tests.qt_test_support import reap_widget, stub_window_startup

# The planner takes a Latin title only from a Latin folder (STYLE_FOLDERS).
_MUSIC = Path(tempfile.mkdtemp(prefix="dp_reroll_music_")) / "LateinCD"
_MUSIC.mkdir()


def _entry(name: str) -> MusicEntry:
    path = _MUSIC / f"{name}.mp3"
    path.write_bytes(b"ID3")
    return MusicEntry(path=path, title=name, dance="CC", bpm=None, popularity=3)


class RerollNewTitleTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_reroll_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.chas = [_entry(f"Cha {i} (CC 30)") for i in range(3)]
        lib = MusicLibrary()
        lib.entries.extend(self.chas)
        self.win._library.lib = lib
        self.table = self.win._deckset.tableB
        # "No alternative song found" is a modal box: answered, not waited on.
        box = mock.patch("gui.table.table_regen.QMessageBox")
        box.start()
        self.addCleanup(box.stop)

    def load(self, songs):
        self.table.load(
            {"Finale": [[s] for s in songs]}, ["CC"],
            [RoundConfig(name="Finale", heats=len(songs), tier="final")], "S",
            play_cb=self.win._play_or_stop,
            suggester=PlaylistSuggester(self.win._library.lib),
            use_timbre=False, style="Latin")
        return next(r for r, m in enumerate(self.table._row_meta) if m and m.entry)

    def reroll(self, row):
        from PySide6.QtWidgets import QApplication
        before = self.table._row_meta[row].entry
        self.table._regen(row)
        QApplication.processEvents()
        return before, self.table._row_meta[row].entry

    def test_the_slot_gets_another_title(self):
        row = self.load([self.chas[0]])
        for _ in range(30):
            before, after = self.reroll(row)
            self.assertIsNot(after, before, f"↺ handed back {before.title}")

    def test_the_slot_keeps_its_title_when_there_is_no_other(self):
        row = self.load(self.chas)
        before, after = self.reroll(row)
        self.assertIs(after, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
