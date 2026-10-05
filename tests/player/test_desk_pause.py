#!/usr/bin/env python3
"""Tests for the row play button AT THE DESK: it pauses instead of unloading.

Run:  py -m unittest tests.player.test_desk_pause -v

In playing mode the grid sits next to the big player's ⏯, so the two buttons
have to mean the same thing: pressing the row's button holds the track where it
is (source loaded, position kept) and pressing it again resumes — no reload, no
lost position. The row keeps its familiar ■/▶ pair, but it now follows the
player whoever pressed pause (row button, Space, the presenter transport), which
is why every re-render of the running row asks for the live state instead of
stamping ■.

While planning, a preview is throw-away: the button keeps the plain stop that
releases the file.

The resume is also where 🔊 Equalize volume starts to count for the title that
is already loaded (`_refresh_loudness_gain`) — it used to reach only the next
one.
"""

import os
import tempfile
import unittest
from pathlib import Path

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pause_"))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from player.mix import OutputMix  # noqa: E402
from player.playback_state import PlaybackState  # noqa: E402
from dancesport_planner import MusicEntry  # noqa: E402
from gui.playlist_table import PlaylistTable, _COL_PLAY  # noqa: E402
from gui.running_order import Row, RunningOrder  # noqa: E402


def _entry(name: str) -> MusicEntry:
    return MusicEntry(path=Path(rf"C:\music\{name}.mp3"), title=name,
                      dance="WW", bpm=29)


def _meta(name: str, h_idx: int) -> Row:
    return Row(entry=_entry(name), dance="WW", h_idx=h_idx)


class _BigPlayer:
    def __init__(self):
        self.toggles = 0

    def toggle_play(self):
        self.toggles += 1


class _Win(QWidget):
    """Stands in for MainWindow: the deck reads the player card off the window."""

    def __init__(self, *, desk: bool):
        super().__init__()
        self._big_player = _BigPlayer() if desk else None
        self.running = True
        self.stopped = False

    def _is_player_running(self) -> bool:
        return self.running

    def _is_player_stopped(self) -> bool:
        return self.stopped


class _Deck(unittest.TestCase):
    """Two song rows, real play buttons, a recorder in place of the player."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def deck(self, *, desk: bool):
        win = _Win(desk=desk)
        t = PlaylistTable()
        t.setParent(win)
        t.setRowCount(2)
        t._row_meta = RunningOrder([_meta("first", 0), _meta("second", 1)])
        self.played = []
        t._play_cb = self.played.append
        t.set_play_highlight_enabled(desk)
        for row in (0, 1):
            t._refill_row(row, t._row_meta[row])
        self.addCleanup(reap_widget, win)
        return t

    def glyph(self, table, row: int) -> str:
        return table.cellWidget(row, _COL_PLAY).text()


class StopButtonTest(_Deck):

    def test_the_desk_pauses_instead_of_unloading(self):
        t = self.deck(desk=True)
        t._on_play_click(1, _entry("second").path)
        self.played.clear()
        t._on_play_click(1, _entry("second").path)      # ⏸ on the running row
        self.assertEqual(t.window()._big_player.toggles, 1)
        self.assertEqual(self.played, [], "the source must not be released")
        self.assertEqual(t._current_play_row, 1, "the row stays the running one")

    def test_pressing_again_resumes(self):
        t = self.deck(desk=True)
        t._on_play_click(0, _entry("first").path)
        t._on_play_click(0, _entry("first").path)
        t._on_play_click(0, _entry("first").path)
        self.assertEqual(t.window()._big_player.toggles, 2)
        self.assertEqual(self.played, [Path(r"C:\music\first.mp3")])

    def test_planning_still_stops(self):
        t = self.deck(desk=False)
        t._on_play_click(1, _entry("second").path)
        self.played.clear()
        t._on_play_click(1, _entry("second").path)
        self.assertEqual(self.played, [None], "the preview must release the file")
        self.assertEqual(t._current_play_row, -1)
        self.assertEqual(self.glyph(t, 1), "▶")

    def test_without_a_player_card_it_stops(self):
        """Playing mode before the card exists — never swallow the click."""
        t = self.deck(desk=True)
        t.window()._big_player = None
        t._on_play_click(0, _entry("first").path)
        self.played.clear()
        t._on_play_click(0, _entry("first").path)
        self.assertEqual(self.played, [None])

    def test_another_row_still_switches_tracks(self):
        t = self.deck(desk=True)
        t._on_play_click(0, _entry("first").path)
        self.played.clear()
        t._on_play_click(1, _entry("second").path)
        self.assertEqual(self.played, [Path(r"C:\music\second.mp3")])
        self.assertEqual(t.window()._big_player.toggles, 0)
        self.assertEqual(self.glyph(t, 0), "▶")


class GlyphSyncTest(_Deck):

    def test_the_desk_row_follows_the_player(self):
        t = self.deck(desk=True)
        t._on_play_click(0, _entry("first").path)
        self.assertEqual(self.glyph(t, 0), "■")
        t.sync_play_glyph(False)
        self.assertEqual(self.glyph(t, 0), "▶")
        t.sync_play_glyph(True)
        self.assertEqual(self.glyph(t, 0), "■")

    def test_planning_keeps_the_stop_square(self):
        t = self.deck(desk=False)
        t._on_play_click(0, _entry("first").path)
        self.assertEqual(self.glyph(t, 0), "■")
        t.sync_play_glyph(False)
        self.assertEqual(self.glyph(t, 0), "■", "a preview button never pauses")

    def test_a_re_render_asks_the_player(self):
        """Sorting / refilling the grid must not stamp ■ onto a paused row."""
        t = self.deck(desk=True)
        t._on_play_click(0, _entry("first").path)
        t.window().running = False
        t._refill_row(0, t._row_meta[0])
        self.assertEqual(self.glyph(t, 0), "▶")
        t.window().running = True
        t._refill_row(0, t._row_meta[0])
        self.assertEqual(self.glyph(t, 0), "■")

    def test_nothing_playing_is_a_no_op(self):
        t = self.deck(desk=True)
        t.sync_play_glyph(True)                     # must not raise
        self.assertEqual(self.glyph(t, 0), "▶")


class RepaintKeepsGlyphTest(_Deck):
    """A row repainted while its title runs keeps its ■. The 🔇 silence probe
    of a title's first play ends a few seconds in and repaints its row
    (`refresh_paths`) — which turned ■ into ▶ on the list just switched to."""

    def running(self):
        t = self.deck(desk=True)
        t._on_play_click(1, _entry("second").path)
        self.assertEqual(self.glyph(t, 1), "■")
        return t

    def test_refresh_paths(self):
        t = self.running()
        self.assertEqual(t.refresh_paths([_entry("second").path]), 1)
        self.assertEqual(self.glyph(t, 1), "■")

    def test_resume_marks(self):
        t = self.running()
        t.set_resume_marks({str(_entry("second").path): 30_000})
        self.assertEqual(self.glyph(t, 1), "■")

    def test_issue_marks(self):
        t = self.running()
        t._issue_paths = {str(_entry("second").path): "⏱ too short"}
        t.refresh_issue_marks()                     # the issue is resolved
        self.assertEqual(self.glyph(t, 1), "■")

    def test_other_rows_stay_play(self):
        t = self.running()
        t.refresh_paths([_entry("first").path])
        self.assertEqual(self.glyph(t, 0), "▶")
        self.assertEqual(self.glyph(t, 1), "■")


class CuedRowTest(_Deck):
    """The first title is cued at startup (loaded, silent) and marked on the
    deck. While planning that row used to show ■ — as if it were running."""

    def cued(self):
        t = self.deck(desk=False)
        t.window().running = False
        t.window().stopped = True
        t.cue_row(0)
        return t

    def test_planning_shows_play_on_a_cued_row(self):
        self.assertEqual(self.glyph(self.cued(), 0), "▶")

    def test_clicking_the_cued_row_starts_it(self):
        t = self.cued()
        t._on_play_click(0, _entry("first").path)
        self.assertEqual(self.played, [Path(r"C:\music\first.mp3")],
                         "a cued title must start, not be unloaded")
        self.assertEqual(t._current_play_row, 0)
        self.assertEqual(self.glyph(t, 0), "■")

    def test_cueing_another_row_moves_the_marker_off_the_old_one(self):
        t = self.deck(desk=False)
        t._on_play_click(0, _entry("first").path)
        t.window().running = False
        t.window().stopped = True
        t.cue_row(1, scroll=False)
        self.assertEqual(t._current_play_row, 1)
        self.assertEqual((self.glyph(t, 0), self.glyph(t, 1)), ("▶", "▶"))

    def test_a_running_preview_keeps_the_stop_square_on_re_render(self):
        t = self.cued()
        t.window().running = True
        t.window().stopped = False
        t._refill_row(0, t._row_meta[0])
        self.assertEqual(self.glyph(t, 0), "■")


class _AwakeOff:
    """Play panel stub: ☀ keep-the-screen-awake switched off."""

    def keep_awake(self):
        return False


class _MixinTest(unittest.TestCase):
    """The desk stripped to `_on_playback_state`: one recording deck, and every
    collaborator the method touches stubbed to something harmless."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtMultimedia import QMediaPlayer
        from player.main_player import PlayerControlMixin
        cls.states = QMediaPlayer.PlaybackState
        cls.Mixin = PlayerControlMixin

    def desk(self):
        seen = []

        class _Table:
            def sync_play_glyph(_self, playing=None):
                seen.append(playing)

        class _Timer:
            def isActive(_self):
                return True

        class _Desk(self.Mixin):
            _all_tables = (_Table(),)
            _fade_timer = _Timer()
            _playback = PlaybackState(dance="WW")
            _big_player = None
            _mix = OutputMix()
            # ☀ The wake lock rides on the same state signal. Nothing here
            # wants the screen held, so it never reaches the OS.
            _play_panel = _AwakeOff()
            _presenter = None
            _awake_held = False

            def _is_player_running(_self):
                return False

            def _is_playing_mode(_self):
                # ↩ marks are a big-player affair; nothing here holds any.
                return False

            def _loudness_gain(_self, path):
                return 1.0

            def _apply_volume(_self):
                pass

        return _Desk(), seen


class PlaybackStateTest(_MixinTest):
    """The player pushes its state to every deck — that is how Space, the
    presenter transport and the card's own ⏯ reach the row glyph."""

    def test_pause_reaches_the_rows(self):
        desk, seen = self.desk()
        desk._on_playback_state(self.states.PausedState)
        self.assertEqual(seen, [False])

    def test_play_reaches_the_rows(self):
        desk, seen = self.desk()
        desk._on_playback_state(self.states.PlayingState)
        self.assertEqual(seen, [True])

    def test_a_stop_is_left_to_the_stop_paths(self):
        """StoppedState also fires on every track switch — the rows would flicker
        to ▶ between two songs; on_playback_stopped clears them properly."""
        desk, seen = self.desk()
        desk._on_playback_state(self.states.StoppedState)
        self.assertEqual(seen, [])


class LoudnessOnResumeTest(_MixinTest):
    """🔊 Equalize volume used to reach only the NEXT title — every resume now
    re-asks the box for the track that is loaded."""

    def desk(self, gain: float = 0.5):
        desk, _ = super().desk()
        applied = []

        class _Card:
            def set_gain(_self, factor):
                applied.append(factor)

        desk._playback.path = Path(r"C:\music\first.mp3")
        desk._big_player = _Card()
        desk._loudness_gain = lambda path: gain
        desk._apply_volume = lambda: applied.append("volume")
        return desk, applied

    def test_a_resume_takes_the_new_setting(self):
        desk, applied = self.desk(gain=0.5)
        desk._on_playback_state(self.states.PlayingState)
        self.assertEqual(desk._mix.gain, 0.5)
        self.assertEqual(desk._mix.gain_target, 0.5)
        self.assertEqual(applied, ["volume", 0.5], "the card's dB readout follows")

    def test_an_unchanged_setting_touches_nothing(self):
        desk, applied = self.desk(gain=1.0)
        desk._on_playback_state(self.states.PlayingState)
        self.assertEqual(applied, [])

    def test_a_pause_leaves_the_level_alone(self):
        """Nothing is coming out — re-levelling belongs at the resume."""
        desk, applied = self.desk(gain=0.5)
        desk._on_playback_state(self.states.PausedState)
        self.assertEqual(applied, [])
        self.assertEqual(desk._mix.gain, 1.0)

    def test_nothing_loaded_is_a_no_op(self):
        desk, applied = self.desk(gain=0.5)
        desk._playback.path = None
        desk._on_playback_state(self.states.PlayingState)
        self.assertEqual(applied, [])


if __name__ == "__main__":
    unittest.main()
