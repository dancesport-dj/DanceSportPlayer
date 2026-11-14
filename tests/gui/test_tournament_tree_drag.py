"""🏆 Dragging inside the tree rearranges it: reorder, or nest a folder.

Run:  py -m unittest tests.gui.test_tournament_tree_drag -v

Marcel: "drag and drop it in the tree view for rearrangement or to put a dir in
a subdir". A drag out of the tree carries the .m3u files as URLs (that is what a
deck takes), so dropped back on the tree it used to be filed a second time.
Now a drag that started in the tree moves the entries it grabbed.

The drag is replayed through a stand-in for QDrag: it hands the dragged mime
data to the tree's own enter / move / drop handlers at a chosen row.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tree_drag_"))

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QApplication

from gui import tournament_tiles as tiles
from gui import tournament_tree as gt
from planner.store import JsonStore
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)


def _names(nodes):
    return [n["name"] + ("" if n.get("m3u") else "/") +
            ("[" + ",".join(_names(n.get("children") or [])) + "]"
             if not n.get("m3u") else "") for n in nodes]


class _FakeDrag:
    """Takes the place of QDrag: exec() plays the drop at `FakeDrag.target`."""
    target = None   # (item, fraction of the row's height from its top)
    tree = None

    def __init__(self, source):
        self.mime = None

    def setMimeData(self, mime):
        self.mime = mime

    def setPixmap(self, *_a):
        pass

    def exec(self, *_a):
        tree = _FakeDrag.tree
        item, frac = _FakeDrag.target
        if item is None:   # the empty space under the last row
            rect = tree.visualItemRect(tree.topLevelItem(tree.topLevelItemCount() - 1))
            pos = QPoint(rect.center().x(), rect.bottom() + 30)
        else:
            rect = tree.visualItemRect(item)
            pos = QPoint(rect.center().x(), rect.top() + int(rect.height() * frac))
        acts = Qt.DropAction.CopyAction | Qt.DropAction.MoveAction
        args = (pos, acts, self.mime, Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier)
        tree.dragEnterEvent(QDragEnterEvent(*args))
        move = QDragMoveEvent(*args)
        tree.dragMoveEvent(move)
        self.accepted = move.isAccepted()
        if self.accepted:
            tree.dropEvent(QDropEvent(QPointF(pos), acts, self.mime,
                                      Qt.MouseButton.LeftButton,
                                      Qt.KeyboardModifier.NoModifier))
        _FakeDrag.last_accepted = self.accepted
        return Qt.DropAction.MoveAction


class TreeDragTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_tree_drag_"))
        self.pane = gt.TournamentTree(JsonStore.at(self.dir / "t.json"))
        self.addCleanup(reap_widget, self.pane)
        for name in ("A", "B", "C"):
            (self.dir / f"{name}.m3u").write_text("#EXTM3U\n", encoding="utf-8")
        self.pane._nodes[:] = [
            {"name": "Fr", "children": [
                {"name": "A", "m3u": str(self.dir / "A.m3u")},
                {"name": "B", "m3u": str(self.dir / "B.m3u")}]},
            {"name": "Sa", "children": [
                {"name": "Unter", "children": []},
                {"name": "C", "m3u": str(self.dir / "C.m3u")}]},
            {"name": "So", "children": []}]
        self.pane._toggle_view()      # ▤ — the leaves are rows
        self.pane.resize(900, 400)
        self.pane.show()
        _app.processEvents()
        self.tree = self.pane._tree
        patch = mock.patch.object(tiles, "QDrag", _FakeDrag)
        patch.start()
        self.addCleanup(patch.stop)
        _FakeDrag.tree = self.tree
        _FakeDrag.last_accepted = None

    def item(self, key):
        it = gt.QTreeWidgetItemIterator(self.tree)
        while it.value():
            if it.value().data(0, gt.ROLE_KEY) == key:
                return it.value()
            it += 1
        raise KeyError(key)

    def drag(self, keys, onto, frac):
        """Select the rows `keys`, drag them to row `onto` at `frac` of its height."""
        self.tree.clearSelection()
        self.tree.setCurrentItem(self.item(keys[0]))   # this resets the marks…
        for k in keys:
            self.item(k).setSelected(True)             # …so mark after it
        _FakeDrag.target = (self.item(onto) if onto is not None else None, frac)
        self.tree.startDrag(Qt.DropAction.CopyAction)
        _app.processEvents()   # the move lands on the next tick

    def shape(self):
        return _names(self.pane._nodes)

    def test_a_playlist_dragged_within_the_tree_is_moved_not_filed_twice(self):
        self.drag(["0/0"], "1/0", 0.5)       # A onto the folder "Unter"
        self.assertEqual(self.shape(),
                         ["Fr/[B]", "Sa/[Unter/[A],C]", "So/[]"])

    def test_a_folder_goes_into_another_folder(self):
        self.drag(["2"], "1", 0.5)           # So onto Sa
        self.assertEqual(self.shape(),
                         ["Fr/[A,B]", "Sa/[Unter/[],C,So/[]]"])

    def test_a_row_dropped_on_the_upper_edge_goes_before_it(self):
        self.drag(["2"], "0", 0.05)          # So before Fr
        self.assertEqual([n["name"] for n in self.pane._nodes], ["So", "Fr", "Sa"])

    def test_a_row_dropped_on_the_lower_edge_goes_after_it(self):
        self.drag(["0"], "2", 0.95)          # Fr after So
        self.assertEqual([n["name"] for n in self.pane._nodes], ["Sa", "So", "Fr"])

    def test_the_line_under_an_open_folder_means_its_first_entry(self):
        self.drag(["2"], "0", 0.95)          # So under the open folder Fr
        self.assertEqual(self.shape(),
                         ["Fr/[So/[],A,B]", "Sa/[Unter/[],C]"])

    def test_a_playlist_dropped_on_a_playlist_lands_beside_it(self):
        self.drag(["1/1"], "0/0", 0.2)       # C before A
        self.assertEqual(self.shape(),
                         ["Fr/[C,A,B]", "Sa/[Unter/[]]", "So/[]"])

    def test_the_empty_space_below_files_it_at_the_top_level(self):
        self.drag(["0/0"], None, 0.5)        # A to the root
        self.assertEqual(self.shape()[-1], "A")

    def test_a_folder_cannot_go_into_itself_or_its_own_child(self):
        self.drag(["1"], "1/0", 0.5)         # Sa into Unter (its own child)
        self.assertFalse(_FakeDrag.last_accepted)
        self.drag(["1"], "1", 0.5)           # Sa onto Sa
        self.assertFalse(_FakeDrag.last_accepted)
        self.assertEqual(self.shape(),
                         ["Fr/[A,B]", "Sa/[Unter/[],C]", "So/[]"])

    def test_several_marked_rows_move_together_in_tree_order(self):
        self.drag(["0/1", "0/0"], "2", 0.5)  # B, A (marked in that order) onto So
        self.assertEqual(self.shape(),
                         ["Fr/[]", "Sa/[Unter/[],C]", "So/[A,B]"])

    def test_a_marked_folder_takes_its_marked_child_along_once(self):
        self.drag(["0", "0/0"], "2", 0.5)    # Fr and its child A onto So
        self.assertEqual(self.shape(),
                         ["Sa/[Unter/[],C]", "So/[Fr/[A,B]]"])

    def test_the_moved_entry_is_the_picked_one_and_the_move_is_saved(self):
        self.drag(["0/0"], "1/0", 0.5)
        self.assertEqual(self.pane._current_node()["name"], "A")
        saved = gt.load_tree(self.pane._store)
        self.assertEqual(_names(saved), self.shape())

    def test_the_playlist_still_leaves_as_a_file_for_a_deck(self):
        self.tree.clearSelection()
        self.item("0/0").setSelected(True)
        seen = []
        _FakeDrag.target = (self.item("0"), 0.5)
        real = _FakeDrag.exec
        _FakeDrag.exec = lambda s, *a: seen.append(s.mime) or Qt.DropAction.CopyAction
        try:
            self.tree.startDrag(Qt.DropAction.CopyAction)
        finally:
            _FakeDrag.exec = real
        self.assertEqual([Path(u.toLocalFile()) for u in seen[0].urls()],
                         [self.dir / "A.m3u"])

    def test_files_dragged_in_from_explorer_are_still_filed(self):
        extra = self.dir / "Neu.m3u"
        extra.write_text("#EXTM3U\n", encoding="utf-8")
        from PySide6.QtCore import QMimeData, QUrl
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(extra))])
        pos = self.tree.visualItemRect(self.item("2")).center()
        self.tree.dropEvent(QDropEvent(
            QPointF(pos), Qt.DropAction.CopyAction, mime,
            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        _app.processEvents()
        self.assertEqual(self.shape()[-1], "So/[Neu]")


if __name__ == "__main__":
    unittest.main()
