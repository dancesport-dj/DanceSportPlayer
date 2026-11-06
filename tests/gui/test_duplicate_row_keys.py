"""The R key in the duplicate dialog opens the replacement picker (review s. 4).

`RowKeys` only called `setCurrentIndex`, which does not emit `activated`: the
row then said "Replace…" with no track picked, and Apply complained. The key
now announces the choice the way a click on the combo does.
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_dup_keys_"))

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox

from gui.dialogs.duplicate_dialog import DuplicateResolveDialog
from tests.gui.window.test_duplicate_check_scope import _Status, _waltz, _Win
from tests.qt_test_support import reap_widget


class DuplicateRowKeysTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.win = _Win()
        self.win.statusBar = lambda: _Status()
        self.addCleanup(reap_widget, self.win)
        wl = self.win._deckset.wishlists[0]
        self.win.fill_list(wl, [_waltz("Omega"), _waltz("Delta"),
                                _waltz("Omega", folder="other")])
        self.picked = []
        self.replacement = _waltz("Sigma")

        def pick(entry):
            self.picked.append(entry)
            return self.replacement

        self.dlg = DuplicateResolveDialog(self.win._deck_dup_report(), self.win,
                                          pick_fn=pick)
        self.addCleanup(reap_widget, self.dlg)
        self.combo = next(c for c in self.dlg.findChildren(QComboBox)
                          if c.findText("🔁  Replace…") >= 0)

    def state(self):
        return next(s for s in self.dlg._occ_state if s["combo"] is self.combo)

    def test_r_opens_the_picker_and_keeps_the_choice(self):
        QTest.keyClick(self.combo, Qt.Key.Key_R)
        self.assertEqual(len(self.picked), 1)
        self.assertIs(self.state()["replacement"], self.replacement)
        self.assertEqual(self.combo.currentData(), "replace")

    def test_a_cancelled_picker_falls_back_to_keep(self):
        self.replacement = None
        QTest.keyClick(self.combo, Qt.Key.Key_R)
        self.assertEqual(len(self.picked), 1)
        self.assertEqual(self.combo.currentData(), "keep")

    def test_k_after_r_drops_the_chosen_replacement(self):
        QTest.keyClick(self.combo, Qt.Key.Key_R)
        QTest.keyClick(self.combo, Qt.Key.Key_K)
        self.assertIsNone(self.state()["replacement"])
        self.assertEqual(self.dlg.pending_replacements(), [])


if __name__ == "__main__":
    unittest.main()
