#!/usr/bin/env python3
"""📌 Pinned titles stay put when their round or dance is re-rolled.

Run:  py -m unittest tests.gui.test_pin_slot -v

↻ on a round header re-rolled every slot of the round, and ↺ on a dance header
every heat of the dance, so a title the operator had settled on went with the
rest. A pinned title now sits out those re-rolls; the ↺ of its own row says
it is pinned instead of replacing it. The pin is drawn like the orange 🔁
mark, only lila, and rides along in the deck snapshot (autosave + undo).
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pin_"))

from dancesport_planner import (
    MusicEntry,
    MusicLibrary,
    PlaylistSuggester,
    RoundConfig,
)
from tests.qt_test_support import reap_widget, stub_window_startup


# Real files: a missing one is painted red, and red outranks the lila pin.
_MUSIC = Path(tempfile.mkdtemp(prefix="dp_pin_music_"))


def _entry(name: str, dance: str) -> MusicEntry:
    path = _MUSIC / dance / f"{name}.mp3"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(b"ID3")
    return MusicEntry(path=path, title=name, dance=dance, bpm=None, popularity=3)


class PinSlotTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        cls._settings_dir = tempfile.mkdtemp(prefix="dp_pin_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._settings_dir)
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)

        self.cha1, self.cha2 = _entry("Cha One (CC 30)", "CC"), _entry("Cha Two (CC 30)", "CC")
        self.rum1, self.rum2 = _entry("Rum One (RB 25)", "RB"), _entry("Rum Two (RB 25)", "RB")
        self.fresh = {"CC": _entry("Cha New (CC 30)", "CC"),
                      "RB": _entry("Rum New (RB 25)", "RB")}
        lib = MusicLibrary()
        lib.entries.extend([self.cha1, self.cha2, self.rum1, self.rum2, *self.fresh.values()])
        self.win._library.lib = lib

        self.table = self.win._deckset.tableB
        self.table.load(
            {"Finale": [[self.cha1, self.rum1], [self.cha2, self.rum2]]},
            ["CC", "RB"],
            [RoundConfig(name="Finale", heats=2, tier="final")],
            "S",
            play_cb=self.win._play_or_stop,
            suggester=PlaylistSuggester(lib),
            use_timbre=False, style="Latin",
        )
        # Every re-roll hands back the dance's "new" title: whatever still shows
        # an old one afterwards was not re-rolled.
        self.rolled = []

        def regenerate(dance, *a, **kw):
            self.rolled.append(dance)
            return self.fresh[dance]
        self.table._suggester.regenerate = regenerate

    def row_of(self, entry) -> int:
        for r, m in enumerate(self.table._row_meta):
            if m and m.entry is entry:
                return r
        self.fail(f"no row for {entry.title}")

    def settle(self):
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

    def titles(self):
        return [m.entry.title for m in self.table._row_meta if m and m.entry is not None]

    # ----- the re-rolls ---------------------------------------------------------

    def test_a_round_reroll_keeps_the_pinned_title(self):
        self.table._toggle_pin({self.row_of(self.cha1)})
        self.table._regen_round("Finale")
        self.settle()
        self.assertEqual(self.table._playlist["Finale"][0][0], self.cha1)
        self.assertEqual(sorted(self.rolled), ["CC", "RB", "RB"])

    def test_a_dance_reroll_keeps_the_pinned_title(self):
        self.table._toggle_pin({self.row_of(self.rum2)})
        self.table._regen_dance("Finale", 1, "RB")
        self.settle()
        self.assertEqual(self.table._playlist["Finale"][1][1], self.rum2)
        self.assertEqual(self.table._playlist["Finale"][0][1], self.fresh["RB"])
        self.assertEqual(self.rolled, ["RB"])

    def test_the_rows_own_reroll_leaves_a_pinned_title_alone(self):
        row = self.row_of(self.cha2)
        self.table._toggle_pin({row})
        with mock.patch("gui.playlist_table._show_toast") as toast:
            self.table._regen(row)
        self.settle()
        self.assertEqual(self.rolled, [])
        self.assertEqual(self.table._playlist["Finale"][1][0], self.cha2)
        toast.assert_called_once()

    def test_unpinned_the_round_reroll_takes_everything(self):
        row = self.row_of(self.cha1)
        self.table._toggle_pin({row})
        self.table._toggle_pin({row})
        self.table._regen_round("Finale")
        self.settle()
        self.assertEqual(len(self.rolled), 4)

    # ----- the look -------------------------------------------------------------

    def test_a_pinned_row_is_lila(self):
        from gui.playlist_table import _C_PIN_BG, _C_PIN_FG
        from shared.columns import _COL_TITLE
        row = self.row_of(self.rum1)
        self.table._toggle_pin({row})
        title = self.table.item(row, _COL_TITLE)
        self.assertEqual(title.background().color(), _C_PIN_BG)
        self.assertEqual(title.foreground().color(), _C_PIN_FG)
        self.assertTrue(self.table._is_row_pinned(row))

    def test_a_pinned_title_shows_the_pin(self):
        from shared.columns import _COL_TITLE
        row = self.row_of(self.rum1)
        self.table._toggle_pin({row})
        self.assertTrue(self.table.item(row, _COL_TITLE).text().startswith("📌"))
        self.table._toggle_pin({row})
        self.assertEqual(self.table.item(row, _COL_TITLE).text(), self.rum1.title)

    # ----- snapshot ---------------------------------------------------------------

    def test_pins_ride_along_in_the_snapshot_and_come_back(self):
        self.table._toggle_pin({self.row_of(self.rum1)})
        state = self.win._serialize_playlist_state(self.table)
        self.assertEqual(state["pinned"], [str(self.rum1.path)])

        self.win._blank_deck(self.table)
        self.assertEqual(self.table._pinned_paths, set())
        self.win._restore_into_deck(self.table, state)
        self.assertEqual(self.table._pinned_paths, {str(self.rum1.path)})

    def test_an_unpinned_deck_writes_no_pinned_key(self):
        self.assertNotIn("pinned", self.win._serialize_playlist_state(self.table))


if __name__ == "__main__":
    unittest.main(verbosity=2)
