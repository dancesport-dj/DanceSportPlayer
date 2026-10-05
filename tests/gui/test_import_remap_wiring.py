#!/usr/bin/env python3
"""📂 Import actually asks the remapper, and actually reports what it did.

Run:  py -m unittest tests.gui.test_import_remap_wiring -v

`planner.m3u` can re-root a carried-over playlist, but only if someone hands
it a remapper — and the desk is the only side that knows the search folders.
This pins the wiring end to end: a playlist full of `Q:\\…` lines, a library
sitting somewhere else on this machine, and a deck that comes out pointing at
the real files, with one dialog's worth of report to show for it.
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_impremap_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from planner.library import MusicLibrary  # noqa: E402
from planner.models import MusicEntry  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)

FOREIGN = "Q:\\my music\\tanzcds\\lateincd\\{0}\\{1}"
TRACKS = [("SB", "Senorita (SB 50).mp3", "SA"),
          ("CC", "Havana (CC 31).mp3", "CC")]


class ImportRemapWiringTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        from PySide6.QtCore import QSettings
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_impremap_qs_"))
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_impremap_lib_"))
        self.root = self.dir / "tanzcds"
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.win._lib = MusicLibrary()
        self.foreign = []
        for sub, name, dance in TRACKS:
            local = self.root / "lateincd" / sub / name
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_bytes(b"\0" * 16)
            self.win._lib.entries.append(
                MusicEntry(path=local, title=local.stem, dance=dance,
                           bpm=50, duration=180))
            self.foreign.append(FOREIGN.format(sub, name))
        # One dialog instead of a real one: the report it is handed is the test.
        self.shown = []
        self.win._show_import_remap_report = self.shown.append

    def _m3u(self) -> Path:
        m = self.dir / "carried.m3u"
        m.write_text("#EXTM3U\n" + "\n".join(self.foreign) + "\n",
                     encoding="utf-8")
        return m

    def _deck_paths(self) -> list[Path]:
        return [Path(e.path) for e in self.win._table._row_meta.entries()]

    def test_the_search_folder_setting_reaches_the_import(self):
        self.win._settings["remap_paths"] = [str(self.root)]
        self.win._import_playlist_path(str(self._m3u()))
        self.assertEqual(sorted(p.name for p in self._deck_paths()),
                         sorted(name for _s, name, _d in TRACKS))
        for p in self._deck_paths():
            self.assertTrue(p.is_file(), f"{p} is not on disk")

    def test_the_report_is_shown_once_with_both_lines(self):
        self.win._settings["remap_paths"] = [str(self.root)]
        self.win._import_playlist_path(str(self._m3u()))
        self.assertEqual(len(self.shown), 1)
        reports = self.shown[0]
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["moved"], 2)
        self.assertEqual(reports[0]["missing"], 0)
        for foreign in self.foreign:
            self.assertIn(foreign, reports[0]["details"])

    def test_no_search_folder_leaves_the_tracks_missing_and_says_so(self):
        """Nothing is invented: with nowhere to look the deck keeps the dead
        paths, and the report is what tells the user why."""
        self.win._settings["remap_paths"] = []
        self.win._settings["reference_path"] = ""
        self.win._import_playlist_path(str(self._m3u()))
        self.assertEqual(len(self.shown), 1)
        self.assertEqual(self.shown[0][0]["moved"], 0)
        self.assertEqual(self.shown[0][0]["missing"], 2)

    def test_a_playlist_that_needs_nothing_shows_no_dialog(self):
        """The Windows case — every path resolves as written."""
        m = self.dir / "local.m3u"
        m.write_text("#EXTM3U\n" + "\n".join(
            str(e.path) for e in self.win._lib.entries) + "\n", encoding="utf-8")
        self.win._settings["remap_paths"] = [str(self.root)]
        self.win._import_playlist_path(str(m))
        self.assertEqual(self.shown, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
