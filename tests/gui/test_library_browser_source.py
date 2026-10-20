#!/usr/bin/env python3
"""⭐ Favorites ⇄ 🌐 Whole library, switched from the 📚 Library header.

Run:  py -m unittest tests.gui.test_library_browser_source -v

Marcel: "the little arrow in library tab on library should be able to switch
between favorites folder and whole library". The ▾ stays the fold; a button
next to it switches what the browser lists. Only the browser — the ≈ similar
search keeps its own ⚙ "Global search" setting.

"Whole library" is the global index (the music repository folder), which may
not be loaded yet: the browser asks for it and switches only once it arrives.
"""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_libsource_"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from gui.library_browser import LibraryBrowser
from gui.window.main_global import GlobalIndexMixin
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget


def _entries(prefix, n):
    return [MusicEntry(path=Path(rf"C:\{prefix}\{i}.mp3"), title=f"{prefix} {i}",
                       dance="SW") for i in range(n)]


FAVS = _entries("favs", 2)
WHOLE = _entries("repo", 5)


class BrowserSourceTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.browser = LibraryBrowser()
        self.addCleanup(reap_widget, self.browser)
        self.browser.set_entries(FAVS)
        self.asked = []
        self.browser.wholeLibraryWanted.connect(lambda: self.asked.append(1))

    def shown(self):
        return self.browser._table.rowCount()

    def test_the_switch_sits_in_the_header_and_starts_on_favorites(self):
        btn = self.browser._source_btn
        self.assertIs(btn.parentWidget(), self.browser._hdr)
        self.assertFalse(btn.isChecked())
        self.assertIn("Favorites", btn.text())

    def test_the_switch_looks_like_a_button(self):
        # Marcel: "it is not distinguable for a user that this is a button which
        # can be clicked". The header's flat background cascades onto it, so it
        # read like the title next to it: it needs its own frame and a hover.
        for btn in (self.browser._source_btn, self.browser._rescan_btn):
            qss = btn.styleSheet()
            self.assertIn("QToolButton {", qss)
            self.assertIn("border:1px solid", qss)
            self.assertIn("QToolButton:hover", qss)
            self.assertEqual(btn.cursor().shape(), Qt.CursorShape.PointingHandCursor)
        self.assertIn("QToolButton:checked", self.browser._source_btn.styleSheet(),
                      "🌐 on reads as pressed")

    def test_the_header_buttons_hug_their_text(self):
        # Marcel: "make the gap left and right of the new style button and sync
        # items smaller currently they are wider than needed". QToolButton's own
        # size hint adds ~12 px of air around the text on top of the QSS padding.
        b = self.browser
        for whole in (False, True):
            if whole:
                b.set_whole_entries(WHOLE)
            for btn in (b._source_btn, b._rescan_btn):
                text_w = btn.fontMetrics().horizontalAdvance(btn.text())
                self.assertLessEqual(btn.sizeHint().width(), text_w + 12, btn.text())
                self.assertGreaterEqual(btn.sizeHint().width(), text_w + 6, btn.text())

    def test_clicking_it_asks_for_the_whole_library_without_switching_yet(self):
        self.browser._source_btn.click()
        self.assertEqual(self.asked, [1])
        self.assertFalse(self.browser._source_btn.isChecked(),
                         "nothing to show yet, so it must not claim 🌐")
        self.assertEqual(self.shown(), 2)

    def test_the_whole_library_arriving_switches_the_list(self):
        self.browser._source_btn.click()
        self.browser.set_whole_entries(WHOLE)
        self.assertTrue(self.browser._source_btn.isChecked())
        self.assertIn("Whole library", self.browser._source_btn.text())
        self.assertEqual(self.shown(), 5)
        self.assertIn("5/5", self.browser._count_lbl.text())

    def test_clicking_again_goes_back_to_the_favorites(self):
        self.browser.set_whole_entries(WHOLE)
        self.browser._source_btn.click()
        self.assertEqual(self.asked, [], "going back needs nothing loaded")
        self.assertFalse(self.browser._source_btn.isChecked())
        self.assertIn("Favorites", self.browser._source_btn.text())
        self.assertEqual(self.shown(), 2)

    def test_a_favorites_rescan_under_the_whole_library_waits_its_turn(self):
        self.browser.set_whole_entries(WHOLE)
        self.browser.set_entries(_entries("favs", 3))
        self.assertEqual(self.shown(), 5, "🌐 stays on screen")
        self.browser._source_btn.click()
        self.assertEqual(self.shown(), 3, "and the new favorites show on the way back")


class _Win(GlobalIndexMixin):
    """Only what _show_whole_library reaches for."""

    def __init__(self, global_lib):
        self._library = SimpleNamespace(global_lib=global_lib, preloader=None)
        self._lib_browser = SimpleNamespace(
            set_whole_entries=lambda entries: self.handed.append(list(entries)))
        self.handed = []
        self.ensured = []

    def _ensure_global_lib(self, then_drop=None, then_build=None):
        self.ensured.append(then_build)


class WindowSourceTest(unittest.TestCase):

    def test_a_loaded_global_index_goes_straight_to_the_browser(self):
        win = _Win(SimpleNamespace(entries=WHOLE))
        win._show_whole_library()
        self.assertEqual(win.handed, [WHOLE])
        self.assertEqual(win.ensured, [])

    def test_an_empty_loaded_index_is_handed_over_rather_than_rescanned(self):
        win = _Win(SimpleNamespace(entries=[]))
        win._show_whole_library()
        self.assertEqual(win.handed, [[]])
        self.assertEqual(win.ensured, [])

    def test_otherwise_it_loads_the_index_first_and_comes_back(self):
        win = _Win(None)
        win._show_whole_library()
        self.assertEqual(win.handed, [])
        self.assertEqual(len(win.ensured), 1)
        win._library.global_lib = SimpleNamespace(entries=WHOLE)
        win.ensured[0]()
        self.assertEqual(win.handed, [WHOLE])


if __name__ == "__main__":
    unittest.main()
