"""🏆 What a new folder or an imported playlist does to the tree's focus.

Run:  py -m unittest tests.gui.test_tournament_focus -v

Marcel: after creating a folder or importing an .m3u the focus was still on the
old row, and a new folder at the top level opened every folder in the tree.
The new entry is what the operator is about to work on, so it is the picked
one, and every folder keeps the fold state the operator left it in.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tree_focus_"))

from PySide6.QtWidgets import QApplication, QInputDialog

from gui import tournament_tree as gt
from planner.store import JsonStore
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)


class TreeFocusTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_tree_focus_"))
        self.pane = gt.TournamentTree(JsonStore.at(self.dir / "t.json"))
        self.addCleanup(reap_widget, self.pane)
        self.pane._nodes.extend([
            {"name": "Freitag", "children": [{"name": "T1", "children": []}]},
            {"name": "Samstag", "children": [{"name": "T2", "children": []}]}])
        self.pane._rebuild()

    def current_name(self):
        node = self.pane._current_node()
        return node["name"] if node else None

    def new_folder(self, name):
        with mock.patch.object(QInputDialog, "getText", return_value=(name, True)):
            self.pane._add_folder()

    def test_a_new_folder_is_the_picked_row(self):
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        self.new_folder("Sonntag")
        self.assertEqual(self.current_name(), "Sonntag")

    def test_a_new_subfolder_is_picked_even_under_a_folded_parent(self):
        top = self.pane._tree.topLevelItem(0)
        self.pane._tree.setCurrentItem(top)
        top.setExpanded(False)
        self.new_folder("Vormittag")
        self.assertEqual(self.current_name(), "Vormittag")
        self.assertTrue(self.pane._tree.topLevelItem(0).isExpanded())

    def test_a_new_folder_leaves_the_other_folds_alone(self):
        tree = self.pane._tree
        tree.topLevelItem(0).setExpanded(False)
        tree.setCurrentItem(None)
        tree.clearSelection()
        self.new_folder("Sonntag")
        self.assertFalse(tree.topLevelItem(0).isExpanded(), "Freitag was folded")
        self.assertTrue(tree.topLevelItem(1).isExpanded(), "Samstag was open")

    def test_an_edit_does_not_open_a_folded_tree_again(self):
        self.pane._toggle_collapse_all()
        self.new_folder("Sonntag")
        tree = self.pane._tree
        self.assertFalse(tree.topLevelItem(0).isExpanded())
        self.assertFalse(tree.topLevelItem(1).isExpanded())

    def test_an_imported_playlist_is_the_picked_one(self):
        m3u = self.dir / "Neu.m3u"
        m3u.write_text("#EXTM3U\n", encoding="utf-8")
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(1))
        self.pane._add_m3u_files(self.pane._target_children(), [m3u])
        # ▦ view: the playlist is a tile on its folder's board
        folder = self.pane._current_node()
        self.assertEqual(folder["name"], "Samstag")
        self.assertEqual(self.pane._board.selected_keys, ["1/1"])

    def test_an_imported_playlist_is_the_picked_row_in_the_list_view(self):
        self.pane._toggle_view()
        m3u = self.dir / "Neu.m3u"
        m3u.write_text("#EXTM3U\n", encoding="utf-8")
        self.pane._add_m3u_files(self.pane._target_children(), [m3u])
        self.assertEqual(self.current_name(), "Neu")

    def test_an_imported_folder_is_the_picked_branch(self):
        src = self.dir / "Wochenende"
        src.mkdir()
        (src / "A.m3u").write_text("#EXTM3U\n", encoding="utf-8")
        self.pane._add_m3u_files(self.pane._target_children(), [src])
        self.assertEqual(self.current_name(), "Wochenende")


class CollapseButtonPlaceTest(unittest.TestCase):
    """Marcel: the collapse button sat at the right edge of the pane, far from
    the tree it folds. It then got a row of its own above the tree, which took
    space for one button. It belongs right next to the "(n playlists)" label,
    in the toolbar row, so the tree starts straight under that row."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_tree_collapse_"))
        self.pane = gt.TournamentTree(JsonStore.at(self.dir / "t.json"))
        self.addCleanup(reap_widget, self.pane)
        self.pane.resize(900, 300)
        self.pane.show()
        _app.processEvents()

    def test_it_shares_the_row_of_the_count_label(self):
        btn, lbl = self.pane._collapse_btn, self.pane._count_lbl
        self.assertIs(btn.parentWidget(), lbl.parentWidget())
        centre = lambda w: w.mapTo(self.pane, w.rect().center()).y()
        self.assertLessEqual(abs(centre(btn) - centre(lbl)), 4)

    def test_it_sits_right_next_to_the_count_label(self):
        btn, lbl = self.pane._collapse_btn, self.pane._count_lbl
        gap = (btn.mapTo(self.pane, btn.rect().topLeft()).x()
               - lbl.mapTo(self.pane, lbl.rect().topRight()).x())
        self.assertGreaterEqual(gap, 0)
        self.assertLessEqual(gap, 12)

    def test_it_takes_no_row_of_its_own_above_the_tree(self):
        btn, tree = self.pane._collapse_btn, self.pane._tree
        btn_bottom = btn.mapTo(self.pane, btn.rect().bottomLeft()).y()
        tree_top = tree.mapTo(self.pane, tree.rect().topLeft()).y()
        # Only the toolbar row sits over the tree: no second strip between.
        self.assertLessEqual(tree_top - btn_bottom, 8)
        self.assertNotEqual(btn.parentWidget(), tree.parentWidget())

    def test_it_still_folds_and_opens_the_tree(self):
        self.pane._nodes.append({"name": "F", "children": [{"name": "G", "children": []}]})
        self.pane._rebuild()
        self.pane._collapse_btn.click()
        self.assertFalse(self.pane._tree.topLevelItem(0).isExpanded())
        self.assertEqual(self.pane._collapse_btn.text(), "⊞")
        self.pane._collapse_btn.click()
        self.assertTrue(self.pane._tree.topLevelItem(0).isExpanded())


if __name__ == "__main__":
    unittest.main()
