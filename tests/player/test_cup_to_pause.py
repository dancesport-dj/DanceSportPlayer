#!/usr/bin/env python3
"""⏸♪ The cup button fades the title out before the pause.

Run:  py -m unittest tests.player.test_cup_to_pause -v

Marcel: "if i use the [cup] button to get into pause i want the title fade
out before". The button cut the title dead and started the pause; a playing
title now goes down over the 🔉↓ ramp, whose end opens the pause.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_cup_to_pause_"))

from PySide6.QtMultimedia import QMediaPlayer

from player.audio.between_dances import BetweenDances
from player.audio.playback_state import PlaybackState
from player.window.main_pause import PauseMusicMixin


class _Player:
    def __init__(self, state):
        self.state = state

    def playbackState(self):
        return self.state


class _Bar:
    def showMessage(self, text, ms):
        pass


class _Desk:
    _on_to_pause = PauseMusicMixin._on_to_pause

    def __init__(self, state=QMediaPlayer.PlaybackState.PlayingState):
        self._between = BetweenDances()
        self._playback = PlaybackState()
        self._playback.path = Path(r"C:\music\LW.mp3")
        self._player = _Player(state)
        self.calls = []

    def _is_playing_mode(self):
        return True

    def _fade_out_now(self):
        self.calls.append("fade")

    def _on_timed_end(self):
        self.calls.append("cut")
        self._between.pending = ("table", 1, "next")

    def statusBar(self):
        return _Bar()


class CupToPauseTest(unittest.TestCase):

    def test_a_playing_title_fades_out_first(self):
        desk = _Desk()
        desk._on_to_pause()
        self.assertEqual(desk.calls, ["fade"])

    def test_a_held_title_goes_into_the_pause_at_once(self):
        # ⏯-paused: nothing is heard, so there is nothing to fade.
        desk = _Desk(QMediaPlayer.PlaybackState.PausedState)
        desk._on_to_pause()
        self.assertEqual(desk.calls, ["cut"])

    def test_in_the_pause_already_it_does_nothing(self):
        desk = _Desk()
        desk._between.pending = ("table", 1, "next")
        desk._on_to_pause()
        self.assertEqual(desk.calls, [])


if __name__ == "__main__":
    unittest.main()
