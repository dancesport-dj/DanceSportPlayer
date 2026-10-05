"""🏆 "Add a folder of playlists…" files a disk folder as a branch of the tree.

Run:  py -m unittest tests.gui.test_tournament_add_folder -v

Marcel wanted, beside "＋ Add playlists…", a menu entry that takes a whole
folder with all its playlists — what dropping that folder in from Explorer
already does, without needing Explorer open beside the app.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tree_add_folder_"))

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox  # noqa: E402

from gui import tournament_tree as gt  # noqa: E402
from planner.store import JsonStore  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)
_CAPTION = "📂  Add a folder of playlists…"


class AddFolderTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_tree_add_folder_"))
        self.pane = gt.TournamentTree(JsonStore.at(self.dir / "t.json"))
        self.addCleanup(reap_widget, self.pane)
        self.pane._nodes.append({"name": "Saison 2026", "children": []})
        self.pane._rebuild()
        self.pane._tree.setCurrentItem(self.pane._tree.topLevelItem(0))
        self.weekend = self.dir / "DanceComp"
        (self.weekend / "Samstag").mkdir(parents=True)
        for f in (self.weekend / "Freitag T1.m3u",
                  self.weekend / "Samstag" / "T2.m3u"):
            f.write_text("#EXTM3U\n", encoding="utf-8")

    def choose(self, caption, folder):
        """Open the folder row's menu, pick `caption`, answer the folder dialog
        with `folder`. Returns every caption the menu offered."""
        offered = []

        class _Menu(gt.QMenu):   # a real exec would block
            def exec(self, *_a):
                offered.extend(a.text() for a in self.actions())
                return next((a for a in self.actions() if a.text() == caption), None)

        tree = self.pane._tree
        pos = tree.visualItemRect(tree.topLevelItem(0)).center()
        with mock.patch.object(gt, "QMenu", _Menu), \
                mock.patch.object(QFileDialog, "getExistingDirectory",
                                  return_value=str(folder)), \
                mock.patch.object(QMessageBox, "information"):
            self.pane._on_context_menu(pos)
        return offered

    def test_it_sits_beside_add_playlists(self):
        offered = self.choose("", "")
        self.assertIn(_CAPTION, offered)
        self.assertEqual(offered.index(_CAPTION),
                         offered.index("＋  Add playlists…") + 1)

    def test_the_folder_arrives_as_its_branch_in_the_picked_folder(self):
        self.choose(_CAPTION, self.weekend)
        self.assertEqual(self.pane._nodes[0]["children"], [
            {"name": "DanceComp", "children": [
                {"name": "Samstag", "children": [
                    {"name": "T2", "m3u": str(self.weekend / "Samstag" / "T2.m3u")}]},
                {"name": "Freitag T1", "m3u": str(self.weekend / "Freitag T1.m3u")}]}])

    def test_cancelling_the_dialog_files_nothing(self):
        self.choose(_CAPTION, "")
        self.assertEqual(self.pane._nodes[0]["children"], [])

    def test_a_folder_without_playlists_files_nothing(self):
        empty = self.dir / "leer"
        empty.mkdir()
        self.choose(_CAPTION, empty)
        self.assertEqual(self.pane._nodes[0]["children"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
