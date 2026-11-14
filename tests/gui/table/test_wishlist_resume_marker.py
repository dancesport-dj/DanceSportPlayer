"""↩ The time marker of a title is shown and can be reset in a wishlist too.

Run:  py -m unittest tests.gui.table.test_wishlist_resume_marker -v

Marcel's list, 6.26: "In a wishlist I miss the context menu to reset the time
marker." A deck repaints a row the moment its title gets a marker; a wishlist row
is a theme row and was left out of that repaint, so its "↩ m:ss" badge never
showed and nothing told the operator there was a marker to reset.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_wish_marker_"))

from PySide6.QtCore import QPoint
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication, QMenu

from gui.table import table_menu
from gui.table.playlist_table import PlaylistTable
from gui.table.table_host import TableHost
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])

RESET = "↩  Reset time marker"


def _e(title):
    return MusicEntry(path=Path(rf"C:\music\{title}.mp3"), title=title, dance="LW",
                      duration=150)


class WishlistResumeMarkerTest(unittest.TestCase):

    def wishlist(self, *titles):
        t = PlaylistTable()
        t.resize(700, 600)
        self.addCleanup(reap_widget, t)
        t.load_wishlist([_e(x) for x in titles], mock.Mock(), None)
        return t

    @staticmethod
    def title_cell(t, title):
        row = next(r for r, m in t._row_meta.numbered() if m.entry.title == title)
        return t.item(row, 4).text()

    def menu(self, t, title, pick=None):
        row = next(r for r, m in t._row_meta.numbered() if m.entry.title == title)
        seen = []

        class _Menu(QMenu):
            def exec(self, *_a):
                seen.extend(a.text() for a in self.actions())
                return next((a for a in self.actions() if a.text() == pick), None)

        pos = QPoint(5, t.rowViewportPosition(row) + 2)
        with mock.patch.object(table_menu, "QMenu", _Menu):
            t.contextMenuEvent(QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, pos, t.mapToGlobal(pos)))
        return seen

    def test_a_marker_set_later_shows_on_the_row(self):
        t = self.wishlist("A", "B")
        t.set_resume_marks({str(_e("A").path): 30000})
        self.assertIn("↩ 0:30", self.title_cell(t, "A"))
        self.assertNotIn("↩", self.title_cell(t, "B"))

    def test_the_badge_goes_when_the_marker_does(self):
        t = self.wishlist("A")
        t.set_resume_marks({str(_e("A").path): 30000})
        t.set_resume_marks({})
        self.assertNotIn("↩", self.title_cell(t, "A"))

    def test_the_menu_offers_to_reset_it(self):
        t = self.wishlist("A", "B")
        t.set_resume_marks({str(_e("A").path): 30000})
        self.assertIn(RESET, self.menu(t, "A"))
        self.assertNotIn(RESET, self.menu(t, "B"))

    def test_picking_it_forgets_the_marker(self):
        t = self.wishlist("A")
        t.set_resume_marks({str(_e("A").path): 30000})
        cleared = []
        with mock.patch.object(TableHost, "clear_resume",
                               lambda _h, p: cleared.append(str(p)), create=True):
            self.menu(t, "A", pick=RESET)
        self.assertEqual(cleared, [str(_e("A").path)])


if __name__ == "__main__":
    unittest.main()
