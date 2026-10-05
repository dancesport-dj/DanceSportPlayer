#!/usr/bin/env python3
"""The deck an 🤖 / 📝 AI run leaves behind is a free running order.

Run:  py -m unittest tests.gui.test_ai_free_order -v

A wish list is not a draw. It is the order the evening is played in, and the
person who wrote it wants to push the rows around and drop more titles in. As a
theme grid a row could only move within its own dance and a drop replaced what
it landed on, so the list came out of the run all but uneditable — ✋ free order
is what it is meant to be, and that is how the run has to hand it over.

A real MainWindow offscreen with a hand-made library; the done-handler is called
straight with the picks a model would have sent back.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_aifree_"))

from dancesport_planner import MusicEntry, MusicLibrary  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)


def _entry(name: str, dance: str) -> MusicEntry:
    return MusicEntry(
        path=Path(rf"C:\music\tanzcds\lateincd\{dance}\{name}.mp3"),
        title=name, dance=dance, bpm=None, popularity=3)


class AiFreeOrderTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        cls._settings_dir = tempfile.mkdtemp(prefix="dp_aifree_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._settings_dir)
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)

        self.tracks = [_entry("Cha One (CC 30)", "CC"),
                       _entry("Rum One (RB 25)", "RB"),
                       _entry("Sam One (SA 50)", "SA")]
        lib = MusicLibrary()
        lib.entries.extend(self.tracks)
        self.win._lib = lib

    def _finish_a_wish_run(self):
        """The done-handler with the picks a wish run would have produced."""
        self.win._ai_ctx = dict(mode="flat", label="📝 Wish list",
                                candidates=list(self.tracks))
        self.win._on_ai_playlist_done(
            [{"n": i + 1, "why": "wished for"} for i in range(len(self.tracks))],
            "", "claude")

    def test_the_deck_comes_out_in_free_order(self):
        self._finish_a_wish_run()
        self.assertTrue(self.win._table.plays_flat())
        self.assertEqual(self.win._deck_mode(self.win._table), "free")

    def test_every_wish_is_still_there_in_the_order_it_was_picked(self):
        """Free order re-renders the list — it must not lose or re-sort it."""
        self._finish_a_wish_run()
        self.assertEqual([e.title for e in self.win._table._row_meta.entries()],
                         [t.title for t in self.tracks])

    def test_a_dropped_title_is_added_not_swapped_in(self):
        """The whole point of free order: a new wish joins the list."""
        self._finish_a_wish_run()
        self.assertTrue(self.win._table._deck_adds_on_drop()
                        or self.win._table._player_list)

    def test_the_deck_is_named_after_the_list(self):
        self._finish_a_wish_run()
        self.assertEqual(self.win.deck(self.win._table).name, "📝 Wish list")

    def test_the_answer_goes_to_the_deck_that_asked_for_it(self):
        """A run takes minutes and the active deck follows the focus. Clicking
        another deck meanwhile must not get that deck's playlist overwritten."""
        asked, other = self.win._decks[0], self.win._decks[1]
        self.win._set_active_table(asked)
        self.win._ai_ctx = dict(mode="flat", label="📝 Wish list",
                                candidates=list(self.tracks), table=asked)
        self.win._set_active_table(other)      # the operator clicks deck 2
        self.win._on_ai_playlist_done(
            [{"n": i + 1} for i in range(len(self.tracks))], "", "claude")
        self.assertEqual([e.title for e in asked._row_meta.entries()],
                         [t.title for t in self.tracks])
        self.assertEqual(list(other._row_meta.entries()), [])

    def test_a_competition_run_still_builds_a_grid(self):
        """Only the flat list changes: a draw is still a draw."""
        from dancesport_planner import RoundConfig
        self.win._ai_ctx = dict(
            mode="competition", style="Latin", age="Hgr", dance_class="D",
            dances=["CC", "RB"],
            rounds=[RoundConfig(name="Runde 1", heats=1, tier="final")],
            use_timbre=False, candidates=list(self.tracks))
        self.win._on_ai_playlist_done(
            [{"n": 1, "dance": "CC", "round": "Runde 1", "heat": 1},
             {"n": 2, "dance": "RB", "round": "Runde 1", "heat": 1}], "", "claude")
        self.assertFalse(self.win._table.plays_flat())


if __name__ == "__main__":
    unittest.main()
