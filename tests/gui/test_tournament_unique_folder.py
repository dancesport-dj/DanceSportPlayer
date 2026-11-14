"""🏆 Two folders on one level of the tournament tree may not share a name.

Run:  py -m unittest tests.gui.test_tournament_unique_folder -v

Marcel: "I can create two folders next to each other both named 'u'". Names are
compared without regard to case (the disk folders they mirror are, on Windows),
only among folders of the same level, and only against other folders: a
playlist called like a folder is no clash.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tree_unique_"))

from PySide6.QtWidgets import QApplication, QInputDialog

from gui import tournament_tree as gt
from planner.store import JsonStore
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)


class UniqueFolderTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_tree_unique_"))
        self.pane = gt.TournamentTree(JsonStore.at(self.dir / "t.json"))
        self.addCleanup(reap_widget, self.pane)
        self.pane._nodes.extend([
            {"name": "u", "children": [{"name": "T1", "children": []},
                                       {"name": "Cup", "m3u": "cup.m3u"}]},
            {"name": "Samstag", "children": []}])
        self.pane._rebuild()
        info = mock.patch.object(gt.QMessageBox, "information")
        self.info = info.start()
        self.addCleanup(info.stop)

    def names(self, nodes=None):
        return [n["name"] for n in (self.pane._nodes if nodes is None else nodes)]

    def new_folder(self, name):
        with mock.patch.object(QInputDialog, "getText", return_value=(name, True)):
            self.pane._add_folder()

    def rename(self, node, name):
        with mock.patch.object(QInputDialog, "getText", return_value=(name, True)):
            self.pane._rename_node(node)

    def pick_top(self, row):
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(row))

    def test_a_second_folder_of_the_same_name_is_refused(self):
        self.pane._tree.setCurrentItem(None)
        self.pane._tree.clearSelection()
        self.new_folder("u")
        self.assertEqual(self.names(), ["u", "Samstag"])
        self.info.assert_called_once()

    def test_case_does_not_make_a_name_new(self):
        self.pane._tree.setCurrentItem(None)
        self.pane._tree.clearSelection()
        self.new_folder("SAMSTAG")
        self.assertEqual(self.names(), ["u", "Samstag"])

    def test_the_check_is_on_the_level_the_folder_goes_into(self):
        self.pick_top(0)
        self.new_folder("T1")
        self.assertEqual(self.names(self.pane._nodes[0]["children"]), ["T1", "Cup"])
        self.info.assert_called_once()

    def test_the_same_name_one_level_down_is_fine(self):
        self.pick_top(1)
        self.new_folder("u")
        self.assertEqual(self.names(self.pane._nodes[1]["children"]), ["u"])
        self.info.assert_not_called()

    def test_a_playlist_of_that_name_is_no_clash(self):
        self.pick_top(0)
        self.new_folder("Cup")
        self.assertEqual(self.names(self.pane._nodes[0]["children"]),
                         ["T1", "Cup", "Cup"])
        self.info.assert_not_called()

    def test_a_new_name_is_added(self):
        self.pane._tree.setCurrentItem(None)
        self.pane._tree.clearSelection()
        self.new_folder("Sonntag")
        self.assertEqual(self.names(), ["u", "Samstag", "Sonntag"])
        self.info.assert_not_called()

    def test_renaming_onto_a_sibling_is_refused(self):
        node = self.pane._nodes[1]
        self.rename(node, "u")
        self.assertEqual(node["name"], "Samstag")
        self.info.assert_called_once()

    def test_renaming_a_folder_to_its_own_name_or_case_is_fine(self):
        node = self.pane._nodes[1]
        self.rename(node, "samstag")
        self.assertEqual(node["name"], "samstag")
        self.info.assert_not_called()

    def test_renaming_to_a_free_name_works(self):
        node = self.pane._nodes[1]
        self.rename(node, "Sonntag")
        self.assertEqual(node["name"], "Sonntag")

    def test_the_message_is_translated(self):
        from planner.i18n.lang_de import CATALOG
        self.pick_top(0)
        self.new_folder("T1")
        text = self.info.call_args.args[2]
        self.assertIn(text.replace("“T1”", "“%s”"), CATALOG)


if __name__ == "__main__":
    unittest.main()
