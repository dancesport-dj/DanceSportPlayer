"""The Custom column: one free field per track, in the decks and the library.

Run:  py -m unittest tests.gui.test_custom_column -v

Marcel: invisible by default, but it can be ticked on to be shown in a
playlist. What it holds is typed in the 🏷 editor (kept in the app), or read
from the MP3 frame it is mapped to — set from the header's right-click menu,
e.g. Custom text (TXXX) with the description ultramixer_last_played. A new
mapping reads that frame of every listed track again, off the GUI thread.
"""
import os
import tempfile
import threading
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_custom_col_"))

from mutagen.id3 import ID3, TIT2, TXXX  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402

import planner.db as pdb  # noqa: E402
from dancesport_planner import (  # noqa: E402
    MusicEntry,
    MusicLibrary,
    PlaylistSuggester,
    RoundConfig,
)
from gui.library_browser import _LIB_COL_CUSTOM  # noqa: E402
from planner import custom_field, tag_edits  # noqa: E402
from shared.columns import _COL_CUSTOM, _COL_REGEN, _N_COLS  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)

_AUDIO = b"\xff\xfb\x90\x00" + b"\x00" * 4000


class _Cache:
    """What edit_tags, the scan cache and the window's repaint ask a cache for,
    keyed by path."""

    def __init__(self, fps: dict[str, str]):
        self.fps = fps

    def fingerprint(self, path):
        return self.fps.get(str(path))

    recorded_fingerprint = fingerprint

    def get_silences(self, *_a, **_kw):
        return None

    def lufs_count(self):
        return 0

    def save(self):
        pass


class ColumnsTest(unittest.TestCase):

    def test_custom_sits_in_front_of_regen(self):
        self.assertEqual((_COL_CUSTOM, _COL_REGEN, _N_COLS), (10, 11, 12))


class CustomColumnTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_custom_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_custom_col_db_"))
        saved = (pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
        pdb.AUDIO_DB_FILE = self.dir / "scratch.db"
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False

        def restore():
            try:
                pdb._DB_LOCAL.conn.close()
            except Exception:
                pass
            pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED = saved
        self.addCleanup(restore)

        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)

        self.cha = self._entry("Cha One (CC 30)", "CC", "-1", custom="-1")
        self.rum = self._entry("Rum One (RB 25)", "RB", "7")
        lib = MusicLibrary()
        lib.entries.extend([self.cha, self.rum])
        self.win._lib = lib
        self.win._cache = _Cache({str(self.cha.path): "fpCha",
                                  str(self.rum.path): "fpRum"})
        # Deck C holds an outside copy of the same file, as a restored M3U would.
        self.copy = MusicEntry(path=self.cha.path, title=self.cha.title,
                               dance="CC", bpm=30, custom="-1")
        self._load(self.win._tableB, self.cha)
        self._load(self.win._tableC, self.copy)
        self.asked = []
        self.win._ask_write_to_mp3 = lambda n, fields: self.asked.append(fields) or False

    def _entry(self, name, dance, played, **kw) -> MusicEntry:
        path = self.dir / f"{name}.mp3"
        path.write_bytes(_AUDIO)
        tags = ID3()
        tags.add(TIT2(encoding=1, text=name))
        tags.add(TXXX(encoding=1, desc="ultramixer_last_played", text=played))
        tags.add(TXXX(encoding=1, desc="ultramixer_meter", text=f"meter {name}"))
        tags.save(path, v2_version=3)
        return MusicEntry(path=path, title=name, dance=dance, bpm=30, **kw)

    def _load(self, table, entry):
        table.load({"Runde 1": [[entry, self.rum]]}, ["CC", "RB"],
                   [RoundConfig(name="Runde 1", heats=1, tier="final")], "S",
                   play_cb=self.win._play_or_stop,
                   suggester=PlaylistSuggester(self.win._lib),
                   use_timbre=False, style="Latin", dynamic=True, capacity=[1])

    def _cell(self, table, entry) -> str:
        for r, m in table._row_meta.numbered():
            if m.entry is entry:
                return table.item(r, _COL_CUSTOM).text()
        self.fail(f"no row for {entry.title}")

    def _lib_cell(self, entry) -> str:
        t = self.win._lib_browser._table
        for r in range(t.rowCount()):
            if str(t.item(r, 0).data(Qt.ItemDataRole.UserRole)) == str(entry.path):
                return t.item(r, _LIB_COL_CUSTOM).text()
        self.fail(f"no library row for {entry.title}")

    class _Answer:
        """A TagEditDialog after Save, without opening one."""

        def __init__(self, changes):
            self._changes = changes
            self.reset_requested = False

        def changes_for(self, entry):
            return dict(self._changes)

        def raw_edits(self):
            return None

        def form_changes(self):
            return {}

        def form_mp3s(self):
            return []

    # ----- the column ---------------------------------------------------------

    def test_a_deck_starts_with_it_put_away(self):
        self.assertTrue(self.win._tableB.isColumnHidden(_COL_CUSTOM))
        self.assertEqual(self.win._tableB.horizontalHeaderItem(_COL_CUSTOM).text(), "Custom")

    def test_a_deck_row_shows_the_value(self):
        self.assertEqual(self._cell(self.win._tableB, self.cha), "-1")
        self.assertEqual(self._cell(self.win._tableB, self.rum), "")

    def test_the_library_starts_with_it_put_away(self):
        self.assertIn(_LIB_COL_CUSTOM, self.win._lib_browser.hidden_columns())

    def test_the_library_shows_the_value(self):
        self.win._lib_browser.set_entries(self.win._lib.entries)
        self.assertEqual(self._lib_cell(self.cha), "-1")

    def test_the_header_menu_offers_the_mapping(self):
        menu = self.win._tableB.build_column_menu()
        texts = [a.text() for a in menu.actions()]
        self.assertIn("Map Custom to an MP3 tag…", texts)
        self.assertIn("Custom", texts)

    def test_the_library_header_menu_offers_the_mapping(self):
        menu = self.win._lib_browser.build_column_menu()
        self.assertIn("Map Custom to an MP3 tag…", [a.text() for a in menu.actions()])

    def test_it_sorts_by_the_value(self):
        key = self.win._tableB._FLAT_SORT_KEYS[_COL_CUSTOM]
        self.assertLess(key(self.rum), key(self.cha))

    # ----- the 🏷 editor -------------------------------------------------------

    def test_what_is_typed_reaches_every_row(self):
        self.win._lib_browser.set_entries(self.win._lib.entries)
        self.win._apply_tag_dialog([self.cha], self._Answer({"custom": "Gala"}))
        self.assertEqual(tag_edits.load("fpCha"), {"custom": "Gala"})
        self.assertEqual(self._cell(self.win._tableB, self.cha), "Gala")
        self.assertEqual(self._cell(self.win._tableC, self.copy), "Gala")
        self.assertEqual(self._lib_cell(self.cha), "Gala")

    def test_without_a_mapping_it_is_not_offered_for_the_mp3(self):
        self.win._apply_tag_dialog([self.cha], self._Answer({"custom": "Gala"}))
        self.assertEqual(self.asked, [])

    def test_with_a_mapping_the_mp3_question_names_it(self):
        custom_field.set_source("TXXX", "ultramixer_last_played")
        self.win._apply_tag_dialog([self.cha], self._Answer({"custom": "Gala", "rating": 3}))
        self.assertEqual(self.asked, [["stars", "custom"]])

    def test_without_a_mapping_only_the_others_go_into_the_mp3(self):
        writes = []
        self.win._write_into_mp3 = lambda e, write, what: writes.append(what) or []
        self.win._ask_write_to_mp3 = lambda n, fields: True
        self.win._apply_tag_dialog([self.cha], self._Answer({"custom": "Gala", "rating": 3}))
        self.assertEqual(len(writes), 1)
        self.assertNotIn("custom", writes[0])

    # ----- mapping it ---------------------------------------------------------

    def _map(self, frame, desc=""):
        import time
        self.win._ask_custom_source = lambda: (frame, desc)
        self.win._map_custom_field()
        self.assertIsNotNone(self.win._custom_reader)
        end = time.monotonic() + 5
        while self.win._custom_reader is not None and time.monotonic() < end:
            self.app.processEvents()
            time.sleep(0.01)
        self.assertIsNone(self.win._custom_reader, "the reader never reported back")

    def test_a_new_mapping_reads_the_frame_into_every_row(self):
        self.win._lib_browser.set_entries(self.win._lib.entries)
        self._map("TXXX", "ultramixer_meter")
        self.assertEqual(custom_field.source(), ("TXXX", "ultramixer_meter"))
        self.assertEqual(self._cell(self.win._tableB, self.cha), "meter Cha One (CC 30)")
        self.assertEqual(self._cell(self.win._tableC, self.copy), "meter Cha One (CC 30)")
        self.assertEqual(self._cell(self.win._tableB, self.rum), "meter Rum One (RB 25)")
        self.assertEqual(self._lib_cell(self.rum), "meter Rum One (RB 25)")

    def test_app_only_empties_what_came_from_the_files(self):
        custom_field.set_source("TXXX", "ultramixer_last_played")
        self._map(None)
        self.assertIsNone(custom_field.source())
        self.assertEqual(self._cell(self.win._tableB, self.cha), "")

    def test_the_tag_editor_maps_it_from_a_row(self):
        import time
        self.assertTrue(self.win._set_custom_source("TXXX", "ultramixer_meter"))
        end = time.monotonic() + 5
        while self.win._custom_reader is not None and time.monotonic() < end:
            self.app.processEvents()
            time.sleep(0.01)
        self.assertEqual(custom_field.source(), ("TXXX", "ultramixer_meter"))
        self.assertEqual(self._cell(self.win._tableB, self.rum), "meter Rum One (RB 25)")

    def test_while_a_reading_runs_the_tag_editor_is_told_no(self):
        self.win._custom_reader = object()
        self.addCleanup(setattr, self.win, "_custom_reader", None)
        self.assertFalse(self.win._set_custom_source("TXXX", "ultramixer_meter"))
        self.assertIsNone(custom_field.source())

    def test_the_dialog_is_shown_what_the_library_mp3s_hold(self):
        from unittest import mock
        from gui import main_music
        seen = {}

        class _Dlg:
            def __init__(self, current, parent, samples):
                seen["samples"] = samples

            def exec(self):
                return 0
        with mock.patch.object(main_music, "CustomSourceDialog", _Dlg):
            self.assertIsNone(self.win._ask_custom_source())
        read, found = seen["samples"]
        self.assertEqual(read, 2)
        self.assertEqual(found[("TXXX", "ultramixer_meter")][0], 2)

    def test_a_cancelled_dialog_changes_nothing(self):
        custom_field.set_source("TXXX", "ultramixer_last_played")
        self.win._ask_custom_source = lambda: None
        self.win._map_custom_field()
        self.assertEqual(custom_field.source(), ("TXXX", "ultramixer_last_played"))
        self.assertIsNone(self.win._custom_reader)


if __name__ == "__main__":
    unittest.main(verbosity=2)
