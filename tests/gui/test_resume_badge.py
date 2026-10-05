#!/usr/bin/env python3
"""Tests for the ↩ resume visual: the “↩ m:ss” badge behind a deck row's
title (PlaylistTable.set_resume_marks).

The seek bar carries no mark of its own — a picked-up title starts at the mark,
so the playhead is already standing on it.

Run:  py -m unittest tests.gui.test_resume_badge -v

Only MARKED titles carry a badge — an unmarked row must look exactly as before.
"""

import os
import tempfile
import unittest
from pathlib import Path

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_resume_badge_"))

from dancesport_planner import (  # noqa: E402
    MusicEntry,
    MusicLibrary,
    PlaylistSuggester,
    RoundConfig,
)
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)


# The rows must not read as "file missing" — that tooltip replaces the rich one
# the ↩ badge writes into, so the entries point at real (empty) files.
_MUSIC = Path(tempfile.mkdtemp(prefix="dp_resume_music_"))


def _entry(name: str, dance: str) -> MusicEntry:
    path = _MUSIC / f"{name}.mp3"
    path.touch()
    return MusicEntry(path=path, title=name, dance=dance, bpm=None, popularity=3)


class ResumeBadgeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        cls._settings_dir = tempfile.mkdtemp(prefix="dp_resume_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._settings_dir)
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)

        self.cha = _entry("Cha One (CC 30)", "CC")
        self.rum = _entry("Rum One (RB 25)", "RB")
        lib = MusicLibrary()
        lib.entries.extend([self.cha, self.rum])
        self.win._lib = lib

        self.table = self.win._tableB
        self.table.load(
            {"Runde 1": [[self.cha, self.rum]]},
            ["CC", "RB"],
            [RoundConfig(name="Runde 1", heats=1, tier="final")],
            "S",
            play_cb=self.win._play_or_stop,
            suggester=PlaylistSuggester(lib),
            use_timbre=False, style="Latin",
            dynamic=True, capacity=[1],
        )

    def _title_of(self, entry) -> str:
        from gui.playlist_table import _COL_TITLE
        for r, m in enumerate(self.table._row_meta):
            if m and m.entry is entry:
                return self.table.item(r, _COL_TITLE).text()
        self.fail(f"no row for {entry.title}")

    # ----- the deck badge -----------------------------------------------------

    def test_a_marked_title_shows_where_it_stopped(self):
        self.table.set_resume_marks({str(self.cha.path): 63_000})
        self.assertIn("↩ 1:03", self._title_of(self.cha))

    def test_an_unmarked_title_stays_plain(self):
        self.table.set_resume_marks({str(self.cha.path): 63_000})
        self.assertEqual(self._title_of(self.rum), self.rum.title)

    def test_the_badge_follows_the_mark(self):
        self.table.set_resume_marks({str(self.cha.path): 63_000})
        self.table.set_resume_marks({str(self.cha.path): 125_000})
        self.assertIn("↩ 2:05", self._title_of(self.cha))

    def test_dropping_the_mark_takes_the_badge_with_it(self):
        self.table.set_resume_marks({str(self.cha.path): 63_000})
        self.table.set_resume_marks({})
        self.assertEqual(self._title_of(self.cha), self.cha.title)

    def test_the_tooltip_says_it_starts_there_again(self):
        from gui.playlist_table import _COL_TITLE
        self.table.set_resume_marks({str(self.cha.path): 63_000})
        for r, m in enumerate(self.table._row_meta):
            if m and m.entry is self.cha:
                self.assertIn("↩ Left at 1:03",
                              self.table.item(r, _COL_TITLE).toolTip())
                return
        self.fail("no row for the marked title")

    def test_marks_for_other_decks_touch_nothing_here(self):
        self.table.set_resume_marks({r"C:\music\elsewhere.mp3": 63_000})
        self.assertEqual(self._title_of(self.cha), self.cha.title)
        self.assertEqual(self._title_of(self.rum), self.rum.title)


if __name__ == "__main__":
    unittest.main()
