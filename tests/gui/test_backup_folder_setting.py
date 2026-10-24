"""💾 The folder the daily user-data backup goes to, set in ⚙ Settings.

Run:  py -m unittest tests.gui.test_backup_folder_setting -v

Empty keeps the backups next to the database; a Dropbox folder takes them off
this PC.
"""
import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication exists, and state files into a temp dir.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_backupfolder_"))

from PySide6.QtWidgets import QApplication

from tests.qt_test_support import reap_widget


class BackupFolderRowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_unset_means_next_to_the_database(self):
        self.assertEqual(self._dlg({}).values()["backup_dir"], "")

    def test_a_stored_folder_is_shown_and_saved(self):
        dlg = self._dlg({"backup_dir": r"E:\Sync\DancePlaylist"})
        self.assertEqual(dlg._backup_edit.text(), r"E:\Sync\DancePlaylist")
        dlg._backup_edit.setText("  E:\\Backups  ")
        self.assertEqual(dlg.values()["backup_dir"], "E:\\Backups")


if __name__ == "__main__":
    unittest.main()
