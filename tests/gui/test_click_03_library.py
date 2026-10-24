#!/usr/bin/env python3
"""Click-through, chapter 03: Library and Tournaments.

Run:  py -m unittest tests.gui.test_click_03_library -v

The operator's paths through the manual, clicked in order on a real
MainWindow (see tests/gui/monkey_support.py):

    docs/manual-planner/03-library-and-tournaments.md
"""

import time
import unittest
from pathlib import Path
from unittest import mock

# First: it points the app's state files at a temp folder before any app
# module is imported.
from tests.gui.monkey_support import ClickThrough, printable

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFileDialog, QInputDialog
from tests.db_support import use_scratch_db
from tests.qt_test_support import reap_widget


class LibraryClickTest(ClickThrough):
    """03 Library and Tournaments."""

    def lib_paths(self) -> set[str]:
        lib = self.win._lib_browser._table
        return {str(lib.item(r, 0).data(Qt.ItemDataRole.UserRole))
                for r in range(lib.rowCount())}

    def test_the_library_filters_narrow_the_table(self):
        browser = self.win._lib_browser
        lib = browser._table
        combo = browser._dance_combo

        def shows(n: int) -> bool:
            return self.wait_until(lambda: lib.rowCount() == n)
        with self.clicking():
            self.assertEqual(lib.rowCount(), 30, "the library is not all there")
            # 🔍 a title substring: Song 00 … Song 09.
            self.type_into(browser._filter_edit, "Song 0")
            self.assertTrue(shows(10), f"'Song 0' left {lib.rowCount()} rows")
            # …and on top of it all Latin dances: Song 05 … Song 09.
            combo.setCurrentIndex(combo.findData("grp:Latin"))
            self.assertTrue(shows(5), f"Latin left {lib.rowCount()} rows")
            browser._filter_edit.selectAll()
            self.key(Qt.Key.Key_Backspace, widget=browser._filter_edit)
            self.assertTrue(shows(15), f"all Latin is {lib.rowCount()} rows")
            # One dance: the three Cha Chas.
            combo.setCurrentIndex(combo.findData("CC"))
            self.assertTrue(shows(3), f"Cha Cha left {lib.rowCount()} rows")
            self.assertTrue(all("(CC " in Path(p).name for p in self.lib_paths()),
                            sorted(self.lib_paths()))
            combo.setCurrentIndex(0)
            self.assertTrue(shows(30))
            # 🆕 Unplanned hides every title an open deck holds.
            self.generate(rounds="1")
            planned = {str(m.entry.path) for t in self.win._deckset.decks
                       for m in t._row_meta if m and m.entry}
            self.assertTrue(planned)
            self.tick(browser._unplanned_chk)
            self.assertTrue(shows(30 - len(planned)),
                            f"{lib.rowCount()} rows beside {len(planned)} planned")
            self.assertFalse(self.lib_paths() & planned)
            self.tick(browser._unplanned_chk)
            self.assertTrue(shows(30), "unticked, the planned titles stay hidden")

    def tree_item(self, tree, text: str):
        """The 🏆 tree row whose text starts with `text`, clicked."""
        view = tree._tree
        items = view.findItems(text, Qt.MatchFlag.MatchStartsWith
                               | Qt.MatchFlag.MatchRecursive)
        self.assertTrue(items, f"no tree row '{printable(text)}'")
        QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier,
                         view.visualItemRect(items[0]).center())
        QTest.qWait(5)
        return items[0]

    def season_folder(self, tree):
        """📁 a folder "Season" in the 🏆 tree, picked."""
        with mock.patch.object(QInputDialog, "getText",
                               lambda *_a, **_kw: ("Season", True)):
            self.click(self.button("New folder", tree))
        self.tree_item(tree, "📁  Season")

    def saved_deck(self) -> tuple[Path, list[str]]:
        """A one-round deck saved as .m3u, then the decks emptied again."""
        self.generate(rounds="1")
        titles = self.titles()
        known = set(self.saved_files())
        self.click(self.win._cfg.save_btn)
        [saved] = [p for p in self.saved_files() if p not in known]
        self.click(self.button("Empty every playlist deck"))
        self.assertEqual(self.titles(), [])
        return saved, titles

    def test_a_tournament_playlist_is_filed_laid_out_and_loaded(self):
        win, tree = self.win, self.win._tourney_tree
        win.show()
        with self.clicking():
            saved, titles = self.saved_deck()
            win._lib_tabs.setCurrentWidget(tree)
            self.assertEqual(tree._board._tiles, {}, "the tree is not empty")
            # 📁 a folder, then ＋ the playlist into it: one slot.
            self.season_folder(tree)
            with mock.patch.object(QFileDialog, "getOpenFileNames",
                                   lambda *_a, **_kw: ([str(saved)], "")):
                self.click(self.button("Add playlist files", tree))
            self.tree_item(tree, "📁  Season  (1)")
            [tile] = tree._board._tiles.values()
            self.assertTrue(tile.toolTip().startswith(str(saved)), tile.toolTip())
            self.assertTrue(tile._sub_lbl.text().startswith(f"{len(titles)} ♪"),
                            printable(tile._sub_lbl.text()))
            self.assertIn("1 playlist", tree._total_lbl.text())
            self.assertIn(f"{len(titles)} songs", tree._total_lbl.text())
            # A double-click on the slot loads it onto the focused deck.
            QTest.mouseDClick(tile, Qt.MouseButton.LeftButton)
            self.assertTrue(self.wait_until(lambda: self.titles() == titles),
                            f"saved {printable(titles)}\nloaded {printable(self.titles())}")
            # ▤ the tracks view: the playlist is a 🎵 row, its titles the list.
            self.click(tree._view_btn)
            self.assertIs(tree._right.currentWidget(), tree._table)
            self.assertEqual(tree._view_btn.text(), "▦")
            self.tree_item(tree, "🎵  " + saved.stem)
            table = tree._table
            self.assertEqual([table.horizontalHeaderItem(c).text() for c in range(5)],
                             ["▶", "Round", "Dance", "Artist", "Title"])
            self.assertEqual([table.item(r, 4).text() for r in range(table.rowCount())],
                             titles)
            self.assertTrue(all(table.item(r, 2).text()
                                for r in range(table.rowCount())), "a dance is blank")
            self.assertTrue(tree._total_lbl.text().startswith(f"Σ  {len(titles)} songs"),
                            printable(tree._total_lbl.text()))
            # ▦ back to the slots.
            self.click(tree._view_btn)
            self.assertIs(tree._right.currentWidget(), tree._board)
            self.assertEqual(tree._view_btn.text(), "▤")
            # The archive outlives a restart.
            self.restart()
            tree = self.win._tourney_tree
            self.assertEqual(
                [(n["name"], [c.get("m3u") for c in n["children"]]) for n in tree._nodes],
                [("Season", [str(saved)])])

    def test_closed_during_the_first_scan_it_opens_whole_next_time(self):
        # A first start on a big library: the operator closes the window while
        # the scan still reads. The quit must not sit on the scan, nor save
        # the evening's deck away; the next start reads the rest and keeps
        # what was read before the close.
        from planner.music.library import MusicLibrary
        make = MusicLibrary._make_entry
        cold = []

        def slow(lib, path, scan_cache, *a, **kw):
            if scan_cache.get(path) is None:
                cold.append(path)
                time.sleep(0.05)
            return make(lib, path, scan_cache, *a, **kw)

        files = len(list(Path(self.settings["library_dir"]).rglob("*.mp3")))
        with self.clicking():
            self.generate(rounds="1")
            titles = self.titles()
            self.win._playback.token += 1
            self.win.close()
            reap_widget(self.win)
            # A cache of its own: the class's is full from the earlier starts.
            use_scratch_db(self, self.out / "audio.db")
            with mock.patch.object(MusicLibrary, "_make_entry", slow):
                win = self.gui.MainWindow()
                self.assertTrue(self.wait_until(lambda: len(cold) >= 5, 10000),
                                "the scan never started")
                loader = win._library.loader
                t0 = time.monotonic()
                win.close()
                self.assertLess(time.monotonic() - t0, 4, "the quit waited out the scan")
                self.assertFalse(loader.isRunning(), "the scan outlived its window")
                reap_widget(win)
                read_before = len(cold)
                self.assertLess(read_before, files, "the scan finished before the close")
                cold.clear()
                self.win = self.gui.MainWindow()
                self._wait_until_loaded()
            self.assertEqual(len(self.win._library.lib.entries), files)
            self.assertEqual(len(cold), files - read_before,
                             "what was read before the close was read again")
            self.assertEqual(self.titles(), titles, "the deck did not survive the close")

    def test_save_and_add_to_tournaments_files_the_deck_into_the_picked_folder(self):
        win, tree = self.win, self.win._tourney_tree
        win.show()
        target = self.out / "Sonntag Finale.m3u8"
        with self.clicking() as op:
            win._lib_tabs.setCurrentWidget(tree)
            self.season_folder(tree)
            self.generate(rounds="1")
            win._lib_tabs.setCurrentIndex(0)   # 📚 is up; the save brings 🏆 back
            op.pick("🏆  Save and add to Tournaments")
            with mock.patch.object(QFileDialog, "getSaveFileName",
                                   lambda *_a, **_kw: (str(target), "")):
                self.right_click(op, win._deckset.table, self.song_rows()[0])
                self.assertTrue(self.wait_until(lambda: not op.script), op.script)
            self.assertTrue(target.exists(), "nothing was saved")
            self.assertIs(win._lib_tabs.currentWidget(), tree, "🏆 did not come up")
            self.assertEqual([n.get("m3u") for n in tree._nodes[0]["children"]],
                             [str(target)], "not filed in the picked folder")
            [tile] = tree._board._tiles.values()
            self.assertTrue(tile._sub_lbl.text().startswith(f"{len(self.titles())} ♪"),
                            printable(tile._sub_lbl.text()))


if __name__ == "__main__":
    unittest.main()
