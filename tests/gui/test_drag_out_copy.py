#!/usr/bin/env python3
"""A title dragged out of the app never offers to MOVE the music file.

Run:  py -m unittest tests.gui.test_drag_out_copy -v

A drag that carries file URLs reaches Explorer, and with Move on offer the
shell picks the effect: a drop on the same drive moves, and so does Shift.
That takes the MP3 out of the library and breaks every saved playlist that
names it. Every file drag offers Copy and Link only; the moves inside the app
are made by hand in the drop handlers and never ask the drag for one.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_drag_out_"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableWidgetItem

import gui.common as common
import gui.library_browser as library_browser
import gui.table.table_dnd as dnd
from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)

_MOVE = Qt.DropAction.MoveAction
_TRACK = Path(r"C:\music\WW1.mp3")


class DragOutOffersNoMoveTest(unittest.TestCase):

    def _offered(self, module, widget):
        with mock.patch.object(module, "QDrag") as drag_cls:
            widget.startDrag(Qt.DropAction.CopyAction)
        drag_cls.return_value.exec.assert_called_once()
        return drag_cls.return_value.exec.call_args.args[0]

    def _check(self, module, widget):
        self.addCleanup(reap_widget, widget)
        actions = self._offered(module, widget)
        self.assertFalse(actions & _MOVE, "the shell may move the MP3")
        self.assertTrue(actions & Qt.DropAction.CopyAction)

    def test_a_deck_or_wishlist_row(self):
        t = PlaylistTable()
        t.load_wishlist([MusicEntry(path=_TRACK, title="WW 1", dance="WW", bpm=None)],
                        play_cb=lambda *a: None, suggester=None)
        t.selectRow(next(r for r, m in t._row_meta.numbered() if m and m.entry))
        self._check(dnd, t)

    def test_a_similar_tracks_or_ai_row(self):
        t = common.DragTable([_TRACK])
        t.setColumnCount(1)
        t.setRowCount(1)
        t.setItem(0, 0, QTableWidgetItem("WW 1"))
        t.selectRow(0)
        self._check(common, t)

    def test_a_library_row(self):
        t = library_browser.LibTable(1, 1)
        it = QTableWidgetItem("WW 1")
        it.setData(Qt.ItemDataRole.UserRole, str(_TRACK))
        t.setItem(0, 0, it)
        t.selectRow(0)
        self._check(library_browser, t)


if __name__ == "__main__":
    unittest.main()
