#!/usr/bin/env python3
"""Tests that the 🎚 player card keeps its full size on a short screen.

Run:  py -m unittest tests.player.test_player_card_size -v

The Playing column wants ~900 px. Maximized on a 768 px panel it got less, and
a Qt layout takes the difference out of its children: the player card went from
247 px to 26 — no transport, no clock, no fader, on the one machine that is
running the evening. It now sits in a QScrollArea, so the column keeps its full
height and what doesn't fit moves under a scrollbar instead.
"""

import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_card_"))

from PySide6.QtWidgets import QApplication, QScrollArea  # noqa: E402

from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)


class PlayerCardSizeTest(unittest.TestCase):
    """A real MainWindow, switched to Playing mode, on shrinking screens."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._qs_dir = tempfile.mkdtemp(prefix="dp_card_qs_")
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
        self.win._set_play_mode(True)
        self.app.processEvents()
        self.card = self.win._big_player

    def _shrink_to(self, height: int):
        """What a maximized window on a screen of that height does to the
        Playing column — the floors the window itself keeps are what a window
        manager overrides."""
        self.win.setMinimumHeight(0)
        self.win._left_stack.setMinimumHeight(0)
        self.win._left_stack.setFixedHeight(height)
        self.app.processEvents()

    def test_the_playing_column_scrolls(self):
        """The panel is in a scroll area, not straight in the stack."""
        self.assertIsInstance(self.win._play_scroll, QScrollArea)
        self.assertIs(self.win._play_scroll.widget(), self.win._play_panel)
        self.assertTrue(self.win._play_scroll.widgetResizable())

    def test_the_card_keeps_its_height_on_a_short_screen(self):
        full = self.card.sizeHint().height()
        for h in (900, 750, 650, 550, 450):
            with self.subTest(column=h):
                self._shrink_to(h)
                self.assertGreaterEqual(self.card.height(), full)

    def test_a_tall_screen_is_still_filled(self):
        """widgetResizable: the panel grows with the column when there IS room,
        so a beamer-sized window doesn't leave the right half of it empty."""
        self._shrink_to(1400)
        self.assertGreaterEqual(self.win._play_panel.height(), 1200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
