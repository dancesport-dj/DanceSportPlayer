#!/usr/bin/env python3
"""The whole library pane folds away from an arrow in the tab bar's corner.

Run:  py -m unittest tests.gui.test_library_pane_fold -v

The 📚 Library tab already had a ▾ in its own header, but that arrow lives
INSIDE the tab, so it is gone the moment the user switches to 🏆 Tournaments —
and it only folds the browser, never the pane the two tabs share. The corner
arrow tested here belongs to the tab bar itself, so it stays reachable while
the pane is collapsed, which is the only way back short of the toolbar button.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_libfold_"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QSplitter, QTabWidget, QWidget,
)

from gui.main_fold import FoldMixin  # noqa: E402


class _Win(FoldMixin):
    """The three attributes the library-pane fold reaches for, and nothing else
    — FoldMixin is a MainWindow mixin, and MainWindow cannot be built headless."""

    def __init__(self):
        self._settings = {}
        self._saved = []
        self._right_split = QSplitter(Qt.Orientation.Vertical)
        self._decks_area = QWidget()
        self._right_split.addWidget(self._decks_area)
        self._lib_tabs = QTabWidget()
        self._lib_tabs.addTab(QWidget(), "📚  Library")
        self._lib_tabs.addTab(QWidget(), "🏆  Tournaments")
        self._right_split.addWidget(self._lib_tabs)
        self._right_split.setSizes([600, 200])
        self.messages = []

    def statusBar(self):
        return self

    def showMessage(self, msg, *a):
        self.messages.append(msg)


class LibraryPaneFoldTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.win = _Win()
        self.win._build_lib_pane_fold_btn()

    def test_the_arrow_sits_in_the_tab_bars_top_right_corner(self):
        btn = self.win._lib_tabs.cornerWidget(Qt.Corner.TopRightCorner)
        self.assertIsNotNone(btn, "no corner widget on the library tabs")
        self.assertIs(btn, self.win._lib_pane_fold_btn)

    def test_no_stray_base_line_hangs_over_the_arrow(self):
        """The tab bar's base line runs its whole width. The tabs hide it on
        the left, but the corner is empty, so it drew a line right above the
        arrow — the tabs keep their own outline without it."""
        self.assertFalse(self.win._lib_tabs.tabBar().drawBase())

    def test_clicking_it_collapses_the_pane_to_the_tab_bar(self):
        w = self.win
        w._lib_pane_fold_btn.click()
        self.assertTrue(w._lib_pane_folded)
        bar = w._lib_tabs.tabBar().sizeHint().height()
        self.assertLessEqual(w._lib_tabs.maximumHeight(), bar + 12)

    def test_the_arrow_survives_the_collapse_and_points_back(self):
        """It is the corner of the TAB BAR, so it is still there to click when
        everything below it is gone — the arrow flips to say so."""
        w = self.win
        w._lib_pane_fold_btn.click()
        # The clamp must leave room for the arrow itself, or folding would cut
        # off the only control that unfolds.
        self.assertGreaterEqual(w._lib_tabs.maximumHeight(),
                                w._lib_pane_fold_btn.sizeHint().height())
        self.assertEqual(w._lib_pane_fold_btn.text(), "▴")
        w._lib_pane_fold_btn.click()
        self.assertEqual(w._lib_pane_fold_btn.text(), "▾")

    def test_clicking_again_gives_the_pane_its_height_back(self):
        w = self.win
        w._lib_pane_fold_btn.click()
        w._lib_pane_fold_btn.click()
        self.assertFalse(w._lib_pane_folded)
        self.assertEqual(w._lib_tabs.maximumHeight(), 16777215)

    def test_the_decks_get_the_freed_height_and_give_it_back(self):
        w = self.win
        sizes = w._right_split.sizes()
        before, decks_before = sum(sizes), sizes[0]
        w._toggle_lib_pane_fold(True)
        self.assertEqual(sum(w._right_split.sizes()), before,
                         "folding must move height, never invent or lose it")
        self.assertGreater(w._right_split.sizes()[0], decks_before)
        w._toggle_lib_pane_fold(False)
        self.assertEqual(sum(w._right_split.sizes()), before)
        self.assertLess(w._right_split.sizes()[0], before)

    def test_the_choice_is_remembered(self):
        w = self.win
        w._toggle_lib_pane_fold(True)
        self.assertTrue(w._settings["library_pane_folded"])
        w._toggle_lib_pane_fold(False)
        self.assertFalse(w._settings["library_pane_folded"])

    def test_picking_a_tab_opens_the_pane_back_up(self):
        """Clicking 🏆 Tournaments on a collapsed pane means 'show me that',
        not 'switch the tab I cannot see'."""
        w = self.win
        w._toggle_lib_pane_fold(True)
        w._lib_tabs.tabBarClicked.emit(1)
        self.assertFalse(w._lib_pane_folded)

    def test_a_folded_pane_is_restored_on_the_next_start(self):
        w = _Win()
        w._settings["library_pane_folded"] = True
        w._build_lib_pane_fold_btn()
        self.assertTrue(w._lib_pane_folded)
        self.assertEqual(w._lib_pane_fold_btn.text(), "▴")


class RealWindowHasTheArrowTest(unittest.TestCase):
    """The stub above proves the mixin; this proves MainWindow actually calls it."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._qs_dir = tempfile.mkdtemp(prefix="dp_libfold_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._qs_dir)
        cls.app = QApplication.instance() or QApplication([])

        from tests.qt_test_support import stub_window_startup

        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def test_the_corner_arrow_is_there_on_a_real_window(self):
        from tests.qt_test_support import reap_widget

        win = self.gui.MainWindow()
        try:
            btn = win._lib_tabs.cornerWidget(Qt.Corner.TopRightCorner)
            self.assertIsNotNone(btn, "MainWindow built no corner arrow")
            self.assertEqual(btn.text(), "▾")
            win._toggle_lib_pane_fold()
            self.assertTrue(win._lib_pane_folded)
            self.assertEqual(btn.text(), "▴")
        finally:
            reap_widget(win)


if __name__ == "__main__":
    unittest.main(verbosity=2)
