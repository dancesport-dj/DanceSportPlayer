#!/usr/bin/env python3
"""⚙ Settings: an action button closes the dialog only once its job runs.

Run:  py -m unittest tests.gui.test_settings_action_confirm -v

🧹 Clean up database, 🗑 Reset database and the ⚗ analysis buttons ask
again before they start. The dialog used to accept first: a "No" there
still kept every edit made in Settings, as if OK had been pressed. Now the
callback runs while the dialog is open and answers whether the job started;
on a "No" the dialog stays open with its edits.
"""

import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_settings_confirm_"))

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from gui.dialogs.settings_dialog import SettingsDialog
from gui.window import main_global
from gui.window.main_global import GlobalIndexMixin
from tests.qt_test_support import reap_widget

_HANDLERS = {
    "maintenance_cb": "_on_maintenance_clicked",
    "reset_cb": "_on_reset_clicked",
    "analyze_cb": "_on_analyze_clicked",
    "loudness_cb": "_on_loudness_clicked",
    "silence_cb": "_on_silence_clicked",
    "pd_cb": "_on_pd_clicked",
    "vocals_cb": "_on_vocals_clicked",
}


class SettingsActionDialogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def press(self, cb_name: str, started: bool) -> tuple[list, list]:
        ran, accepted = [], []
        dlg = SettingsDialog({}, **{cb_name: lambda: ran.append(1) or started})
        self.addCleanup(reap_widget, dlg)
        dlg.accepted.connect(lambda: accepted.append(1))
        getattr(dlg, _HANDLERS[cb_name])()
        return ran, accepted

    def test_a_declined_follow_up_keeps_the_dialog_open(self):
        for cb_name in _HANDLERS:
            with self.subTest(cb_name):
                ran, accepted = self.press(cb_name, started=False)
                self.assertEqual(ran, [1])
                self.assertEqual(accepted, [])

    def test_a_started_job_closes_the_dialog(self):
        for cb_name in _HANDLERS:
            with self.subTest(cb_name):
                ran, accepted = self.press(cb_name, started=True)
                self.assertEqual(ran, [1])
                self.assertEqual(accepted, [1])


class WindowActionAnswerTest(unittest.TestCase):
    """The window's callbacks say whether the job started."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_cleanup_declined_and_started(self):
        no, yes = QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes
        with mock.patch.object(main_global.QMessageBox, "question", return_value=no):
            self.assertIs(GlobalIndexMixin._run_db_maintenance(SimpleNamespace()), False)
        win = SimpleNamespace(_on_maintenance_done=None, _on_maintenance_error=None)
        with (mock.patch.object(main_global.QMessageBox, "question", return_value=yes),
              mock.patch.object(main_global, "BusyDialog"),
              mock.patch.object(main_global, "DbMaintenanceWorker") as worker):
            self.assertIs(GlobalIndexMixin._run_db_maintenance(win), True)
        worker.return_value.start.assert_called_once_with()

    def test_reset_declined_and_started(self):
        with mock.patch.object(main_global, "ResetDatabaseDialog") as dlg:
            dlg.return_value.exec.return_value = QDialog.DialogCode.Rejected
            self.assertIs(GlobalIndexMixin._reset_database(SimpleNamespace()), False)
        win = SimpleNamespace(_on_reset_done=None, _on_reset_error=None)
        with (mock.patch.object(main_global, "ResetDatabaseDialog") as dlg,
              mock.patch.object(main_global, "BusyDialog"),
              mock.patch.object(main_global, "DbResetWorker") as worker):
            dlg.return_value.exec.return_value = QDialog.DialogCode.Accepted
            dlg.return_value.chosen.return_value = ["features"]
            self.assertIs(GlobalIndexMixin._reset_database(win), True)
        worker.return_value.start.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
