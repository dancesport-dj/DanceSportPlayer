#!/usr/bin/env python3
"""Closing the window while music plays asks first.

Run:  py -m unittest tests.app.test_quit_while_playing -v

Closing used to stop the music on the floor without a word: one stray click on
the window's ✕ in the middle of a final. With music playing the close now asks,
and No leaves everything running: nothing is saved, nothing shuts down.
"""

import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QCloseEvent
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox

import dancesport_gui as dg

_YES = QMessageBox.StandardButton.Yes
_NO = QMessageBox.StandardButton.No


class QuitWhilePlayingTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _window(self, state=None):
        # A bare window: only what closeEvent touches, no library load.
        win = dg.MainWindow.__new__(dg.MainWindow)
        QMainWindow.__init__(win)
        self.addCleanup(win.deleteLater)
        win.save_on_quit = mock.Mock()
        win._announcer = mock.Mock()
        win._cartwall_shutdown = mock.Mock()
        win._taskbar_shutdown = mock.Mock()
        win._stop_remote = mock.Mock()
        win._controller_shutdown = mock.Mock()
        win._audio_device = mock.Mock()
        win._stop_workers = mock.Mock()
        if state is not None:
            win._player = mock.Mock()
            win._player.playbackState.return_value = state
        return win

    def _close(self, win, answer=None):
        event = QCloseEvent()
        with mock.patch.object(QMessageBox, "question", return_value=answer) as ask, \
                mock.patch.object(dg, "backup_safely"):
            win.closeEvent(event)
        return event, ask

    def test_music_playing_and_no_keeps_the_app_running(self):
        win = self._window(QMediaPlayer.PlaybackState.PlayingState)
        event, ask = self._close(win, _NO)
        ask.assert_called_once()
        self.assertFalse(event.isAccepted())
        win.save_on_quit.assert_not_called()
        win._stop_workers.assert_not_called()

    def test_music_playing_and_yes_quits(self):
        win = self._window(QMediaPlayer.PlaybackState.PlayingState)
        event, ask = self._close(win, _YES)
        ask.assert_called_once()
        self.assertTrue(event.isAccepted())
        win.save_on_quit.assert_called_once()

    def test_paused_or_stopped_quits_without_asking(self):
        for state in (QMediaPlayer.PlaybackState.PausedState,
                      QMediaPlayer.PlaybackState.StoppedState):
            win = self._window(state)
            event, ask = self._close(win)
            ask.assert_not_called()
            self.assertTrue(event.isAccepted())

    def test_a_window_without_a_player_quits_without_asking(self):
        win = self._window()
        event, ask = self._close(win)
        ask.assert_not_called()
        self.assertTrue(event.isAccepted())


if __name__ == "__main__":
    unittest.main(verbosity=2)
