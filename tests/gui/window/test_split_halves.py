#!/usr/bin/env python3
"""A right click or a double click on the divider between two playlists
splits them 50:50.

Run:  py -m unittest tests.gui.window.test_split_halves -v

"add a context menu item on right click between 2 playlist to align them
50:50". Dragging a divider back to the middle by eye never lands exactly. The
deck and wishlist splitters now hand out handles that offer "Split 50:50" on a
right click and do it straight away on a double click. Only the two panes
beside that divider change; the others keep their size. The dividers between
the deck area, the wishlists and the library split unlike things and get none.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_halves_"))

from PySide6.QtCore import QEvent, QPointF, QSettings, Qt
from PySide6.QtGui import QContextMenuEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QMenu, QSplitter, QWidget

from gui.window import main_deck_setup


def _menu_picking(prefix):
    """A QMenu whose exec records the entries and picks the one starting with
    `prefix` (None = dismissed). Patching QMenu.exec itself doesn't take."""
    seen = []

    def pick(menu):
        seen[:] = [a.text() for a in menu.actions()]
        if prefix is None:
            return None
        return next((a for a in menu.actions() if a.text().startswith(prefix)), None)

    class _Menu(QMenu):
        def exec(self, *_args):
            return pick(self)

    return _Menu, seen


def _right_click(handle):
    QApplication.sendEvent(handle, QContextMenuEvent(
        QContextMenuEvent.Reason.Mouse, handle.rect().center(),
        handle.mapToGlobal(handle.rect().center())))


def _double_click(handle):
    pos = QPointF(handle.rect().center())
    QApplication.sendEvent(handle, QMouseEvent(
        QEvent.Type.MouseButtonDblClick, pos, QPointF(handle.mapToGlobal(pos.toPoint())),
        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier))


class HalvingSplitterTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self, n, orientation=Qt.Orientation.Horizontal, sizes=None):
        split = main_deck_setup.HalvingSplitter(orientation)
        for _ in range(n):
            split.addWidget(QWidget())
        split.resize(1000 + split.handleWidth() * (n - 1), 600)
        split.show()
        split.setSizes(sizes or [1000 // n] * n)
        QApplication.processEvents()
        self.addCleanup(split.deleteLater)
        return split

    def test_double_click_splits_the_two_neighbours_evenly(self):
        split = self.make(2, sizes=[200, 800])
        moved = []
        split.splitterMoved.connect(lambda *a: moved.append(a))
        _double_click(split.handle(1))
        a, b = split.sizes()
        self.assertLessEqual(abs(a - b), 1, split.sizes())
        self.assertEqual(a + b, 1000)
        # what listens to a drag (the paired column, the wish sizes) hears it
        self.assertEqual(len(moved), 1)

    def test_right_click_offers_split_and_does_it(self):
        split = self.make(2, sizes=[700, 300])
        menu, seen = _menu_picking("⇔")
        with mock.patch.object(main_deck_setup, "QMenu", menu):
            _right_click(split.handle(1))
        self.assertEqual(seen, ["⇔  Split 50:50"])
        self.assertEqual(split.sizes(), [500, 500])

    def test_vertical_menu_shows_the_vertical_arrow(self):
        split = self.make(2, Qt.Orientation.Vertical, sizes=[150, 450])
        split.resize(400, 600 + split.handleWidth())
        split.setSizes([150, 450])
        menu, seen = _menu_picking("⇕")
        with mock.patch.object(main_deck_setup, "QMenu", menu):
            _right_click(split.handle(1))
        self.assertEqual(seen, ["⇕  Split 50:50"])
        self.assertEqual(split.sizes(), [300, 300])

    def test_dismissed_menu_changes_nothing(self):
        split = self.make(2, sizes=[700, 300])
        menu, _seen = _menu_picking(None)
        with mock.patch.object(main_deck_setup, "QMenu", menu):
            _right_click(split.handle(1))
        self.assertEqual(split.sizes(), [700, 300])

    def test_only_the_two_panes_beside_the_divider_change(self):
        split = self.make(3, sizes=[100, 300, 600])
        _double_click(split.handle(2))
        self.assertEqual(split.sizes(), [100, 450, 450])

    def test_a_hidden_pane_is_skipped(self):
        split = self.make(3, sizes=[200, 300, 500])
        middle = split.widget(1)
        assert middle is not None
        middle.hide()
        QApplication.processEvents()
        before = split.sizes()
        _double_click(split.handle(2))
        after = split.sizes()
        self.assertEqual(after[1], 0, after)
        self.assertLessEqual(abs(after[0] - after[2]), 1, (before, after))
        self.assertEqual(after[0] + after[2], before[0] + before[2])


class WindowDividersTest(unittest.TestCase):
    """Which of the window's splitters split 50:50."""

    @classmethod
    def setUpClass(cls):
        cls._settings_dir = tempfile.mkdtemp(prefix="dp_halves_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._settings_dir)
        cls.app = QApplication.instance() or QApplication([])
        from tests.qt_test_support import stub_window_startup
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        from tests.qt_test_support import reap_widget
        state = tempfile.mkdtemp(prefix="dp_halves_state_")
        patcher = mock.patch.dict(os.environ, {"DANCEPLAYLIST_STATE_DIR": state})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)

    def test_deck_and_wishlist_splitters_split_the_rest_do_not(self):
        g = self.win._grid
        halving = ("decks_split", "decks_col1", "decks_col2", "decks_split2",
                   "decks_col3", "decks_col4", "day_split", "day_col1", "day_col2",
                   "day_split2", "day_col3", "day_col4", "wish_split",
                   "wish_col1", "wish_col2")
        for name in halving:
            self.assertIsInstance(getattr(g, name), main_deck_setup.HalvingSplitter, name)
        self.assertNotIsInstance(g.right_split, main_deck_setup.HalvingSplitter)
        self.assertIsInstance(g.right_split, QSplitter)

    def test_halving_a_column_keeps_the_rows_shared(self):
        g = self.win._grid
        self.win.resize(1400, 900)
        self.win.show()
        self.win._deckset.deck_count = 4   # deck C under A
        self.win._apply_deck_view()
        g.decks_col1.setSizes([150, 450])
        g.decks_col2.setSizes([150, 450])
        QApplication.processEvents()
        _double_click(g.decks_col1.handle(1))
        a, c = g.decks_col1.sizes()
        self.assertLessEqual(abs(a - c), 1, g.decks_col1.sizes())
        self.assertEqual(g.decks_col2.sizes(), g.decks_col1.sizes())


if __name__ == "__main__":
    unittest.main()
