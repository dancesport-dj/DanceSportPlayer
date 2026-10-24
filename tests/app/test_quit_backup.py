#!/usr/bin/env python3
"""Closing the app writes the day's user-data backup again.

Run:  py -m unittest tests.app.test_quit_backup -v

The backup at start holds the state from BEFORE the session, so an
evening's play log would wait for the next start to be backed up. Closing
the window refreshes today's backup — after the workers have stopped, so
nothing is still writing to the DB while it is copied.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_quitbackup_"))

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMainWindow

import dancesport_gui as dg
from player.audio.fade_now import FadeNow


class QuitBackupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_closing_refreshes_the_backup_after_the_workers_stop(self):
        # A bare window: only what closeEvent touches, no library load.
        win = dg.MainWindow.__new__(dg.MainWindow)
        QMainWindow.__init__(win)
        self.addCleanup(win.deleteLater)
        order = mock.Mock()
        win.save_on_quit = mock.Mock()
        win._announcer = mock.Mock()
        win._cartwall_shutdown = mock.Mock()
        win._taskbar_shutdown = mock.Mock()
        win._stop_remote = mock.Mock()
        win._controller_shutdown = mock.Mock()
        win._audio_device = mock.Mock()
        win._stop_workers = order.stop_workers
        win._fade_now = FadeNow()
        win._quit_after_fade = mock.Mock(return_value=False)   # nothing to fade
        with mock.patch.object(dg, "backup_safely", order.backup_safely):
            win.closeEvent(QCloseEvent())
        self.assertEqual(order.mock_calls,
                         [mock.call.stop_workers(), mock.call.backup_safely(refresh=True)])


if __name__ == "__main__":
    unittest.main()
