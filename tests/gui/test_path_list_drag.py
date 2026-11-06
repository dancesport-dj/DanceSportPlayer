#!/usr/bin/env python3
"""Dragging a title out of a PathListWidget must not offer the real file for a Move,
and must only drop the list item when the drop landed inside the app.

Run:  py -m unittest tests.gui.test_path_list_drag -v
"""

import unittest
from unittest import mock

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QListWidgetItem

from gui import common
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])

_COPY = Qt.DropAction.CopyAction
_IGNORE = Qt.DropAction.IgnoreAction


class _FakeDrag:
    """Stands in for QDrag: records the offered actions, answers exec()."""
    result = _COPY
    target_obj = object()
    last = None

    def __init__(self, source):
        _FakeDrag.last = self
        self.offered = None

    def setMimeData(self, md):
        self.mime = md

    def exec(self, supported, default=Qt.DropAction.MoveAction):
        self.offered = supported
        return _FakeDrag.result

    def target(self):
        return _FakeDrag.target_obj


class PathListDragTest(unittest.TestCase):

    def setUp(self):
        self.lst = common.PathListWidget()
        self.addCleanup(reap_widget, self.lst)
        it = QListWidgetItem("a.mp3")
        it.setToolTip(r"C:\music\a.mp3")
        self.lst.addItem(it)
        it.setSelected(True)
        self.out = []
        self.lst.draggedOut.connect(self.out.append)
        p = mock.patch.object(common, "QDrag", _FakeDrag)
        p.start()
        self.addCleanup(p.stop)
        _FakeDrag.result = _COPY
        _FakeDrag.target_obj = object()

    def test_the_real_file_is_never_offered_for_a_move(self):
        self.lst.startDrag(Qt.DropAction.MoveAction)
        self.assertFalse(_FakeDrag.last.offered & Qt.DropAction.MoveAction)

    def test_a_cancelled_drag_keeps_the_item(self):
        _FakeDrag.result = _IGNORE
        self.lst.startDrag(Qt.DropAction.MoveAction)
        self.assertEqual(self.out, [])

    def test_a_drop_outside_the_app_keeps_the_item(self):
        _FakeDrag.target_obj = None
        self.lst.startDrag(Qt.DropAction.MoveAction)
        self.assertEqual(self.out, [])

    def test_a_drop_inside_the_app_removes_the_item(self):
        self.lst.startDrag(Qt.DropAction.MoveAction)
        self.assertEqual(self.out, [[r"C:\music\a.mp3"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
