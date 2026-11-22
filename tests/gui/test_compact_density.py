#!/usr/bin/env python3
"""📐 Compact: the desk sits tighter.

Run:  py -m unittest tests.gui.test_compact_density -v

On a 13″ laptop every pixel of height is a playlist row. Compact starts on
the 🗜 compact header view (unless one was picked before), the song rows
are 22 px instead of 24 and the setup fields on the left close up.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_density_"))

from PySide6.QtWidgets import QApplication

import dancesport_gui as gui
from gui import screen_mode
from tests.qt_test_support import reap_widget, stub_window_startup


class CompactDensityTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        stub_window_startup(cls, {"app_mode": "both"})

    def window(self, compact, settings=None):
        self.addCleanup(setattr, screen_mode, "_compact", screen_mode._compact)
        loaded = {"app_mode": "both", **(settings or {})}
        with mock.patch.object(screen_mode, "is_compact", return_value=compact), \
                mock.patch.object(gui, "load_settings", lambda *_a, **_k: dict(loaded)):
            win = gui.MainWindow()
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        return win

    # ===== Acceptance criteria =====
    def test_compact_starts_on_the_compact_header_view(self):
        self.assertEqual(self.window(compact=True)._compact_state, 1)

    def test_compact_song_rows_are_22_px(self):
        table = self.window(compact=True)._deckset.tableA
        self.assertEqual(table.song_row_height, 22)

    def test_compact_closes_up_the_setup_fields(self):
        win = self.window(compact=True)
        self.assertLess(win._cfg.layout().spacing(), 5)

    # ===== Core behavior =====
    def test_a_header_view_picked_before_is_kept(self):
        win = self.window(compact=True, settings={"compact": 0})
        self.assertEqual(win._compact_state, 0)

    def test_normal_is_left_as_it_was(self):
        win = self.window(compact=False)
        self.assertEqual(win._compact_state, 0)
        self.assertEqual(win._deckset.tableA.song_row_height, 24)
        self.assertEqual(win._cfg.layout().spacing(), 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
