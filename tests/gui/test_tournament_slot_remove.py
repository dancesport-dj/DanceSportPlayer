"""🏆 A playlist picked on the slot board is what Del and 🗑 remove.

Run:  py -m unittest tests.gui.test_tournament_slot_remove -v

Marcel: "single select a playlist under turnier baum should with entf also
delete it not the whole folder", then "trash button is not working there".
On the ▦ board the tree's current row is the FOLDER, so Del, 🗑 and F2 all
reached for the folder while a single tile was the thing picked.
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tree_slot_rm_"))

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QKeyEvent  # noqa: E402
from PySide6.QtWidgets import (QApplication, QInputDialog, QMessageBox,  # noqa: E402
                               QToolButton)

from gui import tournament_tree as gt  # noqa: E402
from planner.store import JsonStore  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)
_YES = QMessageBox.StandardButton.Yes


class SlotRemoveTest(unittest.TestCase):

    def setUp(self):
        d = tempfile.mkdtemp(prefix="dp_tree_slot_rm_")
        self.pane = gt.TournamentTree(JsonStore.at(os.path.join(d, "t.json")))
        self.addCleanup(reap_widget, self.pane)
        self.pane._nodes.append({"name": "Freitag", "children": [
            {"name": "T1", "m3u": "t1.m3u"}, {"name": "T2", "m3u": "t2.m3u"}]})
        self.pane._rebuild()
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))

    def names(self):
        return [n["name"] for n in self.pane._nodes[0]["children"]] \
            if self.pane._nodes else None

    def press(self, key):
        self.pane.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, key,
                                          Qt.KeyboardModifier.NoModifier))

    def trash(self):
        return next(b for b in self.pane.findChildren(QToolButton)
                    if b.text() == "🗑")

    def test_del_removes_the_picked_playlist_not_its_folder(self):
        self.pane._board._tiles["0/1"].picked.emit("0/1")
        with mock.patch.object(QMessageBox, "question", return_value=_YES):
            self.press(Qt.Key.Key_Delete)
        self.assertEqual(self.names(), ["T1"])

    def test_the_trash_button_removes_the_picked_playlist(self):
        self.pane._board._tiles["0/0"].picked.emit("0/0")
        with mock.patch.object(QMessageBox, "question", return_value=_YES):
            self.trash().click()
        self.assertEqual(self.names(), ["T2"])

    def test_f2_renames_the_picked_playlist(self):
        self.pane._board._tiles["0/0"].picked.emit("0/0")
        with mock.patch.object(QInputDialog, "getText", return_value=("Neu", True)):
            self.press(Qt.Key.Key_F2)
        self.assertEqual(self.names(), ["Neu", "T2"])
        self.assertEqual(self.pane._nodes[0]["name"], "Freitag")

    def test_without_a_picked_tile_del_still_means_the_folder(self):
        with mock.patch.object(QMessageBox, "question", return_value=_YES):
            self.press(Qt.Key.Key_Delete)
        self.assertEqual(self.pane._nodes, [])

    def test_clicking_the_folder_again_drops_the_tile_pick(self):
        self.pane._board._tiles["0/0"].picked.emit("0/0")
        self.pane._tree.itemPressed.emit(self.pane._tree.topLevelItem(0), 0)
        with mock.patch.object(QMessageBox, "question", return_value=_YES):
            self.press(Qt.Key.Key_Delete)
        self.assertEqual(self.pane._nodes, [])

    def test_the_folder_rows_menu_acts_on_the_folder(self):
        self.pane._board._tiles["0/0"].picked.emit("0/0")
        tree = self.pane._tree
        pos = tree.visualItemRect(tree.topLevelItem(0)).center()

        class _Menu(gt.QMenu):   # a real exec would block
            def exec(self, *_a):
                return next(a for a in self.actions() if "Remove" in a.text())

        with mock.patch.object(gt, "QMenu", _Menu),                 mock.patch.object(QMessageBox, "question", return_value=_YES):
            self.pane._on_context_menu(pos)
        self.assertEqual(self.pane._nodes, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
