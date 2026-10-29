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
from player.audio.fade_now import FadeNow

_YES = QMessageBox.StandardButton.Yes
_NO = QMessageBox.StandardButton.No


class _QuitCase(unittest.TestCase):

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
        win._fade_now = FadeNow()
        win._quit_after_fade = mock.Mock(return_value=False)   # nothing to fade
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


class QuitWhilePlayingTest(_QuitCase):

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

    def test_music_playing_and_yes_fades_out_before_quitting(self):
        win = self._window(QMediaPlayer.PlaybackState.PlayingState)
        win._quit_after_fade.return_value = True
        event, _ask = self._close(win, _YES)
        self.assertFalse(event.isAccepted())
        win.save_on_quit.assert_not_called()

    def test_the_close_after_the_fade_does_not_ask_again(self):
        win = self._window(QMediaPlayer.PlaybackState.PlayingState)
        win._fade_now.quitting = True
        event, ask = self._close(win)
        ask.assert_not_called()
        self.assertTrue(event.isAccepted())

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


class RestartWhilePlayingTest(_QuitCase):
    """Marcel: a font change, Restart now? Yes, with a title playing — the
    music faded out with the countdown bar, the app closed, and no new one
    started. The close that ran the fade was ignored, so the offer took it as
    the operator backing out; the restart now waits for the close after it."""

    def _offer(self, win, fades):
        def fade():
            if fades and not win._fade_now.quitting:
                win._fade_now.quitting = True
                return True
            return False
        win._quit_after_fade = mock.Mock(side_effect=fade)
        with mock.patch.object(QMessageBox, "question", return_value=_YES), \
                mock.patch.object(dg, "backup_safely"):
            win._offer_restart("🎨 Look", "Restart now?")

    def _close_after_fade(self, win):
        with mock.patch.object(dg, "backup_safely"):
            win.close()

    def test_the_restart_waits_for_the_fade(self):
        win = self._window(QMediaPlayer.PlaybackState.PlayingState)
        with mock.patch("gui.window.main_global.restart_app",
                        return_value=True) as restart, \
                mock.patch.object(QApplication, "quit") as quit_app:
            self._offer(win, fades=True)
            restart.assert_not_called()
            win.save_on_quit.assert_not_called()
            self._close_after_fade(win)
        restart.assert_called_once()
        quit_app.assert_called_once()
        win.save_on_quit.assert_called_once()

    def test_without_a_fade_it_restarts_at_once(self):
        win = self._window()
        with mock.patch("gui.window.main_global.restart_app",
                        return_value=True) as restart, \
                mock.patch.object(QApplication, "quit"):
            self._offer(win, fades=False)
        restart.assert_called_once()

    def test_backing_out_of_the_close_restarts_nothing(self):
        win = self._window(QMediaPlayer.PlaybackState.PlayingState)
        win._quit_after_fade = mock.Mock(return_value=False)
        answers = iter([_YES, _NO])   # restart: yes; stop the music: no
        with mock.patch("gui.window.main_global.restart_app") as restart, \
                mock.patch.object(QMessageBox, "question",
                                  side_effect=lambda *_a, **_k: next(answers)):
            win._offer_restart("🎨 Look", "Restart now?")
        restart.assert_not_called()
        win.save_on_quit.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
