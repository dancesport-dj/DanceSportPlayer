#!/usr/bin/env python3
"""📁 The library as folders, with a toggle beside the whole list.

Run:  py -m unittest tests.gui.test_library_folders -v

Titles are stored in folders, so the pane can show them that way: choosing a
folder lists only the titles directly in it. In this view 🆕 Unplanned hides the
planned FILE, and a copy of that music in another folder stays with a marker.
"""

import functools
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_folders_"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from gui.library_browser import LIB_COL_TITLE, LibraryBrowser
from gui.window.main_dupes import DuplicateCheckMixin
from gui.window.main_libpane import LibraryPaneMixin
from planner.models import MusicEntry
from planner.playlist.planned import path_key
from tests.qt_test_support import reap_widget

ROOT = Path(tempfile.gettempdir(), "Music")


def entry(*parts, title=None, dance="LW"):
    path = ROOT.joinpath(*parts)
    return MusicEntry(path=path, title=title or path.stem, dance=dance, duration=180)


class FolderBase(unittest.TestCase):

    def setUp(self):
        self.app = QApplication.instance() or QApplication([])
        self.a1 = entry("Standard", "Moon.mp3")
        self.a2 = entry("Standard", "Fly.mp3")
        self.b1 = entry("Standard", "old", "Moon copy.mp3")
        self.c1 = entry("latin", "Rumba.mp3", dance="RB")
        self.entries = [self.a1, self.a2, self.b1, self.c1]
        self.browser = LibraryBrowser()
        self.addCleanup(reap_widget, self.browser)
        self.browser.set_entries(self.entries)

    def shown(self):
        return sorted(e.title for e in self.browser._shown)

    def folders_on(self):
        self.browser._folder_btn.click()

    def choose(self, folder: Path):
        tree = self.browser._folders
        for item in tree.all_items():
            if item.data(0, Qt.ItemDataRole.UserRole) == path_key(folder):
                tree.setCurrentItem(item)
                return
        self.fail(f"no {folder} in the tree")

    def unplanned_on(self):
        chk = self.browser._unplanned_chk
        chk.blockSignals(True)
        chk.setChecked(True)
        chk.blockSignals(False)

    def plan(self, on_deck, fps=None):
        """The real pane code on the real browser: `on_deck` in an open deck."""
        fps = fps or {}
        cache = SimpleNamespace(
            fingerprint=lambda p: fps.get(str(p)),
            recorded_fingerprint=lambda p: fps.get(str(p)))
        deck = SimpleNamespace(_row_meta=SimpleNamespace(entries=lambda: list(on_deck)))
        win: Any = SimpleNamespace(
            _library=SimpleNamespace(cache=cache, lib=SimpleNamespace(entries=self.entries),
                                     global_lib=None),
            _lib_browser=self.browser,
            _visible_deck_tables=lambda: [deck],
            _planned_source_tables=lambda: [deck])
        win._deck_dedup_index = functools.partial(
            DuplicateCheckMixin._deck_dedup_index, win)
        LibraryPaneMixin._refresh_library_planned_filter(win)

    def title_cell(self, title):
        table = self.browser._table
        for r in range(table.rowCount()):
            text = table.item(r, LIB_COL_TITLE).text()
            if title in text:
                return text
        self.fail(f"{title} is not listed")


class FolderViewTest(FolderBase):

    def test_the_tree_stays_away_until_asked_for(self):
        self.browser.show()
        self.assertFalse(self.browser._folders.isVisible())
        self.assertEqual(len(self.shown()), 4)

    def test_the_toggle_shows_the_tree_and_keeps_the_list(self):
        self.browser.show()
        self.folders_on()
        self.assertTrue(self.browser._folders.isVisible())
        self.assertEqual(len(self.shown()), 4, "no folder chosen yet: everything stays")

    def test_a_folder_shows_only_the_titles_directly_in_it(self):
        self.folders_on()
        self.choose(ROOT / "Standard")
        self.assertEqual(self.shown(), ["Fly", "Moon"])

    def test_a_subfolder_shows_its_own_titles(self):
        self.folders_on()
        self.choose(ROOT / "Standard" / "old")
        self.assertEqual(self.shown(), ["Moon copy"])

    def test_the_toggle_off_brings_the_whole_list_back(self):
        self.folders_on()
        self.choose(ROOT / "latin")
        self.assertEqual(self.shown(), ["Rumba"])
        self.browser._folder_btn.click()
        self.assertEqual(len(self.shown()), 4)

    def test_the_other_filters_still_apply_inside_a_folder(self):
        self.folders_on()
        self.choose(ROOT / "Standard")
        self.browser._filter_edit.setText("fly")
        self.browser._refilter()
        self.assertEqual(self.shown(), ["Fly"])

    def test_folders_differing_in_case_are_one_folder(self):
        self.entries.append(entry("STANDARD", "Waltz.mp3"))
        self.browser.set_entries(self.entries)
        self.folders_on()
        self.choose(ROOT / "standard")
        self.assertEqual(self.shown(), ["Fly", "Moon", "Waltz"])

    def test_the_chain_above_the_library_is_one_line(self):
        self.folders_on()
        tree = self.browser._folders
        self.assertEqual(tree.topLevelItemCount(), 2, "all folders + the one root")
        self.assertIn("Music", tree.topLevelItem(1).text(0))

    def test_a_folder_with_no_titles_of_its_own_cannot_be_chosen(self):
        self.folders_on()
        self.entries.append(entry("Latin2", "deep", "Samba.mp3", dance="SB"))
        self.browser.set_entries(self.entries)
        tree = self.browser._folders
        top = next(i for i in tree.all_items()
                   if i.data(0, Qt.ItemDataRole.UserRole) == path_key(ROOT))
        self.assertFalse(top.flags() & Qt.ItemFlag.ItemIsSelectable)

    def test_the_chosen_folder_stays_when_the_library_is_listed_again(self):
        self.folders_on()
        self.choose(ROOT / "latin")
        self.browser.set_entries(list(self.entries))
        self.assertEqual(self.shown(), ["Rumba"])

    def test_a_folder_that_went_away_shows_every_title_again(self):
        self.folders_on()
        self.choose(ROOT / "latin")
        self.browser.set_entries([self.a1, self.a2])
        self.assertEqual(self.shown(), ["Fly", "Moon"])

    def test_the_tree_follows_the_whole_library(self):
        other = entry("Repository", "Tango.mp3", dance="TG")
        self.folders_on()
        self.browser.set_whole_entries([other])
        self.choose(ROOT / "Repository")
        self.assertEqual(self.shown(), ["Tango"])

    def test_a_filter_from_outside_is_not_cut_down_by_a_folder(self):
        """📊 The gap dashboard asks for one dance × class view: a folder left
        chosen would read as 'the library has nothing'."""
        self.folders_on()
        self.choose(ROOT / "latin")
        self.browser.focus_filter(dance="LW")
        self.assertEqual(self.shown(), ["Fly", "Moon", "Moon copy"])

    def test_the_toggle_is_reported_for_the_settings(self):
        seen = []
        self.browser.folderViewChanged.connect(seen.append)
        self.folders_on()
        self.assertEqual(seen, [True])

    def test_a_saved_view_comes_back_silently(self):
        seen = []
        self.browser.folderViewChanged.connect(seen.append)
        self.browser.show()
        self.browser.set_folder_view(True)
        self.assertTrue(self.browser._folders.isVisible())
        self.assertEqual(seen, [])


class PerFileHidingTest(FolderBase):
    """The Moon on a deck and its copy in another folder share a fingerprint."""

    def fps(self):
        return {str(self.a1.path): "fp-moon", str(self.b1.path): "fp-moon",
                str(self.a2.path): "fp-fly", str(self.c1.path): "fp-rumba"}

    def test_the_planned_file_goes_and_its_copy_stays_marked(self):
        self.folders_on()
        self.unplanned_on()
        self.plan([self.a1], self.fps())
        self.assertEqual(self.shown(), ["Fly", "Moon copy", "Rumba"])
        self.assertNotEqual(self.title_cell("Moon copy"), "Moon copy")
        self.assertIn(self.browser.DUPLICATE_MARK, self.title_cell("Moon copy"))
        self.assertEqual(self.title_cell("Fly"), "Fly")

    def test_inside_a_folder_too(self):
        self.folders_on()
        self.unplanned_on()
        self.plan([self.a1], self.fps())
        self.choose(ROOT / "Standard")
        self.assertEqual(self.shown(), ["Fly"])
        self.choose(ROOT / "Standard" / "old")
        self.assertEqual(self.shown(), ["Moon copy"])

    def test_the_marker_explains_itself(self):
        self.folders_on()
        self.unplanned_on()
        self.plan([self.a1], self.fps())
        table = self.browser._table
        row = next(r for r in range(table.rowCount())
                   if "Moon copy" in table.item(r, LIB_COL_TITLE).text())
        self.assertIn("same music", self.browser.cell_tooltip(row, LIB_COL_TITLE))

    def test_sorting_by_title_ignores_the_marker(self):
        self.folders_on()
        self.unplanned_on()
        self.plan([self.a1], self.fps())
        hh = self.browser._table.horizontalHeader()
        hh.setSortIndicator(LIB_COL_TITLE, Qt.SortOrder.AscendingOrder)
        self.browser._populate(list(self.browser._shown))
        self.assertEqual([e.title for e in self.browser._shown],
                         ["Fly", "Moon copy", "Rumba"])

    def test_the_whole_list_still_hides_the_copy(self):
        self.unplanned_on()
        self.plan([self.a1], self.fps())
        self.assertEqual(self.shown(), ["Fly", "Rumba"])

    def test_without_unplanned_nothing_is_hidden_or_marked(self):
        self.folders_on()
        self.browser.set_planned_paths({"x"}, copies={"x"})
        self.assertEqual(len(self.shown()), 4)
        self.assertEqual(self.title_cell("Moon copy"), "Moon copy")

    def test_leaving_the_folder_view_hides_the_copy_again(self):
        self.folders_on()
        self.unplanned_on()
        self.plan([self.a1], self.fps())
        self.browser._folder_btn.click()
        self.assertEqual(self.shown(), ["Fly", "Rumba"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
