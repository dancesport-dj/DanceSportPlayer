#!/usr/bin/env python3
"""Tests for playlist decks in a player-only install.

Run:  py -m unittest tests.gui.test_player_deck_drop -v

Someone who only runs the music never plans a round, so a deck there has no
static/dynamic choice to make: the 🔒/🔓 toggle is gone from the header and from
both context menus, and a song dragged in is ADDED to the list where it was
dropped instead of replacing the title under the cursor — losing a planned title
to a drop is never what the operator at the desk meant.
"""

import os
import tempfile
import unittest
from pathlib import Path

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pdrop_"))

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl  # noqa: E402
from PySide6.QtGui import QDropEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.models import MusicEntry, RoundConfig  # noqa: E402


def _e(dance, n):
    return MusicEntry(path=Path(rf"C:\music\{dance}{n}.mp3"), title=f"{dance} {n}",
                      dance=dance, bpm=None)


class _Win(QWidget):
    """Stands in for MainWindow: the deck reads its app mode off the window."""

    def __init__(self, mode: str):
        super().__init__()
        self._settings = {"app_mode": mode}


class _DeckTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.file = Path(tempfile.mkdtemp(prefix="dp_pdrop_f_")) / "wish.mp3"
        cls.file.write_bytes(b"x")

    def deck(self, mode: str):
        """A STATIC two-round deck inside a window of app mode `mode`."""
        win = _Win(mode)
        t = PlaylistTable()
        t.setParent(win)
        self.addCleanup(reap_widget, win)
        t.load({"Vorrunde": [[_e("LW", 1), _e("TG", 2)]],
                "Finale": [[_e("LW", 3), _e("TG", 4)]]},
               ["LW", "TG"],
               [RoundConfig(name="Vorrunde", heats=1, tier="early"),
                RoundConfig(name="Finale", heats=1, tier="final")],
               "S", play_cb=None, suggester=None, use_timbre=False)
        return t

    def drop(self, table, row: int):
        """Drop the file onto `row` and report which route took it: 'add' (the
        grid grows) or 'replace' (the slot under the cursor) — an empty list
        means neither, i.e. the flat insert of a player-only install."""
        took = []
        table._dynamic_drop = lambda *a, **kw: took.append("add")
        table._replace_row_with_path = lambda *a, **kw: took.append("replace") or True
        table._move_from_drag_source = lambda *a, **kw: None
        table._planned_keys = lambda *a, **kw: set()
        # The temp file is a placeholder, not a real MP3 — resolving it would ask
        # the library (and pop a "couldn't read" box). The drop ROUTE is what is
        # under test, so hand the deck the entry it would have got.
        table._resolve_drop_entries = lambda files: [
            MusicEntry(path=self.file, title="wish", dance="WW", bpm=None)]
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(self.file))])
        pos = QPointF(20, table.rowViewportPosition(row) + table.rowHeight(row) / 2)
        table.resize(700, 400)
        table.dropEvent(QDropEvent(pos, Qt.DropAction.CopyAction, mime,
                                   Qt.MouseButton.LeftButton,
                                   Qt.KeyboardModifier.NoModifier))
        return took


class DropRouteTest(_DeckTest):

    def _song_row(self, table) -> int:
        return next(r for r, m in enumerate(table._row_meta)
                    if m and m.entry is not None)

    def test_a_player_flattens_the_grid_and_inserts(self):
        """A draw still on screen from before the install was switched is
        re-rendered as the running order, and the dropped song lands in it —
        no slot is overwritten and no round is grown."""
        t = self.deck("player")
        self.assertEqual(self.drop(t, self._song_row(t)), [],
                         "took the grid-building or the slot-replacing route")
        self.assertTrue(t._player_list)
        titles = [m.entry.title for m in t._row_meta if m and m.entry]
        self.assertIn("wish", titles)
        self.assertEqual(len(titles), 5, "the four planned titles are all kept")

    def test_a_planner_still_replaces_the_slot(self):
        """Unchanged where playlists are built: a drop onto a slot swaps its
        song — that IS how a planned title gets exchanged."""
        t = self.deck("both")
        self.assertEqual(self.drop(t, self._song_row(t)), ["replace"])


class AddsOnDropTest(_DeckTest):

    def test_only_decks_take_the_new_route(self):
        """The flat wishlists and the ETDS party list already insert at the
        cursor gap — they must keep their own paths."""
        t = self.deck("player")
        self.assertTrue(t._deck_adds_on_drop())
        t._warmup = True
        self.assertFalse(t._deck_adds_on_drop())
        t._warmup, t._flat_mode = False, True
        self.assertFalse(t._deck_adds_on_drop())

    def test_a_planner_deck_does_not(self):
        self.assertFalse(self.deck("both")._deck_adds_on_drop())

    def test_an_older_settings_file_reads_as_a_planner(self):
        t = self.deck("both")
        t.window()._settings = {}
        self.assertFalse(t.player_only())


class ModeToggleTest(_DeckTest):
    """The 🔒/🔓 entry in the grid's own right-click menu."""

    def _menu_texts(self, mode: str):
        from unittest import mock

        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QContextMenuEvent
        from PySide6.QtWidgets import QMenu

        from gui import table_actions

        opened = []

        class _Menu(QMenu):
            def exec(self, *_args):
                opened.append([a.text() for a in self.actions()])
                return None

        t = self.deck(mode)
        t.resize(700, 400)
        row = next(r for r, m in enumerate(t._row_meta) if m and m.entry)
        pos = QPoint(20, t.rowViewportPosition(row) + 2)
        with mock.patch.object(table_actions, "QMenu", _Menu):
            t.contextMenuEvent(QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, pos, t.mapToGlobal(pos)))
        self.assertTrue(opened, "the context menu never opened")
        return opened[0]

    def test_a_player_is_not_offered_the_mode(self):
        self.assertFalse([x for x in self._menu_texts("player")
                          if "dynamic mode" in x or "static mode" in x])

    def test_a_planner_keeps_it(self):
        self.assertTrue([x for x in self._menu_texts("both")
                         if "dynamic mode" in x or "static mode" in x])

    def test_the_menu_is_not_simply_empty(self):
        """Guards the fixture."""
        self.assertTrue([x for x in self._menu_texts("player")
                         if "Copy file path" in x])


if __name__ == "__main__":
    unittest.main()
