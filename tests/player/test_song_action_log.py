#!/usr/bin/env python3
"""📜 The session log says what the operator did with a song.

Run:  py -m unittest tests.player.test_song_action_log -v

A show that went wrong is reconstructed from the log. "Song ended" was there,
but not how it came to that: a pause, a fade out and how long it ran, a skip,
a repeat. One line each, with the file and where the title stood.
"""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_actionlog_"))

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

from player.audio.fade_now import FadeNow
from player.window.main_player import PlayerControlMixin, log_song_action

LOGGER = "dancesport.gui.player"
_PLAYING = QMediaPlayer.PlaybackState.PlayingState
_PAUSED = QMediaPlayer.PlaybackState.PausedState


class _Player:
    def __init__(self, state=_PLAYING):
        self.state = state

    def position(self):
        return 61_000

    def duration(self):
        return 180_000

    def playbackState(self):
        return self.state


def _host(**more):
    host = SimpleNamespace(
        _playback=SimpleNamespace(path=Path("C:/music/waltz.mp3"), stall_seen=None),
        _player=_Player(),
        _fade_now=FadeNow(),
        _settings={},
        _mix=SimpleNamespace(fade=1.0),
        _fade_timer=SimpleNamespace(start=lambda: None),
        _pv=lambda key: 3.0,
        _celebrating=lambda: False,
        _set_fade_indicator=lambda on: None,
    )
    for k, v in more.items():
        setattr(host, k, v)
    return host


class SongActionLogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_a_line_names_the_action_the_file_and_the_place(self):
        with self.assertLogs(LOGGER, level="INFO") as seen:
            log_song_action(_host(), "⏸ Song paused")
        text = seen.records[0].getMessage()
        self.assertTrue(text.startswith("⏸ Song paused\n"), text)
        self.assertIn("file: waltz.mp3", text)
        self.assertIn("position: 01:01.000 / 03:00.000", text)

    def test_the_position_keeps_its_milliseconds(self):
        from player.window.main_player import fmt_clock
        self.assertEqual(fmt_clock(32_706), "00:32.706")
        self.assertEqual(fmt_clock(241_841), "04:01.841")
        self.assertEqual(fmt_clock(0), "00:00.000")
        self.assertEqual(fmt_clock(3_723_004), "1:02:03.004")
        self.assertEqual(fmt_clock(-1), "00:00.000")

    def test_extra_lines_come_below(self):
        with self.assertLogs(LOGGER, level="INFO") as seen:
            log_song_action(_host(), "🔉 Fade out", "fade: 3.0s")
        self.assertTrue(seen.records[0].getMessage().endswith("\nfade: 3.0s"))

    def test_a_fade_out_says_how_long_it_runs(self):
        host = _host()
        with self.assertLogs(LOGGER, level="INFO") as seen:
            PlayerControlMixin._fade_out_now(host)
        text = seen.records[0].getMessage()
        self.assertIn("🔉 Fade out", text)
        self.assertIn("fade: 3.0s", text)

    def test_a_fade_out_that_does_not_start_logs_nothing(self):
        host = _host(_player=_Player(_PAUSED))
        with self.assertNoLogs(LOGGER, level="INFO"):
            PlayerControlMixin._fade_out_now(host)

    def test_a_skip_names_the_step(self):
        host = _host(_announcer=SimpleNamespace(stop=lambda: None),
                     _deckset=SimpleNamespace(all_tables=[]),
                     _event_compare=None,
                     _lib_browser=SimpleNamespace(skip=lambda step: None))
        with self.assertLogs(LOGGER, level="INFO") as seen:
            PlayerControlMixin._preview_skip(host, -1)
        text = seen.records[0].getMessage()
        self.assertTrue(text.startswith("⏭ Song skipped\n"), text)
        self.assertIn("step: -1", text)

    def test_pause_and_play_are_logged(self):
        host = _host(
            _xfade_follow=lambda s: None, _refresh_wake_lock=lambda: None,
            _stop_background_analysis=lambda: None,
            _deckset=SimpleNamespace(all_tables=[]),
            _fade_now=SimpleNamespace(freeze=lambda: None, thaw=lambda: None),
            _clear_resume=lambda p: None, _is_playing_mode=lambda: False,
            _level_owed=False, _refresh_loudness_gain=lambda: None,
            _fade_timer=SimpleNamespace(isActive=lambda: True),
            _cued=False, _pd_stop_at=None)
        host._playback.dance = ""
        with self.assertLogs(LOGGER, level="INFO") as seen:
            PlayerControlMixin._on_playback_state(host, _PAUSED)
            PlayerControlMixin._on_playback_state(host, _PLAYING)
        first, second = (r.getMessage() for r in seen.records)
        self.assertTrue(first.startswith("⏸ Song paused"), first)
        self.assertTrue(second.startswith("▶ Song playing"), second)

    def _state_host(self, **more):
        host = _host(
            _xfade_follow=lambda s: None, _refresh_wake_lock=lambda: None,
            _stop_background_analysis=lambda: None,
            _deckset=SimpleNamespace(all_tables=[]),
            _clear_resume=lambda p: None, _is_playing_mode=lambda: False,
            _level_owed=False, _refresh_loudness_gain=lambda: None,
            _fade_timer=SimpleNamespace(isActive=lambda: True),
            _cued=False, _pd_stop_at=None, **more)
        host._playback.dance = ""
        return host

    def _logged(self, host, state):
        with self.assertLogs(LOGGER, level="INFO") as seen:
            PlayerControlMixin._on_playback_state(host, state)
        return seen.records[0].getMessage()

    def test_without_a_fade_the_line_says_so(self):
        text = self._logged(self._state_host(), _PAUSED)
        self.assertIn("\nfade: none", text)

    def test_a_running_fade_in_is_named_with_its_length_and_level(self):
        host = self._state_host(_mix=SimpleNamespace(fade=1.0, fade_in=0.4))
        host._playback.fade_in_from = 0.0
        host._playback.fade_in_secs = 3.0
        text = self._logged(host, _PAUSED)
        self.assertIn("\nfade in: 3.0s, 40% up", text)
        self.assertNotIn("fade: none", text)

    def test_a_running_crossfade_is_named_not_reported_as_no_fade(self):
        """The title a crossfade brings in starts inside it: "fade: none" there
        read as if the crossfade had not happened."""
        host = self._state_host(_mix=SimpleNamespace(fade=1.0, fade_in=0.4),
                                _between=SimpleNamespace(xfade=SimpleNamespace(
                                    state="fading", length=6.0, paused_at=None)))
        text = self._logged(host, _PLAYING)
        self.assertIn("\ncrossfade: 6.0s, 40% in", text)
        self.assertNotIn("fade: none", text)

    def test_an_idle_crossfade_leaves_the_no_fade_line(self):
        host = self._state_host(_between=SimpleNamespace(xfade=SimpleNamespace(
            state=None, length=0.0, paused_at=None)))
        self.assertIn("\nfade: none", self._logged(host, _PAUSED))

    def test_a_running_fade_out_is_named_with_what_is_left(self):
        host = self._state_host()
        host._fade_now.start(4.0)
        text = self._logged(host, _PAUSED)
        self.assertIn("\nfade out: 4.0s, ", text)
        self.assertIn("s left", text)

    def test_a_pause_inside_a_fade_out_reads_what_was_frozen(self):
        """freeze() runs after the line is written, so the left time is live."""
        host = self._state_host()
        host._fade_now.start(4.0)
        text = self._logged(host, _PLAYING)
        self.assertIn("fade out: 4.0s", text)

    def test_the_taskbar_caption_stays_out_of_the_log_when_it_worked(self):
        from player.widgets import taskbar
        bar = SimpleNamespace(
            _title="", _added=True, _tb=object(), _hwnd=object(),
            _w32=SimpleNamespace(set_thumbnail_tooltip=lambda *a: 0))
        with self.assertNoLogs(level="INFO"):
            taskbar.TaskbarPlayer.set_title(bar, "106 JI The Cast")

    def test_a_refused_taskbar_caption_still_shows(self):
        from player.widgets import taskbar
        bar = SimpleNamespace(
            _title="", _added=True, _tb=object(), _hwnd=object(),
            _w32=SimpleNamespace(set_thumbnail_tooltip=lambda *a: 0x80004005))
        with self.assertLogs(level="WARNING") as seen:
            taskbar.TaskbarPlayer.set_title(bar, "106 JI The Cast")
        self.assertIn("0x80004005", seen.records[0].getMessage())


if __name__ == "__main__":
    unittest.main(verbosity=2)
