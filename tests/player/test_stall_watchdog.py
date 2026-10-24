#!/usr/bin/env python3
"""A title that stops moving while the player says it plays is rescued.

Run:  .venv\\Scripts\\python.exe -m unittest tests.player.test_stall_watchdog -v

A decoder hang or an output device that went away left the player in
PlayingState with the position standing still: the card said ▶, the floor
heard nothing, and nothing ever ended the title. The tick now watches the
position. Five seconds without a move reload the title where it stood and
tell the operator; a second stall of the same title gives up on it like any
title that would not play, which skips to the next one in a running round.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_stall_"))

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication
from tests.qt_test_support import reap_widget

from player.window import main_player
from tests.player.audio.test_fade_indicator import _Desk

PLAYING = QMediaPlayer.PlaybackState.PlayingState


class _Media:
    def __init__(self):
        self.pos = 0
        self.calls = []

    def playbackState(self):
        return PLAYING

    def position(self):
        return self.pos

    def stop(self):
        self.calls.append("stop")

    def setSource(self, url):
        self.calls.append(url)

    def play(self):
        self.calls.append("play")


class _StallDesk(_Desk):
    def __init__(self):
        super().__init__()
        self._player = _Media()
        self._resume_seek_ms = None
        self.failed = []

    def _is_playing_mode(self):
        return False      # the tick ends after the watchdog and the fades

    def _playback_failed(self, path, reason, message):
        self.failed.append((path, reason))


class StallWatchdogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.desk = _StallDesk()
        self.addCleanup(reap_widget, self.desk)
        self.now = 100.0
        clock = mock.patch.object(main_player.time, "monotonic",
                                  side_effect=lambda: self.now)
        toast = mock.patch.object(main_player, "_show_toast")
        clock.start()
        self.toast = toast.start()
        self.addCleanup(clock.stop)
        self.addCleanup(toast.stop)
        self.desk._player.pos = 83_000

    def tick_after(self, secs):
        self.now += secs
        self.desk._on_play_tick()

    def test_a_moving_title_is_left_alone(self):
        for _ in range(40):
            self.desk._player.pos += 200
            self.tick_after(0.2)
        self.assertEqual(self.desk._player.calls, [])
        self.toast.assert_not_called()

    def test_a_short_halt_is_not_a_stall(self):
        self.tick_after(0.2)
        self.tick_after(4.0)
        self.assertEqual(self.desk._player.calls, [])

    def test_a_stalled_title_is_reloaded_where_it_stood(self):
        self.tick_after(0.2)
        self.tick_after(5.0)
        path = self.desk._playback.path
        self.assertEqual(self.desk._player.calls,
                         ["stop", QUrl(), QUrl.fromLocalFile(str(path)), "play"])
        self.assertEqual(self.desk._resume_seek_ms, 83_000)
        self.toast.assert_called_once()
        self.assertEqual(self.desk.failed, [])

    def test_the_reload_keeps_the_heard_time(self):
        # _on_media_status books the resume seek as skipped ground; the stalled
        # part was heard, so the ⏳ play length must not start over.
        self.desk._playback.offset_ms = 2_000
        self.tick_after(0.2)
        self.tick_after(5.0)
        self.assertEqual(self.desk._playback.offset_ms
                         + self.desk._resume_seek_ms, 2_000)

    def test_a_second_stall_gives_the_title_up(self):
        self.tick_after(0.2)
        self.tick_after(5.0)
        self.desk._player.pos = 0      # the reload never got going
        self.tick_after(0.2)
        self.tick_after(5.0)
        self.assertEqual(self.desk.failed,
                         [(self.desk._playback.path, "stalled")])

    def test_a_new_title_gets_its_own_reload(self):
        self.tick_after(0.2)
        self.tick_after(5.0)
        self.desk._playback.token += 1   # the next title loaded
        self.desk._player.calls.clear()
        self.tick_after(0.2)
        self.tick_after(5.0)
        self.assertIn("play", self.desk._player.calls)
        self.assertEqual(self.desk.failed, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
