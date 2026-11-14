"""🔁 Enter in the Check duplicates dialog applies, it does not cancel.

Marcel: "Check duplicates (duplicate_dialog.py) still has Cancel as its
default ... fix it". The ♊ Remove duplicate titles dialog got the same
change in a2468ef4.
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR", tempfile.mkdtemp(prefix="dp_dup_default_"))

from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from gui.dialogs import duplicate_dialog as dd
from tests.qt_test_support import reap_widget


class DupDialogDefaultTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def dialog(self, report):
        # The report's rows are not what this test is about: an empty tab
        # keeps the button row, which is built from the report's truthiness.
        with mock.patch.object(dd.DuplicateResolveDialog, "_build_decks_tab",
                               lambda self, r: QWidget()):
            dlg = dd.DuplicateResolveDialog(report, None, lambda e: None)
        self.addCleanup(reap_widget, dlg)
        dlg.show()
        self.app.processEvents()
        return dlg

    def test_enter_applies_when_there_are_duplicates(self):
        dlg = self.dialog({"within": [{"x": 1}], "cross": []})
        self.assertEqual(dlg._action_btn.text(), "✅  Apply")
        self.assertTrue(dlg._action_btn.isDefault())
        self.assertIs(dlg.focusWidget(), dlg._action_btn)
        cancel = [b for b in dlg.findChildren(QPushButton) if b.text() == "Cancel"]
        self.assertEqual(len(cancel), 1)
        self.assertFalse(cancel[0].isDefault())

    def test_with_nothing_to_apply_enter_closes(self):
        dlg = self.dialog({"within": [], "cross": []})
        self.assertFalse(dlg._action_btn.isVisible())
        close = [b for b in dlg.findChildren(QPushButton) if b.text() == "Close"]
        self.assertTrue(close[0].isDefault())


if __name__ == "__main__":
    unittest.main()
