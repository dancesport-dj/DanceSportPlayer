#!/usr/bin/env python3
"""📚 A big library fills the browser step by step, the window stays usable.

Run:  py -m unittest tests.gui.test_library_fill_steps -v

Marcel: "also the filling dialog is not nice: can we not fill a current table
step by step so the user can still work while updating?" The whole repository
(54 368 titles) took ~5 s to fill, behind a modal "Filling the library
browser…" dialog. Now the first rows are written at once (a small list is
still filled in one go) and the rest in short steps between turns of the
event loop: the rows appear as they are written, and a new filter typed
mid-fill drops the old fill instead of waiting for it.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_libsteps_"))

from PySide6.QtWidgets import QApplication

import gui.library_browser as library_browser
from gui.library_browser import LibraryBrowser
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget

_TITLE = 3
FIRST = library_browser._FILL_FIRST
CHUNK = library_browser._FILL_CHUNK


def _entries(n, name="Title"):
    return [MusicEntry(path=Path(rf"C:\music\{name}{i}.mp3"), title=f"{name} {i}",
                       dance="LW", bpm=29) for i in range(n)]


class FillStepsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.b = LibraryBrowser()
        self.addCleanup(reap_widget, self.b)
        self.t = self.b._table
        # No time budget: every later step writes exactly one chunk.
        patcher = mock.patch.object(library_browser, "_FILL_BUDGET", 0.0)
        patcher.start()
        self.addCleanup(patcher.stop)

    def pump(self, turns=200):
        counts = []
        for _ in range(turns):
            QApplication.processEvents()
            if counts[-1:] != [self.t.rowCount()]:
                counts.append(self.t.rowCount())
        return counts

    def titles(self):
        return [self.t.item(r, _TITLE).text() for r in range(self.t.rowCount())]

    def test_a_small_list_is_there_at_once(self):
        self.b._populate(_entries(FIRST))
        self.assertEqual(self.t.rowCount(), FIRST)

    def test_a_big_list_shows_its_first_rows_at_once_and_the_rest_in_steps(self):
        n = FIRST + 2 * CHUNK + 7
        self.b._populate(_entries(n))
        self.assertEqual(self.t.rowCount(), FIRST, "only written rows exist")
        self.assertEqual(self.t.item(FIRST - 1, _TITLE).text(), f"Title {FIRST - 1}")
        self.assertEqual(self.pump(), [FIRST + CHUNK, FIRST + 2 * CHUNK, n])
        self.assertEqual(self.titles(), [f"Title {i}" for i in range(n)])

    def test_no_dialog_comes_up(self):
        self.b._populate(_entries(FIRST + 3 * CHUNK))
        self.assertIsNone(QApplication.activeModalWidget())
        self.pump()
        self.assertIsNone(QApplication.activeModalWidget())

    def test_each_step_tells_the_view_once_about_its_own_rows(self):
        seen = []
        self.t.model().dataChanged.connect(
            lambda tl, br, *_a: seen.append((tl.row(), br.row())))
        n = FIRST + CHUNK + 3
        self.b._populate(_entries(n))
        self.pump()
        self.assertEqual(seen, [(0, FIRST - 1), (FIRST, FIRST + CHUNK - 1),
                                (FIRST + CHUNK, n - 1)])

    def test_a_new_filter_mid_fill_drops_the_old_fill(self):
        self.b._populate(_entries(FIRST + 5 * CHUNK))
        QApplication.processEvents()
        self.b._populate(_entries(3, "Other"))
        self.pump()
        self.assertEqual(self.titles(), ["Other 0", "Other 1", "Other 2"])

    def test_a_pane_closed_mid_fill_is_no_error(self):
        b = LibraryBrowser()
        b._populate(_entries(FIRST + 2 * CHUNK))
        b.deleteLater()
        for _ in range(20):
            QApplication.processEvents()


if __name__ == "__main__":
    unittest.main()
