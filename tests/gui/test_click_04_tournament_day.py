#!/usr/bin/env python3
"""Click-through, chapter 04: Tournament day.

Run:  py -m unittest tests.gui.test_click_04_tournament_day -v

The operator's paths through the manual, clicked in order on a real
MainWindow (see tests/gui/monkey_support.py):

    docs/manual-planner/04-tournament-day.md
"""

import unittest
from unittest import mock

from PySide6.QtWidgets import QDialogButtonBox, QFileDialog, QPushButton

# First: it points the app's state files at a temp folder before any app
# module is imported.
from tests.gui.monkey_support import ClickThrough, Operator


class TournamentDayClickTest(ClickThrough):
    """04 Tournament day."""

    def plan_day(self, op: Operator, patterns: list[str]) -> list[list[str]]:
        """📅 Day plan with one competition per round pattern (Latin S, as the
        panel stands); returns the titles of each day deck it filled."""
        def fill(dlg):
            add = next(b for b in dlg.findChildren(QPushButton)
                       if b.text().startswith("➕"))
            for _ in patterns[1:]:
                self.click(add)
            for row, pattern in zip(dlg._rows, patterns, strict=True):
                row[4].setText(pattern)
            self.click(dlg.findChild(QDialogButtonBox).button(
                QDialogButtonBox.StandardButton.Ok))
        op.answer(self.titled("📅 Plan tournament day"), fill)
        self.click(self.button("Plan a whole tournament day"))
        days = self.win._deckset.day_decks
        self.assertTrue(self.wait_until(
            lambda: sum(1 for t in days if self.titles(t)) == len(patterns)),
            "the day decks did not fill")
        return [self.titles(t) for t in days if self.titles(t)]

    def test_a_planned_day_repeats_no_title_but_the_paso(self):
        with self.clicking() as op:
            # Three heats of one title per dance, and the library holds three
            # of each: only a shared pool fills them all without a repeat.
            self.plan_day(op, ["1", "1", "1"])
            self.assertEqual(self.win._grid.deck_tabs.currentIndex(), 2,
                             "the 📅 tab is not in front")
            played = [m.entry.title for t in self.win._deckset.day_decks
                      for m in t._row_meta
                      if m and m.entry and m.entry.dance != "PD"]
            self.assertEqual(len(played), 12)
            self.assertEqual(len(set(played)), 12, "a title is played twice that day")

    def test_the_saved_day_comes_back_title_for_title(self):
        with self.clicking() as op:
            day = self.plan_day(op, ["1", "2-1"])
            op.pick("💾  Save all competition M3Us")
            tabs = self.win._grid.deck_tabs.tabBar()
            with mock.patch.object(QFileDialog, "getExistingDirectory",
                                   lambda *_a, **_kw: str(self.out)):
                op._context_menu(tabs, tabs.tabRect(2).center(), "")
                self.assertTrue(self.wait_until(lambda: not op.script), op.script)
            [folder] = self.out.glob("Tournament_day_*")
            saved = sorted(folder.glob("*.m3u*"))
            self.assertEqual(len(saved), 2, [p.name for p in saved])
            back = []
            for path in saved:
                self.click(self.button("Empty every playlist deck"))
                self.win._grid.deck_tabs.setCurrentIndex(0)
                self.import_list(path)
                self.assertTrue(self.wait_until(lambda: self.titles()), path.name)
                back.append(self.titles())
            self.assertEqual(sorted(back), sorted(day))

    def test_practice_builds_a_list_into_the_practice_panel(self):
        with self.clicking() as op:
            op.answer(self.titled("🤸"), lambda dlg: dlg.accept())
            self.click(self.button("Build a practice playlist"))
            panel = self.win._deckset.warmup_table
            self.assertTrue(self.wait_until(lambda: self.song_rows(panel), 10000),
                            "the practice list stayed empty")


if __name__ == "__main__":
    unittest.main()
