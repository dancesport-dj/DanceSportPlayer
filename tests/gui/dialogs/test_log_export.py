#!/usr/bin/env python3
"""❔ → 📝 Export log: the app's log files land in one zip the user saves.

A Save dialog, not a folder picker: the native macOS folder panel has an
"Open" button and no Save, which is what the export looked like there.

Run:  py -m unittest tests.gui.dialogs.test_log_export -v
"""

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from PySide6.QtWidgets import QApplication

from gui.dialogs import log_export


class ZipLogsTest(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.app_dir = Path(tmp.name) / "app"
        self.zip = Path(tmp.name) / "out.zip"
        self.app_dir.mkdir()

    def test_every_log_goes_into_the_zip_under_its_own_name(self):
        (self.app_dir / "session.log").write_text("now", encoding="utf-8")
        (self.app_dir / "session.prev.log").write_text("before", encoding="utf-8")
        (self.app_dir / "crash.log").write_text("💥", encoding="utf-8")
        written = log_export.zip_logs(self.app_dir, self.zip)
        self.assertEqual(written, ["session.log", "session.prev.log", "crash.log"])
        with zipfile.ZipFile(self.zip) as z:
            self.assertEqual(z.namelist(), written)
            self.assertEqual(z.read("crash.log").decode("utf-8"), "💥")

    def test_missing_and_empty_logs_are_left_out(self):
        (self.app_dir / "session.log").write_text("now", encoding="utf-8")
        (self.app_dir / "crash.log").write_text("", encoding="utf-8")
        self.assertEqual(log_export.zip_logs(self.app_dir, self.zip), ["session.log"])
        with zipfile.ZipFile(self.zip) as z:
            self.assertEqual(z.namelist(), ["session.log"])

    def test_no_log_writes_no_zip(self):
        self.assertEqual(log_export.zip_logs(self.app_dir, self.zip), [])
        self.assertFalse(self.zip.exists())


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

    def save_to(self, path):
        return mock.patch.object(log_export.QFileDialog, "getSaveFileName",
                                 return_value=(str(path), ""))

    def test_the_chosen_file_gets_the_logs(self):
        out = self.target / "mine.zip"
        with self.save_to(out), \
                mock.patch.object(log_export.QMessageBox, "information") as told:
            log_export.export_log(None)
        with zipfile.ZipFile(out) as z:
            self.assertEqual(z.namelist(), ["session.log"])
        self.assertIn(str(out), told.call_args.args[2])

    def test_a_name_without_zip_gets_the_extension(self):
        with self.save_to(self.target / "mine"), \
                mock.patch.object(log_export.QMessageBox, "information"):
            log_export.export_log(None)
        self.assertEqual([p.name for p in self.target.iterdir()], ["mine.zip"])

    def test_the_dialog_proposes_a_dated_zip_name(self):
        with self.save_to(""), mock.patch.object(log_export.QMessageBox, "information"):
            with mock.patch.object(log_export.QFileDialog, "getSaveFileName",
                                   return_value=("", "")) as ask:
                log_export.export_log(None)
        proposed = Path(ask.call_args.args[2])
        self.assertRegex(proposed.name, r"^dancesport-log_\d{4}-\d{2}-\d{2}_\d{6}\.zip$")

    def test_cancelling_the_dialog_writes_nothing(self):
        with self.save_to(""), \
                mock.patch.object(log_export.QMessageBox, "information") as told:
            log_export.export_log(None)
        self.assertEqual(list(self.target.iterdir()), [])
        told.assert_not_called()

    def test_with_no_log_it_says_so_without_asking_for_a_file(self):
        (self.app_dir / "session.log").unlink()
        with mock.patch.object(log_export.QFileDialog, "getSaveFileName") as ask, \
                mock.patch.object(log_export.QMessageBox, "information") as told:
            log_export.export_log(None)
        ask.assert_not_called()
        self.assertIn("no log", told.call_args.args[2])

    def test_a_failed_write_is_reported(self):
        with self.save_to(self.target / "mine.zip"), \
                mock.patch.object(log_export.zipfile, "ZipFile",
                                  side_effect=PermissionError("denied")), \
                mock.patch.object(log_export.QMessageBox, "warning") as warned:
            log_export.export_log(None)
        self.assertIn("denied", warned.call_args.args[2])


if __name__ == "__main__":
    unittest.main()
