#!/usr/bin/env python3
"""Tests that the planning panel keeps its full size on a short screen.

Run:  py -m unittest tests.gui.test_config_panel_scroll -v

The Playing column got its scroll area for a measured reason (see
tests/player/test_player_card_size.py); the Planning column next to it never
did, and it has the same shape of problem. It wants 873 px. On a 650 px column
the layout takes the difference out of its children and the four combos —
style, age, class, source — come out 12 px tall; at 450 px they are 2 px and
the dance checkboxes are 2 px instead of 89. Scrolled, everything keeps its
full size and what doesn't fit moves under a scrollbar.
"""

import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_cfgscroll_"))

from PySide6.QtWidgets import QApplication, QScrollArea  # noqa: E402

from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)


class ConfigPanelScrollTest(unittest.TestCase):
    """A real MainWindow in Planning mode, on shrinking screens."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._qs_dir = tempfile.mkdtemp(prefix="dp_cfgscroll_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._qs_dir)
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        # Nothing is laid out until the window is on screen, and every height
        # below is measured against that layout.
        self.win.show()
        self.app.processEvents()
        self.cfg = self.win._cfg

    def _shrink_to(self, height: int):
        """What a maximized window on a screen of that height does to the
        Planning column — the floors the window itself keeps are what a window
        manager overrides."""
        self.win.setMinimumHeight(0)
        self.win._left_stack.setMinimumHeight(0)
        self.win._left_stack.setFixedHeight(height)
        self.app.processEvents()

    def test_the_planning_column_scrolls(self):
        """The panel is in a scroll area, not straight in the stack."""
        self.assertIsInstance(self.win._cfg_scroll, QScrollArea)
        self.assertIs(self.win._cfg_scroll.widget(), self.cfg)
        self.assertTrue(self.win._cfg_scroll.widgetResizable())

    def test_the_two_panels_stay_where_the_player_looks_for_them(self):
        """main_player switches on index: 0 planning, 1 playing."""
        self.assertIs(self.win._left_stack.widget(0), self.win._cfg_scroll)
        self.assertIs(self.win._left_stack.widget(1), self.win._play_scroll)
        self.win._set_play_mode(True)
        self.assertEqual(self.win._left_stack.currentIndex(), 1)
        self.win._set_play_mode(False)
        self.assertEqual(self.win._left_stack.currentIndex(), 0)

    def test_the_panel_keeps_its_height_on_a_short_screen(self):
        full = self.cfg.sizeHint().height()
        for h in (900, 750, 650, 550, 450):
            with self.subTest(column=h):
                self._shrink_to(h)
                self.assertGreaterEqual(self.cfg.height(), full)

    def test_the_controls_keep_their_height_on_a_short_screen(self):
        """The four combos and the dance checkboxes are what collapsed: 12 px
        combos at 650, 2 px at 450."""
        parts = [self.cfg.style_combo, self.cfg.age_combo,
                 self.cfg.class_combo, self.cfg.dances_box]
        want = [w.sizeHint().height() for w in parts]
        for h in (650, 450):
            self._shrink_to(h)
            for w, hint in zip(parts, want):
                with self.subTest(column=h, part=w.objectName() or type(w).__name__):
                    self.assertGreaterEqual(w.height(), hint)

    def test_a_tall_screen_is_still_filled(self):
        """widgetResizable: the panel grows with the column when there IS room,
        so a beamer-sized window doesn't leave the left half of it empty."""
        self._shrink_to(1400)
        self.assertGreaterEqual(self.cfg.height(), 1200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
