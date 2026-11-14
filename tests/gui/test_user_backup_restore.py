"""⚙ Settings → Analysis offers the dated user-data backups for a restore."""
import datetime as dt
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtWidgets import QApplication

import planner.music.db as pdb
import planner.music.db_upkeep as upkeep
from gui.dialogs.settings_dialog import SettingsDialog
from gui.window import main_global
from tests.db_support import use_scratch_db


class RestoreUserDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_restore_ui_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
        conn = pdb._db()
        conn.execute("INSERT INTO tag_edits (fp, rating) VALUES ('fp1', 4)")
        self.backup = upkeep.backup_user_data(today=dt.date(2026, 10, 9))
        conn.execute("DELETE FROM tag_edits")

    def test_settings_has_the_restore_button(self):
        cb = mock.Mock()
        dlg = SettingsDialog({}, None, backup_restore_cb=cb)
        self.addCleanup(dlg.deleteLater)
        self.assertTrue(dlg._backup_restore_btn.isEnabled())
        dlg._backup_restore_btn.click()
        cb.assert_called_once()

    def test_restore_opens_in_the_backup_folder_and_merges(self):
        host = mock.Mock()
        with mock.patch.object(main_global.QFileDialog, "getOpenFileName",
                               return_value=(str(self.backup), "")) as ask, \
                mock.patch.object(main_global.QMessageBox, "information") as info:
            main_global.GlobalIndexMixin._restore_user_data(host)
        self.assertEqual(Path(ask.call_args.args[2]), self.backup.parent)
        self.assertEqual(pdb._db().execute("SELECT fp, rating FROM tag_edits").fetchall(),
                         [("fp1", 4)])
        info.assert_called_once()

    def test_a_wrong_file_is_refused(self):
        bad = self.dir / "bad.db"
        bad.write_text("nope")
        with mock.patch.object(main_global.QFileDialog, "getOpenFileName",
                               return_value=(str(bad), "")), \
                mock.patch.object(main_global.QMessageBox, "warning") as warn:
            main_global.GlobalIndexMixin._restore_user_data(mock.Mock())
        warn.assert_called_once()

    def test_a_locked_database_is_reported_not_raised(self):
        # Review 5.B: only ValueError was caught, so a busy database left a
        # traceback and no word to the user.
        import sqlite3
        with mock.patch.object(main_global.QFileDialog, "getOpenFileName",
                               return_value=(str(self.backup), "")), \
                mock.patch.object(upkeep, "restore_user_data",
                                  side_effect=sqlite3.OperationalError("database is locked")), \
                mock.patch.object(main_global.QMessageBox, "warning") as warn:
            main_global.GlobalIndexMixin._restore_user_data(mock.Mock())
        warn.assert_called_once()
        self.assertIn("database is locked", warn.call_args.args[2])


class LockedTagWritesTest(unittest.TestCase):
    """Review 5.A: a tag edit, a rating or the Custom mapping that meets a
    locked database is reported in a toast, not left as a traceback."""

    def _host(self):
        import sqlite3
        host = mock.Mock()
        host._library.lib.edit_tags.side_effect = sqlite3.OperationalError("database is locked")
        host._custom_reader = None
        return host

    def test_a_rating_is_reported(self):
        from gui.window import main_tags
        with mock.patch.object(main_tags, "show_toast") as toast:
            main_tags.TagEditMixin._set_entry_rating(self._host(), mock.Mock(path="a.mp3"), 4)
        self.assertIn("database is locked", toast.call_args.args[1])

    def test_the_custom_mapping_is_reported_and_left_unmapped(self):
        import sqlite3

        from gui.window import main_tags
        with mock.patch.object(main_tags, "show_toast") as toast, \
                mock.patch.object(main_tags.custom_field, "set_source",
                                  side_effect=sqlite3.OperationalError("database is locked")):
            self.assertFalse(main_tags.TagEditMixin._set_custom_source(self._host(), "TXXX", "x"))
        self.assertIn("database is locked", toast.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
