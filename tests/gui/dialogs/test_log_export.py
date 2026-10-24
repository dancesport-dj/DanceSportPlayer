#!/usr/bin/env python3
"""❔ → 📝 Export log: the app's log files land in a folder the user picks.

Run:  py -m unittest tests.gui.dialogs.test_log_export -v
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtWidgets import QApplication

from gui.dialogs import log_export


class ExportLogsTest(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.app_dir = Path(tmp.name) / "app"
        self.target = Path(tmp.name) / "target"
        self.app_dir.mkdir()
        self.target.mkdir()

    def test_every_log_is_copied_with_the_time_in_its_name(self):
        (self.app_dir / "session.log").write_text("now", encoding="utf-8")
        (self.app_dir / "session.prev.log").write_text("before", encoding="utf-8")
        (self.app_dir / "crash.log").write_text("💥", encoding="utf-8")
        written = log_export.export_logs(self.app_dir, self.target, "2026-10-22_1430")
        self.assertEqual([p.name for p in written],
                         ["session_2026-10-22_1430.log",
                          "session.prev_2026-10-22_1430.log",
                          "crash_2026-10-22_1430.log"])
        self.assertEqual((self.target / "crash_2026-10-22_1430.log")
                         .read_text(encoding="utf-8"), "💥")

    def test_missing_and_empty_logs_are_left_out(self):
        (self.app_dir / "session.log").write_text("now", encoding="utf-8")
        (self.app_dir / "crash.log").write_text("", encoding="utf-8")
        written = log_export.export_logs(self.app_dir, self.target, "x")
        self.assertEqual([p.name for p in written], ["session_x.log"])
        self.assertEqual(sorted(p.name for p in self.target.iterdir()), ["session_x.log"])


class ExportLogDialogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.app_dir = Path(tmp.name) / "app"
        self.target = Path(tmp.name) / "target"
        self.app_dir.mkdir()
        self.target.mkdir()
        (self.app_dir / "session.log").write_text("now", encoding="utf-8")
        patcher = mock.patch.object(log_export.planner.config, "APP_DIR", self.app_dir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_chosen_folder_gets_the_logs(self):
        with mock.patch.object(log_export.QFileDialog, "getExistingDirectory",
                               return_value=str(self.target)), \
                mock.patch.object(log_export.QMessageBox, "information") as told:
            log_export.export_log(None)
        self.assertEqual(len(list(self.target.glob("session_*.log"))), 1)
        self.assertIn(str(self.target), told.call_args.args[2])

    def test_cancelling_the_folder_picker_writes_nothing(self):
        with mock.patch.object(log_export.QFileDialog, "getExistingDirectory",
                               return_value=""), \
                mock.patch.object(log_export.QMessageBox, "information") as told:
            log_export.export_log(None)
        self.assertEqual(list(self.target.iterdir()), [])
        told.assert_not_called()

    def test_a_failed_copy_is_reported(self):
        with mock.patch.object(log_export.QFileDialog, "getExistingDirectory",
                               return_value=str(self.target)), \
                mock.patch.object(log_export.shutil, "copy2",
                                  side_effect=PermissionError("denied")), \
                mock.patch.object(log_export.QMessageBox, "warning") as warned:
            log_export.export_log(None)
        self.assertIn("denied", warned.call_args.args[2])


if __name__ == "__main__":
    unittest.main()
