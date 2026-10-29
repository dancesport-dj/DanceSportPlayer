#!/usr/bin/env python3
"""Click-through, chapter 02 / 13: Saving and loading.

Run:  py -m unittest tests.gui.test_click_02_saving -v

The operator's paths through the manual, clicked in order on a real
MainWindow (see tests/gui/monkey_support.py):

    docs/manual-planner/02-planning.md
    docs/manual-planner/13-export-print-paths.md
"""

import unittest
from unittest import mock

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog

# First: it points the app's state files at a temp folder before any app
# module is imported.
from tests.gui.monkey_support import ClickThrough, printable


class SavingClickTest(ClickThrough):
    """02 / 13 Saving and loading."""

    def test_save_m3u_then_import_gives_the_same_titles(self):
        with self.clicking():
            self.generate(rounds="2-1")
            titles = self.titles()
            known = set(self.saved_files())
            self.click(self.win._cfg.save_btn)
            [saved] = [p for p in self.saved_files() if p not in known]
            self.click(self.button("Empty every playlist deck"))
            self.assertEqual(self.titles(), [])
            with mock.patch.object(QFileDialog, "getOpenFileNames",
                                   lambda *_a, **_kw: ([str(saved)], "")):
                self.click(self.win._cfg.import_btn)
            self.assertTrue(self.wait_until(lambda: self.titles() == titles),
                            f"saved {printable(titles)}\nimported {printable(self.titles())}")

    def test_ctrl_s_saves_the_focused_deck(self):
        with self.clicking():
            self.generate(rounds="1")
            target = self.out / "ctrl_s.m3u8"
            with mock.patch.object(QFileDialog, "getSaveFileName",
                                   lambda *_a, **_kw: (str(target), "")):
                self.key(Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
            self.assertTrue(target.exists(), "Ctrl+S wrote nothing")
            text = target.read_text(encoding="utf-8-sig", errors="replace")
            for t in self.titles():
                self.assertIn(t, text)

    def test_save_all_writes_one_file_per_filled_deck(self):
        with self.clicking():
            self.generate(rounds="1")
            known = set(self.saved_files())
            self.click(self.button("Export every non-empty playlist deck"))
            new = [p for p in self.saved_files() if p not in known]
            filled = [t for t in self.win._deckset.decks if t.rowCount()]
            self.assertEqual(len(new), len(filled), new)


if __name__ == "__main__":
    unittest.main()
