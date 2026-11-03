#!/usr/bin/env python3
"""📁 The folder tree: a short top, a search box and a sort choice.

Run:  py -m unittest tests.gui.test_library_folder_tree_view -v
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_foldertree_"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from gui.library_browser import LibraryBrowser
from gui.library_folders import FolderTree
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget


def entry(path):
    p = Path(path)
    return MusicEntry(path=p, title=p.stem, dance="LW", duration=180)


LIBRARY = [
    entry("D:/Musik/tanzcds/Latein/a.mp3"),
    entry("D:/Musik/tanzcds/Latein/b.mp3"),
    entry("D:/Musik/tanzcds/Standard/c.mp3"),
    entry("D:/Downloads/Samba night/d.mp3"),
    entry("D:/Downloads/Samples/e.mp3"),
    entry("D:/Downloads/Samples/f.mp3"),
    entry("D:/Downloads/Samples/g.mp3"),
]


def labels(tree, parent=None):
    """The visible lines of the tree, as (depth, text)."""
    out = []

    def walk(item, depth):
        if item.isHidden():
            return
        out.append((depth, item.text(0)))
        for i in range(item.childCount()):
            walk(item.child(i), depth + 1)

    if parent is None:
        for i in range(tree.topLevelItemCount()):
            walk(tree.topLevelItem(i), 0)
    return out


class TreeViewTest(unittest.TestCase):

    def setUp(self):
        self.app = QApplication.instance() or QApplication([])
        self.tree = FolderTree()
        self.addCleanup(reap_widget, self.tree)
        self.tree.set_titles(LIBRARY)

    def names(self):
        return [t for _d, t in labels(self.tree)]

    def test_a_shared_drive_line_is_left_out(self):
        tops = [t for d, t in labels(self.tree) if d == 0]
        self.assertEqual(len(tops), 3, tops)
        self.assertTrue(any(t.startswith("tanzcds") for t in tops), tops)
        self.assertFalse(any(t.rstrip().endswith(":\\") for t in tops), tops)

    def test_every_folder_line_has_the_same_folder_icon(self):
        items = [i for i in self.tree.all_items() if i.data(0, Qt.ItemDataRole.UserRole)]
        self.assertTrue(items)
        for item in items:
            self.assertFalse(item.icon(0).isNull(), item.text(0))
        self.assertEqual({i.icon(0).cacheKey() for i in items},
                         {items[0].icon(0).cacheKey()})
        self.assertEqual(items[0].icon(0).cacheKey(), self.tree._folder_icon.cacheKey())

    def test_the_tooltip_still_has_the_whole_path(self):
        top = next(i for i in self.tree.all_items()
                   if i.text(0).startswith("tanzcds"))
        self.assertTrue(top.toolTip(0).startswith("D:"), top.toolTip(0))

    def test_search_keeps_matches_and_their_parents(self):
        self.tree.set_search("sam")
        names = self.names()
        self.assertTrue(any("Samba night" in n for n in names), names)
        self.assertTrue(any("Samples" in n for n in names), names)
        self.assertFalse(any("Latein" in n for n in names), names)
        self.assertFalse(any("Standard" in n for n in names), names)

    def test_clearing_the_search_brings_everything_back(self):
        before = self.names()
        self.tree.set_search("sam")
        self.tree.set_search("")
        self.assertEqual(self.names(), before)

    def test_search_ignores_case(self):
        self.tree.set_search("LATEIN")
        self.assertTrue(any("Latein" in n for n in self.names()))

    def test_the_chosen_folder_survives_a_search_that_hides_it(self):
        latein = next(i for i in self.tree.all_items() if i.text(0).startswith("Latein"))
        self.tree.setCurrentItem(latein)
        key = self.tree.folder()
        self.tree.set_search("sam")
        self.assertEqual(self.tree.folder(), key)

    def test_sorting_by_count_puts_the_biggest_folder_first(self):
        self.tree.set_sort("count")
        under = next(i for i in self.tree.all_items() if i.text(0).startswith("Downloads"))
        first = under.child(0).text(0)
        self.assertTrue(first.startswith("Samples"), first)

    def test_sorting_by_name_is_alphabetical(self):
        self.tree.set_sort("count")
        self.tree.set_sort("name")
        under = next(i for i in self.tree.all_items() if i.text(0).startswith("Downloads"))
        self.assertTrue(under.child(0).text(0).startswith("Samba night"))

    def test_sorting_keeps_the_chosen_folder(self):
        samples = next(i for i in self.tree.all_items() if i.text(0).startswith("Samples"))
        self.tree.setCurrentItem(samples)
        key = self.tree.folder()
        self.tree.set_sort("count")
        self.assertEqual(self.tree.folder(), key)


class PaneTest(unittest.TestCase):

    def setUp(self):
        self.app = QApplication.instance() or QApplication([])
        self.browser = LibraryBrowser()
        self.addCleanup(reap_widget, self.browser)
        self.browser.set_entries(LIBRARY)
        self.browser._folder_btn.click()

    def test_the_search_box_and_sort_choice_drive_the_tree(self):
        self.browser._folder_search.setText("sam")
        self.assertTrue(any("Samples" in t for _d, t in labels(self.browser._folders)))
        self.assertFalse(any("Latein" in t for _d, t in labels(self.browser._folders)))
        self.sortAction("count").trigger()
        self.assertEqual(self.browser._folders.sort_mode(), "count")
        self.sortAction("name").trigger()
        self.assertEqual(self.browser._folders.sort_mode(), "name")

    def sortAction(self, mode):
        menu = self.browser._folder_filter.menu()
        return next(a for a in menu.actions() if a.data() == mode)

    def test_the_sort_choice_is_an_icon_button_beside_the_search_box(self):
        self.assertFalse(hasattr(self.browser, "_folder_sort"))
        button = self.browser._folder_filter
        self.assertFalse(button.icon().isNull())
        self.assertEqual(button.parentWidget(), self.browser._folder_search.parentWidget())
        row = self.browser._folder_pane.layout().itemAt(0).layout()
        self.assertIsNotNone(row)
        self.assertIs(row.itemAt(0).widget(), self.browser._folder_search)
        self.assertIs(row.itemAt(1).widget(), button)

    def test_the_menu_ticks_the_active_sort_and_the_button_shows_a_change(self):
        by_name, by_size = self.sortAction("name"), self.sortAction("count")
        self.assertTrue(by_name.isChecked())
        self.assertFalse(self.browser._folder_filter.isChecked())
        by_size.trigger()
        self.assertTrue(by_size.isChecked())
        self.assertFalse(by_name.isChecked())
        self.assertTrue(self.browser._folder_filter.isChecked())

    def test_the_search_box_hides_with_the_tree(self):
        self.browser.show()
        self.assertTrue(self.browser._folder_search.isVisible())
        self.browser._folder_btn.click()
        self.assertFalse(self.browser._folder_search.isVisible())


if __name__ == "__main__":
    unittest.main()
