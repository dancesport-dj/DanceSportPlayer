#!/usr/bin/env python3
"""Playlist rows dragged onto the EMPTY 🤸 panel become a party list.

Run:  py -m unittest tests.gui.test_party_drop_rows -v

Marcel: rows dragged from a playlist deck onto the empty party panel were
sorted into a competition grid, the ✋ button never showed and the window froze
with no progress bar. An empty panel has `_warmup` down (only a load raises it),
so the drop took the deck's dynamic-grid path. It is now opened like an .m3u
dropped there: the rows in the order they were dragged, as a party list.

A real MainWindow on screen offscreen, as the panel's buttons are the window's.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pdrop_"))

from PySide6.QtWidgets import QApplication, QToolButton

from planner.models import MusicEntry
from planner.music.library import MusicLibrary
from tests.gui.monkey_support import drag_rows
from tests.qt_test_support import reap_widget, stub_window_startup

# Not in the order a competition grid puts them: a sort shows at once.
DANCES = ("CC", "WW", "SA", "TG", "LW", "RB")


class PartyDropRowsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        cls._qs_dir = tempfile.mkdtemp(prefix="dp_pdrop_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._qs_dir)
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)
        cls.dir = Path(tempfile.mkdtemp(prefix="dp_pdrop_music_"))

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.lib = MusicLibrary()
        self.win._library.lib = self.lib
        self.win.resize(1600, 1000)
        self.win.show()
        self.app.processEvents()
        self.entries = [MusicEntry(path=self.dir / f"t_{i}_{d}.mp3", title=f"{d} {i}",
                                   dance=d, duration=180)
                        for i, d in enumerate(DANCES)]
        for e in self.entries:      # a drop onto a filled list reads the files
            e.path.touch()
        self.lib.entries.extend(self.entries)
        self.deck = self.win._deckset.table
        self.deck.load_player_list(self.entries, "Deck", play_cb=self.win._play_or_stop)
        self.app.processEvents()
        self.party = self.win._deckset.warmup_table
        self.win._ensure_empty_warmup()
        self.app.processEvents()

    def _drop_all(self):
        self.deck.selectAll()
        drag_rows(self.deck, self.party, None)
        self.app.processEvents()

    def _titles(self, table):
        return [m.entry.title for m in table._row_meta if m and m.entry is not None]

    def _row(self, table, title):
        return next(r for r, m in enumerate(table._row_meta)
                    if m and m.entry is not None and m.entry.title == title)

    def test_the_rows_arrive_in_the_order_they_were_dragged(self):
        self.assertEqual(self._titles(self.party), [])
        self._drop_all()
        self.assertEqual(self._titles(self.party), [e.title for e in self.entries])

    def test_the_panel_holds_a_party_list_not_a_grid(self):
        self._drop_all()
        self.assertTrue(self.party._warmup, "the panel did not become a party list")
        self.assertFalse(self.party._dynamic, "the panel became a competition grid")

    def test_the_hand_button_shows(self):
        self._drop_all()
        # The panel's own, in its header next to 🩺: a deck has one too.
        header = self.win._warmup_check_btn.parentWidget()
        hands = [b for b in header.findChildren(QToolButton)
                 if b.isCheckable() and b.text() in ("✋", "🔒")]
        self.assertEqual(len(hands), 1, "no ✋ button on the panel")
        self.assertTrue(any(b.isVisible() for b in hands), "✋ stays hidden")

    def test_the_titles_move_out_of_the_deck(self):
        """As onto a filled panel: a drag from a deck moves, Ctrl copies."""
        self.deck.selectRow(self._row(self.deck, "SA 2"))
        drag_rows(self.deck, self.party, None)
        self.app.processEvents()
        self.assertEqual(self._titles(self.party), ["SA 2"])
        self.assertNotIn("SA 2", self._titles(self.deck))

    def test_a_second_drop_inserts_into_the_list(self):
        self.deck.selectRow(self._row(self.deck, "SA 2"))
        drag_rows(self.deck, self.party, None)
        self.app.processEvents()
        self.deck.selectRow(self._row(self.deck, "LW 4"))
        drag_rows(self.deck, self.party, self._row(self.party, "SA 2"))
        self.app.processEvents()
        self.assertEqual(sorted(self._titles(self.party)), ["LW 4", "SA 2"])
        self.assertTrue(self.party._warmup)
        self.assertFalse(self.party._dynamic)


if __name__ == "__main__":
    unittest.main(verbosity=2)
