#!/usr/bin/env python3
"""Tests for an autosave write that does not land.

Run:  py -m unittest tests.gui.test_autosave_failure -v

📌 said "Session saved" whatever the write did, so a full disk or a file held
open by a scanner left the operator believing the session was safe.
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_autosavefail_"))

from PySide6.QtWidgets import QApplication

import dancesport_gui as gui
from gui import dialogs
from gui.window import main_persist
from tests.qt_test_support import reap_widget


class SaveAutosaveResultTest(unittest.TestCase):

    def test_it_reports_a_write_that_did_not_land(self):
        with mock.patch.object(dialogs.AUTOSAVE, "write", return_value=False), \
                mock.patch.object(dialogs, "_rotate_autosave_backups"):
            self.assertFalse(dialogs.save_autosave({"version": 4}))

    def test_it_reports_a_write_that_landed(self):
        with mock.patch.object(dialogs.AUTOSAVE, "write", return_value=True), \
                mock.patch.object(dialogs, "_rotate_autosave_backups"):
            self.assertTrue(dialogs.save_autosave({"version": 4}))


class SaveStateNowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        patcher = mock.patch.object(gui, "load_settings",
                                    lambda *a, **kw: {"app_mode": "both"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.win = gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        # Something worth saving, so _autosave_playlist really writes.
        self.win._build_env = lambda: {"version": 4, "day_tab_keep": "x"}
        toast = mock.patch.object(main_persist, "show_toast")
        self.toast = toast.start()
        self.addCleanup(toast.stop)

    def _press_pin(self, landed):
        with mock.patch.object(main_persist, "save_autosave",
                               return_value=landed):
            self.win._save_state_now()

    def test_a_write_that_landed_is_announced(self):
        self._press_pin(True)
        self.assertIn("Session saved", self.win.statusBar().currentMessage())

    def test_a_write_that_failed_is_not_announced_as_saved(self):
        self._press_pin(False)
        shown = self.win.statusBar().currentMessage()
        self.assertNotIn("Session saved", shown)
        self.assertIn("NOT saved", shown)
        self.assertNotIn("Session saved", str(self.toast.call_args_list))


if __name__ == "__main__":
    unittest.main()
