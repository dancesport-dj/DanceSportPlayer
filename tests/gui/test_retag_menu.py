#!/usr/bin/env python3
"""🏷 Re-read MP3 tags, from the context menu of a deck row or the library pane.

Run:  py -m unittest tests.gui.test_retag_menu -v

Tags edited in mp3tag while the app is running are invisible to it: the scan
cache only notices at the next startup. This is that re-read on demand, so what
matters here is that the ROW changes — the deck and the library hold the same
MusicEntry object, and repainting is the only way the new dance or takt shows.
"""

import os
import tempfile
import unittest
from pathlib import Path

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_retag_menu_"))

from dancesport_planner import (  # noqa: E402
    MusicEntry,
    MusicLibrary,
    PlaylistSuggester,
    RoundConfig,
)
from gui.main_music import _tag_change_summary  # noqa: E402
from gui.playlist_table import _COL_BPM, _COL_TITLE  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)


class _StubScan:
    """The ScanCache seam as a dict — no DB, no fingerprints. `_cache` is what
    MusicLibrary._get_scan_cache compares against, so this survives the call."""

    def __init__(self, cache):
        self._cache = cache
        self._store: dict[str, dict] = {}
        self.forgotten: list[Path] = []

    def get(self, path):
        return self._store.get(str(path))

    def put(self, path, data):
        self._store[str(path)] = dict(data)

    def forget(self, path):
        self.forgotten.append(path)
        return self._store.pop(str(path), None) is not None

    def save(self):
        pass


# Real files: the re-read refuses a path that is gone (and a missing file paints
# the row red, which would hide what is under test).
_MUSIC = Path(tempfile.mkdtemp(prefix="dp_retag_music_"))


def _entry(name: str, dance: str, bpm: int | None) -> MusicEntry:
    """An entry whose STORED metadata disagrees with its filename — the state a
    file left in after someone else edited its tags."""
    path = _MUSIC / f"{name}.mp3"
    path.touch()
    return MusicEntry(path=path, title="stale title", dance=dance, bpm=bpm,
                      popularity=3)


class RetagTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        cls._settings_dir = tempfile.mkdtemp(prefix="dp_retag_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._settings_dir)
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)

        # The filename says Cha-Cha at takt 30; the entry still says Slowfox 29.
        self.cha = _entry("Cha One (CC 30)", "SF", 29)
        self.rum = _entry("Rum One (RB 25)", "RB", 25)
        lib = MusicLibrary()
        lib.entries.extend([self.cha, self.rum])
        self.win._lib = lib
        self.scan = _StubScan(self.win._cache)
        lib._scan_cache = self.scan

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

    def _row_of(self, entry) -> int:
        for r, m in enumerate(self.table._row_meta):
            if m and m.entry is entry:
                return r
        self.fail(f"no row for {entry.title}")

    def _cell(self, entry, col) -> str:
        return self.table.item(self._row_of(entry), col).text()

    # ----- the re-read itself -------------------------------------------------

    def test_the_deck_row_shows_the_new_tags(self):
        """The whole point: no restart, no rescan — the row itself changes."""
        self.assertIn("29", self._cell(self.cha, _COL_BPM))
        self.assertEqual(self._cell(self.cha, _COL_TITLE), "stale title")
        self.win._rescan_entry_tags(self.cha)
        self.assertIn("30", self._cell(self.cha, _COL_BPM))
        self.assertIn("Cha One", self._cell(self.cha, _COL_TITLE))

    def test_the_other_rows_are_left_alone(self):
        before = self._cell(self.rum, _COL_TITLE)
        self.win._rescan_entry_tags(self.cha)
        self.assertEqual(self._cell(self.rum, _COL_TITLE), before)

    def test_what_changed_is_reported(self):
        changed = self.win._rescan_entry_tags(self.cha)
        self.assertEqual(changed["dance"], ("SF", "CC"))
        self.assertEqual(changed["bpm"], (29, 30))

    def test_the_cached_row_is_dropped_first(self):
        """Without the drop the re-read just hands back the stale cache."""
        self.win._rescan_entry_tags(self.cha)
        self.assertEqual(self.scan.forgotten, [Path(self.cha.path)])

    def test_a_file_that_is_gone_changes_nothing(self):
        ghost = MusicEntry(path=_MUSIC / "not here.mp3", title="ghost",
                           dance="SF", bpm=29)
        self.assertEqual(self.win._rescan_entry_tags(ghost), {})
        self.assertEqual(self.scan.forgotten, [])
        self.assertEqual(ghost.dance, "SF")

    def test_an_empty_slot_is_ignored(self):
        self.assertEqual(self.win._rescan_entry_tags(None), {})

    # ----- the library pane ---------------------------------------------------

    def test_the_library_pane_re_reads_the_row_it_was_clicked_on(self):
        browser = self.win._lib_browser
        browser.set_entries(self.win._lib.entries)
        browser._rescan_tags(Path(self.cha.path))
        self.assertEqual((self.cha.dance, self.cha.bpm), ("CC", 30))

    def test_the_library_pane_ignores_a_path_it_does_not_hold(self):
        browser = self.win._lib_browser
        browser.set_entries([self.rum])
        browser._rescan_tags(Path(self.cha.path))
        self.assertEqual(self.cha.dance, "SF")


class TagChangeSummaryTest(unittest.TestCase):
    """The one line the toast shows — DB column names would mean nothing."""

    def test_fields_are_named_the_way_the_ui_names_them(self):
        self.assertEqual(_tag_change_summary({"bpm": (29, 30)}), "takt 29 → 30")

    def test_several_changes_are_listed(self):
        out = _tag_change_summary({"dance": ("SF", "CC"), "bpm": (29, 30)})
        self.assertEqual(out, "dance SF → CC, takt 29 → 30")

    def test_a_cleared_field_still_reads_as_a_change(self):
        self.assertEqual(_tag_change_summary({"tag_artist": ("Abba", None)}),
                         "artist Abba → —")

    def test_a_list_of_markers_is_joined(self):
        self.assertEqual(_tag_change_summary({"classes_ok": (None, ["B", "A"])}),
                         "classes — → B/A")

    def test_nothing_changed_is_an_empty_line(self):
        self.assertEqual(_tag_change_summary({}), "")

    def test_the_toast_names_the_fields_in_german(self):
        """The toast follows the UI language; the log line stays English."""
        from planner import i18n
        i18n.set_active("de")
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)
        changed = {"dance": ("SF", "CC"), "bpm": (29, 30)}
        self.assertEqual(_tag_change_summary(changed, translate=True),
                         "Tanz SF → CC, Takt 29 → 30")
        self.assertEqual(_tag_change_summary(changed), "dance SF → CC, takt 29 → 30")


if __name__ == "__main__":
    unittest.main(verbosity=2)
