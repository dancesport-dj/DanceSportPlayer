"""🗑 Reset database: the dialog that picks the parts, and its ⚙ Settings button.

Run:  py -m unittest tests.gui.dialogs.test_reset_db_dialog -v
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_reset_db_"))

from PySide6.QtWidgets import QApplication, QTabWidget

from gui.dialogs.reset_db_dialog import ResetDatabaseDialog
from gui.dialogs.settings_dialog import SettingsDialog
from planner.music.db_upkeep import RESET_GROUPS
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])


class ResetDialogTest(unittest.TestCase):

    def setUp(self):
        self.dlg = ResetDatabaseDialog()
        self.addCleanup(reap_widget, self.dlg)

    def test_one_box_per_part_and_none_ticked(self):
        self.assertEqual(set(self.dlg.boxes), set(RESET_GROUPS))
        self.assertEqual(self.dlg.chosen(), set())
        self.assertFalse(self.dlg.reset_btn.isEnabled())

    def test_a_tick_arms_the_reset(self):
        self.dlg.boxes["analysis"].setChecked(True)
        self.dlg.boxes["user"].setChecked(True)
        self.assertEqual(self.dlg.chosen(), {"analysis", "user"})
        self.assertTrue(self.dlg.reset_btn.isEnabled())
        self.dlg.boxes["analysis"].setChecked(False)
        self.dlg.boxes["user"].setChecked(False)
        self.assertFalse(self.dlg.reset_btn.isEnabled())


class SettingsButtonTest(unittest.TestCase):

    def test_the_button_sits_on_the_analysis_tab_and_calls_back(self):
        reset = mock.Mock()
        dlg = SettingsDialog({}, None, reset_cb=reset)
        self.addCleanup(reap_widget, dlg)
        tabs = dlg.findChild(QTabWidget)
        captions = [tabs.tabText(i) for i in range(tabs.count())]
        page = tabs.widget(captions.index("⚗ Analysis"))
        self.assertTrue(page.isAncestorOf(dlg._reset_btn))
        dlg._reset_btn.click()
        reset.assert_called_once_with()

    def test_without_a_callback_it_is_grey(self):
        dlg = SettingsDialog({}, None)
        self.addCleanup(reap_widget, dlg)
        self.assertFalse(dlg._reset_btn.isEnabled())


if __name__ == "__main__":
    unittest.main()
