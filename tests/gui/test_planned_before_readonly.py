#!/usr/bin/env python3
"""📜 Find planned before leaves the deck's tooltips alone.

Run:  .venv\\Scripts\\python.exe -m unittest tests.gui.test_planned_before_readonly -v

The lookup reads every tournament list of every class, and it wrote what it
found into each matched song's shared `replay_sources` — the "In these matching
past lists" part of the tooltip of that song in every deck. After one lookup, a
deck generated from past competitions described its songs by lists it was never
built from. The window now gets copies carrying the narrowed lists.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_planned_"))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)

import gui.table_actions as table_actions  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from planner import library as planner_library  # noqa: E402
from planner.library import MusicLibrary  # noqa: E402
from planner.models import MusicEntry, RoundConfig  # noqa: E402
from planner.suggester import PlaylistSuggester  # noqa: E402

_TRACK = r"C:\music\standardcd\Tango One (TG 32).mp3"


class _Win(QWidget):
    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "full"}


class _FakeDialog:
    """Stands in for SimilarTracksDialog and keeps what it was shown."""
    shown = []

    def __init__(self, source, results, *a, **kw):
        _FakeDialog.shown.append(results)

    def __getattr__(self, name):
        return lambda *a, **kw: None


class PlannedBeforeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        orig = planner_library.PLAYLIST_DIR
        self.dir = Path(tempfile.mkdtemp(prefix="dp_planned_lists_"))
        planner_library.PLAYLIST_DIR = self.dir
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.addCleanup(setattr, planner_library, "PLAYLIST_DIR", orig)
        (self.dir / "Turnier Hgr S STD.m3u").write_text(
            "#EXTM3U\n" + _TRACK + "\n", encoding="utf-8")

        orig_dlg = table_actions.SimilarTracksDialog
        table_actions.SimilarTracksDialog = _FakeDialog
        self.addCleanup(setattr, table_actions, "SimilarTracksDialog", orig_dlg)
        _FakeDialog.shown = []

    def test_the_lookup_shows_copies_and_keeps_the_shared_entry(self):
        entry = MusicEntry(path=Path(_TRACK), title="Tango One", dance="TG", bpm=32)
        entry.replay_sources = ["Hgr B / this deck's own competition"]
        lib = MusicLibrary()
        lib.entries.append(entry)

        win = _Win()
        t = PlaylistTable()
        t.setParent(win)
        self.addCleanup(reap_widget, win)
        t.load({"Endrunde": [[entry]]}, ["TG"],
               [RoundConfig(name="Endrunde", heats=1, tier="final")],
               "S", play_cb=None, suggester=PlaylistSuggester(lib), use_timbre=False)

        t._show_planned_before("TG", "Endrunde")

        self.assertEqual(len(_FakeDialog.shown), 1, "the window opened")
        (_cls, shown), = _FakeDialog.shown[0]
        self.assertEqual(shown.path, entry.path)
        self.assertEqual(shown.replay_sources,
                         [f"{self.dir.name} / Turnier Hgr S STD"])
        self.assertEqual(entry.replay_sources,
                         ["Hgr B / this deck's own competition"])


class GenerateLabelsTest(unittest.TestCase):
    """The labels still reach the tooltip where they belong: a deck generated
    from past competitions names the lists of THAT competition."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._settings_dir = tempfile.mkdtemp(prefix="dp_planned_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._settings_dir)
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls)

    def setUp(self):
        orig = planner_library.PLAYLIST_DIR
        self.dir = Path(tempfile.mkdtemp(prefix="dp_planned_gen_"))
        planner_library.PLAYLIST_DIR = self.dir
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.addCleanup(setattr, planner_library, "PLAYLIST_DIR", orig)
        (self.dir / "Turnier Hgr B STD.m3u").write_text(
            "#EXTM3U\n" + _TRACK + "\n", encoding="utf-8")

        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)

    def test_generate_labels_its_tracks_with_the_competition_lists(self):
        from planner.competition import parse_competition_schedule
        from planner.models import rounds_from_pattern

        entry = MusicEntry(path=Path(_TRACK), title="Tango One", dance="TG", bpm=32)
        lib = MusicLibrary()
        lib.entries.append(entry)
        self.win._lib = lib
        spec = parse_competition_schedule("HGR B STD 1")[0]
        self.win._cfg.get_replay_config = lambda: (spec, rounds_from_pattern("1"),
                                                   False)

        self.win._generate_replay()

        self.assertEqual(entry.replay_sources,
                         [f"{self.dir.name} / Turnier Hgr B STD"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
