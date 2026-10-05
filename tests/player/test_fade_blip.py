#!/usr/bin/env python3
"""A fade never ends in a blip at full volume.

Run:  .venv\\Scripts\\python.exe -m unittest tests.player.test_fade_blip -v

The 🛑 panic fade paused the song at silence and then put the output straight
back to the full level, so ⏯ would resume at the normal volume. ⏹ and the end
of a 🔉↓ fade did the same through `_stop_play_timer`, before the stop. On the
Windows backend pause() and stop() land asynchronously: whatever audio was
still buffered came out at full level — a short "blipp" right after the fade.

The level now stays where the ramp left it until the song runs again, and the
start of playback puts it back, whoever pressed ⏯.
"""

import os
import tempfile
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_blip_"))

from PySide6.QtMultimedia import QMediaPlayer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from tests.player.test_fade_indicator import _Desk  # noqa: E402

PLAYING = QMediaPlayer.PlaybackState.PlayingState


class _LoggedMedia:
    def __init__(self, log):
        self.log = log

    def playbackState(self):
        return PLAYING

    def pause(self):
        self.log.append("pause")

    def stop(self):
        self.log.append("stop")


class _LoggedDesk(_Desk):
    """Every level pushed to the output goes into one log with the player
    calls, so the test can read what the hall heard, in order."""

    def __init__(self):
        super().__init__()
        self.log = []
        self._player = _LoggedMedia(self.log)
        self._playback.dance = "WW"

    def _apply_volume(self):
        self.log.append(round(self._mix.deck(), 2))

    def _refresh_wake_lock(self):
        pass

    def _refresh_loudness_gain(self):
        pass

    def _clear_resume(self, path):
        pass

    def pushed_after(self, call):
        return [v for v in self.log[self.log.index(call) + 1:]
                if not isinstance(v, str)]


class FadeBlipTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.desk = _LoggedDesk()
        self.addCleanup(reap_widget, self.desk)

    def ramp_to_the_end(self):
        self.desk._fade_now_end = time.monotonic() + 0.2   # the last tick of it
        self.desk._on_play_tick()
        self.desk._fade_now_end = time.monotonic() - 0.1
        self.desk._on_play_tick()

    def test_the_panic_hold_does_not_turn_the_paused_song_back_up(self):
        self.desk._fade_and_hold()
        self.ramp_to_the_end()
        self.assertIn("pause", self.desk.log)
        self.assertEqual(self.desk.pushed_after("pause"), [])

    def test_resuming_after_the_hold_plays_at_the_full_level(self):
        self.desk._fade_and_hold()
        self.ramp_to_the_end()
        self.desk._on_playback_state(PLAYING)
        self.assertEqual(self.desk.log[-1], 1.0)

    def test_stopping_mid_fade_does_not_raise_the_running_song(self):
        """⏹ and the end of 🔉↓ halt the engine BEFORE the stop reaches the
        player — a level pushed there is heard."""
        self.desk._fade_out_now()
        self.desk._fade_now_end = time.monotonic() + 0.3
        self.desk._on_play_tick()
        quiet = self.desk.log[-1]
        self.assertLess(quiet, 1.0)
        self.desk.log.append("halt")
        self.desk._stop_play_timer()
        self.assertTrue(all(v <= quiet for v in self.desk.pushed_after("halt")))

    def test_the_next_start_is_at_the_full_level(self):
        self.desk._fade_out_now()
        self.desk._fade_now_end = time.monotonic() + 0.3
        self.desk._on_play_tick()
        self.desk._stop_play_timer()
        self.desk._on_playback_state(PLAYING)
        self.assertEqual(self.desk.log[-1], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
