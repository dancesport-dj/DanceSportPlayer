#!/usr/bin/env python3
"""⭐ Find similar (in my wishlist only) opens its window.

Run:  .venv\\Scripts\\python.exe -m unittest tests.gui.test_similar_wishlist_only -v

The menu entry opens the Similar window with the ⭐ box already ticked. The
tick fired the box's handler while the window was still being built, and the
handler re-drew the list through filters whose widgets did not exist yet:
AttributeError '_instr_chk' in Marcel's session.log from the 💥 handler.
"""

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from gui.similar_dialog import SimilarTracksDialog  # noqa: E402
from planner.models import MusicEntry  # noqa: E402


def _rumba(name: str) -> MusicEntry:
    return MusicEntry(path=Path(rf"C:\music\lateincd\{name} (RB 25).mp3"),
                      title=name, dance="RB", bpm=25)


_SOURCE = _rumba("Source Song")
_WISHED = _rumba("Wished Song")
_OTHER = _rumba("Other Song")


class WishlistOnlyTest(unittest.TestCase):
    """Qt hands an exception raised in a slot to sys.excepthook (the app's
    💥 handler) and carries on, so the hook is where the test looks."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.raised = []
        orig = sys.excepthook
        sys.excepthook = lambda *exc: self.raised.append(exc[1])
        self.addCleanup(setattr, sys, "excepthook", orig)

    def tearDown(self):
        self.assertEqual(self.raised, [])

    def test_it_opens_ticked_and_shows_only_the_wishlist(self):
        dlg = SimilarTracksDialog(_SOURCE, [(0.9, _OTHER), (0.8, _WISHED)],
                                  wishlist_paths=[str(_WISHED.path)],
                                  wishlist_only=True)
        self.addCleanup(reap_widget, dlg)
        self.assertTrue(dlg._wishlist_chk.isChecked())
        self.assertEqual(dlg._row_entries, [_WISHED])

    def test_unticking_shows_everything_again(self):
        dlg = SimilarTracksDialog(_SOURCE, [(0.9, _OTHER), (0.8, _WISHED)],
                                  wishlist_paths=[str(_WISHED.path)],
                                  wishlist_only=True)
        self.addCleanup(reap_widget, dlg)
        dlg._wishlist_chk.setChecked(False)
        self.assertEqual(dlg._row_entries, [_OTHER, _WISHED])


if __name__ == "__main__":
    unittest.main(verbosity=2)
