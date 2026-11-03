#!/usr/bin/env python3
"""🔍 The find bar: a search over the list instead of a dialog in front of it.

Run:  py -m unittest tests.gui.table.test_find_bar -v

Marcel's list, 7.3: "Replace the full search dialog with a search bar above the
playlist or a floating overlay, with forward/backward icons like a PDF reader or
browser. Show the correct shortcut per platform (Cmd+F on Mac)."

`sys.platform` is patched for the Mac texts: they are checked, not run on macOS.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR", tempfile.mkdtemp(prefix="dp_findbar_"))

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QWidget

import gui.dialogs
from gui.table.find_bar import FindBar
from gui.table.playlist_table import PlaylistTable
from gui.table.table_actions import _C_FIND_BG
from planner import i18n
from planner.models import MusicEntry
from shared.columns import _COL_DANCE
from tests.qt_test_support import reap_widget

_DIR = Path(tempfile.mkdtemp(prefix="dp_findbar_m_"))
SHIFT = Qt.KeyboardModifier.ShiftModifier


def _e(title, dance="PD"):
    path = _DIR / f"{title}.mp3"
    path.write_bytes(b"x")
    return MusicEntry(path=path, title=title, dance=dance, duration=150)


class _Win(QWidget):
    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "both"}


class _Base(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def table(self, titles=("Topic One", "Other", "Topic Two", "Topic Three")):
        win = _Win()
        win.resize(800, 500)
        t = PlaylistTable()
        t.setParent(win)
        t.resize(780, 480)
        self.addCleanup(reap_widget, win)
        t.load_warmup([_e(x) for x in titles], "ETDS Party", "", "S", True,
                      lambda _p: None, None)
        win.show()
        win.activateWindow()
        self.app.processEvents()
        return t

    def row_of(self, t, title):
        return next(r for r, m in t._row_meta.numbered()
                    if m.entry is not None and m.entry.title == title)

    def open_on(self, t, text):
        t._search_title()
        t._find_bar._title.setText(text)
        return t._find_bar


class OpensTest(_Base):

    def test_the_dialog_is_gone(self):
        self.assertFalse(hasattr(gui.dialogs, "FindInListDialog"))

    def test_ctrl_f_opens_it_over_the_list_without_a_modal_window(self):
        t = self.table()
        t.setFocus()
        with mock.patch.object(QDialog, "exec", side_effect=AssertionError("a dialog")):
            QTest.keyClick(t, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
        self.assertIsInstance(t._find_bar, FindBar)
        self.assertTrue(t._find_bar.isVisible())
        self.assertIs(t._find_bar.parentWidget(), t)

    def test_the_cursor_lands_in_the_title_field(self):
        t = self.table()
        self.open_on(t, "topic")
        self.assertTrue(t._find_bar._title.hasFocus())

    def test_ctrl_f_again_in_the_field_closes_it(self):
        t = self.table()
        bar = self.open_on(t, "topic")
        QTest.keyClick(bar._title, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
        self.assertFalse(bar.isVisible())

    def test_it_reopens_with_the_last_text_marked(self):
        t = self.table()
        bar = self.open_on(t, "topic")
        bar.dismiss()
        t._search_title()
        self.assertTrue(bar.isVisible())
        self.assertEqual(bar._title.selectedText(), "topic")

    def test_esc_then_ctrl_f_reopens(self):
        t = self.table()
        t.setFocus()
        ctrl = Qt.KeyboardModifier.ControlModifier
        QTest.keyClick(t, Qt.Key.Key_F, ctrl)
        QTest.keyClick(t._find_bar._title, Qt.Key.Key_Escape)
        QTest.keyClick(t, Qt.Key.Key_F, ctrl)
        self.assertTrue(t._find_bar.isVisible())

    def test_it_hides_no_row_of_a_short_list(self):
        """Over the column titles: the first rows are where a short list's hits are."""
        t = self.table()
        t._search_title()
        self.app.processEvents()
        bar = t._find_bar
        self.assertEqual(bar.y(), 0)
        self.assertLessEqual(bar.height(),
                             t.horizontalHeader().height() + t.rowHeight(0) // 2)

    def test_it_stands_at_the_top_right_and_follows_a_resize(self):
        t = self.table()
        t._search_title()
        self.app.processEvents()
        bar = t._find_bar
        self.assertEqual(t.width() - bar.geometry().right() - 1, bar.GAP)
        t.resize(600, 300)
        self.app.processEvents()
        self.assertEqual(t.width() - bar.geometry().right() - 1, bar.GAP)

    def test_a_narrow_list_keeps_it_inside(self):
        t = self.table()
        t.resize(300, 200)
        t._search_title()
        self.app.processEvents()
        self.assertGreaterEqual(t._find_bar.x(), 0)
        self.assertLessEqual(t._find_bar.geometry().right(), t.width())


class StepsTest(_Base):

    def test_enter_walks_forward_and_wraps(self):
        t = self.table()
        one, two, three = [self.row_of(t, f"Topic {n}") for n in ("One", "Two", "Three")]
        bar = self.open_on(t, "topic")
        rows = []
        for _i in range(4):
            QTest.keyClick(bar._title, Qt.Key.Key_Return)
            rows.append(t.currentRow())
        self.assertEqual(rows, [one, two, three, one])

    def test_shift_enter_walks_back_and_wraps(self):
        t = self.table()
        one, two, three = [self.row_of(t, f"Topic {n}") for n in ("One", "Two", "Three")]
        bar = self.open_on(t, "topic")
        QTest.keyClick(bar._title, Qt.Key.Key_Return)
        rows = []
        for _i in range(3):
            QTest.keyClick(bar._title, Qt.Key.Key_Return, SHIFT)
            rows.append(t.currentRow())
        self.assertEqual(rows, [three, two, one])

    def test_back_on_a_fresh_search_lands_on_the_last_match(self):
        t = self.table()
        bar = self.open_on(t, "topic")
        QTest.keyClick(bar._title, Qt.Key.Key_Return, SHIFT)
        self.assertEqual(t.currentRow(), self.row_of(t, "Topic Three"))

    def test_the_arrows_step_like_the_keys(self):
        t = self.table()
        one, two = self.row_of(t, "Topic One"), self.row_of(t, "Topic Two")
        bar = self.open_on(t, "topic")
        QTest.mouseClick(bar._next, Qt.MouseButton.LeftButton)
        QTest.mouseClick(bar._next, Qt.MouseButton.LeftButton)
        self.assertEqual(t.currentRow(), two)
        QTest.mouseClick(bar._prev, Qt.MouseButton.LeftButton)
        self.assertEqual(t.currentRow(), one)

    def test_stepping_leaves_the_cursor_in_the_field(self):
        """So Enter can be pressed again, and a typo corrected."""
        t = self.table()
        bar = self.open_on(t, "topic")
        QTest.keyClick(bar._title, Qt.Key.Key_Return)
        self.assertTrue(bar._title.hasFocus())
        QTest.mouseClick(bar._next, Qt.MouseButton.LeftButton)
        self.assertTrue(bar._title.hasFocus())

    def test_enter_in_the_genre_field_searches_too(self):
        t = self.table(("A", "B"))
        t._search_title()
        bar = t._find_bar
        bar._genre.setText("PD")
        QTest.keyClick(bar._genre, Qt.Key.Key_Return)
        self.assertEqual(t._find_rows, [self.row_of(t, "A"), self.row_of(t, "B")])

    def test_a_changed_text_starts_at_its_own_first_match(self):
        t = self.table()
        bar = self.open_on(t, "topic")
        QTest.keyClick(bar._title, Qt.Key.Key_Return)
        QTest.keyClick(bar._title, Qt.Key.Key_Return)
        bar._title.setText("topic t")
        QTest.keyClick(bar._title, Qt.Key.Key_Return)
        self.assertEqual(t.currentRow(), self.row_of(t, "Topic Two"))

    def test_enter_does_not_reach_the_list(self):
        """The list starts the selected title on Enter."""
        t = self.table()
        bar = self.open_on(t, "topic")
        with mock.patch.object(t, "keyPressEvent") as key:
            QTest.keyClick(bar._title, Qt.Key.Key_Return)
            QTest.keyClick(bar._title, Qt.Key.Key_Return, SHIFT)
        key.assert_not_called()


class ClosesTest(_Base):

    def test_esc_closes_it_and_takes_the_tint_back(self):
        t = self.table()
        bar = self.open_on(t, "topic")
        QTest.keyClick(bar._title, Qt.Key.Key_Return)
        hit = self.row_of(t, "Topic One")
        self.assertEqual(t.item(hit, _COL_DANCE).background().color(), _C_FIND_BG)
        QTest.keyClick(bar._title, Qt.Key.Key_Escape)
        self.assertFalse(bar.isVisible())
        self.assertEqual(t._find_rows, [])
        self.assertNotEqual(t.item(hit, _COL_DANCE).background().color(), _C_FIND_BG)

    def test_the_cross_closes_it_too(self):
        t = self.table()
        bar = self.open_on(t, "topic")
        QTest.mouseClick(bar._close, Qt.MouseButton.LeftButton)
        self.assertFalse(bar.isVisible())

    def test_the_found_row_keeps_the_cursor_and_the_list_the_keyboard(self):
        t = self.table()
        bar = self.open_on(t, "topic t")
        QTest.keyClick(bar._title, Qt.Key.Key_Return)
        QTest.keyClick(bar._title, Qt.Key.Key_Escape)
        self.assertEqual(t.currentRow(), self.row_of(t, "Topic Two"))
        self.assertTrue(t.hasFocus())

    def test_esc_belongs_to_the_bar_and_not_to_a_window_shortcut(self):
        t = self.table()
        bar = self.open_on(t, "topic")
        ev = QKeyEvent(QEvent.Type.ShortcutOverride, Qt.Key.Key_Escape,
                       Qt.KeyboardModifier.NoModifier)
        ev.ignore()
        QApplication.sendEvent(bar._title, ev)
        self.assertTrue(ev.isAccepted())


class ShortcutTextTest(_Base):

    def tearDown(self):
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def placeholder(self, platform):
        with mock.patch.object(sys, "platform", platform):
            t = self.table()
            t._search_title()
        return t._find_bar._title.placeholderText()

    def test_windows_says_ctrl(self):
        self.assertIn("Ctrl+F", self.placeholder("win32"))

    def test_a_mac_says_cmd(self):
        self.assertIn("Cmd+F", self.placeholder("darwin"))

    def test_a_german_windows_says_strg(self):
        i18n.set_active("de")
        self.assertIn("Strg+F", self.placeholder("win32"))

    def test_a_german_mac_says_cmd(self):
        i18n.set_active("de")
        text = self.placeholder("darwin")
        self.assertIn("Cmd+F", text)
        self.assertNotIn("Strg", text)


class TypingAndToggleTest(_Base):

    def test_ctrl_f_opens_closes_and_opens_again(self):
        t = self.table()
        t.setFocus()
        ctrl = Qt.KeyboardModifier.ControlModifier
        QTest.keyClick(t, Qt.Key.Key_F, ctrl)
        self.assertTrue(t._find_bar.isVisible())
        QTest.keyClick(t._find_bar._title, Qt.Key.Key_F, ctrl)   # closes from the field
        self.assertFalse(t._find_bar.isVisible())
        QTest.keyClick(t, Qt.Key.Key_F, ctrl)
        self.assertTrue(t._find_bar.isVisible())
        QTest.keyClick(t, Qt.Key.Key_F, ctrl)                    # closes from the list
        QTest.keyClick(t, Qt.Key.Key_F, ctrl)
        self.assertTrue(t._find_bar.isVisible())

    def test_ctrl_x_clears_the_field_even_without_a_selection(self):
        t = self.table()
        t._search_title()
        bar = t._find_bar
        QTest.keyClicks(bar._title, "Topic")
        QTest.keyClick(bar._title, Qt.Key.Key_Home)
        QTest.keyClick(bar._title, Qt.Key.Key_X, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(bar._title.text(), "")
        self.assertEqual(t._find_rows, [])

    def test_ctrl_x_on_the_list_clears_both_fields(self):
        t = self.table()
        t._search_title()
        bar = t._find_bar
        bar._genre.setText("PD")
        bar._title.setText("Topic")
        t.setFocus()
        QTest.keyClick(t, Qt.Key.Key_X, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual((bar._title.text(), bar._genre.text()), ("", ""))
        self.assertTrue(bar._title.hasFocus())

    def test_esc_and_ctrl_f_work_with_the_focus_on_the_list(self):
        t = self.table()
        t._search_title()
        t.setFocus()
        QTest.keyClick(t, Qt.Key.Key_Escape)
        self.assertFalse(t._find_bar.isVisible())
        t._search_title()
        t.setFocus()
        QTest.keyClick(t, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
        self.assertFalse(t._find_bar.isVisible())

    def test_ctrl_f_again_closes_the_bar(self):
        t = self.table()
        t.setFocus()
        t._search_title()
        self.assertTrue(t._find_bar.isVisible())
        t._search_title()
        self.assertFalse(t._find_bar.isVisible())

    def test_typing_tints_the_matches_without_jumping(self):
        t = self.table()
        t._search_title()
        t.setCurrentCell(self.row_of(t, "Other"), 0)
        QTest.keyClicks(t._find_bar._title, "Topic")
        self.assertEqual(len(t._find_rows), 3)
        self.assertEqual(t.currentRow(), self.row_of(t, "Other"))

    def test_enter_then_jumps_to_the_first_match(self):
        t = self.table()
        t._search_title()
        t.setCurrentCell(self.row_of(t, "Other"), 0)
        QTest.keyClicks(t._find_bar._title, "Topic")
        QTest.keyClick(t._find_bar._title, Qt.Key.Key_Return)
        self.assertEqual(t.currentRow(), self.row_of(t, "Topic One"))

    def test_tab_goes_from_title_to_genre_and_back(self):
        t = self.table()
        t._search_title()
        bar = t._find_bar
        self.assertTrue(bar._title.hasFocus())
        QTest.keyClick(bar._title, Qt.Key.Key_Tab)
        self.assertTrue(bar._genre.hasFocus())
        QTest.keyClick(bar._genre, Qt.Key.Key_Backtab)
        self.assertTrue(bar._title.hasFocus())


if __name__ == "__main__":
    unittest.main(verbosity=2)
