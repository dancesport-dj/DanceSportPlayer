"""🏆 Ctrl+A in the tournament tab marks everything; Del and a drag take it all.

Run:  py -m unittest tests.gui.test_tournament_select_all -v

Marcel: "strg+a should select all elements in Turniere Tab", what for:
"Löschen (Entf/🗑)", and then "markieren und ziehen soll auch gehen". On the
▦ board everything is the folder's playlist tiles, in the ▤ view it is every
entry of the tree.
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tree_select_all_"))

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QKeyEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox, QToolButton  # noqa: E402

from gui import tournament_tree as gt  # noqa: E402
from planner.store import JsonStore  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)
_YES = QMessageBox.StandardButton.Yes


def _key(widget, key, mods=Qt.KeyboardModifier.NoModifier):
    widget.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, key, mods))


def _ctrl_a(widget):
    _key(widget, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)


class _Case(unittest.TestCase):

    def setUp(self):
        d = tempfile.mkdtemp(prefix="dp_tree_select_all_")
        self.pane = gt.TournamentTree(JsonStore.at(os.path.join(d, "t.json")))
        self.addCleanup(reap_widget, self.pane)
        self.pane._nodes.extend([
            {"name": "Freitag", "children": [
                {"name": "T1", "m3u": "t1.m3u"}, {"name": "T2", "m3u": "t2.m3u"},
                {"name": "T3", "m3u": "t3.m3u"}]},
            {"name": "Samstag", "children": [{"name": "T4", "m3u": "t4.m3u"}]}])
        self.pane._rebuild()
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))

    def trash(self):
        with mock.patch.object(QMessageBox, "question", return_value=_YES) as ask:
            next(b for b in self.pane.findChildren(QToolButton)
                 if b.text() == "🗑").click()
        return ask


class BoardSelectAllTest(_Case):

    def tiles(self):
        return sorted(k for k, t in self.pane._board._tiles.items() if t._selected)

    def test_ctrl_a_marks_every_tile_of_the_folder(self):
        _ctrl_a(self.pane)
        self.assertEqual(self.tiles(), ["0/0", "0/1", "0/2"])

    def test_ctrl_a_in_the_folder_tree_marks_the_tiles_not_the_folders(self):
        _ctrl_a(self.pane._tree)
        self.assertEqual(self.tiles(), ["0/0", "0/1", "0/2"])
        self.assertEqual(len(self.pane._tree.selectedItems()), 1)

    def test_del_then_removes_them_all_and_keeps_the_folder(self):
        _ctrl_a(self.pane)
        ask = self.trash()
        self.assertEqual(ask.call_count, 1)   # one question, not one per tile
        self.assertEqual(self.pane._nodes[0], {"name": "Freitag", "children": []})
        self.assertEqual(self.pane._nodes[1]["children"][0]["name"], "T4")

    def test_no_answers_no_removal(self):
        _ctrl_a(self.pane)
        with mock.patch.object(QMessageBox, "question",
                               return_value=QMessageBox.StandardButton.No):
            _key(self.pane, Qt.Key.Key_Delete)
        self.assertEqual(len(self.pane._nodes[0]["children"]), 3)

    def test_a_marked_tile_drags_every_marked_playlist(self):
        _ctrl_a(self.pane)
        self.assertEqual(self.pane._board._tiles["0/1"].drag_paths(),
                         ["t1.m3u", "t2.m3u", "t3.m3u"])

    def test_pressing_a_marked_tile_keeps_the_marking_for_the_drag(self):
        _ctrl_a(self.pane)
        self.pane._board._tiles["0/1"].picked.emit("0/1")
        self.assertEqual(self.tiles(), ["0/0", "0/1", "0/2"])

    def test_a_click_without_a_drag_marks_that_tile_alone(self):
        _ctrl_a(self.pane)
        tile = self.pane._board._tiles["0/1"]
        tile.picked.emit("0/1")
        tile.released.emit("0/1")
        self.assertEqual(self.tiles(), ["0/1"])

    def test_an_unmarked_tile_drags_only_itself(self):
        self.pane._board._tiles["0/0"].picked.emit("0/0")
        self.assertEqual(self.pane._board._tiles["0/2"].drag_paths(), ["t3.m3u"])


class ListSelectAllTest(_Case):

    def setUp(self):
        super().setUp()
        self.pane._toggle_view()

    def test_ctrl_a_marks_every_entry_of_the_tree(self):
        _ctrl_a(self.pane._tree)
        self.assertEqual(len(self.pane._tree.selectedItems()), 6)

    def test_del_then_empties_the_tree_with_one_question(self):
        _ctrl_a(self.pane._tree)
        ask = self.trash()
        self.assertEqual(ask.call_count, 1)
        self.assertEqual(self.pane._nodes, [])

    def test_the_marked_playlists_drag_out_together(self):
        _ctrl_a(self.pane._tree)
        dragged = []
        with mock.patch.object(gt.QDrag, "exec",
                               lambda drag, *a: dragged.extend(
                                   u.toLocalFile() for u in drag.mimeData().urls())):
            self.pane._tree.startDrag(Qt.DropAction.CopyAction)
        self.assertEqual(sorted(os.path.basename(p) for p in dragged),
                         ["t1.m3u", "t2.m3u", "t3.m3u", "t4.m3u"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
