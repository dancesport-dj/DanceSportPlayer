#!/usr/bin/env python3
"""Every deck offers "take this title out" in its right-click menu.

Run:  py -m unittest tests.gui.test_remove_title_menu -v

Del (and ⌫) has always removed the selected titles, and a dynamic deck has
always had the menu entry as well. A static deck and a player-only running
order had only the key — which is not discoverable, and on a Mac laptop
there is no Del key at all, just ⌫.

The wording is the part worth pinning. A planned grid keeps the empty slot
and a free running order does not, so the two cannot share a sentence: told
"the slot stays empty" while running an evening off a free order, the
operator is being promised something that will not happen.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_rmmenu_"))

from PySide6.QtCore import QPoint  # noqa: E402
from PySide6.QtGui import QContextMenuEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QMenu, QWidget  # noqa: E402

from gui import table_actions  # noqa: E402
from planner.models import MusicEntry  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

SONGS = [MusicEntry(path=Path(rf"C:\music\tanzcds\LW{i}.mp3"),
                    title=f"LW {i}", dance="LW", duration=180)
         for i in (1, 2, 3)]


class RemoveTitleMenuTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _table(self, running_order: bool):
        from gui.playlist_table import PlaylistTable
        win = QWidget()
        win._settings = {"app_mode": "both"}
        self.addCleanup(reap_widget, win)
        t = PlaylistTable()
        t.setParent(win)
        if running_order:
            t.load_player_list(SONGS, "🏁 Order", lambda *a: None, None)
        else:
            t.load_warmup(SONGS, "🤸 Party", "both", "S", False,
                          lambda *a: None, None)
        return t

    def _menu(self, t, row):
        """Action texts of the menu opened on `row`. QMenu.exec is swapped out
        the same way test_app_mode does it — a real exec would block."""
        opened = []

        class _Menu(QMenu):
            def exec(self, *_args):
                opened.append([a.text() for a in self.actions()])
                return None

        pos = QPoint(5, t.rowViewportPosition(row) + 2)
        with mock.patch.object(table_actions, "QMenu", _Menu):
            t.contextMenuEvent(QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, pos, t.mapToGlobal(pos)))
        self.assertTrue(opened, "the context menu never opened")
        return opened[0]

    def _song_row(self, t):
        rows = list(t._row_meta.song_rows())
        self.assertTrue(rows, "the fixture holds no songs")
        return rows[0]

    def test_a_static_deck_offers_it(self):
        t = self._table(running_order=False)
        texts = self._menu(t, self._song_row(t))
        self.assertIn("🗑  Remove this title (keep slot)", texts)

    def test_a_running_order_says_the_title_simply_goes(self):
        """No slot is left behind there, so it must not promise one."""
        t = self._table(running_order=True)
        texts = self._menu(t, self._song_row(t))
        self.assertIn("🗑  Remove this title", texts)
        self.assertNotIn("🗑  Remove this title (keep slot)", texts)

    def test_a_selection_is_removed_as_a_whole(self):
        t = self._table(running_order=False)
        rows = list(t._row_meta.song_rows())
        self.assertGreaterEqual(len(rows), 2)
        t.clearSelection()
        for r in rows:
            t.selectRow(r)
            t.setSelectionMode(t.SelectionMode.MultiSelection)
        texts = self._menu(t, rows[0])
        self.assertIn(f"🗑  Remove {len(rows)} selected titles (keep slots)",
                      texts)

    def test_right_clicking_outside_the_selection_takes_only_that_row(self):
        """Otherwise a stray right-click wipes a selection made minutes ago."""
        t = self._table(running_order=False)
        rows = list(t._row_meta.song_rows())
        t.clearSelection()
        t.selectRow(rows[0])
        self.assertEqual(t._title_rows_for(rows[-1]), {rows[-1]})

    def test_the_prompt_matches_the_kind_of_list(self):
        self.assertIn("slot", self._table(False)._remove_songs_prompt(1))
        self.assertIn("running order",
                      self._table(True)._remove_songs_prompt(1))

    def test_german_reaches_the_plural_too(self):
        """The plural is built with %, not an f-string, for exactly this: an
        f-string arrives at the menu assembled and matches no catalog key."""
        from planner import i18n
        i18n.set_active("de")
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)
        t = self._table(running_order=False)
        for n in (1, 3):
            caption = t._remove_titles_caption(n)
            prompt = t._remove_songs_prompt(n)
            self.assertIn("entfernen", caption, f"n={n} caption stayed English")
            self.assertIn("entfernen", prompt, f"n={n} prompt stayed English")
        self.assertIn("3", t._remove_titles_caption(3))

    def test_the_running_order_caption_is_short_in_german_too(self):
        from planner import i18n
        i18n.set_active("de")
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)
        t = self._table(running_order=True)
        self.assertEqual(t._remove_titles_caption(1),
                         "🗑  Diesen Titel entfernen")
        self.assertEqual(t._remove_titles_caption(3),
                         "🗑  3 ausgewählte Titel entfernen")


if __name__ == "__main__":
    unittest.main()
