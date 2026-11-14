"""🔁 The duplicate dialog shows a playlist's file name as typed.

A QLabel on its default format renders text that looks like HTML: a playlist
called "Rumba <live> & Co.m3u" lost its "<live>" and the header read
"Rumba  & Co.m3u".
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR", tempfile.mkdtemp(prefix="dp_dup_labels_"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from gui.dialogs import duplicate_dialog as dd
from tests.qt_test_support import reap_widget

NAME = "Rumba <b>live</b> & Co.m3u"


class DupLabelsPlainTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dlg = dd.DuplicateResolveDialog({}, None, lambda e: None,
                                             ref_clean_factory=lambda: None)
        self.addCleanup(reap_widget, self.dlg)

    def test_a_column_header_shows_the_file_name_as_typed(self):
        lbl = self.dlg._col_header(f"📁  {NAME}")
        self.assertEqual(lbl.textFormat(), Qt.TextFormat.PlainText)
        self.assertEqual(lbl.text(), f"📁  {NAME}")

    def test_the_reference_label_shows_the_file_name_as_typed(self):
        self.dlg._ref_path = Path(NAME)
        self.dlg._ref_lbl.setText(f"📌  {self.dlg._ref_path.name}")
        self.assertEqual(self.dlg._ref_lbl.textFormat(), Qt.TextFormat.PlainText)


if __name__ == "__main__":
    unittest.main()
