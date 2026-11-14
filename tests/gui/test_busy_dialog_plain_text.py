"""The wait dialog shows file and tag text as text, never as rich text.

Run:  py -m unittest tests.gui.test_busy_dialog_plain_text -v

A title like `<img src="\\\\host\\x">` in the message made Qt's rich-text
label open that path (an SMB login). Security audit run-2 #3.
"""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_busy_plain_"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from gui.common import BusyDialog
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)

BAIT = '<img src="\\\\evil-host\\share\\x.png">'


class BusyPlainTextTest(unittest.TestCase):

    def _dialog(self):
        win = QWidget()
        self.addCleanup(reap_widget, win)
        return BusyDialog(win, message=BAIT)

    def test_both_labels_are_plain_text(self):
        dlg = self._dialog()
        self.assertEqual(dlg._lbl.textFormat(), Qt.TextFormat.PlainText)
        self.assertEqual(dlg._detail.textFormat(), Qt.TextFormat.PlainText)

    def test_the_markup_stays_visible_as_text(self):
        dlg = self._dialog()
        dlg.set_progress(1, 2, BAIT)
        self.assertIn(BAIT, dlg._lbl.text() + dlg._detail.text())

if __name__ == "__main__":
    unittest.main()
