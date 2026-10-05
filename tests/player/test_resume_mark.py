#!/usr/bin/env python3
"""Tests for the ↩ "remember where a title stopped" marks
(player.main_player: _remember_stop_point / _note_resume / _clear_resume and the
resume seek in _on_media_status).

Run:  py -m unittest tests.player.test_resume_mark -v

One audio player serves every deck, so stepping away from a half-heard title is
the normal way to lose your place in it. The marks live in memory only — for as
long as the app runs — and a title heard to its end loses its mark again. Only
the big player takes them: the floating overlay is for a quick listen.
"""

import os
import tempfile
import unittest
from pathlib import Path
from player.playback_state import PlaybackState
from player.between_dances import BetweenDances

TRACK = Path(r"C:\music\track.mp3")
OTHER = Path(r"C:\music\other.mp3")


def _player_mixin():
    # Same deal as test_silence: gui.dialogs resolves the state files at import
    # time, so import at TEST time and give a standalone run a temp dir.
    os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                          tempfile.mkdtemp(prefix="dp_resume_"))
    from player.main_player import PlayerControlMixin
    return PlayerControlMixin


class _FakePlayer:
    def __init__(self, pos_ms=0, dur_ms=180_000, playing=True):
        from PySide6.QtMultimedia import QMediaPlayer
        self._pos = pos_ms
        self._dur = dur_ms
        self._state = (QMediaPlayer.PlaybackState.PlayingState if playing
                       else QMediaPlayer.PlaybackState.StoppedState)
        self.seeks = []

    def position(self):
        return self._pos

    def duration(self):
        return self._dur

    def playbackState(self):
        return self._state

    def setPosition(self, ms):
        self.seeks.append(ms)
        self._pos = ms


class _FakeTable:
    def __init__(self):
        self.marks = None
        self.stopped = 0

    def sync_play_glyph(self, _playing):
        pass

    def set_resume_marks(self, marks):
        self.marks = dict(marks)

    def on_playback_stopped(self):
        self.stopped += 1


class _FakeBar:
    def __init__(self):
        self.msgs = []

    def showMessage(self, text, *_a):
        self.msgs.append(text)


class _FakeLabel:
    def setText(self, *_a):
        pass


class _FakePanel:
    def pd_editing(self):
        return False

    def keep_awake(self):
        return False

    def pd_highlight_stop(self):
        return False


class _FakeTimer:
    def isActive(self):
        return True


class _FakeWindow:
    """Just enough MainWindow for the ↩ helpers."""

    def __init__(self, remember=True, pos_ms=60_000, dur_ms=180_000, playing=True,
                 big=True):
        self._big = big
        self._player = _FakePlayer(pos_ms, dur_ms, playing)
        self._playback = PlaybackState()
        self._playback.path = TRACK
        self._resume_pos: dict[str, int] = {}
        self._resume_seek_ms = None
        self._playback.offset_ms = 0
        self._settings = {"remember_pos": remember}
        self._preview = None
        self._big_player = None
        self._play_panel = _FakePanel()
        self._now_playing = _FakeLabel()
        self._between = BetweenDances()
        self._between.pending = None
        self._bar = _FakeBar()
        self.table = _FakeTable()
        self._all_tables = (self.table,)
        self._play_ready_logged = True
        self._play_t0 = None
        # …and what `_on_playback_state` walks past on its way to the ↩ line.
        self._fade_timer = _FakeTimer()
        self._presenter = None
        self._awake_held = False
        self._playback.dance = "WW"
        self._pd_stop_at = None

    def statusBar(self):
        return self._bar

    def _is_playing_mode(self):
        return self._big

    # Everything the EndOfMedia branch reaches past the ↩ line.
    def _stop_play_timer(self):
        pass

    def _queue_auto_advance(self):
        pass

    def _show_pause_status(self):
        pass

    def _reset_aux_play_markers(self):
        pass

    def _is_player_running(self):
        return True

    def _refresh_loudness_gain(self):
        pass


class ResumeMarkTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        class Win(_FakeWindow, _player_mixin()):
            pass
        cls.Win = Win

    # ----- taking the mark ----------------------------------------------------

    def test_switching_away_mid_title_keeps_the_spot(self):
        w = self.Win(pos_ms=63_000)
        w._remember_stop_point()
        self.assertEqual(w._resume_pos, {str(TRACK): 63_000})
        self.assertEqual(w.table.marks, {str(TRACK): 63_000})

    def test_the_opening_seconds_are_no_place_to_come_back_to(self):
        # 10 s, the same window in which the player counts a title as heard.
        w = self.Win(pos_ms=8_000)
        w._remember_stop_point()
        self.assertEqual(w._resume_pos, {})

    def test_a_title_stopped_on_its_last_note_counts_as_finished(self):
        w = self.Win(pos_ms=172_000, dur_ms=180_000)
        w._remember_stop_point()
        self.assertEqual(w._resume_pos, {})

    def test_the_floating_overlay_leaves_no_mark(self):
        """Planning means trying a dozen rows for a few seconds each — none of
        them is a title anyone comes back to."""
        w = self.Win(big=False, pos_ms=63_000)
        w._remember_stop_point()
        self.assertEqual(w._resume_pos, {})

    def test_a_late_stop_drops_the_earlier_mark(self):
        w = self.Win(pos_ms=178_000, dur_ms=180_000)
        w._resume_pos[str(TRACK)] = 20_000
        w._remember_stop_point()
        self.assertEqual(w._resume_pos, {})

    def test_nothing_is_noted_while_the_switch_is_off(self):
        w = self.Win(remember=False, pos_ms=63_000)
        w._remember_stop_point()
        self.assertEqual(w._resume_pos, {})

    def test_a_stopped_deck_does_not_wipe_the_mark(self):
        # _load_track is re-entered once the loudness is known; by then the deck
        # is stopped and position() reads 0 — recording that would wipe it.
        w = self.Win(playing=False, pos_ms=0)
        w._resume_pos[str(TRACK)] = 42_000
        w._remember_stop_point()
        self.assertEqual(w._resume_pos, {str(TRACK): 42_000})

    def test_with_nothing_loaded_there_is_nothing_to_note(self):
        w = self.Win(pos_ms=63_000)
        w._playback.path = None
        w._remember_stop_point()
        self.assertEqual(w._resume_pos, {})

    # ----- spending it --------------------------------------------------------

    def test_the_seek_waits_for_the_media_to_open(self):
        from PySide6.QtMultimedia import QMediaPlayer
        w = self.Win()
        w._resume_seek_ms = 63_000
        w._on_media_status(QMediaPlayer.MediaStatus.LoadingMedia)
        self.assertEqual(w._player.seeks, [])
        self.assertEqual(w._resume_seek_ms, 63_000)

    def test_loaded_media_picks_the_title_up(self):
        from PySide6.QtMultimedia import QMediaPlayer
        w = self.Win()
        w._resume_seek_ms = 63_000
        w._on_media_status(QMediaPlayer.MediaStatus.LoadedMedia)
        self.assertEqual(w._player.seeks, [63_000])
        self.assertIsNone(w._resume_seek_ms)     # spent — not again on Buffered
        # The ⏳ timed cut is told to ignore what was skipped, exactly as the
        # 🔇 silence skip does.
        self.assertEqual(w._playback.offset_ms, 63_000)
        self.assertTrue(any("↩" in m for m in w._bar.msgs))

    def test_the_floating_overlay_never_picks_a_title_up(self):
        """A pre-listen starts at the top and leaves the mark where it is."""
        w = self.Win(big=False)
        w._resume_pos[str(TRACK)] = 63_000
        self.assertIsNone(w._resume_mark_for(TRACK))
        self.assertEqual(w._resume_mark_for(OTHER), None)

    def test_the_big_player_picks_the_marked_title_up(self):
        w = self.Win()
        w._resume_pos[str(TRACK)] = 63_000
        self.assertEqual(w._resume_mark_for(TRACK), 63_000)
        self.assertIsNone(w._resume_mark_for(OTHER))

    def test_no_mark_is_spent_while_the_switch_is_off(self):
        w = self.Win(remember=False)
        w._resume_pos[str(TRACK)] = 63_000
        self.assertIsNone(w._resume_mark_for(TRACK))

    def test_loading_a_title_leaves_its_badge_alone(self):
        """A double-click only loads: the playhead parks on the mark, and
        looking at a title must not cost the place in it."""
        from PySide6.QtMultimedia import QMediaPlayer
        w = self.Win()
        w._resume_pos[str(TRACK)] = 63_000
        w._resume_seek_ms = 63_000
        w._on_media_status(QMediaPlayer.MediaStatus.LoadedMedia)
        self.assertEqual(w._player.seeks, [63_000])
        self.assertEqual(w._resume_pos, {str(TRACK): 63_000})

    def test_pressing_play_spends_the_badge(self):
        """The music is running from the mark, so a badge still pointing at it
        names a place already passed."""
        from PySide6.QtMultimedia import QMediaPlayer
        w = self.Win()
        w._resume_pos[str(TRACK)] = 63_000
        w._on_playback_state(QMediaPlayer.PlaybackState.PlayingState)
        self.assertEqual(w._resume_pos, {})
        self.assertEqual(w.table.marks, {})

    def test_the_other_decks_keep_their_marks(self):
        from PySide6.QtMultimedia import QMediaPlayer
        w = self.Win()
        w._resume_pos.update({str(TRACK): 63_000, str(OTHER): 20_000})
        w._on_playback_state(QMediaPlayer.PlaybackState.PlayingState)
        self.assertEqual(w._resume_pos, {str(OTHER): 20_000})

    def test_a_pre_listen_that_starts_keeps_the_badge(self):
        from PySide6.QtMultimedia import QMediaPlayer
        w = self.Win(big=False)
        w._resume_pos[str(TRACK)] = 63_000
        w._on_playback_state(QMediaPlayer.PlaybackState.PlayingState)
        self.assertEqual(w._resume_pos, {str(TRACK): 63_000})

    def test_without_a_mark_the_title_starts_at_the_top(self):
        from PySide6.QtMultimedia import QMediaPlayer
        w = self.Win()
        w._on_media_status(QMediaPlayer.MediaStatus.LoadedMedia)
        self.assertEqual(w._player.seeks, [])
        self.assertEqual(w._playback.offset_ms, 0)

    # ----- losing it ----------------------------------------------------------

    def test_a_title_heard_out_loses_its_mark(self):
        from PySide6.QtMultimedia import QMediaPlayer
        w = self.Win()
        w._resume_pos[str(TRACK)] = 63_000
        w._on_media_status(QMediaPlayer.MediaStatus.EndOfMedia)
        self.assertEqual(w._resume_pos, {})
        self.assertEqual(w.table.marks, {})

    def test_hearing_it_out_in_the_overlay_keeps_the_mark(self):
        """The pre-listen ran the whole title — the place the SET was left at
        is still the place the big player has to come back to."""
        from PySide6.QtMultimedia import QMediaPlayer
        w = self.Win(big=False)
        w._resume_pos[str(TRACK)] = 63_000
        w._on_media_status(QMediaPlayer.MediaStatus.EndOfMedia)
        self.assertEqual(w._resume_pos, {str(TRACK): 63_000})

    def test_switching_the_feature_off_drops_every_mark(self):
        w = self.Win()
        w._resume_pos.update({str(TRACK): 63_000, str(OTHER): 20_000})
        w._set_remember_pos(False)
        self.assertEqual(w._resume_pos, {})
        self.assertEqual(w.table.marks, {})

    def test_switching_it_on_keeps_what_is_there(self):
        w = self.Win()
        w._resume_pos[str(TRACK)] = 63_000
        w._set_remember_pos(True)
        self.assertEqual(w._resume_pos, {str(TRACK): 63_000})


if __name__ == "__main__":
    unittest.main()
