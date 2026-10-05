#!/usr/bin/env python3
"""The viewport stays where the operator left it when a list re-renders.

Run:  py -m unittest tests.gui.test_scroll_kept -v

A running order and the Wishlist are rebuilt row by row whenever they change —
a track dragged out to another deck, a track dropped in, a sort. The rebuild
throws every row away, so the scrollbar falls back to the top and the operator,
who was reading the middle of a 200-title evening, has to find their place
again. `_rebuild_dynamic` always kept its offset; these lists now do too.
"""

import os
import tempfile
import unittest
from pathlib import Path

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_scroll_"))

from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from shared.columns import _COL_TITLE  # noqa: E402
from gui.playlist_table import _SCROLL_MS, PlaylistTable  # noqa: E402
from planner.models import MusicEntry  # noqa: E402
from player.main_player import PlayerControlMixin  # noqa: E402
from player.playback_state import PlaybackState  # noqa: E402


def _e(n):
    return MusicEntry(path=Path(rf"C:\music\LW{n}.mp3"), title=f"LW {n}",
                      dance="LW", bpm=None)


class _Win(QWidget):

    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "both"}


class _ScrollTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def scrolled_table(self, loader) -> PlaylistTable:
        """A list long enough to scroll, parked in the middle of itself."""
        win = _Win()
        t = PlaylistTable()
        t.setParent(win)
        t.resize(700, 300)
        win.resize(720, 320)
        self.addCleanup(reap_widget, win)
        loader(t, [_e(i) for i in range(60)])
        win.show()
        self.app.processEvents()
        bar = t.verticalScrollBar()
        self.assertGreater(bar.maximum(), 0, "list is not long enough to scroll")
        bar.setValue(bar.maximum() // 2)
        self.app.processEvents()
        return t

    def middle_row(self, table) -> int:
        return table.rowAt(table.viewport().rect().center().y())


class FreeOrderScrollTest(_ScrollTest):

    def deck(self) -> PlaylistTable:
        return self.scrolled_table(
            lambda t, entries: t.load_player_list(entries, "Abend", play_cb=None))

    def test_dragging_a_track_out_keeps_the_view(self):
        """The source side of a deck → deck move: the row is taken out of the
        running order, and the rest of the list stays under the eye."""
        t = self.deck()
        before = t.verticalScrollBar().value()
        t._clear_slots_at({self.middle_row(t)}, select_after=True)
        self.assertEqual(t.verticalScrollBar().value(), before)

    def test_a_re_render_keeps_the_view(self):
        t = self.deck()
        before = t.verticalScrollBar().value()
        t._reload_warmup()
        self.assertEqual(t.verticalScrollBar().value(), before)

    def test_a_shorter_list_scrolls_no_further_than_its_end(self):
        """Emptying most of the list cannot leave the bar past the new end."""
        t = self.deck()
        keep = t._row_meta.entries()[:3]
        t._reload_warmup(keep)
        bar = t.verticalScrollBar()
        self.assertLessEqual(bar.value(), bar.maximum())


class _Desk(PlayerControlMixin):
    """The player desk down to the cue decision; `_play_or_stop` only records."""

    def __init__(self, playing: Path, tables):
        self._player = object()          # only tested for truthiness
        self._playback = PlaybackState()
        self._playback.path = playing
        self._all_tables = tuple(tables)

    def _play_or_stop(self, path, start=True):
        self._playback.path = path


class LoadedTitleDraggedOutTest(_ScrollTest):
    """Dragging the title that sits on the player out to another deck stops it,
    and the emptied player cues the deck's first title. That cue marks the row —
    it must not also scroll the deck up to it, away from where the operator was
    working."""

    def test_the_view_stays_where_the_title_was_dragged_from(self):
        t = self.scrolled_table(
            lambda tbl, entries: tbl.load_player_list(entries, "Abend", play_cb=None))
        row = self.middle_row(t)
        desk = _Desk(t._row_meta[row].entry.path, tables=(t,))
        t._play_cb = desk._play_or_stop
        t._current_play_row = row
        t.loaded.connect(desk._cue_first_track)
        before = t.verticalScrollBar().value()

        t._clear_slots_at({row}, select_after=True)
        QTest.qWait(_SCROLL_MS + 200)     # let a glide to the cued row finish

        self.assertEqual(desk._playback.path, t.first_track_path())   # it was cued
        self.assertEqual(t.verticalScrollBar().value(), before)

    def test_selecting_the_cued_row_does_not_scroll_either(self):
        """With nothing selected the cue picks its row — in place, no jump."""
        t = self.scrolled_table(
            lambda tbl, entries: tbl.load_player_list(entries, "Abend", play_cb=None))
        t.clearSelection()
        desk = _Desk(None, tables=(t,))
        before = t.verticalScrollBar().value()

        desk._cue_first_track(t)
        QTest.qWait(_SCROLL_MS + 200)

        self.assertEqual(t.currentRow(), t._current_play_row)
        self.assertEqual(t.verticalScrollBar().value(), before)


class WishlistScrollTest(_ScrollTest):

    def test_sorting_keeps_the_view(self):
        t = self.scrolled_table(
            lambda tbl, entries: tbl.load_wishlist(entries, play_cb=None,
                                                   suggester=None))
        before = t.verticalScrollBar().value()
        t._on_header_section_double_clicked(_COL_TITLE)
        self.assertEqual(t.verticalScrollBar().value(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
