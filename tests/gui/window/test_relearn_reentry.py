"""📜 Re-learn playlists runs once at a time.

Run:  py -m unittest tests.gui.window.test_relearn_reentry -v

The busy dialog only shows after 200 ms, so a second click could start a
second worker on the same library. It is refused while one runs.
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_relearn_reentry_"))

from PySide6.QtWidgets import QApplication, QMainWindow

import dancesport_gui as dg
from gui.window import main_global
from gui.window.library_service import LibraryService


class RelearnReentryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_a_second_click_while_one_runs_starts_nothing(self):
        win = dg.MainWindow.__new__(dg.MainWindow)
        QMainWindow.__init__(win)
        self.addCleanup(win.deleteLater)
        win._library = LibraryService()
        win._library.lib = mock.Mock()
        worker = mock.Mock()
        worker.isRunning.return_value = True
        with mock.patch.object(main_global, "BusyDialog"), \
             mock.patch.object(main_global, "PlaylistRelearnWorker",
                               return_value=worker) as make:
            win._relearn_playlists()
            win._relearn_playlists()
        self.assertEqual(make.call_count, 1)
        worker.start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
