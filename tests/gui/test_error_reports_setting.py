#!/usr/bin/env python3
"""⚙ Settings → 🐞 Send error reports: off until the user ticks it.

Run:  py -m unittest tests.gui.test_error_reports_setting -v

The switch exists only in a build that knows where to send (see
shared.error_reports), and saving it starts or stops the reports at once —
no restart, unlike the language.
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_error_reports_"))

from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

import dancesport_gui as gui  # noqa: E402
from gui import main_global  # noqa: E402
from shared import error_reports  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class SettingsCheckboxTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self, settings, available=True):
        from gui.dialogs import SettingsDialog
        with mock.patch.object(error_reports, "available", return_value=available):
            dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_a_build_without_an_address_offers_nothing(self):
        dlg = self._dialog({}, available=False)
        self.assertIsNone(dlg._error_reports_chk)
        self.assertNotIn("error_reports", dlg.values())

    def test_it_is_off_until_ticked(self):
        dlg = self._dialog({})
        self.assertFalse(dlg._error_reports_chk.isChecked())
        self.assertFalse(dlg.values()["error_reports"])
        dlg._error_reports_chk.setChecked(True)
        self.assertTrue(dlg.values()["error_reports"])

    def test_a_saved_choice_is_shown(self):
        dlg = self._dialog({"error_reports": True})
        self.assertTrue(dlg._error_reports_chk.isChecked())


class _Dialog:
    """⚙ Settings with the operator ticking 🐞."""

    def __init__(self, settings, parent, **_kw):
        self._given = dict(settings)

    def exec(self):
        return QDialog.DialogCode.Accepted

    def values(self):
        return {**self._given, "error_reports": True}

    def running_look_touched(self):
        return False


class SaveAppliesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        gui.load_settings = lambda *a, **kw: {"app_mode": "both"}
        self.win = gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        for name, value in (("SettingsDialog", _Dialog),
                            ("save_settings", lambda s: None)):
            patch = mock.patch.object(main_global, name, value)
            patch.start()
            self.addCleanup(patch.stop)

    def test_saving_starts_the_reports_at_once(self):
        with mock.patch.object(error_reports, "apply") as apply:
            self.win._open_settings()
        apply.assert_called_once()
        self.assertTrue(apply.call_args.args[0]["error_reports"])


if __name__ == "__main__":
    unittest.main()
