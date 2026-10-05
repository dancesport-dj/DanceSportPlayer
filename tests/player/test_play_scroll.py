#!/usr/bin/env python3
"""Tests for the auto-play scroll rule (`PlaylistTable.scroll_row_into_play_view`).

Run:  py -m unittest tests.player.test_play_scroll -v

Auto-advance used to call plain `scrollToItem()`, which stops as soon as the new
title is *barely* inside the viewport — at the very bottom, with no headroom, so
the operator could not see what comes next. A row that has scrolled out of sight
now goes to the TOP; a row that is already fully visible is left alone.

A bare PlaylistTable is filled with plain title cells offscreen — no library, no
MainWindow.
"""

import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_scroll_"))

from PySide6.QtWidgets import QApplication, QTableWidgetItem  # noqa: E402

from PySide6.QtCore import QTimer  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from shared.columns import _COL_TITLE  # noqa: E402
from gui.playlist_table import PlaylistTable, _SCROLL_MS  # noqa: E402

_ROW_H = 24
_ROWS = 60


class PlayScrollTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.t = PlaylistTable()
        self.t.setRowCount(_ROWS)
        for r in range(_ROWS):
            self.t.setItem(r, _COL_TITLE, QTableWidgetItem(f"Title {r}"))
            self.t.setRowHeight(r, _ROW_H)
        # A viewport that holds ~8 rows, so most of the list is off screen.
        self.t.resize(700, 10 * _ROW_H)
        self.t.show()
        self.app.processEvents()
        self.t.scrollToTop()
        self.addCleanup(reap_widget, self.t)

    def _settle(self):
        """Run the event loop until the scroll animation has arrived."""
        done = []
        QTimer.singleShot(int(_SCROLL_MS) + 120, lambda: done.append(True))
        while not done:
            self.app.processEvents()

    def _top_of(self, row: int) -> int:
        return self.t.visualItemRect(self.t.item(row, _COL_TITLE)).top()

    def _rows_on_screen(self) -> int:
        return max(1, self.t.viewport().height() // _ROW_H)

    def test_a_row_far_below_lands_at_the_top(self):
        """The whole rest of the list stays visible underneath it."""
        target = _ROWS - 20
        self.t.scroll_row_into_play_view(target)
        self._settle()
        self.assertLess(abs(self._top_of(target)), _ROW_H,
                        "the starting title should sit at the top of the viewport")

    def test_it_glides_there_instead_of_jumping(self):
        """Mid-flight the list is on its way, not already arrived — and it does
        arrive."""
        target = _ROWS - 20
        self.t.scroll_row_into_play_view(target)
        bar = self.t.verticalScrollBar()
        self.assertEqual(bar.value(), 0, "the jump must never be shown")
        anim = self.t._scroll_anim
        self.assertIsNotNone(anim)
        self.assertEqual(anim.endValue(), self._end_of(target))
        self._settle()
        self.assertEqual(bar.value(), anim.endValue())

    def _end_of(self, row: int) -> int:
        """Where the bar has to end up for `row` to sit at the top."""
        bar = self.t.verticalScrollBar()
        keep = bar.value()
        from PySide6.QtWidgets import QAbstractItemView
        self.t.scrollToItem(self.t.item(row, _COL_TITLE),
                            QAbstractItemView.ScrollHint.PositionAtTop)
        end = bar.value()
        bar.setValue(keep)
        return end

    def test_a_row_already_on_screen_does_not_jump(self):
        """No scroll on every auto-advance while the next titles are still visible."""
        row = min(2, self._rows_on_screen() - 1)
        before = self.t.verticalScrollBar().value()
        self.t.scroll_row_into_play_view(row)
        self._settle()
        self.assertEqual(self.t.verticalScrollBar().value(), before)

    def test_the_row_after_a_jump_stays_put(self):
        """Row N goes to the top; N+1 is then visible, so it must not scroll again."""
        target = _ROWS - 20
        self.t.scroll_row_into_play_view(target)
        self._settle()
        after_jump = self.t.verticalScrollBar().value()
        self.t.scroll_row_into_play_view(target + 1)
        self._settle()
        self.assertEqual(self.t.verticalScrollBar().value(), after_jump)

    def test_a_burst_of_skips_ends_on_the_last_row(self):
        """Restarting the glide mid-flight must not strand the list halfway."""
        for row in (20, 30, 40):
            self.t.scroll_row_into_play_view(row)
            self.app.processEvents()
        self._settle()
        self.assertLess(abs(self._top_of(40)), _ROW_H)

    def test_scrolling_back_up_also_puts_the_row_on_top(self):
        """Jumping backwards (⏮ / a click far above) reads the same way."""
        self.t.scroll_row_into_play_view(_ROWS - 1)
        self._settle()
        self.t.scroll_row_into_play_view(5)
        self._settle()
        self.assertLess(abs(self._top_of(5)), _ROW_H)

    def test_a_missing_row_is_ignored(self):
        """Empty decks / out-of-range rows must not raise."""
        before = self.t.verticalScrollBar().value()
        self.t.scroll_row_into_play_view(_ROWS + 10)
        self.t.scroll_row_into_play_view(-1)
        self.assertEqual(self.t.verticalScrollBar().value(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
