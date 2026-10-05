#!/usr/bin/env python3
"""📚 The library's filter row on a pane that is not 1600 px wide.

Run:  py -m unittest tests.gui.test_library_filter_row -v

A combo's minimum width is the width of its LONGEST entry, so six of them in
a row made the library pane refuse to be narrower than its own filter strip.
The 🔍 search box — the only control that can give way — was squeezed to a
sliver, which is how the most used field on the pane became invisible.

So the combos are capped to the width of their resting label and the row is a
FlowLayout: it breaks onto a second line rather than push the pane wider than
the window.
"""

import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_filterrow_"))

from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QLineEdit, QToolButton, QWidget)
from tests.qt_test_support import reap_widget  # noqa: E402

from shared.widgets import FlowLayout  # noqa: E402
from gui.library_browser import LibraryBrowser  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)

_COMBOS = ("_dance_combo", "_class_combo", "_vocal_combo", "_cat_combo",
           "_plays_combo", "_added_combo")
_ROW = ("_filter_edit",) + _COMBOS + ("_unplanned_chk",)


class FilterRowTest(unittest.TestCase):
    """What the row does at the widths a real pane actually has."""

    def setUp(self):
        self.b = LibraryBrowser()
        self.addCleanup(reap_widget, self.b)
        self.b.show()
        self._at(1800)

    def _at(self, width: int):
        """Resize the pane and let the layout settle."""
        self.b.resize(width, 600)
        _app.processEvents()

    def _row(self):
        return [getattr(self.b, name) for name in _ROW]

    def _lines(self) -> int:
        return len({w.y() for w in self._row()})

    def _one_line_width(self) -> int:
        """What the filters ask for side by side — font-dependent, so it is
        measured rather than written down."""
        return sum(w.sizeHint().width() for w in self._row()) + 8 * 4

    def test_the_pane_can_be_made_as_narrow_as_the_window_asks(self):
        """The filter strip must never be what keeps the pane wide."""
        self._at(520)
        self.assertLessEqual(self.b.width(), 520)

    def test_the_search_box_stays_readable_at_every_width(self):
        """It is the field the operator types in — it may shrink, not vanish."""
        floor = self.b.fontMetrics().horizontalAdvance("M") * 10
        for width in (520, 700, 900, 1200, 1800):
            with self.subTest(pane=width):
                self._at(width)
                self.assertGreaterEqual(self.b._filter_edit.width(), floor)

    def test_a_narrow_pane_breaks_the_row_up(self):
        """Half the width it would like: it wraps, it does not push back."""
        half = self._one_line_width() // 2
        self._at(half)
        self.assertGreater(self._lines(), 1)
        self.assertLessEqual(self.b.width(), half)

    def test_a_wide_pane_keeps_them_on_one_line(self):
        self._at(self._one_line_width() + 20)
        self.assertEqual(self._lines(), 1)

    def test_a_wrapped_row_is_given_the_height_it_asked_for(self):
        """A flow layout that wraps without reporting the taller height puts
        its second line underneath the table instead of above it."""
        self._at(self._one_line_width() // 2)
        bottom = max(w.y() + w.height() for w in self._row())
        self.assertGreaterEqual(self.b._table.y(), bottom)

    def test_nothing_is_pushed_past_the_pane_edge(self):
        for width in (520, 700, 900, 1200, 1800):
            with self.subTest(pane=width):
                self._at(width)
                right = max(w.x() + w.width() for w in self._row())
                self.assertLessEqual(right, self.b.width())

    def test_no_filter_is_wider_than_the_others(self):
        """One long entry ('🎉 Party / background music …') used to set the
        width of its whole combo, and of the pane with it."""
        widths = {getattr(self.b, name).width() for name in _COMBOS}
        self.assertEqual(len(widths), 1)

    def test_the_search_box_takes_whatever_the_filters_leave(self):
        """Capping the combos must not leave a gap where the box used to be."""
        wide = self._one_line_width() + 200
        self._at(wide)
        edit = self.b._filter_edit
        last = max(self._row(), key=lambda w: w.x() + w.width())
        self.assertGreater(edit.width(), edit.sizeHint().width())
        self.assertLessEqual(last.x() + last.width(), wide)


class FlowStretchTest(unittest.TestCase):
    """The shared FlowLayout: a line's leftover width goes to the greedy."""

    def setUp(self):
        self.host = QWidget()
        self.addCleanup(reap_widget, self.host)
        self.flow = FlowLayout(self.host, spacing=6)

    def _lay(self, width: int):
        self.host.resize(width, 80)
        self.host.show()
        _app.processEvents()

    def test_an_expanding_control_fills_the_rest_of_its_line(self):
        btn = QToolButton()
        btn.setText("BB")
        edit = QLineEdit()          # Expanding, like every QLineEdit
        self.flow.addWidget(btn)
        self.flow.addWidget(edit)
        self._lay(600)
        self.assertGreater(edit.width(), edit.sizeHint().width())
        self.assertLessEqual(edit.x() + edit.width(), 600)

    def test_controls_that_did_not_ask_are_left_at_their_size(self):
        a = QToolButton()
        a.setText("AA")
        b = QToolButton()
        b.setText("BB")
        self.flow.addWidget(a)
        self.flow.addWidget(b)
        self._lay(600)
        self.assertEqual(a.width(), a.sizeHint().width())
        self.assertEqual(b.width(), b.sizeHint().width())

    def test_the_wrap_itself_still_happens(self):
        edits = [QLineEdit() for _ in range(4)]
        for e in edits:
            e.setMinimumWidth(120)
            self.flow.addWidget(e)
        self._lay(300)
        self.assertGreater(len({e.y() for e in edits}), 1)

    def test_height_for_width_is_measured_without_stretching(self):
        """The wrap height must not depend on who grows on the last line."""
        for _ in range(3):
            self.flow.addWidget(QLineEdit())
        self.assertGreater(self.flow.heightForWidth(200),
                           self.flow.heightForWidth(2000))


if __name__ == "__main__":
    unittest.main(verbosity=2)
