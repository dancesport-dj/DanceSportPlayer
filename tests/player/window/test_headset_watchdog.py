#!/usr/bin/env python3
"""The load watchdog leaves a play that the headset question is holding alone.

Run:  .venv/Scripts/python.exe -m unittest tests.player.window.test_headset_watchdog -v
"""
import unittest
from unittest import mock

from PySide6.QtMultimedia import QMediaPlayer

from player.window import main_load
from player.window.main_load import TrackLoadMixin


def _host(asking):
    host = mock.Mock()
    host._playback.token = 1
    host._player.playbackState.return_value = QMediaPlayer.PlaybackState.StoppedState
    host._player.mediaStatus.return_value = QMediaPlayer.MediaStatus.LoadedMedia
    vars(host)["_headset_asking"] = asking
    return host


class WatchdogTest(unittest.TestCase):
    def check(self, host):
        with mock.patch.object(main_load.QTimer, "singleShot") as single:
            TrackLoadMixin._check_playback(host, 1, mock.Mock(name="path"))
        return single

    def test_a_play_held_for_the_question_is_not_reloaded(self):
        for flag in ("_headset_asking", "_headset_dialog"):
            host = _host(False)
            vars(host)[flag] = True
            single = self.check(host)
            host._player.stop.assert_not_called()
            host._player.setSource.assert_not_called()
            host._player.play.assert_not_called()
            single.assert_called_once()          # looks again later

    def test_a_really_stuck_play_is_still_reloaded(self):
        host = _host(False)
        self.check(host)
        host._player.setSource.assert_called()
        host._player.play.assert_called_once()


if __name__ == "__main__":
    unittest.main()
