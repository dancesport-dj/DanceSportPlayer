"""🔎 Typing in the filter keeps the selected row and the ■ marker (#75)."""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_refilter_"))

from PySide6.QtWidgets import QApplication

from gui.library_browser import LibraryBrowser
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget


def _e(n):
    return MusicEntry(path=Path(rf"C:\music\Tango{n}.mp3"), title=f"track {n}",
                      dance="TG", bpm=None)


class RefilterKeepsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.lb = LibraryBrowser()
        self.addCleanup(reap_widget, self.lb)
        self.lb.resize(1000, 400)
        self.lb.show()
        self.lb.set_entries([_e(1), _e(2), _e(3)])
        self.app.processEvents()

    def selected(self):
        return {str(self.lb._row_path(i.row()))
                for i in self.lb._table.selectionModel().selectedRows()}

    def test_the_selected_row_survives_a_narrower_filter(self):
        row = next(r for r in range(3) if "track 2" in self.lb._table.item(r, 3).text())
        self.lb._table.selectRow(row)
        self.lb._filter_edit.setText("track")      # still matches all three
        self.lb._refilter()
        self.app.processEvents()
        self.assertEqual(self.selected(), {str(_e(2).path)})

    def test_a_row_filtered_out_is_simply_gone(self):
        self.lb._table.selectRow(0)
        self.lb._filter_edit.setText("zzz")
        self.lb._refilter()
        self.app.processEvents()
        self.assertEqual(self.selected(), set())


if __name__ == "__main__":
    unittest.main()
