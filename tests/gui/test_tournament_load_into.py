"""🏆 "Load into…" on a playlist of the tree: Playlist 1-4, Wishlist 1-2, Party.

Run:  py -m unittest tests.gui.test_tournament_load_into -v

Marcel wanted to send a filed playlist to a chosen list from its context menu,
instead of loading it onto whichever deck happens to have the focus. On the ▦
board the playlists are tiles, in the ▤ view they are tree rows: both menus
carry the entry, folders do not.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tree_load_into_"))

from PySide6.QtWidgets import QApplication, QMessageBox

from gui import tournament_tree as gt
from planner.store import JsonStore
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)

_WANTED = ["Playlist 1", "Playlist 2", "Playlist 3", "Playlist 4",
           "Wishlist 1", "Wishlist 2", "Party"]


class LoadIntoMenuTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_tree_load_into_"))
        self.m3u = self.dir / "T1.m3u"
        self.m3u.write_text("#EXTM3U\n", encoding="utf-8")
        self.pane = gt.TournamentTree(JsonStore.at(self.dir / "t.json"))
        self.addCleanup(reap_widget, self.pane)
        self.pane._nodes.append({"name": "Freitag", "children": [
            {"name": "T1", "m3u": str(self.m3u)}]})
        self.pane._rebuild()
        self.requests = []
        self.pane.loadIntoRequested.connect(
            lambda *a: self.requests.append(a))

    def pick(self, show, label):
        """Run `show()` (opens a menu) and choose `label` inside the "Load into"
        submenu. Returns (top-level captions, the submenu's captions)."""
        seen = {"top": [], "sub": []}

        class _Menu(gt.QMenu):
            def exec(self, *_a):
                seen["top"] = [a.text() for a in self.actions()]
                chosen = None
                for a in self.actions():
                    if a.menu() is not None:
                        seen["sub"] = [x.text() for x in a.menu().actions()]
                        chosen = next((x for x in a.menu().actions()
                                       if x.text() == label), None)
                return chosen

        with mock.patch.object(gt, "QMenu", _Menu), \
                mock.patch.object(QMessageBox, "warning"):
            show()
        return seen

    def tile_menu(self, label):
        return self.pick(lambda: self.pane._on_slot_menu("0/0", self.pane.pos()),
                         label)

    def test_a_tile_offers_every_list(self):
        seen = self.tile_menu("")
        self.assertEqual(seen["sub"], _WANTED)

    def test_choosing_a_list_asks_for_that_list(self):
        self.tile_menu("Wishlist 2")
        self.assertEqual(self.requests, [(str(self.m3u), "wish", 2)])
        self.requests.clear()
        self.tile_menu("Playlist 4")
        self.assertEqual(self.requests, [(str(self.m3u), "deck", 4)])
        self.requests.clear()
        self.tile_menu("Party")
        self.assertEqual(self.requests, [(str(self.m3u), "party", 1)])

    def test_a_row_in_the_list_view_offers_it_too(self):
        self.pane._toggle_view()
        tree = self.pane._tree
        folder = tree.topLevelItem(0)
        leaf = folder.child(0)
        pos = tree.visualItemRect(leaf).center()
        seen = self.pick(lambda: self.pane._on_context_menu(pos), "Playlist 3")
        self.assertEqual(seen["sub"], _WANTED)
        self.assertEqual(self.requests, [(str(self.m3u), "deck", 3)])

    def test_a_folder_row_does_not(self):
        tree = self.pane._tree
        pos = tree.visualItemRect(tree.topLevelItem(0)).center()
        seen = self.pick(lambda: self.pane._on_context_menu(pos), "Party")
        self.assertEqual(seen["sub"], [])
        self.assertEqual(self.requests, [])

    def test_a_missing_file_is_not_requested(self):
        self.m3u.unlink()
        self.tile_menu("Party")
        self.assertEqual(self.requests, [])


if __name__ == "__main__":
    unittest.main()
