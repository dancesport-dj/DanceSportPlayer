"""⚙ Settings → Analysis offers the dated user-data backups for a restore."""
import datetime as dt
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtWidgets import QApplication

import planner.db as pdb
from gui import main_global
from gui.dialogs import SettingsDialog


class RestoreUserDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_restore_ui_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        saved = (pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
        pdb.AUDIO_DB_FILE = self.dir / "scratch.db"
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False

        def restore():
            try:
                pdb._DB_LOCAL.conn.close()
            except Exception:
                pass
            pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED = saved
        self.addCleanup(restore)
        conn = pdb._db()
        conn.execute("INSERT INTO tag_edits (fp, rating) VALUES ('fp1', 4)")
        self.backup = pdb.backup_user_data(today=dt.date(2026, 10, 9))
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


if __name__ == "__main__":
    unittest.main()
