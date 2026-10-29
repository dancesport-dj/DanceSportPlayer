#!/usr/bin/env python3
"""Tests that the ■ marker follows the playing TITLE through a re-render.

Run:  py -m unittest tests.gui.test_play_row_follows_rerender -v

`_current_play_row` is a row number. Toggling the grouping, rebuilding a
dynamic deck or reordering a dance re-renders the table through `load()`, and
the row numbers move under the title that is playing. The marker then sat on
whatever slid into that row, and auto-advance continued from the wrong place.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_playrow_"))

from PySide6.QtWidgets import QApplication

from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry, RoundConfig
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)


def _e(dance: str, n: int) -> MusicEntry:
    return MusicEntry(path=Path(rf"C:\music\{dance}{n}.mp3"),
                      title=f"{dance} {n}", dance=dance, bpm=None)


class PlayRowFollowsRerenderTest(unittest.TestCase):

    def setUp(self):
        self.t = PlaylistTable()
        self.addCleanup(reap_widget, self.t)
        self.playing = _e("LW", 3)

    def _load(self, dances=("LW", "TG"), dynamic=False, playlist=None):
        playlist = playlist or {
            "Vorrunde": [[_e("LW", 1), _e("TG", 2)]],
            "Finale": [[self.playing, _e("TG", 4)]],
        }
        rounds = [RoundConfig(name=n, heats=1, tier="final") for n in playlist]
        kw = {"dynamic": True, "capacity": [1, 1]} if dynamic else {}
        self.t.load(playlist, list(dances), rounds, "S",
                    play_cb=lambda *a: None, suggester=None, use_timbre=False,
                    **kw)

    def _row_of(self, title: str) -> int:
        return next(r for r, m in self.t._row_meta.numbered()
                    if m.entry.title == title)

    def _start(self):
        self.t._current_play_row = self._row_of(self.playing.title)

    def _marked_title(self):
        m = self.t._row_meta.at(self.t._current_play_row)
        return m.entry.title if m is not None and m.entry else None

    def test_dropping_the_headers_keeps_the_marker_on_the_title(self):
        self._load()
        self._start()
        self.t.set_grouping(2)
        self.assertEqual(self._marked_title(), self.playing.title)

    def test_restoring_the_headers_keeps_the_marker_on_the_title(self):
        self._load()
        self.t.set_grouping(2)
        self._start()
        self.t.set_grouping(0)
        self.assertEqual(self._marked_title(), self.playing.title)

    def test_reordering_the_dances_keeps_the_marker_on_the_title(self):
        self._load()
        self._start()
        self.t._reorder_dance("LW", "TG")
        self.assertEqual(self._marked_title(), self.playing.title)

    def test_a_dynamic_rebuild_keeps_the_marker_on_the_title(self):
        self._load(dynamic=True)
        self.t.set_grouping(2)
        self._start()
        self.t.set_grouping(0)          # → _rebuild_dynamic
        self.assertEqual(self._marked_title(), self.playing.title)

    def test_a_load_without_the_title_clears_the_marker(self):
        self._load()
        self._start()
        self._load(playlist={"Finale": [[_e("LW", 7), _e("TG", 8)]]})
        self.assertEqual(self.t._current_play_row, -1)

    def _move_block(self, title: str, onto: str):
        self.t._move_rows_block([self._row_of(title)], self._row_of(onto))
        _app.processEvents()             # the rows are redrawn in a 0 ms timer

    def test_a_block_move_elsewhere_keeps_the_marker(self):
        """Moving rows the playing title is not part of must leave it alone."""
        self._load()
        self._start()                    # LW 3 plays
        self._move_block("TG 2", onto="TG 4")
        self.assertEqual(self._marked_title(), self.playing.title)

    def test_a_block_move_of_the_playing_title_takes_the_marker_along(self):
        self._load()
        self._start()
        self._move_block(self.playing.title, onto="LW 1")
        self.assertEqual(self._marked_title(), self.playing.title)


class RemovingThePlayingTitleStopsItTest(unittest.TestCase):
    """✖ heat / ✖ round clicked on ANOTHER row of the block the playing title
    sits in: the title leaves the deck, so the music has to stop — the desk
    decides that on `loaded`, as it does for every re-render."""

    _load = PlayRowFollowsRerenderTest._load
    _row_of = PlayRowFollowsRerenderTest._row_of
    _start = PlayRowFollowsRerenderTest._start
    _marked_title = PlayRowFollowsRerenderTest._marked_title

    def setUp(self):
        PlayRowFollowsRerenderTest.setUp(self)
        from tests.player.test_double_click_play import _Desk
        self._load(dynamic=True)
        self._start()
        self.t._confirm_delete = lambda *_a: True
        self.desk = _Desk(playing=self.playing.path)
        self.desk._between.pending = None
        self.t.loaded.connect(self.desk._stop_if_playing_from)  # as MainWindow wires it

    def test_removing_its_heat_stops_the_music(self):
        self.t._remove_dynamic_heat(self._row_of("TG 4"))
        self.assertIn((None, True), self.desk.calls)
        self.assertEqual(self.t._current_play_row, -1)

    def test_removing_its_round_stops_the_music(self):
        self.t._remove_dynamic_round(self._row_of("TG 4"))
        self.assertIn((None, True), self.desk.calls)
        self.assertEqual(self.t._current_play_row, -1)

    def test_removing_another_heat_keeps_playing(self):
        self.t._remove_dynamic_heat(self._row_of("TG 2"))
        self.assertEqual(self.desk.calls, [])
        self.assertEqual(self._marked_title(), self.playing.title)


class LoadingAnotherFlatListStopsItTest(unittest.TestCase):
    """BUG_REVIEW B5.3: only `load()` told the desk its playing title was
    gone. A theme, warm-up, running order or wishlist loaded over the playing
    one — or a warm-up edit that took the title out — left it running with no
    ■ anywhere, and ⏭ / auto-advance with nowhere to go on from."""

    _row_of = PlayRowFollowsRerenderTest._row_of
    _start = PlayRowFollowsRerenderTest._start

    def setUp(self):
        PlayRowFollowsRerenderTest.setUp(self)
        from tests.player.test_double_click_play import _Desk
        self.first = [_e("LW", 1), _e("TG", 2), self.playing, _e("TG", 4)]
        self.other = [_e("SW", 5), _e("VW", 6)]
        self.desk = _Desk(playing=self.playing.path)
        self.desk._between.pending = None

    def _play_in(self, load):
        load(self.first)
        self._start()
        self.t.loaded.connect(self.desk._stop_if_playing_from)  # as MainWindow wires it

    def _theme(self, entries):
        self.t.load_theme(entries, "Theme", play_cb=lambda *a: None, suggester=None)

    def _warmup(self, entries):
        self.t.load_warmup(entries, "Warm-up", style="S", dance_class="S",
                           relax=True, play_cb=lambda *a: None, suggester=None)

    def _player_list(self, entries):
        self.t.load_player_list(entries, "Order", play_cb=lambda *a: None)

    def _wishlist(self, entries):
        self.t.load_wishlist(entries, play_cb=lambda *a: None, suggester=None)

    def test_each_loader_stops_a_title_it_no_longer_holds(self):
        for load in (self._theme, self._warmup, self._player_list, self._wishlist):
            with self.subTest(load.__name__):
                self.desk.calls.clear()
                self.desk._playback.path = self.playing.path
                self._play_in(load)
                load(self.other)
                self.t.loaded.disconnect(self.desk._stop_if_playing_from)
                self.assertIn((None, True), self.desk.calls)
                self.assertEqual(self.t._current_play_row, -1)

    def test_each_loader_keeps_a_title_it_still_holds(self):
        for load in (self._theme, self._warmup, self._player_list, self._wishlist):
            with self.subTest(load.__name__):
                self.desk.calls.clear()
                self._play_in(load)
                load(self.other + [self.playing])
                self.t.loaded.disconnect(self.desk._stop_if_playing_from)
                self.assertEqual(self.desk.calls, [])

    def test_a_warmup_edit_that_drops_the_title_stops_it(self):
        self._play_in(self._warmup)
        with mock.patch.object(self.t, "load_warmup",
                               side_effect=AssertionError("not edited in place")):
            self.t._reload_warmup([e for e in self.first if e is not self.playing])
        self.assertIn((None, True), self.desk.calls)
        self.assertEqual(self.t._current_play_row, -1)

    def test_a_warmup_edit_elsewhere_keeps_playing(self):
        self._play_in(self._warmup)
        with mock.patch.object(self.t, "load_warmup",
                               side_effect=AssertionError("not edited in place")):
            self.t._reload_warmup(self.first[:3])
        self.assertEqual(self.desk.calls, [])
        self.assertEqual(self.t._row_meta.at(self.t._current_play_row).entry, self.playing)


if __name__ == "__main__":
    unittest.main(verbosity=2)
