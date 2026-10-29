#!/usr/bin/env python3
"""▸ Advanced on the 🔊 Sound & player tab remembers whether it was left open.

Run:  py -m unittest tests.gui.dialogs.test_settings_advanced_fold -v
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_adv_fold_"))

from PySide6.QtWidgets import QApplication

from gui.dialogs.settings_dialog import SettingsDialog


class AdvancedFoldTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self, **settings):
        dlg = SettingsDialog(settings)
        self.addCleanup(dlg.deleteLater)
        return dlg

    def test_folded_by_default(self):
        dlg = self._dialog()
        self.assertFalse(dlg._advanced_btn.isChecked())
        self.assertTrue(dlg._advanced_box.isHidden())
        self.assertFalse(dlg.values()["sound_advanced_open"])

    def test_opening_it_is_stored_and_restored(self):
        dlg = self._dialog()
        dlg._advanced_btn.setChecked(True)
        saved = dlg.values()["sound_advanced_open"]
        self.assertTrue(saved)
        again = self._dialog(sound_advanced_open=saved)
        self.assertTrue(again._advanced_btn.isChecked())
        self.assertFalse(again._advanced_box.isHidden())


if __name__ == "__main__":
    unittest.main()
