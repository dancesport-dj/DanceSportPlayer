#!/usr/bin/env python3
"""Tests for the two desk conveniences on a deck:

  * a double-click PLAYS the row in playing mode and opens the file in the
    default player while planning (`PlaylistTable._on_row_double_clicked`), and
  * a playlist landing in a deck cues its first title so the player card is not
    blank (`PlayerControlMixin._cue_first_track`).

Run:  py -m unittest tests.player.test_double_click_play -v

Handing a track to the OS music player mid-tournament is the failure this
guards: the operator double-clicks the next title expecting sound in the hall
and gets a second player fighting the desk for the audio device.
"""

import os
import tempfile
import unittest
from pathlib import Path

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_dblclick_"))

from PySide6.QtWidgets import QApplication  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from gui import playlist_table as gpt  # noqa: E402
from dancesport_planner import MusicEntry  # noqa: E402
from player.main_player import PlayerControlMixin  # noqa: E402
from player.playback_state import PlaybackState  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from gui.running_order import Row, RunningOrder  # noqa: E402
from player.between_dances import BetweenDances  # noqa: E402


def _entry(name: str) -> MusicEntry:
    return MusicEntry(path=Path(rf"C:\music\{name}.mp3"), title=name,
                      dance="WW", bpm=29)


class _Silent:
    def stop(self):
        pass


class _Desk(PlayerControlMixin):
    """The player desk stripped to the cue decision; `_play_or_stop` records."""

    def __init__(self, playing: Path = None, tables=()):
        self._player = object()          # only tested for truthiness
        self._playback = PlaybackState()
        self._playback.path = playing
        # An armed pause into some other deck: the reload stop takes it too.
        self._between = BetweenDances()
        self._between.pending = (None, 0, playing) if playing else None
        self._between.round_start = None
        self._announcer = _Silent()
        self._all_tables = tuple(tables)
        self.calls = []

    def _play_or_stop(self, path, start=True):
        self.calls.append((path, start))
        if path is None:
            self._playback.path = None

    # The rest of the stop: each one only has to be called, not to work here.
    def _stop_pause_music(self):
        self.calls.append(("pause music stopped", None))

    def _on_stop_btn(self):
        self.calls.append(("markers reset", None))

    def statusBar(self):
        return self

    def showMessage(self, *_a):
        pass


class _Table(unittest.TestCase):
    """A deck with two song rows and a recorder in place of the player."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.t = PlaylistTable()
        # The table is its own window() here, so the settings the desk keeps on
        # MainWindow hang off it. Started on "a double-click plays" — the party
        # value; the cue-only half has its own case below.
        self.t._settings = {"dblclick_plays": True}
        self.t.setRowCount(2)
        self.t._row_meta = RunningOrder([Row(entry=_entry("first")),
                                         Row(entry=_entry("second"))])
        self.played = []
        self.t._play_cb = self.played.append
        self.opened = []
        real_open = gpt._open_in_default_player
        gpt._open_in_default_player = lambda p, parent=None: self.opened.append(p)
        self.addCleanup(setattr, gpt, "_open_in_default_player", real_open)
        self.addCleanup(reap_widget, self.t)


class DoubleClickTest(_Table):

    def test_planning_mode_opens_the_file(self):
        """Auditioning a candidate while building a list — unchanged behaviour."""
        self.t._on_row_double_clicked(1, 0)
        self.assertEqual(self.opened, [Path(r"C:\music\second.mp3")])
        self.assertEqual(self.played, [])

    def test_playing_mode_plays_the_row(self):
        self.t.set_play_highlight_enabled(True)
        self.t._on_row_double_clicked(1, 0)
        self.assertEqual(self.played, [Path(r"C:\music\second.mp3")])
        self.assertEqual(self.opened, [])            # nothing handed to the OS
        self.assertEqual(self.t._current_play_row, 1)

    def test_the_running_row_is_not_stopped_by_a_double_click(self):
        """No stray double-click may silence the hall mid-heat."""
        self.t.set_play_highlight_enabled(True)
        self.t._on_row_double_clicked(0, 0)
        self.t._on_row_double_clicked(0, 0)
        self.assertEqual(self.played, [Path(r"C:\music\first.mp3")])
        self.assertEqual(self.t._current_play_row, 0)

    def test_nothing_configured_yet_cues(self):
        """The desk is a tournament until a party list says otherwise, and there
        the music starts on ⏯."""
        del self.t._settings
        self.assertFalse(self.t.dblclick_plays())

    def test_a_header_row_does_nothing_in_either_mode(self):
        self.t._row_meta[0] = None
        self.t._on_row_double_clicked(0, 0)
        self.t.set_play_highlight_enabled(True)
        self.t._on_row_double_clicked(0, 0)
        self.assertEqual((self.opened, self.played), ([], []))


class DoubleClickCuesTest(_Table):
    """⚙ Settings → 'Double-click starts the title' switched OFF: the click only
    CUES the title on the player, and ⏯ starts it. For a desk that wants the
    next title loaded and the level seen before anything reaches the hall.

    The table is its own window() here, so the settings dict and the cue route
    hang off it — in the app they belong to MainWindow."""

    def setUp(self):
        super().setUp()
        self.t.set_play_highlight_enabled(True)
        self.t._settings["dblclick_plays"] = False
        self.cued = []
        self.t._on_player_drop = self.cued.append

    def test_the_row_is_cued_and_nothing_starts(self):
        self.t._on_row_double_clicked(1, 0)
        self.assertEqual(self.cued, [r"C:\music\second.mp3"])
        self.assertEqual(self.played, [])
        self.assertEqual(self.opened, [])

    def test_switching_it_back_on_plays_again(self):
        self.t._settings["dblclick_plays"] = True
        self.t._on_row_double_clicked(1, 0)
        self.assertEqual(self.played, [Path(r"C:\music\second.mp3")])
        self.assertEqual(self.cued, [])

    def test_the_running_title_is_not_cued_over_itself(self):
        """Re-loading it would stop the music — the very thing a double-click
        may not do mid-heat."""
        self.t._current_play_row = 1
        self.t._on_row_double_clicked(1, 0)
        self.assertEqual(self.cued, [])

    def test_planning_mode_still_opens_the_file(self):
        """The option is about the player; without one there is nothing to
        cue."""
        self.t.set_play_highlight_enabled(False)
        self.t._on_row_double_clicked(1, 0)
        self.assertEqual(self.opened, [Path(r"C:\music\second.mp3")])
        self.assertEqual(self.cued, [])


class DoubleClickEventTest(_Table):
    """The click has to ARRIVE, too.

    Qt's cellDoubleClicked is emitted only when the second press lands on the
    same index the first press stored; a grid that scrolled, a deck header that
    re-laid out on focus or an internal drag in between swallow the whole
    double-click. The desk therefore reads the row out of the event itself."""

    def _dbl(self, row: int):
        """A bare double-click on `row` — no press stored for that index, which
        is exactly what Qt refuses to turn into cellDoubleClicked."""
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent

        self.t.resize(600, 200)
        pos = QPointF(20, self.t.rowViewportPosition(row) + self.t.rowHeight(row) / 2)
        ev = QMouseEvent(QEvent.Type.MouseButtonDblClick, pos,
                         self.t.viewport().mapToGlobal(pos.toPoint()),
                         Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(self.t.viewport(), ev)

    def test_the_row_under_the_cursor_plays(self):
        self.t.set_play_highlight_enabled(True)
        self._dbl(1)
        self.assertEqual(self.played, [Path(r"C:\music\second.mp3")])

    def test_it_happens_exactly_once(self):
        """Guards against a second route firing as well — in planning mode a
        double route would hand the file to the OS player twice."""
        self._dbl(0)
        self.assertEqual(self.opened, [Path(r"C:\music\first.mp3")])

    def test_the_area_below_the_last_row_is_ignored(self):
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent

        self.t.resize(600, 400)
        pos = QPointF(20, 380)                       # empty space under the grid
        QApplication.sendEvent(self.t.viewport(), QMouseEvent(
            QEvent.Type.MouseButtonDblClick, pos,
            self.t.viewport().mapToGlobal(pos.toPoint()),
            Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier))
        self.assertEqual((self.opened, self.played), ([], []))

    def test_a_right_double_click_plays_nothing(self):
        """The context menu opens on right-click — it must not start music."""
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent

        self.t.set_play_highlight_enabled(True)
        self.t.resize(600, 200)
        pos = QPointF(20, self.t.rowViewportPosition(1) + self.t.rowHeight(1) / 2)
        QApplication.sendEvent(self.t.viewport(), QMouseEvent(
            QEvent.Type.MouseButtonDblClick, pos,
            self.t.viewport().mapToGlobal(pos.toPoint()),
            Qt.MouseButton.RightButton, Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier))
        self.assertEqual(self.played, [])


class FirstTrackTest(_Table):

    def test_it_finds_the_first_song(self):
        self.assertEqual(self.t.first_track_path(), Path(r"C:\music\first.mp3"))

    def test_it_skips_round_and_dance_headers(self):
        self.t._row_meta = RunningOrder([None, Row(), Row(entry=_entry("second"))])
        self.assertEqual(self.t.first_track_path(), Path(r"C:\music\second.mp3"))

    def test_an_empty_deck_has_none(self):
        self.t._row_meta = RunningOrder()
        self.assertIsNone(self.t.first_track_path())

    def test_loading_a_playlist_announces_it(self):
        seen = []
        self.t.loaded.connect(seen.append)
        self.t.load_wishlist([_entry("wish")], play_cb=None, suggester=None)
        self.assertEqual(seen, [self.t])


class CueFirstTrackTest(_Table):

    def test_an_idle_player_gets_the_first_title_cued(self):
        desk = _Desk()
        desk._cue_first_track(self.t)
        self.assertEqual(desk.calls, [(Path(r"C:\music\first.mp3"), False)])

    def test_it_cues_and_never_starts(self):
        """start=False: loading a deck must not put music in the hall."""
        desk = _Desk()
        desk._cue_first_track(self.t)
        self.assertFalse(desk.calls[0][1])

    def test_a_running_tournament_is_left_alone(self):
        """Generating the next round mid-heat must not touch the player."""
        desk = _Desk(playing=Path(r"C:\music\running.mp3"))
        desk._cue_first_track(self.t)
        self.assertEqual(desk.calls, [])

    def test_an_empty_deck_cues_nothing(self):
        self.t._row_meta = RunningOrder()
        desk = _Desk()
        desk._cue_first_track(self.t)
        self.assertEqual(desk.calls, [])

    def test_no_multimedia_is_harmless(self):
        desk = _Desk()
        desk._player = None
        desk._cue_first_track(self.t)
        self.assertEqual(desk.calls, [])

    def test_the_cued_row_is_marked_on_the_deck(self):
        """The title is on the player, so the deck has to say which one it is —
        the same marker a drop onto the card leaves, and what ⏭ walks on from."""
        desk = _Desk(tables=(self.t,))
        desk._cue_first_track(self.t)
        self.assertEqual(self.t._current_play_row, 0)

    def test_the_cued_row_is_selected(self):
        """At startup the cued title is the row the operator sees picked."""
        desk = _Desk(tables=(self.t,))
        desk._cue_first_track(self.t)
        self.assertEqual(self.t.currentRow(), 0)
        self.assertTrue(self.t.selectionModel().isRowSelected(0))

    def test_an_existing_selection_is_not_taken_away(self):
        """The cue also follows an edit — whatever the operator picked stays."""
        self.t.selectRow(1)
        desk = _Desk(tables=(self.t,))
        desk._cue_first_track(self.t)
        self.assertEqual(self.t.currentRow(), 1)
        self.assertFalse(self.t.selectionModel().isRowSelected(0))

    def test_a_deck_that_cues_nothing_marks_nothing(self):
        self.t._row_meta = RunningOrder()
        desk = _Desk(tables=(self.t,))
        desk._cue_first_track(self.t)
        self.assertEqual(self.t._current_play_row, -1)


class StopOnReloadTest(_Table):
    """A new playlist in the deck the music is playing from stops the music —
    a re-render of the same tracks never does."""

    def desk_for(self, playing: str, play_row: int = 0):
        self.t._current_play_row = play_row
        return _Desk(playing=Path(rf"C:\music\{playing}.mp3"))

    def test_a_new_list_in_the_playing_deck_stops_the_music(self):
        desk = self.desk_for("gone")     # not among the deck's two rows
        desk._stop_if_playing_from(self.t)
        self.assertIn((None, True), desk.calls)
        self.assertIsNone(desk._between.pending)

    def test_the_stop_clears_the_card_so_the_new_first_track_can_be_cued(self):
        desk = self.desk_for("gone")
        desk._stop_if_playing_from(self.t)
        desk._cue_first_track(self.t)
        self.assertEqual(desk.calls[-1], (Path(r"C:\music\first.mp3"), False))

    def test_a_re_render_of_the_same_tracks_keeps_playing(self):
        # A drop, a sort or a grid turning into a running order reloads the
        # deck with the track that is running still in it.
        desk = self.desk_for("second")
        desk._stop_if_playing_from(self.t)
        self.assertEqual(desk.calls, [])

    def test_loading_another_deck_is_left_alone(self):
        desk = self.desk_for("gone", play_row=-1)
        desk._stop_if_playing_from(self.t)
        self.assertEqual(desk.calls, [])

    def test_an_idle_player_has_nothing_to_stop(self):
        self.t._current_play_row = 0
        desk = _Desk()
        desk._stop_if_playing_from(self.t)
        self.assertEqual(desk.calls, [])

    def test_no_multimedia_is_harmless(self):
        desk = self.desk_for("gone")
        desk._player = None
        desk._stop_if_playing_from(self.t)
        self.assertEqual(desk.calls, [])

    # -- through a real load(), which re-finds the running row by path, and
    #    the `loaded` signal the desk listens on --------------------------------

    def _reload(self, *names):
        from planner.models import RoundConfig
        self.t.load({"Runde": [[_entry(n)] for n in names]}, ["WW"],
                    [RoundConfig(name="Runde", heats=len(names), tier="final")],
                    "S", play_cb=self.played.append, suggester=None,
                    use_timbre=False)

    def _song_row(self, name):
        return next(r for r, m in self.t._row_meta.numbered()
                    if m.entry.title == name)

    def test_a_real_load_of_a_new_list_into_the_playing_deck_stops_the_music(self):
        """load() drops the ■ marker when the title is gone; the deck must
        still count as the one the music came from."""
        self._reload("first", "second")
        self.t._current_play_row = self._song_row("first")
        desk = _Desk(playing=_entry("first").path)
        self.t.loaded.connect(desk._stop_if_playing_from)   # as MainWindow wires it
        self._reload("new one", "new two")
        self.assertIn((None, True), desk.calls)

    def test_a_real_re_render_keeps_playing(self):
        self._reload("first", "second")
        self.t._current_play_row = self._song_row("first")
        desk = _Desk(playing=_entry("first").path)
        self.t.loaded.connect(desk._stop_if_playing_from)
        self._reload("second", "first")
        self.assertEqual(desk.calls, [])

    def _pausing_into(self, name):
        """The title ended; the pause before `name` in this deck is running."""
        self._reload("first", "second")
        desk = _Desk(playing=_entry("first").path)
        desk._between.pending = (self.t, self._song_row(name), _entry(name).path)
        return desk

    def test_a_new_list_during_the_pause_cancels_the_advance(self):
        """No running row during the pause — the armed advance names the deck."""
        desk = self._pausing_into("second")
        self.t.loaded.connect(desk._stop_if_playing_from)   # as MainWindow wires it
        self._reload("new one", "new two")
        self.assertIsNone(desk._between.pending)
        self.assertIn(("pause music stopped", None), desk.calls)

    def test_a_re_render_during_the_pause_keeps_the_advance(self):
        desk = self._pausing_into("second")
        armed = desk._between.pending
        self.t.loaded.connect(desk._stop_if_playing_from)
        self._reload("second", "first")
        self.assertIs(desk._between.pending, armed)
        self.assertEqual(desk.calls, [])

    def test_a_new_list_drops_the_next_round_start_into_it(self):
        self._reload("first", "second")
        desk = _Desk()
        desk._between.round_start = (self.t, self._song_row("second"),
                                  _entry("second").path)
        self.t.loaded.connect(desk._stop_if_playing_from)   # as MainWindow wires it
        self._reload("new one", "new two")
        self.assertIsNone(desk._between.round_start)


class _NoHeat:
    def announce_heat(self):
        return False


class AdvanceTargetFollowsTheTitleTest(_Table):
    """The armed advance is a row NUMBER; a re-render during the pause moves
    the title it was armed for. Whatever fires it must find the title again
    instead of starting whatever now sits on the old row."""

    _reload = StopOnReloadTest._reload
    _song_row = StopOnReloadTest._song_row

    def _armed(self, name):
        self._reload("first", "second", "third")
        desk = _Desk(playing=_entry("first").path)
        desk._big_player = None
        desk._play_panel = _NoHeat()
        target = (self.t, self._song_row(name), _entry(name).path)
        return desk, target

    def test_the_pause_starts_the_title_it_was_armed_for(self):
        desk, desk._between.pending = self._armed("second")
        self._reload("third", "first", "second")
        desk._fire_pending_advance()
        self.assertEqual(self.t._current_play_row, self._song_row("second"))

    def test_a_title_gone_from_the_deck_starts_nothing(self):
        desk, desk._between.pending = self._armed("second")
        self._reload("new one", "new two", "new three")
        desk._fire_pending_advance()
        self.assertEqual(self.t._current_play_row, -1)
        self.assertIsNone(desk._between.pending)

    def test_the_next_round_starts_on_its_own_title(self):
        desk, desk._between.round_start = self._armed("third")
        self._reload("third", "first", "second")
        self.assertTrue(desk._start_next_round())
        self.assertEqual(self.t._current_play_row, self._song_row("third"))

    def test_the_announcement_names_the_moved_title(self):
        desk, target = self._armed("second")
        self._reload("third", "first", "second")
        self.t._row_meta[self._song_row("second")].entry.bpm = 33
        _code, takt, _heat = desk._announce_dance_of(target)
        self.assertEqual(takt, 33)

    def test_an_unmoved_title_keeps_its_row(self):
        from player.main_pause import _live_target
        desk, target = self._armed("second")
        self.assertIs(_live_target(target), target)
        self._reload("first", "second", "third")
        self.assertEqual(_live_target(target)[1], self._song_row("second"))


if __name__ == "__main__":
    unittest.main()
