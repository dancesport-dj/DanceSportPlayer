#!/usr/bin/env python3
"""A view toggle / column reorder / dynamic rebuild re-renders the deck through
`PlaylistTable.load()`. That call used to reset whatever it was not handed, so the
pins, the marks, the hidden dances and the stacked day-plan context vanished (and
the autosave stored the empty state).

Run:  py -m unittest tests.gui.test_view_toggle_keeps_state -v
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_viewtoggle_"))

from dancesport_planner import (
    MusicEntry,
    MusicLibrary,
    PlaylistSuggester,
    RoundConfig,
)
from tests.qt_test_support import reap_widget, stub_window_startup


def _entry(name: str, dance: str) -> MusicEntry:
    return MusicEntry(
        path=Path(rf"C:\music\tanzcds\lateincd\{dance}\{name}.mp3"),
        title=name, dance=dance, bpm=None, popularity=3)


class ViewToggleKeepsStateTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        cls._settings_dir = tempfile.mkdtemp(prefix="dp_viewtoggle_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._settings_dir)
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)

        self.cha = _entry("Cha One (CC 30)", "CC")
        self.rum = _entry("Rum One (RB 25)", "RB")
        lib = MusicLibrary()
        lib.entries.extend([self.cha, self.rum])
        self.win._library.lib = lib
        self.lib = lib
        self.table = self.win._deckset.tableB

    def _loadStatic(self):
        self.table.load(
            {"Runde 1": [[self.cha, self.rum]]},
            ["CC", "RB"],
            [RoundConfig(name="Runde 1", heats=1, tier="final")],
            "S",
            play_cb=self.win._play_or_stop,
            suggester=PlaylistSuggester(self.lib),
            use_timbre=False, style="Latin",
            dynamic=False,
        )
        self.table._pinned_paths = {str(self.cha.path)}
        self.table._round_skip_dances = {"Runde 1": {"RB"}}
        self.table._round_ctx = {"Runde 1": {"exclude": [str(self.rum.path)]}}

    def _assertStateKept(self):
        self.assertEqual(self.table._pinned_paths, {str(self.cha.path)})
        self.assertEqual(self.table._round_skip_dances, {"Runde 1": {"RB"}})
        self.assertEqual(self.table._round_ctx,
                         {"Runde 1": {"exclude": [str(self.rum.path)]}})

    def test_static_grouping_toggle_keeps_pins_skips_and_ctx(self):
        self._loadStatic()
        self.table.set_grouping(1)
        self._assertStateKept()

    def test_static_dance_column_reorder_keeps_pins(self):
        self._loadStatic()
        self.table._reorder_dance("RB", "CC")
        self.assertEqual(self.table._loaded_dances, ["RB", "CC"])
        self._assertStateKept()

    def test_dynamic_rebuild_keeps_round_ctx(self):
        self.table.load(
            {"Runde 1": [[self.cha, self.rum]]},
            ["CC", "RB"],
            [RoundConfig(name="Runde 1", heats=1, tier="final")],
            "S",
            play_cb=self.win._play_or_stop,
            suggester=PlaylistSuggester(self.lib),
            use_timbre=False, style="Latin",
            dynamic=True, capacity=[1],
        )
        self.table._round_ctx = {"Runde 1": {"exclude": [str(self.rum.path)]}}
        self.table._pinned_paths = {str(self.cha.path)}
        self.table._rebuild_dynamic()
        self.assertEqual(self.table._round_ctx,
                         {"Runde 1": {"exclude": [str(self.rum.path)]}})
        self.assertEqual(self.table._pinned_paths, {str(self.cha.path)})

    # The .m3u the deck was imported from / saved to: load() resets it for a
    # fresh load, and the autosave then stored the deck as detached from its file.
    def test_static_grouping_toggle_keeps_the_m3u_path(self):
        self._loadStatic()
        self.table._m3u_path = Path(r"C:\lists\saturday.m3u")
        self.table.set_grouping(1)
        self.assertEqual(self.table._m3u_path, Path(r"C:\lists\saturday.m3u"))

    def test_static_dance_column_reorder_keeps_the_m3u_path(self):
        self._loadStatic()
        self.table._m3u_path = Path(r"C:\lists\saturday.m3u")
        self.table._reorder_dance("RB", "CC")
        self.assertEqual(self.table._m3u_path, Path(r"C:\lists\saturday.m3u"))

    def test_dynamic_rebuild_keeps_the_m3u_path(self):
        self._loadDynamic()
        self.table._m3u_path = Path(r"C:\lists\saturday.m3u")
        self.table._rebuild_dynamic()
        self.assertEqual(self.table._m3u_path, Path(r"C:\lists\saturday.m3u"))

    def test_a_fresh_load_still_detaches_the_deck_from_its_file(self):
        self._loadStatic()
        self.table._m3u_path = Path(r"C:\lists\saturday.m3u")
        self._loadStatic()
        self.assertIsNone(self.table._m3u_path)

    def _loadDynamic(self):
        self.table.load(
            {"Runde 1": [[self.cha, self.rum]]},
            ["CC", "RB"],
            [RoundConfig(name="Runde 1", heats=1, tier="final")],
            "S",
            play_cb=self.win._play_or_stop,
            suggester=PlaylistSuggester(self.lib),
            use_timbre=False, style="Latin",
            dynamic=True, capacity=[1],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
