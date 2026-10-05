#!/usr/bin/env python3
"""Tests that the 🔁 "potential replace" marks (Ctrl+M) survive a save/restore.

Run:  py -m unittest tests.gui.test_marks_persist -v

The marks used to live only in `PlaylistTable._marked_paths`, so closing the app
threw them away. They now ride along in the deck snapshot that feeds both the
autosave file and the undo timeline ("marked" key of _serialize_playlist_state).

A real MainWindow is built offscreen with a hand-made library (no scan, no file
reads) and one dynamic deck; the deck is then snapshotted, wiped and restored.
"""

import os
import tempfile
import unittest
from pathlib import Path

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_marks_"))

from dancesport_planner import (  # noqa: E402
    MusicEntry,
    MusicLibrary,
    PlaylistSuggester,
    RoundConfig,
)
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)


def _entry(name: str, dance: str) -> MusicEntry:
    return MusicEntry(
        path=Path(rf"C:\music\tanzcds\lateincd\{dance}\{name}.mp3"),
        title=name, dance=dance, bpm=None, popularity=3)


class MarkPersistenceTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        cls._settings_dir = tempfile.mkdtemp(prefix="dp_marks_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._settings_dir)
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)

        self.cha = _entry("Cha One (CC 30)", "CC")
        self.rum = _entry("Rum One (RB 25)", "RB")
        lib = MusicLibrary()
        lib.entries.extend([self.cha, self.rum])
        self.win._lib = lib

        # Deck B (not the active deck) so _deck_meta falls back to the stored
        # context instead of the live combos.
        self.table = self.win._tableB
        self.table.load(
            {"Runde 1": [[self.cha, self.rum]]},
            ["CC", "RB"],
            [RoundConfig(name="Runde 1", heats=1, tier="final")],
            "S",
            play_cb=self.win._play_or_stop,
            suggester=PlaylistSuggester(lib),
            use_timbre=False, style="Latin",
            dynamic=True, capacity=[1],
        )

    def _song_row(self, entry) -> int:
        """Grid row showing `entry` (skips header/spacer rows)."""
        for r, m in enumerate(self.table._row_meta):
            if m and m.entry is entry:
                return r
        self.fail(f"no row for {entry.title}")

    # ----- save ---------------------------------------------------------------

    def test_marked_songs_land_in_the_snapshot(self):
        self.table._toggle_mark({self._song_row(self.cha)})
        state = self.win._serialize_playlist_state(self.table)
        self.assertEqual(state["marked"], [str(self.cha.path)])

    def test_unmarked_deck_writes_no_marked_key(self):
        state = self.win._serialize_playlist_state(self.table)
        self.assertNotIn("marked", state)

    def test_stale_marks_are_not_saved(self):
        """A mark left behind by a re-rolled/removed song must not pile up."""
        self.table._marked_paths.add(r"C:\music\tanzcds\lateincd\CC\Gone (CC 30).mp3")
        self.table._marked_paths.add(str(self.rum.path))
        state = self.win._serialize_playlist_state(self.table)
        self.assertEqual(state["marked"], [str(self.rum.path)])

    # ----- restore ------------------------------------------------------------

    def test_marks_come_back_after_a_wipe_and_restore(self):
        self.table._toggle_mark({self._song_row(self.rum)})
        state = self.win._serialize_playlist_state(self.table)

        self.win._blank_deck(self.table)
        self.win._restore_into_deck(self.table, state)

        self.assertEqual(self.table._marked_paths, {str(self.rum.path)})
        # …and the restored deck still snapshots them (round-trip is stable).
        self.assertEqual(
            self.win._serialize_playlist_state(self.table)["marked"],
            [str(self.rum.path)])

    def test_restoring_a_snapshot_without_marks_clears_them(self):
        state = self.win._serialize_playlist_state(self.table)   # no marks
        self.table._toggle_mark({self._song_row(self.cha)})
        self.win._restore_into_deck(self.table, state)
        self.assertEqual(self.table._marked_paths, set())

    def test_blanking_a_deck_drops_its_marks(self):
        self.table._toggle_mark({self._song_row(self.cha)})
        self.win._blank_deck(self.table)
        self.assertEqual(self.table._marked_paths, set())

    def test_a_fresh_load_starts_unmarked(self):
        """Generating into the deck again must not hand a re-picked song the
        orange mark it carried in the previous playlist."""
        self.table._toggle_mark({self._song_row(self.cha)})
        self.table.load(
            {"Runde 1": [[self.cha, self.rum]]},
            ["CC", "RB"],
            [RoundConfig(name="Runde 1", heats=1, tier="final")],
            "S",
            play_cb=self.win._play_or_stop,
            suggester=PlaylistSuggester(self.win._lib),
            use_timbre=False, style="Latin",
            dynamic=True, capacity=[1],
        )
        self.assertEqual(self.table._marked_paths, set())

    def test_an_in_place_rebuild_keeps_the_marks(self):
        """Structural re-renders (drop, add heat, compact toggle) go through
        _rebuild_dynamic — the marks must ride along."""
        self.table._toggle_mark({self._song_row(self.cha)})
        self.table._rebuild_dynamic()
        self.assertEqual(self.table._marked_paths, {str(self.cha.path)})

    # ----- who may mark at all ------------------------------------------------

    def test_a_dynamic_deck_may_mark(self):
        self.assertTrue(self.table._marks_allowed())

    def test_a_static_deck_may_not_mark(self):
        """A planned grid is output, not a working list — nothing to flag there."""
        self.table.load(
            {"Runde 1": [[self.cha, self.rum]]},
            ["CC", "RB"],
            [RoundConfig(name="Runde 1", heats=1, tier="final")],
            "S",
            play_cb=self.win._play_or_stop,
            suggester=PlaylistSuggester(self.win._lib),
            use_timbre=False, style="Latin",
            dynamic=False,
        )
        self.assertFalse(self.table._marks_allowed())


class FreeOrderMarkTest(MarkPersistenceTest):
    """The same marks on a free running order — the mode the evening is played
    from, where "come back to this one" matters most."""

    def setUp(self):
        super().setUp()
        self.table.load_player_list([self.cha, self.rum], "Abend",
                                    play_cb=self.win._play_or_stop)

    # The inherited dynamic-grid cases don't apply to a flat list; the ones that
    # do are re-stated below against the running order.
    test_stale_marks_are_not_saved = None
    test_a_fresh_load_starts_unmarked = None
    test_an_in_place_rebuild_keeps_the_marks = None
    test_a_dynamic_deck_may_mark = None
    test_a_static_deck_may_not_mark = None

    def test_a_free_running_order_may_mark(self):
        self.assertTrue(self.table._marks_allowed())

    def test_the_snapshot_is_still_a_running_order(self):
        """The mark must not turn the list back into a themed deck on restore."""
        self.table._toggle_mark({self._song_row(self.cha)})
        state = self.win._serialize_playlist_state(self.table)
        self.assertTrue(state["player_list"])
        self.assertEqual(state["marked"], [str(self.cha.path)])

    def test_marks_survive_a_conversion_from_a_grid(self):
        """Switching a marked dynamic deck to the free order keeps the marks —
        it is the same list, only laid out flat."""
        self.table.load(
            {"Runde 1": [[self.cha, self.rum]]},
            ["CC", "RB"],
            [RoundConfig(name="Runde 1", heats=1, tier="final")],
            "S",
            play_cb=self.win._play_or_stop,
            suggester=PlaylistSuggester(self.win._lib),
            use_timbre=False, style="Latin",
            dynamic=True, capacity=[1],
        )
        self.table._toggle_mark({self._song_row(self.rum)})
        self.table.become_player_list()
        self.assertTrue(self.table._player_list)
        self.assertEqual(self.table._marked_paths, {str(self.rum.path)})


if __name__ == "__main__":
    unittest.main()
