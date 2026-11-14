#!/usr/bin/env python3
"""Closing the window says so when the session could not be written.

Run:  py -m unittest tests.app.test_quit_unsaved -v

save_on_quit dropped the answer of the autosave: a full disk or a scanner
holding the file left the quit looking clean, and everything since the last
good write was gone on the next start without a word.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_quitunsaved_"))

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox

import dancesport_gui as dg
from gui.window.main_persist import PersistenceMixin
from player.audio.fade_now import FadeNow


class SaveOnQuitTest(unittest.TestCase):

    def _bare(self, landed):
        win = PersistenceMixin.__new__(PersistenceMixin)
        win._autosave_playlist = mock.Mock(return_value=landed)
        win._save_layout = mock.Mock()
        win._vol_save_timer = mock.Mock(isActive=mock.Mock(return_value=False))
        return win

    def test_it_hands_back_whether_the_session_landed(self):
        self.assertIs(self._bare(True).save_on_quit(), True)
        self.assertIs(self._bare(False).save_on_quit(), False)

    def test_the_layout_is_still_written_when_the_session_did_not_land(self):
        win = self._bare(False)
        win.save_on_quit()
        win._save_layout.assert_called_once()


class CloseWhenUnsavedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _window(self, landed):
        win = dg.MainWindow.__new__(dg.MainWindow)
        QMainWindow.__init__(win)
        self.addCleanup(win.deleteLater)
        win.save_on_quit = mock.Mock(return_value=landed)
        win._announcer = mock.Mock()
        win._cartwall_shutdown = mock.Mock()
        win._taskbar_shutdown = mock.Mock()
        win._stop_remote = mock.Mock()
        win._controller_shutdown = mock.Mock()
        win._audio_device = mock.Mock()
        win._stop_workers = mock.Mock()
        win._fade_now = FadeNow()
        win._quit_after_fade = mock.Mock(return_value=False)
        return win

    def _close(self, win, answer):
        event = QCloseEvent()
        with mock.patch.object(dg, "backup_safely"), \
                mock.patch.object(dg.QMessageBox, "question",
                                  return_value=answer) as ask:
            win.closeEvent(event)
        return event, ask

    def test_a_session_that_landed_closes_without_asking(self):
        win = self._window(True)
        event, ask = self._close(win, QMessageBox.StandardButton.No)
        ask.assert_not_called()
        win._stop_workers.assert_called_once()

    def test_a_session_that_did_not_land_asks_and_stays_open_on_no(self):
        win = self._window(False)
        event, ask = self._close(win, QMessageBox.StandardButton.No)
        ask.assert_called_once()
        self.assertFalse(event.isAccepted())
        win._stop_workers.assert_not_called()

    def test_staying_open_after_the_quit_fade_is_no_quit_any_more(self):
        """Full review 2026-11-11 #6: the fade had set `quitting`, and it
        stayed set. The pause between two songs then started no next title,
        and the next ✕ skipped "Music is playing" and the fade."""
        win = self._window(False)
        win._fade_now.quitting = True       # ✕ with music: the fade ran
        win._fade_now.restart = "Language"  # ⚙ a restart was asked for
        event, _ask = self._close(win, QMessageBox.StandardButton.No)
        self.assertFalse(event.isAccepted())
        self.assertFalse(win._fade_now.quitting)
        self.assertIsNone(win._fade_now.restart)

    def test_a_session_that_did_not_land_still_closes_on_yes(self):
        win = self._window(False)
        event, ask = self._close(win, QMessageBox.StandardButton.Yes)
        ask.assert_called_once()
        win._stop_workers.assert_called_once()

    def test_a_save_that_raised_does_not_trap_the_window(self):
        win = self._window(None)
        win.save_on_quit = mock.Mock(side_effect=OSError("disk full"))
        event, ask = self._close(win, QMessageBox.StandardButton.No)
        ask.assert_not_called()
        win._stop_workers.assert_called_once()


if __name__ == "__main__":
    unittest.main()
