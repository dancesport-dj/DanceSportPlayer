"""🏆 "New folder…" from the white space makes a top-level folder.

Run:  py -m unittest tests.gui.test_tournament_blank_folder -v

With every folder collapsed the selected one is still the tree's current item,
out of sight. A right-click on the empty part of the tree then filed the new
folder into it — a sub-folder nobody could see — instead of at the top.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tree_blank_folder_"))

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QInputDialog

from gui import tournament_tree as gt
from planner.store import JsonStore
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)
_CAPTION = "📁  New folder…"


class BlankFolderTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_tree_blank_folder_"))
        self.pane = gt.TournamentTree(JsonStore.at(self.dir / "t.json"))
        self.addCleanup(reap_widget, self.pane)
        self.pane._nodes.append({"name": "Saison 2026", "children": []})
        self.pane._rebuild()
        self.tree = self.pane._tree
        self.tree.collapseAll()
        self.tree.setCurrentItem(self.tree.topLevelItem(0))

    def new_folder(self, pos, name="Neu"):
        class _Menu(gt.QMenu):   # a real exec would block
            def exec(self, *_a):
                return next((a for a in self.actions() if a.text() == _CAPTION), None)

        with mock.patch.object(gt, "QMenu", _Menu), \
                mock.patch.object(QInputDialog, "getText", return_value=(name, True)):
            self.pane._on_context_menu(pos)

    def names(self, nodes):
        return [n["name"] for n in nodes]

    def test_the_white_space_files_it_at_the_top(self):
        self.new_folder(QPoint(5, 5000))
        self.assertEqual(self.names(self.pane._nodes), ["Saison 2026", "Neu"])
        self.assertEqual(self.pane._nodes[0]["children"], [])

    def test_a_folder_row_still_takes_it_inside(self):
        row = self.tree.visualItemRect(self.tree.topLevelItem(0)).center()
        self.new_folder(row)
        self.assertEqual(self.names(self.pane._nodes), ["Saison 2026"])
        self.assertEqual(self.names(self.pane._nodes[0]["children"]), ["Neu"])


if __name__ == "__main__":
    unittest.main()
