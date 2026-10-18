#!/usr/bin/env python3
"""Click-through, chapter 02: Planning.

Run:  py -m unittest tests.gui.test_click_02_planning -v

The operator's paths through the manual, clicked in order on a real
MainWindow (see tests/gui/monkey_support.py):

    docs/manual-planner/02-planning.md
"""

import unittest

# First: it points the app's state files at a temp folder before any app
# module is imported.
from tests.gui.monkey_support import ClickThrough, printable

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from shared.columns import _COL_REGEN, _COL_TITLE


class PlanningClickTest(ClickThrough):
    """02 Planning."""

    def test_generate_fills_the_deck(self):  # overconfidence:short-test-ok - asserts in the helper
        with self.clicking():
            self.generate()

    def test_the_rounds_field_sets_rounds_and_heats(self):
        with self.clicking():
            self.generate(rounds="2-1")
            metas = [m for m in self.win._deckset.table._row_meta if m and m.round_name]
            rounds = list(dict.fromkeys(m.round_name for m in metas))
            self.assertEqual(len(rounds), 2, rounds)
            heats = {r: len({m.h_idx for m in metas if m.round_name == r}) for r in rounds}
            self.assertEqual(sorted(heats.values()), [1, 2], heats)

    def test_an_unticked_dance_is_left_out(self):
        with self.clicking():
            jive = self.win._cfg.dance_checks["JI"]
            self.tick(jive)
            self.assertFalse(jive.isChecked())
            self.generate(rounds="1")
            dances = {m.dance for m in self.win._deckset.table._row_meta if m and m.dance}
            self.assertEqual(dances, {"SA", "CC", "RB", "PD"})

    def test_row_reroll_puts_another_title_of_the_same_dance(self):
        with self.clicking():
            self.generate(rounds="1")
            for row in self.song_rows():
                before = self.entry_at(row)
                self.click_cell(self.win._deckset.table, row, _COL_REGEN)
                QTest.qWait(20)
                after = self.entry_at(row)
                self.assertIsNot(after, before, f"row {row}: re-roll kept the title")
                self.assertEqual(after.dance, before.dance)

    def test_ctrl_r_rerolls_the_selected_row(self):
        with self.clicking():
            self.generate(rounds="1")
            row = self.song_rows()[1]
            before = self.entry_at(row)
            self.click_cell(self.win._deckset.table, row, _COL_TITLE)
            self.key(Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
            QTest.qWait(20)
            self.assertIsNot(self.entry_at(row), before)

    def test_undo_and_redo_a_reroll(self):
        with self.clicking():
            self.generate(rounds="1")
            row = self.song_rows()[0]
            before = self.entry_at(row)
            self.click_cell(self.win._deckset.table, row, _COL_REGEN)
            QTest.qWait(20)
            after = self.entry_at(row)
            self.assertIsNot(after, before)
            self.key(Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
            self.assertEqual(self.entry_at(row).path, before.path, "Ctrl+Z")
            self.key(Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
            self.assertEqual(self.entry_at(row).path, after.path, "Ctrl+Y")

    def test_del_empties_the_selected_slot_and_undo_brings_it_back(self):
        with self.clicking():
            self.generate(rounds="1")
            row = self.song_rows()[2]
            before = self.entry_at(row)
            self.click_cell(self.win._deckset.table, row, _COL_TITLE)
            self.key(Qt.Key.Key_Delete)
            self.assertIsNone(self.entry_at(row), "Del left the title in its slot")
            self.assertEqual(len(self.song_rows()), 4)
            self.key(Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
            self.assertEqual(self.entry_at(row).path, before.path)

    def test_a_pinned_title_survives_its_reroll(self):
        with self.clicking() as op:
            self.generate(rounds="1")
            table = self.win._deckset.table
            row = self.song_rows()[0]
            before = self.entry_at(row)
            op.pick("📌  Pin")
            self.right_click(op, table, row)
            self.assertIn(str(before.path), table._pinned_paths)
            self.click_cell(table, row, _COL_REGEN)
            QTest.qWait(20)
            self.assertIs(self.entry_at(row), before)
            op.pick("📌  Unpin")
            self.right_click(op, table, row)
            self.assertNotIn(str(before.path), table._pinned_paths)

    def test_dance_header_reroll_keeps_the_other_dances(self):
        with self.clicking():
            self.generate(rounds="1")
            table = self.win._deckset.table
            dances = {r: self.entry_at(r) for r in self.song_rows()}
            self.click(self.button("Regenerate every heat of this dance"))
            QTest.qWait(20)
            changed = [r for r, e in dances.items() if self.entry_at(r) is not e]
            self.assertTrue(all(self.entry_at(r).dance == dances[r].dance
                                for r in changed))
            self.assertLessEqual(len(changed), 1, "one dance, one heat")
            self.assertEqual(len(self.song_rows(table)), len(dances))

    def test_ctrl_m_marks_and_unmarks_a_title_in_a_dynamic_deck(self):
        with self.clicking():
            self.generate(rounds="1")
            table = self.win._deckset.table
            self.click(self.button("Static deck"))
            self.assertTrue(table._dynamic)
            row = self.song_rows()[0]
            path = str(self.entry_at(row).path)
            self.click_cell(table, row, _COL_TITLE)
            self.key(Qt.Key.Key_M, Qt.KeyboardModifier.ControlModifier)
            self.assertIn(path, table._marked_paths)
            self.key(Qt.Key.Key_M, Qt.KeyboardModifier.ControlModifier)
            self.assertNotIn(path, table._marked_paths)

    def test_the_deck_mode_button_cycles_and_keeps_the_titles(self):
        with self.clicking():
            self.generate(rounds="1")
            table = self.win._deckset.table
            titles = sorted(self.titles())
            btn = self.button("Static deck")
            seen = [btn.text()]
            for _ in range(3):
                self.click(btn)
                seen.append(btn.text())
                self.assertEqual(sorted(self.titles()), titles, printable(btn.text()))
                if len(seen) == 2:
                    self.assertTrue(table._dynamic, "second mode: dynamic")
                if len(seen) == 3:
                    self.assertTrue(table.plays_flat(), "third mode: free order")
            self.assertEqual(len(set(seen[:3])), 3, [printable(s) for s in seen])
            self.assertEqual(seen[3], seen[0])
            self.assertFalse(table._dynamic or table.plays_flat())

    def test_ctrl_shift_del_empties_the_focused_deck(self):
        with self.clicking():
            self.generate(rounds="1")
            self.key(Qt.Key.Key_Delete, Qt.KeyboardModifier.ControlModifier
                     | Qt.KeyboardModifier.ShiftModifier)
            self.assertEqual(self.song_rows(), [])

    def test_clear_all_empties_every_deck(self):
        with self.clicking():
            self.generate()
            self.click(self.button("Empty every playlist deck"))
            self.assertEqual([t.rowCount() for t in self.win._deckset.decks
                              if t.rowCount()], [])


if __name__ == "__main__":
    unittest.main()
