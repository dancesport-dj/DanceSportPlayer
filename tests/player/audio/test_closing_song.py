#!/usr/bin/env python3
"""🌙 The closing song after the planned ⏹ stop.

Run:  py -m unittest tests.player.audio.test_closing_song -v

Item 26: once the stop has ended the music, one more title plays — "Who
moved the clock today" — at the music's level and to its end. The title the
stop put under the cursor keeps waiting and is cued for ⏯ when it is over.
Set on the ▶ panel under the ⏹ row, and saved.
"""
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtMultimedia import QMediaPlayer

from player.audio.between_dances import BetweenDances
from player.audio.fade_now import FadeNow
from player.audio.playback_state import PlaybackState
from player.widgets.play_mode_panel import PlayModePanel
from player.window.main_load import TrackLoadMixin
from tests.player.audio.test_repeat_list import _Fixture
from tests.qt_test_support import reap_widget


def _closing_file(test) -> Path:
    fd, name = tempfile.mkstemp(suffix=".mp3", prefix="dp_closing_")
    os.close(fd)
    test.addCleanup(os.remove, name)
    return Path(name)


class ClosingRowTest(_Fixture):
    """The row under ⏹ Stop."""

    def panel(self, **settings) -> PlayModePanel:
        p = PlayModePanel(settings)
        self.addCleanup(reap_widget, p)
        p.show()
        return p

    def choose(self, p, mode):
        p.stop_combo.setCurrentIndex(p.stop_combo.findData(mode))

    def test_none_unless_set(self):
        p = self.panel(auto_advance=True)
        self.assertEqual(p.closing_song(), "")
        self.assertEqual(p.closing_lbl.text(), "none")

    def test_the_saved_song_comes_back(self):
        p = self.panel(auto_advance=True, closing_song=r"C:\music\clock.mp3")
        self.assertEqual(p.closing_song(), r"C:\music\clock.mp3")
        self.assertEqual(p.closing_lbl.text(), "clock")

    def test_it_shows_only_while_a_stop_is_armed(self):
        p = self.panel(auto_advance=True)
        self.assertFalse(p.closing_box.isVisible())
        self.choose(p, "this")
        self.assertTrue(p.closing_box.isVisible())
        p.advance_check.setChecked(False)
        self.assertFalse(p.closing_box.isVisible())
        p.advance_check.setChecked(True)
        self.choose(p, "never")
        self.assertFalse(p.closing_box.isVisible())

    def test_a_spent_rule_takes_it_off(self):
        p = self.panel(auto_advance=True)
        self.choose(p, "this")
        self.assertTrue(p.stop_title_ended(datetime.now()))
        self.assertFalse(p.closing_box.isVisible())

    def test_a_change_is_saved_and_the_cross_clears_it(self):
        p = self.panel(auto_advance=True, closing_song=r"C:\music\clock.mp3")
        saved = []
        p.settingsChanged.connect(lambda: saved.append(1))
        p._set_closing_song("")
        self.assertEqual(p.closing_song(), "")
        self.assertEqual(p.closing_lbl.text(), "none")
        self.assertEqual(saved, [1])


class ClosingEngineTest(_Fixture):
    """What the planned stop and the ends after it do with the song."""

    def stopping_deck(self, closing: str):
        desk = self.deck(closing_song=closing)
        self.rows = self.song_rows()
        self.table._current_play_row = self.rows[0]
        p = desk._play_panel
        p.stop_combo.setCurrentIndex(p.stop_combo.findData("this"))
        self.loads = []
        desk._play_or_stop = lambda path, start=True: self.loads.append((path, start))
        return desk

    def test_the_stop_queues_the_song_and_keeps_the_next_title(self):
        song = _closing_file(self)
        desk = self.stopping_deck(str(song))
        desk._queue_auto_advance()
        self.assertEqual(desk._between.closing, song)
        self.assertIsNone(desk._between.pending)
        cued = desk._between.cue_next
        assert cued is not None
        self.assertEqual(cued[1], self.rows[1])

    def test_the_cue_plays_the_song_not_the_next_title(self):
        song = _closing_file(self)
        desk = self.stopping_deck(str(song))
        desk._queue_auto_advance()
        desk._cue_next_song()
        self.assertEqual(self.loads, [(song, True)])
        self.assertEqual(desk._playback.closing, song)
        self.assertIsNone(desk._between.closing)
        self.assertIsNotNone(desk._between.cue_next)

    def test_its_end_cues_the_waiting_title(self):
        song = _closing_file(self)
        desk = self.stopping_deck(str(song))
        desk._queue_auto_advance()
        desk._cue_next_song()
        desk._playback.path = song   # the load the stub only recorded
        self.loads.clear()
        desk._queue_auto_advance()   # …the song has ended
        self.assertIsNone(desk._playback.closing)
        self.assertIsNone(desk._between.pending)
        desk._cue_next_song()
        self.assertEqual(len(self.loads), 1)
        path, start = self.loads[0]
        self.assertFalse(start)
        self.assertEqual(path, self.table._row_meta[self.rows[1]].entry.path)

    def test_a_missing_file_stops_as_before(self):
        desk = self.stopping_deck(r"Z:\nowhere\clock.mp3")
        desk._queue_auto_advance()
        self.assertIsNone(desk._between.closing)
        desk._cue_next_song()
        self.assertEqual(len(self.loads), 1)
        self.assertFalse(self.loads[0][1])

    def test_without_a_song_it_stops_as_before(self):
        desk = self.stopping_deck("")
        desk._queue_auto_advance()
        self.assertIsNone(desk._between.closing)

    def test_the_song_plays_in_full(self):
        """F11: the song kept the play length of the title before it (a
        cha-cha's), so the card drew that title's cut and fade marks."""
        song = _closing_file(self)
        desk = self.stopping_deck(str(song))
        self.assertGreater(desk._play_limit_secs(), 0)
        desk._playback.closing = desk._playback.path = song
        desk._playback.dance = ""
        self.assertEqual(desk._play_limit_secs(), 0)
        self.assertEqual(desk._play_end_secs(), 0)

    def test_an_end_that_does_not_stop_plays_no_song(self):
        song = _closing_file(self)
        desk = self.stopping_deck(str(song))
        p = desk._play_panel
        p.stop_combo.setCurrentIndex(p.stop_combo.findData("never"))
        desk._queue_auto_advance()
        self.assertIsNone(desk._between.closing)
        self.assertIsNotNone(desk._between.pending)


class _TickPlayer:
    """Just enough media player for the play tick."""

    def playbackState(self):
        return QMediaPlayer.PlaybackState.PlayingState

    def position(self):
        return 30_000

    def duration(self):
        return 90_000

    def playbackRate(self):
        return 1.0


class ClosingTickTest(unittest.TestCase):
    """The play tick while the song is on the deck."""

    def desk(self, song: Path):
        from player.window.main_player import PlayerControlMixin

        class Desk(PlayerControlMixin):
            def __init__(self):
                self._player = _TickPlayer()
                self._playback = PlaybackState(path=song, closing=song)
                self._between = BetweenDances()
                self._fade_now = FadeNow()
                self._played_marked = False
                self._mix = SimpleNamespace(fade=0.2)
                self.countdowns = []
                self.on_air = []

            def _maybe_skip_silence(self):
                return False

            def _watch_stall(self):
                return False

            def _step_fade_in(self):
                pass

            def _is_playing_mode(self):
                return True

            def _apply_volume(self):
                pass

            def _set_countdown(self, text):
                self.countdowns.append(text)

            def _note_on_air(self):
                self.on_air.append(True)

        return Desk()

    def test_it_plays_at_the_music_level_to_its_end(self):
        desk = self.desk(Path(r"C:\music\clock.mp3"))
        desk._on_play_tick()
        self.assertEqual(desk._mix.fade, 1.0)
        self.assertEqual(desk.countdowns, ["🌙  1:00"])
        self.assertEqual(desk.on_air, [])
        self.assertFalse(desk._played_marked)

    def test_another_title_on_the_deck_is_not_it(self):
        desk = self.desk(Path(r"C:\music\clock.mp3"))
        desk._playback.path = Path(r"C:\music\ww.mp3")
        self.assertFalse(desk._closing_tick())


class ClosingAdoptTest(unittest.TestCase):
    """The deck takes the song on: no dance, so no call, length or Paso stop."""

    def desk(self):
        class Desk(TrackLoadMixin):
            def __init__(self):
                self._playback = PlaybackState()
                self._between = BetweenDances()
                self._play_panel = SimpleNamespace(set_pd_loaded=lambda on: None)

            def _resolve_entry(self, path):
                return None

            def _row_dance(self, path):
                return "WW"

            def _sync_dance_len(self):
                pass

            def _resume_mark_for(self, path: Path) -> int | None:
                return None

            def _pre_roll_ms_for(self, path: Path) -> int:
                return 0

            def _refresh_resume_marks(self, path: Path | None = None):
                pass

            def _sync_taskbar_title(self):
                pass

        return Desk()

    def test_the_song_has_no_dance(self):
        desk = self.desk()
        song = Path(r"C:\music\clock.mp3")
        desk._playback.closing = song
        desk._adopt_track(song)
        self.assertEqual(desk._playback.dance, "")
        self.assertEqual(desk._playback.closing, song)

    def test_the_next_title_ends_it(self):
        desk = self.desk()
        desk._playback.closing = Path(r"C:\music\clock.mp3")
        desk._adopt_track(Path(r"C:\music\ww.mp3"))
        self.assertIsNone(desk._playback.closing)
        self.assertEqual(desk._playback.dance, "WW")


if __name__ == "__main__":
    unittest.main()
