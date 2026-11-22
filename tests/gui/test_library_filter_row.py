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

from PySide6.QtWidgets import QApplication, QLineEdit, QToolButton, QWidget

from gui.library_browser import LibraryBrowser
from shared.widgets import FlowLayout
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)

_COMBOS = ("_dance_combo", "_class_combo", "_cat_combo")
# Always on the line (Marcel: "most often i filter by dance, class and category").
_FIRST = ("_filter_edit",) + _COMBOS + ("_unplanned_chk", "_class_only_chk")
# The less-used ones, behind MORE_BTN when the line has no room for them.
_MORE = ("_vocal_combo", "_plays_combo", "_added_combo")
_ALL = _FIRST + _MORE
# With room: the combos first, then the checkboxes (the original layout).
_WIDE = ("_filter_edit",) + _COMBOS + _MORE + ("_unplanned_chk", "_class_only_chk",
                                              "_more_btn")
# Without: the checkboxes stay on the line; the button comes last, also
# after the filters it opened (Marcel).
_NARROW = _FIRST + _MORE + ("_more_btn",)


def _all_width(b) -> int:
    """What every filter asks for side by side, font-dependent, so measured."""
    return sum(getattr(b, n).sizeHint().width() for n in _ALL) + 8 * len(_ALL)


class MoreFiltersTest(unittest.TestCase):
    """All filters on one line when they fit; otherwise vocal, plays and added
    wait behind the more button, so the line does not wrap on a 13 inch laptop."""

    def setUp(self):
        self.b = LibraryBrowser()
        self.addCleanup(reap_widget, self.b)
        self.b.show()

    def _at(self, width: int):
        self.b.resize(width, 600)
        _app.processEvents()

    def _more(self):
        return [getattr(self.b, name) for name in _MORE]

    def _order(self) -> tuple:
        """The filters' names in the order the flow lays them out."""
        names = {id(getattr(self.b, n)): n for n in _ALL + ("_more_btn",)}
        flow = self.b._filter_flow
        return tuple(names[id(flow.itemAt(i).widget())] for i in range(flow.count()))

    # ===== Acceptance criteria =====
    def test_a_pane_with_room_shows_every_filter_and_no_more_button(self):
        self._at(_all_width(self.b) + 40)
        self.assertTrue(all(w.isVisible() for w in self._more()))
        self.assertFalse(self.b._more_btn.isVisible())

    def test_a_pane_without_room_hides_the_less_used_behind_the_button(self):
        self._at(_all_width(self.b) - 120)
        self.assertTrue(self.b._more_btn.isVisible())
        self.assertFalse(any(w.isVisible() for w in self._more()))
        self.b._more_btn.click()
        self.assertTrue(all(w.isVisible() for w in self._more()))
        self.b._more_btn.click()
        self.assertFalse(any(w.isVisible() for w in self._more()))

    def test_category_stays_on_the_line_and_vocal_moves_behind(self):
        self._at(_all_width(self.b) - 120)
        self.assertTrue(self.b._cat_combo.isVisible())
        self.assertFalse(self.b._vocal_combo.isVisible())

    def test_widening_the_pane_again_brings_them_back(self):
        self._at(_all_width(self.b) - 120)
        self._at(_all_width(self.b) + 40)
        self.assertTrue(all(w.isVisible() for w in self._more()))
        self.assertFalse(self.b._more_btn.isVisible())

    def test_with_room_the_combos_come_first_then_the_checkboxes(self):
        """Marcel: the original layout, buttons first, then the checkboxes,
        with category before vocal."""
        self._at(_all_width(self.b) + 40)
        self.assertEqual(self._order(), _WIDE)

    def test_without_room_the_checkboxes_stay_before_the_button(self):
        self._at(_all_width(self.b) - 120)
        self.assertEqual(self._order(), _NARROW)
        self.b._more_btn.click()
        _app.processEvents()
        btn, last = self.b._more_btn, self.b._added_combo
        self.assertTrue(btn.y() > last.y()
                        or (btn.y() == last.y() and btn.x() > last.x()))
        self._at(_all_width(self.b) + 40)
        self.assertEqual(self._order(), _WIDE)

    # ===== Core behavior =====
    def test_the_more_button_counts_the_filters_it_hides(self):
        """A hidden filter that is set must not silently empty the list."""
        self.assertNotIn("(", self.b._more_btn.text())
        self.b._vocal_combo.setCurrentIndex(self.b._vocal_combo.findData("vocal"))
        self.b._added_combo.setCurrentIndex(self.b._added_combo.findData("30"))
        self.assertIn("(2)", self.b._more_btn.text())
        self.b._vocal_combo.setCurrentIndex(0)
        self.b._added_combo.setCurrentIndex(0)
        self.assertNotIn("(", self.b._more_btn.text())

    def test_a_jump_from_outside_opens_the_row_it_set(self):
        """The gap dashboard sets Plays: the filter it set must show."""
        self._at(_all_width(self.b) - 120)
        self.b.focus_filter(dance="SA", plays="never")
        _app.processEvents()
        self.assertTrue(self.b._plays_combo.isVisible())


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
        """The controls on screen: which ones depends on the width."""
        names = _ALL + ("_more_btn",)
        return [w for w in (getattr(self.b, n) for n in names) if w.isVisible()]

    def _lines(self) -> int:
        """A line's controls share a middle, not a top: a control below
        the bottom of every control above it starts the next line."""
        lines, bottom = 0, None
        for w in sorted(self._row(), key=lambda w: w.y()):
            if bottom is None or w.y() >= bottom:
                lines += 1
            bottom = max(bottom or 0, w.y() + w.height())
        return lines

    def _one_line_width(self) -> int:
        """What the filters ask for side by side — font-dependent, so it is
        measured rather than written down."""
        return _all_width(self.b)

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
        self.assertGreaterEqual(self.b._table.parentWidget().y(), bottom)

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

    def test_a_control_that_can_shrink_does_on_a_narrow_line(self):
        wide = QToolButton()
        wide.setText("W" * 80)
        wide.setMinimumWidth(40)
        self.flow.addWidget(wide)
        self._lay(120)
        self.assertEqual(wide.width(), 120)

    def test_a_control_of_a_fixed_width_keeps_it(self):
        fixed = QToolButton()
        fixed.setFixedWidth(300)
        self.flow.addWidget(fixed)
        self._lay(120)
        self.assertEqual(fixed.width(), 300)

    def test_a_hidden_control_leaves_no_gap(self):
        """The library's ⋯ Filters sits after the filters it hides: hidden,
        they must not push it right by their spacing."""
        a, hidden, b = QToolButton(), QToolButton(), QToolButton()
        for w in (a, hidden, b):
            w.setText("AA")
            self.flow.addWidget(w)
        hidden.setVisible(False)
        self._lay(600)
        self.assertEqual(b.x(), a.x() + a.width() + 6)

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

    def test_a_line_centres_its_controls(self):
        """The cartwall's 🗂 sat on the top edge beside the taller volume
        fader: a line's controls share one middle, not one top."""
        tall = QWidget()
        tall.setFixedSize(60, 30)
        btn = QToolButton()
        btn.setText("🗂")
        btn.setFixedSize(24, 20)
        self.flow.addWidget(tall)
        self.flow.addWidget(btn)
        self._lay(600)
        self.assertEqual(tall.y(), 0)
        self.assertEqual(btn.y() + btn.height() / 2, tall.y() + tall.height() / 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
