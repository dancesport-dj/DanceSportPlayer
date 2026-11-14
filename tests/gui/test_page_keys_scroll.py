#!/usr/bin/env python3
"""PageUp / PageDown move the selection AND the view.

Run:  py -m unittest tests.gui.test_page_keys_scroll -v

In a long list the selection followed PageUp / PageDown but the scrollbar stayed
put, so the selected title left the visible part of the list.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pagekeys_"))

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry
from shared.columns import _COL_TITLE
from tests.qt_test_support import reap_widget


def _e(n):
    return MusicEntry(path=Path(rf"C:\music\LW{n}.mp3"), title=f"LW {n}",
                      dance="LW", bpm=None)


class PageKeysScrollTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def table(self) -> PlaylistTable:
        win = QWidget()
        t = PlaylistTable()
        t.setParent(win)
        t.resize(700, 300)
        win.resize(720, 320)
        self.addCleanup(reap_widget, win)
        t.load_player_list([_e(i) for i in range(80)], "Abend", play_cb=None)
        win.show()
        t.setFocus()
        self.app.processEvents()
        t.setCurrentCell(0, _COL_TITLE)
        self.app.processEvents()
        self.assertGreater(t.verticalScrollBar().maximum(), 0)
        return t

    def press(self, t, key, times=1):
        for _ in range(times):
            QTest.keyClick(t, key)
        self.app.processEvents()

    def visible(self, t) -> bool:
        item = t.item(t.currentRow(), _COL_TITLE)
        rect = t.visualItemRect(item)
        # Vertical only: Ctrl+End also lands in the last column, which scrolls
        # the view sideways, and that says nothing about the row being in sight.
        return rect.top() >= 0 and rect.bottom() <= t.viewport().height()

    def test_arrow_down_keeps_the_selection_in_view(self):
        t = self.table()
        self.press(t, Qt.Key.Key_Down, 40)
        self.assertTrue(self.visible(t))

    def test_page_down_moves_the_view_with_the_selection(self):
        t = self.table()
        self.press(t, Qt.Key.Key_PageDown, 3)
        self.assertGreater(t.currentRow(), 0)
        self.assertGreater(t.verticalScrollBar().value(), 0)
        self.assertTrue(self.visible(t))

    def test_page_up_moves_the_view_with_the_selection(self):
        t = self.table()
        QTest.keyClick(t, Qt.Key.Key_End, Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents()
        self.assertEqual(t.verticalScrollBar().value(),
                         t.verticalScrollBar().maximum())
        self.press(t, Qt.Key.Key_PageUp, 2)
        self.assertLess(t.verticalScrollBar().value(),
                        t.verticalScrollBar().maximum())
        self.assertTrue(self.visible(t))


if __name__ == "__main__":
    unittest.main()
