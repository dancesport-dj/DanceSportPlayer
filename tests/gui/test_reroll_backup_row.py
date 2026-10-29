#!/usr/bin/env python3
"""↺ on a '↳ backup N' row re-rolls that backup, never the slot above it.

Run:  .venv\\Scripts\\python.exe -m unittest tests.gui.test_reroll_backup_row -v

Found by the multi-model review 2026-10-22 (G8+G9): a backup row's Row is a
spare() copy of its slot's, so it carries the slot's round, heat and dance
column. The per-song, per-dance and per-round ↺ all wrote their pick to
`_playlist[round][heat][dance]` from that meta: re-rolling a backup replaced
the primary title in the plan, while the backup in the overlay stayed as it
was, and the next redraw showed the old backup under a title nobody picked.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_rerollbackup_"))

from PySide6.QtWidgets import QApplication, QWidget

from gui.table.playlist_table import PlaylistTable
from planner.generate.suggester import PlaylistSuggester
from planner.models import MusicEntry, RoundConfig
from planner.music.library import MusicLibrary
from tests.qt_test_support import reap_widget

_MUSIC = Path(tempfile.mkdtemp(prefix="dp_rerollbackup_music_")) / "StandardCD"
_MUSIC.mkdir()


def _waltz(name: str) -> MusicEntry:
    path = _MUSIC / f"{name} (LW 29).mp3"
    path.write_bytes(b"ID3")
    return MusicEntry(path=path, title=name, dance="LW", bpm=29, popularity=3)


class _Win(QWidget):
    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "full"}


class RerollBackupRowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.slot, self.spare = _waltz("Slot"), _waltz("Spare")
        self.others = [_waltz(f"Other {i}") for i in range(6)]
        lib = MusicLibrary()
        lib.entries += [self.slot, self.spare, *self.others]
        win = _Win()
        self.t = PlaylistTable()
        self.t.setParent(win)
        self.addCleanup(reap_widget, win)
        box = mock.patch("gui.table.table_regen.QMessageBox")
        box.start()
        self.addCleanup(box.stop)
        self.t.load({"Endrunde": [[self.slot]]}, ["LW"],
                    [RoundConfig(name="Endrunde", heats=1, tier="final")],
                    "A", play_cb=None, suggester=PlaylistSuggester(lib),
                    use_timbre=False, style="Standard", dynamic=True, capacity=[6],
                    backups={("Endrunde", 0, 0): [self.spare]})

    def rows(self):
        primary = next(r for r, m in enumerate(self.t._row_meta)
                       if m and m.entry and not m.backup)
        backup = next(r for r, m in enumerate(self.t._row_meta)
                      if m and m.backup)
        return primary, backup

    def assert_plan_matches_rows(self):
        primary, backup = self.rows()
        self.assertIs(self.t._playlist["Endrunde"][0][0],
                      self.t._row_meta[primary].entry)
        self.assertEqual(self.t._dynamic_backups[("Endrunde", 0, 0)],
                         [self.t._row_meta[backup].entry])

    def test_reroll_of_a_backup_keeps_the_slot(self):
        _, backup = self.rows()
        self.t._regen(backup)
        QApplication.processEvents()
        self.assertIs(self.t._playlist["Endrunde"][0][0], self.slot)
        new = self.t._dynamic_backups[("Endrunde", 0, 0)]
        self.assertEqual(len(new), 1)
        self.assertIsNot(new[0], self.spare)
        self.assert_plan_matches_rows()

    def test_dance_reroll_keeps_slot_and_backup_apart(self):
        self.t._regen_dance("Endrunde", 0, "LW")
        QApplication.processEvents()
        self.assert_plan_matches_rows()

    def test_round_reroll_keeps_slot_and_backup_apart(self):
        self.t._regen_round("Endrunde")
        QApplication.processEvents()
        self.assert_plan_matches_rows()

    def test_a_drop_on_a_backup_replaces_the_backup(self):
        """G10: the same copied coordinates on the drop path — a file dropped
        on a backup row of a static deck replaced the primary title."""
        self.t._dynamic = False
        _, backup = self.rows()
        self.assertTrue(self.t._replace_row_with_path(backup, self.others[0].path))
        QApplication.processEvents()
        self.assertIs(self.t._playlist["Endrunde"][0][0], self.slot)
        self.assertEqual(self.t._dynamic_backups[("Endrunde", 0, 0)],
                         [self.others[0]])
        self.assert_plan_matches_rows()


if __name__ == "__main__":
    unittest.main(verbosity=2)
