"""The library-gaps dialog sorts its percentage columns by number (review s. 4).

"Tempo OK" and "Stale" show "100 %  (10/10)" as text, so a header click put
"100 %" before "50 %". They now carry the number to sort by.
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_gapsort_"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from gui.dialogs import LibraryGapsDialog
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])

_TEMPO = 5
_STALE = 9


def _row(tempo_ok, tempo_known, stale, pool):
    return {"style": "Latin", "cls": "D", "dance": "CC", "lo": 28, "hi": 32,
            "pool": pool, "tempo_ok": tempo_ok, "tempo_known": tempo_known,
            "proven": 20, "fresh": 5, "never": 1, "stale": stale}


_ROWS = [
    _row(10, 10, 10, 10),    # tempo 100 %, stale 100 %
    _row(5, 10, 5, 10),      # tempo 50 %,  stale 50 %
    _row(0, 0, 4, 20),       # tempo unknown, stale 20 %
]


class GapsPercentSortTest(unittest.TestCase):

    def setUp(self):
        with mock.patch("gui.dialogs.gap_stats", return_value=_ROWS):
            self.dlg = LibraryGapsDialog(object())
        self.addCleanup(reap_widget, self.dlg)

    def column(self, col, order):
        t = self.dlg._table
        t.sortItems(col, order)
        return [t.item(r, col).text() for r in range(t.rowCount())]

    def test_tempo_sorts_by_the_percentage(self):
        got = self.column(_TEMPO, Qt.SortOrder.AscendingOrder)
        self.assertEqual([s.split(" ")[0] for s in got], ["—", "50", "100"])

    def test_stale_sorts_by_the_percentage(self):
        got = self.column(_STALE, Qt.SortOrder.AscendingOrder)
        self.assertEqual([s.split(" ")[0] for s in got], ["20", "50", "100"])


if __name__ == "__main__":
    unittest.main()
