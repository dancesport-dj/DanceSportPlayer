"""🏆 A folder added from disk stays linked to it: own icon, 🔄 refresh.

Run:  py -m unittest tests.gui.test_tournament_linked_folder -v

"Add a folder of playlists…" used to copy what was in the folder once. The
branch now remembers the folder it came from, shows 🔗 instead of 📁, and a
menu entry on it reads the disk again — new playlists appear, deleted ones go.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tree_linked_"))

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from gui import tournament_tree as gt
from planner.store import JsonStore
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)
_ADD = "📂  Add a folder of playlists…"
_REFRESH = "🔄  Refresh from disk"


class LinkedFolderTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_tree_linked_"))
        self.store = JsonStore.at(self.dir / "t.json")
        self.pane = gt.TournamentTree(self.store)
        self.addCleanup(reap_widget, self.pane)
        self.weekend = self.dir / "DanceComp"
        self.weekend.mkdir()
        (self.weekend / "T1.m3u").write_text("#EXTM3U\n", encoding="utf-8")
        self.menu(_ADD, None, folder=self.weekend)

    def menu(self, caption, item, folder=""):
        """Open the menu on `item` (None = white space), pick `caption`."""
        offered = []

        class _Menu(gt.QMenu):   # a real exec would block
            def exec(self, *_a):
                offered.extend(a.text() for a in self.actions())
                return next((a for a in self.actions() if a.text() == caption), None)

        tree = self.pane._tree
        pos = (tree.visualItemRect(item).center() if item is not None
               else tree.viewport().rect().bottomRight())
        if item is not None:
            tree.setCurrentItem(item)
        with mock.patch.object(gt, "QMenu", _Menu), \
                mock.patch.object(QFileDialog, "getExistingDirectory",
                                  return_value=str(folder)), \
                mock.patch.object(QMessageBox, "information"):
            self.pane._on_context_menu(pos)
        return offered

    def linked(self):
        return self.pane._tree.topLevelItem(0)

    def test_the_branch_remembers_its_folder(self):
        self.assertEqual(self.pane._nodes[0]["source"], str(self.weekend))

    def test_the_link_survives_a_restart(self):
        again = gt.TournamentTree(self.store)
        self.addCleanup(reap_widget, again)
        self.assertEqual(again._nodes[0]["source"], str(self.weekend))

    def test_it_shows_its_own_icon(self):
        self.assertTrue(self.linked().text(0).startswith("🔗"))

    def test_a_plain_folder_keeps_the_folder_icon(self):
        self.pane._nodes.append({"name": "Hand", "children": []})
        self.pane._rebuild()
        self.assertTrue(self.pane._tree.topLevelItem(1).text(0).startswith("📁"))

    def test_only_a_linked_folder_offers_the_refresh(self):
        self.pane._nodes.append({"name": "Hand", "children": []})
        self.pane._rebuild()
        self.assertIn(_REFRESH, self.menu("", self.linked()))
        self.assertNotIn(_REFRESH, self.menu("", self.pane._tree.topLevelItem(1)))
        self.assertNotIn(_REFRESH, self.menu("", None))

    def test_refresh_reads_the_disk_again(self):
        (self.weekend / "T2.m3u").write_text("#EXTM3U\n", encoding="utf-8")
        (self.weekend / "T1.m3u").unlink()
        self.menu(_REFRESH, self.linked())
        self.assertEqual([c["name"] for c in self.pane._nodes[0]["children"]], ["T2"])
        self.assertEqual(self.pane._nodes[0]["source"], str(self.weekend))

    def test_refresh_keeps_a_name_the_operator_gave(self):
        self.pane._nodes[0]["name"] = "Saturday"
        self.pane._rebuild()
        self.menu(_REFRESH, self.linked())
        self.assertEqual(self.pane._nodes[0]["name"], "Saturday")

    # Full review 2026-11-11 #3: the refresh replaced the whole branch, so
    # everything done to it below the top level was lost.

    def names(self, node=None):
        node = self.pane._nodes[0] if node is None else node
        return [c["name"] for c in node["children"]]

    def child(self, name):
        return next(c for c in self.pane._nodes[0]["children"] if c["name"] == name)

    def test_refresh_keeps_a_renamed_playlist(self):
        self.pane._nodes[0]["children"][0]["name"] = "Opening"
        (self.weekend / "T2.m3u").write_text("#EXTM3U\n", encoding="utf-8")
        self.menu(_REFRESH, self.linked())
        self.assertEqual(self.names(), ["Opening", "T2"])

    def test_refresh_keeps_a_playlist_filed_in_by_hand(self):
        other = self.dir / "Other.m3u"
        other.write_text("#EXTM3U\n", encoding="utf-8")
        self.pane._nodes[0]["children"].append({"name": "Other", "m3u": str(other)})
        self.menu(_REFRESH, self.linked())
        self.assertEqual(self.names(), ["T1", "Other"])

    def test_refresh_keeps_a_folder_of_the_operators_own(self):
        node = self.pane._nodes[0]
        t1 = node["children"].pop(0)
        node["children"].append({"name": "Mine", "children": [t1]})
        self.menu(_REFRESH, self.linked())
        self.assertEqual(self.names(), ["Mine"])
        self.assertEqual(self.names(node["children"][0]), ["T1"])

    def test_a_new_playlist_lands_in_its_known_sub_folder(self):
        latin = self.weekend / "Latin"
        latin.mkdir()
        (latin / "L1.m3u").write_text("#EXTM3U\n", encoding="utf-8")
        self.menu(_REFRESH, self.linked())
        self.child("Latin")["children"][0]["name"] = "Rumba first"
        (latin / "L2.m3u").write_text("#EXTM3U\n", encoding="utf-8")
        self.menu(_REFRESH, self.linked())
        self.assertEqual(self.names(), ["T1", "Latin"])   # a new folder goes last
        self.assertEqual(self.names(self.child("Latin")), ["Rumba first", "L2"])

    def test_a_sub_folder_that_could_not_be_read_keeps_its_playlists(self):
        latin = self.weekend / "Latin"
        latin.mkdir()
        (latin / "L1.m3u").write_text("#EXTM3U\n", encoding="utf-8")
        self.menu(_REFRESH, self.linked())
        real = gt.TournamentTree._folder_node

        def unreadable_latin(pane, folder, *a, **kw):
            return None if folder.name == "Latin" else real(pane, folder, *a, **kw)

        with mock.patch.object(gt.TournamentTree, "_folder_node", unreadable_latin):
            self.menu(_REFRESH, self.linked())
        self.assertEqual(self.names(self.child("Latin")), ["L1"])

    def test_a_folder_that_is_gone_leaves_the_branch_alone(self):
        (self.weekend / "T1.m3u").unlink()
        self.weekend.rmdir()
        self.menu(_REFRESH, self.linked())
        self.assertEqual([c["name"] for c in self.pane._nodes[0]["children"]], ["T1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
