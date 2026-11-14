#!/usr/bin/env python3
"""Enter in the replacement chooser: it takes the selected row, unless a
button has the focus — Enter on Cancel cancels.

Run:  py -m unittest tests.gui.test_similar_enter_key -v
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_sim_enter_"))

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from gui.dialogs.similar_dialog import SimilarTracksDialog
from tests.gui.test_similar_preview_stop import _RESULTS, _SOURCE
from tests.qt_test_support import reap_widget


class SimilarEnterKeyTest(unittest.TestCase):

    def setUp(self):
        self.picked = []
        self.dlg = SimilarTracksDialog(_SOURCE, _RESULTS, None,
                                       pick_cb=self.picked.append)
        self.addCleanup(reap_widget, self.dlg)
        self.dlg.show()
        self.dlg.activateWindow()
        QApplication.processEvents()

    def button(self, text: str) -> QPushButton:
        return next(b for b in self.dlg.findChildren(QPushButton) if b.text() == text)

    def test_enter_on_cancel_cancels(self):
        rejected = []
        self.dlg.rejected.connect(lambda: rejected.append(True))
        for key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            with self.subTest(key=key):
                rejected.clear()
                self.dlg.show()
                self.dlg._table.setCurrentCell(1, 0)     # a row Enter would take
                cancel = self.button("Cancel")
                cancel.setFocus()
                QApplication.processEvents()
                QTest.keyClick(cancel, key)
                QApplication.processEvents()
                self.assertEqual(self.picked, [])
                self.assertEqual(rejected, [True])

    def test_enter_after_a_rows_play_button_takes_the_row(self):
        # Hear it with ▶, then Enter: a clicked button holds the focus on
        # Windows, and Enter must still take the row, not stop the preview.
        played = []
        dlg = SimilarTracksDialog(_SOURCE, _RESULTS, None, play_cb=played.append,
                                  pick_cb=self.picked.append)
        self.addCleanup(reap_widget, dlg)
        dlg.show()
        dlg.activateWindow()
        QApplication.processEvents()
        dlg._table.setCurrentCell(1, 1)
        play = dlg._table.cellWidget(1, 0)
        play.setFocus()
        play.click()
        QApplication.processEvents()
        QTest.keyClick(play, Qt.Key.Key_Return)
        QApplication.processEvents()
        self.assertEqual(self.picked, [_RESULTS[1][1]])

    def test_enter_in_the_table_takes_the_selected_row(self):
        self.dlg._table.setCurrentCell(1, 0)
        self.dlg._table.setFocus()
        QApplication.processEvents()
        QTest.keyClick(self.dlg._table, Qt.Key.Key_Return)
        QApplication.processEvents()
        self.assertEqual(self.picked, [_RESULTS[1][1]])


if __name__ == "__main__":
    unittest.main()
