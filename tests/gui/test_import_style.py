#!/usr/bin/env python3
"""📂 An imported list's style comes from its tracks; the file name only fills a blank.

Run:  py -m unittest tests.gui.test_import_style -v

The tracks' dances (their tags) say what the list really holds. A file named
"…_Standard" full of Sambas is a Latin list with a misleading name. Only when the
tracks name no ballroom dance at all (a social-dance list) does the file name's
style decide.
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_impstyle_"))

from PySide6.QtWidgets import QApplication

from planner.models import MusicEntry
from planner.music.library import MusicLibrary
from tests.qt_test_support import reap_widget, stub_window_startup

LATIN = [("Senorita (SB 50).mp3", "SA"), ("Havana (CC 31).mp3", "CC")]
SOCIAL = [("Fox One.mp3", "DISCOFOX"), ("Salsa One.mp3", "SALSA")]


class ImportStyleTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        from PySide6.QtCore import QSettings
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_impstyle_qs_"))
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_impstyle_lib_"))
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.lib = MusicLibrary()
        self.win._library.lib = self.lib
        self.win._show_import_remap_report = lambda reports: None

    def _import(self, stem: str, tracks) -> str | None:
        lines = []
        for name, dance in tracks:
            f = self.dir / name
            f.write_bytes(b"\0" * 16)
            self.lib.entries.append(
                MusicEntry(path=f, title=f.stem, dance=dance, bpm=50, duration=180))
            lines.append(str(f))
        m3u = self.dir / f"{stem}.m3u"
        m3u.write_text("#EXTM3U\n" + "\n".join(lines) + "\n", encoding="utf-8")
        self.win._import_playlist_path(str(m3u))
        return self.win._style

    def test_the_tracks_style_beats_a_contradicting_file_name(self):
        self.assertEqual(self._import("Hauptgruppe_D_Standard", LATIN), "Latin")

    def test_the_tracks_style_holds_without_a_style_in_the_name(self):
        self.assertEqual(self._import("Hauptgruppe_D", LATIN), "Latin")

    def test_the_file_name_fills_in_when_the_tracks_name_no_ballroom_dance(self):
        self.assertEqual(self._import("Hauptgruppe_D_Latein", SOCIAL), "Latin")


if __name__ == "__main__":
    unittest.main()
