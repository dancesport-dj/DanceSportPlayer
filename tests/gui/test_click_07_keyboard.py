#!/usr/bin/env python3
"""Click-through, chapter 07: Keyboard.

Run:  py -m unittest tests.gui.test_click_07_keyboard -v

The operator's paths through the manual, clicked in order on a real
MainWindow (see tests/gui/monkey_support.py):

    docs/manual-planner/07-shortcuts.md
"""

import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QDrag
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QInputDialog

from gui.dialogs import load_autosave

# First: it points the app's state files at a temp folder before any app
# module is imported.
from tests.gui.monkey_support import ClickThrough, DropFrom


def files(*paths) -> QMimeData:
    """What Explorer hands over when files are dragged out of it."""
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    return mime


class KeyboardClickTest(ClickThrough):
    """07 Keyboard."""

    def test_f1_shows_the_cheat_sheet(self):
        with self.clicking() as op:
            self.key(Qt.Key.Key_F1)
            self.assertTrue(any("Shortcuts" in w for w in op.opened), op.opened)

    def test_ctrl_f_jumps_to_the_title_asked_for(self):
        with self.clicking():
            self.generate(rounds="1")
            table = self.win._deckset.table
            first, *_, last = self.song_rows()
            table.selectRow(first)
            wanted = self.entry_at(last).title
            with mock.patch.object(QInputDialog, "getText",
                                   lambda *_a, **_kw: (wanted, True)):
                self.key(Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
            self.assertEqual(table.currentRow(), last)

    def test_space_plays_the_selected_title(self):
        with self.clicking():
            self.generate(rounds="1")
            table = self.win._deckset.table
            row = self.song_rows()[1]
            table.selectRow(row)
            # A double tap is one press. Back to back: under load, the event
            # processing of a wait between the taps outlasted the interval.
            QTest.keyClick(table, Qt.Key.Key_Space)
            self.key(Qt.Key.Key_Space)
            self.assertTrue(self.wait_until(lambda: table._current_play_row == row),
                            f"playing row {table._current_play_row}, not {row}")
            self.assertTrue(self.wait_until(lambda: not table._player_stopped()))
            QTest.qWait(QApplication.doubleClickInterval() + 50)
            self.assertEqual(table._current_play_row, row, "the double tap stopped it")
            self.key(Qt.Key.Key_Space)
            self.assertTrue(self.wait_until(lambda: table._current_play_row < 0),
                            "Space did not stop it")

    def test_ctrl_del_takes_a_heat_out_of_a_dynamic_deck(self):
        with self.clicking():
            self.generate(rounds="2-1")
            table = self.win._deckset.table
            self.click(self.button("Static deck"))
            self.assertTrue(table._dynamic)
            row = self.song_rows()[0]
            meta = table._row_meta[row]
            heat = [m.entry for m in table._row_meta
                    if m and m.entry and m.round_name == meta.round_name
                    and m.h_idx == meta.h_idx]
            n = len(self.titles())
            table.selectRow(row)
            self.key(Qt.Key.Key_Delete, Qt.KeyboardModifier.ControlModifier)
            self.assertEqual(len(self.titles()), n - len(heat))

    # ── Mouse ───────────────────────────────────────────────────────────────

    def test_a_click_on_a_round_or_dance_header_folds_only_that_section(self):
        with self.clicking():
            self.generate(rounds="2-1")
            table = self.win._deckset.table
            first, second = sorted(table._round_hdr_rows)

            def under(hdr, by) -> list[int]:
                return [r for r in self.song_rows() if by.get(r) == hdr]

            def hidden(rows) -> list[bool]:
                return [table.isRowHidden(r) for r in rows]

            round1, round2 = (under(h, table._row_round_hdr) for h in (first, second))
            self.assertTrue(round1 and round2)
            self.click_cell(table, first, 0)
            self.assertEqual(hidden(round1), [True] * len(round1))
            self.assertEqual(hidden(round2), [False] * len(round2), "the other round folded too")
            self.assertTrue(table.item(first, 0).text().startswith("▶"))
            self.click_cell(table, first, 0)
            self.assertEqual(hidden(round1), [False] * len(round1))
            self.assertTrue(table.item(first, 0).text().startswith("▼"))

            # A dance header folds its own titles; the round's others stay.
            dance = min(h for h in table._dance_hdr_rows
                        if table._row_round_hdr.get(h) == second)
            mine = under(dance, table._row_dance_hdr)
            rest = [r for r in round2 if r not in mine]
            self.assertTrue(mine and rest)
            self.click_cell(table, dance, 0)
            self.assertEqual(hidden(mine), [True] * len(mine))
            self.assertEqual(hidden(rest + [dance, second]), [False] * (len(rest) + 2))
            self.click_cell(table, dance, 0)
            self.assertEqual(hidden(mine), [False] * len(mine))

    def test_ctrl_on_a_drop_replaces_the_title_in_a_dynamic_slot(self):
        with self.clicking():
            self.generate(rounds="1")
            table = self.win._deckset.table
            self.click(self.button("Static deck"))
            self.assertTrue(table._dynamic)
            row = self.song_rows()[0]
            old = self.entry_at(row)
            planned = {str(m.entry.path) for m in table._row_meta if m and m.entry}
            spare = [e for e in self.win._library.lib.entries
                     if e.dance == old.dance and str(e.path) not in planned]
            self.assertGreaterEqual(len(spare), 2, "no spare title of the dance")
            n = len(self.titles())

            def drop(path, mods):
                y = table.rowViewportPosition(row) + table.rowHeight(row) // 2
                mime = files(path)     # the event does not keep it alive
                table.dropEvent(DropFrom(QPointF(20, y), mime, None, mods))
                QTest.qWait(5)

            drop(spare[0].path, Qt.KeyboardModifier.ControlModifier)
            self.assertEqual(Path(self.entry_at(row).path), Path(spare[0].path))
            self.assertEqual(len(self.titles()), n, "Ctrl + drop added a title")
            self.assertNotIn(old.title, self.titles())

            # Without Ctrl the slot keeps its title and the new one is added.
            drop(spare[1].path, Qt.KeyboardModifier.NoModifier)
            self.assertEqual(len(self.titles()), n + 1)
            self.assertIn(spare[0].title, self.titles())
            self.assertIn(spare[1].title, self.titles())

    def test_a_double_click_on_the_deck_title_renames_it(self):
        with self.clicking():
            self.generate(rounds="1")
            table = self.win._deckset.table
            deck = self.win.deck(table)
            before = deck.name

            def rename(text, key):
                QTest.mouseDClick(deck.header, Qt.MouseButton.LeftButton)
                edit = self.win._rename_edit
                self.assertIsNotNone(edit, "a double-click opened no editor")
                QTest.keyClick(edit, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
                QTest.keyClicks(edit, text)
                QTest.keyClick(edit, key)
                QTest.qWait(5)

            rename("Ignored", Qt.Key.Key_Escape)
            self.assertEqual(deck.name, before, "Esc kept the typed name")
            rename("Senioren II S Latein", Qt.Key.Key_Return)
            self.assertEqual(deck.name, "Senioren II S Latein")
            self.assertIn("Senioren II S Latein", deck.header.text())
            self.assertTrue(deck.header.isVisible())
            # Saved at once, not only on quit: a crash keeps it too.
            self.assertIn("Senioren II S Latein", repr(load_autosave()))
            self.restart()
            self.assertEqual(self.win.deck(self.win._deckset.table).name,
                             "Senioren II S Latein", "the name did not survive a restart")

    # ── Cartwall ────────────────────────────────────────────────────────────

    def test_cartwall_drops_fill_free_pads_and_a_dragged_pad_swaps(self):
        from planner.playing import cartwall as pc
        win = self.win
        with self.clicking():
            self.click(win._mode_play_btn)
            if not win._cart_btn.isChecked():
                self.click(win._cart_btn)
            wall = win._cartwall
            self.assertTrue(wall.isVisible(), "🎛 shows no wall")
            page = wall.current_page()
            k0, k1, k2, k3 = [(page, *c) for c in list(pc.cells_in_order(wall.grid()))[:4]]
            a, b, x, y = sorted(Path(self.settings["library_dir"]).rglob("*.mp3"))[:4]

            def on(key):
                # Assigning a sample builds the grid anew: never keep a button.
                return wall._buttons[key]

            def path(key):
                pad = wall.pad_at(key)
                return pad and Path(pad.path)

            def drop(key, *paths):
                mime = files(*paths)   # the event does not keep it alive
                on(key).dropEvent(DropFrom(QPointF(5, 5), mime, None))
                QTest.qWait(5)

            drop(k1, a)
            self.assertIsNone(wall.pad_at(k1), "a drop landed with ✏ off")
            self.click(wall._edit_btn)
            drop(k1, a)
            self.assertEqual(path(k1), a)
            # Three at once: the first where aimed, the rest skip the set pad.
            drop(k0, b, x, y)
            self.assertEqual([path(k) for k in (k0, k1, k2, k3)], [b, a, x, y])

            def release(drag, *_a, **_kw):
                on(k1).dropEvent(DropFrom(QPointF(5, 5), drag.mimeData(), drag.source()))
                return Qt.DropAction.MoveAction
            src = on(k0)
            with mock.patch.object(QDrag, "exec", release):
                QTest.mousePress(src, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
                QTest.mouseMove(src, QPoint(5 + 3 * QApplication.startDragDistance(), 5))
            QTest.qWait(5)
            self.assertEqual([path(k) for k in (k0, k1)], [a, b], "the pads did not swap")
            self.click(wall._edit_btn)


if __name__ == "__main__":
    unittest.main()
