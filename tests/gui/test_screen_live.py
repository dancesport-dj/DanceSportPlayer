#!/usr/bin/env python3
"""📐 Auto follows the window onto a screen of another size.

Run:  py -m unittest tests.gui.test_screen_live -v

Marcel moves the app between a laptop and a big monitor. Under Auto the shape
re-decides when the window changes screen: the song rows, the one-line hints,
the library's six rows, the 🗜 view (until one was picked) and the setup
spacing follow at once. The empty-wishlist fold stays a start-up thing: done
live it would fight the operator's own folding.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_screen_live_"))

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication

import dancesport_gui as gui
from gui import screen_mode
from tests.qt_test_support import reap_widget, stub_window_startup


class _Screen:
    def __init__(self, height):
        self._h = height

    def availableGeometry(self):
        return QRect(0, 0, 1280, self._h)


class ScreenLiveTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        stub_window_startup(cls, {"app_mode": "both"})

    def window(self, compact=False, settings=None):
        self.addCleanup(setattr, screen_mode, "_compact", screen_mode._compact)
        loaded = {"app_mode": "both", **(settings or {})}
        with mock.patch.object(screen_mode, "is_compact", return_value=compact), \
                mock.patch.object(gui, "load_settings", lambda *_a, **_k: dict(loaded)):
            win = gui.MainWindow()
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        return win

    def _lib_min(self, win):
        return win._lib_browser._table.minimumHeight()

    # ===== Acceptance criteria =====
    def test_moving_to_a_small_screen_turns_compact_on(self):
        win = self.window(compact=False)
        win._on_screen_changed(_Screen(700))
        self.assertTrue(screen_mode.compact())
        self.assertEqual(win._deckset.tableA.song_row_height, 22)
        self.assertEqual(win._compact_state, 1)
        self.assertLess(win._cfg.layout().spacing(), 5)
        self.assertTrue(win._hints_lbl._compact)
        self.assertGreater(self._lib_min(win), 0)

    def test_moving_to_a_big_screen_turns_compact_off(self):
        win = self.window(compact=True)
        win._on_screen_changed(_Screen(1040))
        self.assertFalse(screen_mode.compact())
        self.assertEqual(win._deckset.tableA.song_row_height, 24)
        self.assertEqual(win._compact_state, 0)
        self.assertEqual(win._cfg.layout().spacing(), 5)
        self.assertFalse(win._hints_lbl._compact)
        self.assertEqual(self._lib_min(win), 0)

    def test_the_window_handle_reports_a_screen_change(self):
        """The wiring: QWindow.screenChanged reaches the window once shown."""
        win = self.window(compact=False)
        win.show()
        self.app.processEvents()
        with mock.patch.object(screen_mode, "is_compact", return_value=True):
            win.windowHandle().screenChanged.emit(QApplication.primaryScreen())
        self.assertTrue(screen_mode.compact())

    # ===== Core behavior =====
    def test_a_chosen_shape_does_not_follow_the_screen(self):
        for mode in ("normal", "compact"):
            with self.subTest(mode=mode):
                win = self.window(compact=mode == "compact",
                                  settings={"screen_mode": mode})
                win._on_screen_changed(_Screen(700 if mode == "normal" else 1040))
                self.assertEqual(screen_mode.compact(), mode == "compact")

    def test_a_picked_header_view_is_kept(self):
        win = self.window(compact=False, settings={"compact": 2})
        win._on_screen_changed(_Screen(700))
        self.assertEqual(win._compact_state, 2)

    def test_the_live_switch_does_not_save_a_header_view(self):
        """The default must stay a default: saved, it would read as picked."""
        win = self.window(compact=False)
        win._on_screen_changed(_Screen(700))
        self.assertNotIn("compact", win._settings)

    def test_the_song_rows_get_the_new_height(self):
        table = self.window(compact=False)._deckset.tableA
        table.setRowCount(3)
        for r in range(3):
            table.setRowHeight(r, 30)
        with mock.patch.object(table._row_meta, "at",
                               side_effect=lambda r: None if r == 0 else object()):
            screen_mode._compact = True
            table.apply_row_height()
        self.assertEqual([table.rowHeight(r) for r in range(3)], [30, 22, 22])

    # ===== Coverage and null checks =====
    def test_no_screen_changes_nothing(self):
        win = self.window(compact=False)
        win._on_screen_changed(None)
        self.assertFalse(screen_mode.compact())


if __name__ == "__main__":
    unittest.main(verbosity=2)
