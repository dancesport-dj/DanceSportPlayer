#!/usr/bin/env python3
"""A Similar window opened from a deck previews the way the library pane's does.

Run:  .venv\\Scripts\\python.exe -m unittest tests.gui.table.test_similar_preview_route -v

Marcel: "if i pre hear a title from similar window it is loaded into main
player, after than closing the dialog the sync of play stop icon of the normal
playlists is broken". A deck's Similar window (and the 🔁 duplicate picker)
played through the deck's `_play_or_stop`, so with a 🎧 pre-listen output
chosen the preview took over the hall's player. Everything else around it
expects pre-listen: `release_play_markers` left the deck's ■ standing (the deck
"plays on"), and the close asked the pre-listen player whether the preview
was still on — it was not, so the preview kept running on the main player
under a stale ■. The window has to preview through `_prehear`, like the
library pane's Similar window does.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_simroute_"))

from PySide6.QtWidgets import QApplication, QWidget

import gui.table.table_menu as table_menu
from gui.table.playlist_table import PlaylistTable
from planner.generate.suggester import PlaylistSuggester
from planner.models import MusicEntry, RoundConfig
from planner.music.library import MusicLibrary
from tests.gui.test_duplicate_replacement_pick import _PickWin, _waltz
from tests.qt_test_support import reap_widget


def _tango(name: str) -> MusicEntry:
    return MusicEntry(path=Path(rf"C:\music\standardcd\{name} (TG 32).mp3"),
                      title=name, dance="TG", bpm=32)


class _Win(QWidget):
    def __init__(self, prehear=True):
        super().__init__()
        self._settings = {"app_mode": "full"}
        self.prehears: list = []
        self.seeks: list = []
        if prehear:
            self._prehear = self.prehears.append
            self._prehear_seek = self.seeks.append


class _FakeDialog:
    """Stands in for SimilarTracksDialog and keeps what it was given."""
    kwargs = []

    def __init__(self, source, results, *a, **kw):
        _FakeDialog.kwargs.append(kw)

    def __getattr__(self, name):
        return lambda *a, **kw: None


class DeckSimilarRouteTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        orig_dlg = table_menu.SimilarTracksDialog
        table_menu.SimilarTracksDialog = _FakeDialog
        self.addCleanup(setattr, table_menu, "SimilarTracksDialog", orig_dlg)
        _FakeDialog.kwargs = []
        self.lib = MusicLibrary()
        self.source, self.other = _tango("On The Deck"), _tango("Other")
        self.source.features = [0.0]
        self.lib.entries += [self.source, self.other]
        self.lib.similar_tracks = lambda *a, **kw: [(0.9, self.other)]
        self.deck_played: list = []

    def _table(self, win):
        t = PlaylistTable()
        t.setParent(win)
        self.addCleanup(reap_widget, win)
        t.load({"Endrunde": [[self.source]]}, ["TG"],
               [RoundConfig(name="Endrunde", heats=1, tier="final")],
               "S", play_cb=self.deck_played.append,
               suggester=PlaylistSuggester(self.lib), use_timbre=False)
        return t

    def test_the_preview_goes_through_prehear(self):
        win = _Win()
        self._table(win)._show_similar(self.source)
        play_cb = _FakeDialog.kwargs[0]["play_cb"]
        play_cb(self.other.path)
        self.assertEqual(win.prehears, [self.other.path])
        self.assertEqual(self.deck_played, [])

    def test_its_ctrl_arrows_seek_the_pre_listen(self):
        win = _Win()
        self._table(win)._show_similar(self.source)
        _FakeDialog.kwargs[0]["seek_cb"](30000)
        self.assertEqual(win.seeks, [30000])

    def test_outside_the_main_window_the_deck_plays_it(self):
        win = _Win(prehear=False)
        self._table(win)._show_similar(self.source)
        _FakeDialog.kwargs[0]["play_cb"](self.other.path)
        self.assertEqual(self.deck_played, [self.other.path])


class _PrehearPickWin(_PickWin):
    def __init__(self):
        super().__init__()
        self.prehears: list = []

    def _prehear(self, path):
        self.prehears.append(path)


class DuplicatePickRouteTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_the_duplicate_picker_previews_through_prehear(self):
        win = _PrehearPickWin()
        self.addCleanup(reap_widget, win)
        a = _waltz("Alpha")
        win.fill_deck(win._deckset.decks[0], [a])
        win._library.lib.similar_tracks = lambda *a, **k: [(0.6, _waltz("Zeta"))]
        seen = {}

        def capture(entry, res, *a, **k):
            seen.update(k)
            dlg = mock.Mock()
            dlg.exec.return_value = 0
            return dlg
        with mock.patch("gui.window.main_dupes.SimilarTracksDialog", side_effect=capture):
            win._pick_dup_replacement(a)
        seen["play_cb"](Path("x.mp3"))
        self.assertEqual(win.prehears, [Path("x.mp3")])
        self.assertEqual(seen["seek_cb"], win._prehear_seek)


if __name__ == "__main__":
    unittest.main(verbosity=2)
