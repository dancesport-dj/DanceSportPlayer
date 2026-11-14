#!/usr/bin/env python3
"""💾 A settings save that does not land is told, from one place.

Review 2026-11-12, suggestion 2 (finding 2.3): save_settings is called some
fifty times and almost none of them looks at the result, so a full disk or
a Dropbox lock lost every change without a word. save_settings now tells a
hook the window installs: a status-bar line every time, a box once a
session. A caller that shows its own box passes report=False.

Run:  .venv/Scripts/python.exe -m unittest tests.shared.test_settings_save_report -v
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_save_report_"))

from PySide6.QtWidgets import QApplication, QMainWindow
from shiboken6 import isValid

from shared import stores


class SaveSettingsHookTest(unittest.TestCase):

    def setUp(self):
        self.told = []
        stores.report_settings_failures(lambda: self.told.append(1))
        self.addCleanup(stores.report_settings_failures, None)

    def test_a_failed_write_is_reported(self):
        with mock.patch.object(stores.SETTINGS, "write", return_value=False):
            self.assertFalse(stores.save_settings({}))
        self.assertEqual(self.told, [1])

    def test_a_write_that_lands_is_not(self):
        with mock.patch.object(stores.SETTINGS, "write", return_value=True):
            self.assertTrue(stores.save_settings({}))
        self.assertEqual(self.told, [])

    def test_a_caller_with_its_own_box_can_opt_out(self):
        with mock.patch.object(stores.SETTINGS, "write", return_value=False):
            stores.save_settings({}, report=False)
        self.assertEqual(self.told, [])

    def test_without_a_hook_it_only_returns_false(self):
        stores.report_settings_failures(None)
        with mock.patch.object(stores.SETTINGS, "write", return_value=False):
            self.assertFalse(stores.save_settings({}))


class WindowReportTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from gui import settings_save_report
        self.mod = settings_save_report
        self.win = QMainWindow()
        win = self.win
        self.addCleanup(lambda: isValid(win) and win.deleteLater())   # one test deletes it
        self.addCleanup(stores.report_settings_failures, None)
        settings_save_report.install_report(self.win)
        self.warn = mock.patch.object(settings_save_report.QMessageBox, "warning").start()
        self.addCleanup(mock.patch.stopall)

    def _fail(self):
        with mock.patch.object(stores.SETTINGS, "write", return_value=False):
            stores.save_settings({})
        self.app.processEvents()

    def test_the_status_bar_says_so(self):
        self._fail()
        self.assertIn("could not be saved", self.win.statusBar().currentMessage())

    def test_the_box_comes_once_a_session(self):
        self._fail()
        self._fail()
        self.warn.assert_called_once()
        self.assertIn("could not be saved", self.win.statusBar().currentMessage())

    def test_the_box_waits_for_the_event_loop(self):
        """Never a modal box inside the slider or click that was saving."""
        with mock.patch.object(stores.SETTINGS, "write", return_value=False):
            stores.save_settings({})
        self.warn.assert_not_called()
        self.app.processEvents()
        self.warn.assert_called_once()

    def test_the_box_stands_on_an_open_modal_dialog(self):
        sentinel = object()
        with mock.patch.object(self.mod.QApplication, "activeModalWidget",
                               return_value=sentinel):
            self._fail()
        self.assertIs(self.warn.call_args.args[0], sentinel)

    def test_a_closed_window_does_not_break_the_next_save(self):
        self.win.deleteLater()
        self.app.processEvents()
        from PySide6.QtCore import QCoreApplication, QEvent
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        with mock.patch.object(stores.SETTINGS, "write", return_value=False):
            self.assertFalse(stores.save_settings({}))

    def test_the_window_holds_no_new_attribute(self):
        before = set(vars(self.win))
        self.mod.install_report(self.win)
        self.assertEqual(set(vars(self.win)), before)


if __name__ == "__main__":
    unittest.main()
