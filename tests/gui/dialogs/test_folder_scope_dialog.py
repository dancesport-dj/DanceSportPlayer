#!/usr/bin/env python3
"""The folder checklist behind ⚡ Generate's 'Chosen library folders' source.

Run:  py -m unittest tests.gui.dialogs.test_folder_scope_dialog -v
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_foldlg_"))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QCheckBox, QDialog, QListWidget

from gui.dialogs.folder_scope_dialog import ask_library_folders
from planner.models import MusicEntry

ROOT = "C:/fav"
ENTRIES = [MusicEntry(path=Path(f"{ROOT}/{rel}"), title=rel, dance="SA", bpm=51)
           for rel in ("a.mp3", "vlt/b.mp3", "vlt/vlt/c.mp3", "vlt/vlt/d.mp3")]


class FolderScopeDialogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _run(self, act, chosen=()):
        """Ask, with `act(list_widget, dialog)` standing in for the user."""
        def drive():
            dlg = next(w for w in QApplication.topLevelWidgets()
                       if isinstance(w, QDialog) and w.isVisible())
            act(dlg.findChild(QListWidget), dlg)
        QTimer.singleShot(0, drive)
        return ask_library_folders(None, ROOT, ENTRIES, chosen)

    def test_it_lists_every_folder_with_its_titles(self):
        seen = []

        def act(lst, dlg):
            seen.extend(lst.item(i).text() for i in range(lst.count()))
            dlg.reject()
        self._run(act)
        self.assertEqual(len(seen), 3)
        self.assertIn("2", seen[2])

    def test_the_ticked_folders_come_back(self):
        def act(lst, dlg):
            lst.item(0).setCheckState(Qt.CheckState.Checked)
            lst.item(2).setCheckState(Qt.CheckState.Checked)
            dlg.accept()
        self.assertEqual(self._run(act), ["", "vlt/vlt"])

    def _all(self, dlg):
        return dlg.findChild(QCheckBox, "select_all")

    def test_select_all_ticks_every_folder(self):
        def act(lst, dlg):
            self._all(dlg).click()
            dlg.accept()
        self.assertEqual(self._run(act), ["", "vlt", "vlt/vlt"])

    def test_a_second_click_clears_the_earlier_picks(self):
        def act(lst, dlg):
            box = self._all(dlg)
            box.click()
            box.click()
            dlg.accept()
        self.assertEqual(self._run(act, chosen=["vlt", ""]), [])

    def test_the_box_shows_none_some_or_all(self):
        seen = []

        def act(lst, dlg):
            box = self._all(dlg)
            seen.append(box.checkState())
            lst.item(0).setCheckState(Qt.CheckState.Checked)
            seen.append(box.checkState())
            for i in range(lst.count()):
                lst.item(i).setCheckState(Qt.CheckState.Checked)
            seen.append(box.checkState())
            dlg.reject()
        self._run(act)
        self.assertEqual(seen, [Qt.CheckState.Unchecked,
                                Qt.CheckState.PartiallyChecked,
                                Qt.CheckState.Checked])

    def test_a_click_on_a_partly_ticked_box_ticks_everything(self):
        def act(lst, dlg):
            self._all(dlg).click()
            dlg.accept()
        self.assertEqual(self._run(act, chosen=["vlt"]), ["", "vlt", "vlt/vlt"])

    def test_cancel_changes_nothing(self):
        self.assertIsNone(self._run(lambda _lst, dlg: dlg.reject()))

    def test_earlier_picks_start_ticked(self):
        def act(lst, dlg):
            dlg.accept()
        self.assertEqual(self._run(act, chosen=["vlt"]), ["vlt"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
