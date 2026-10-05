#!/usr/bin/env python3
"""A final-round backup row draws — and a deck holding one restores.

Run:  .venv\\Scripts\\python.exe -m unittest tests.gui.test_backup_row_render -v

Marcel switched the 📅 "Jug A STD" day deck to dynamic, which stacked backup
titles under its final slots, and restarted: the playlists were gone. Drawing
a backup row still called `meta.get('backup_n')` from when rows were dicts,
so `load()` raised, the restore stopped after that deck, and the autosave
lost every deck and wishlist behind it.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_backuprow_"))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.library import MusicLibrary  # noqa: E402
from planner.models import MusicEntry, RoundConfig  # noqa: E402
from planner.suggester import PlaylistSuggester  # noqa: E402
from shared.columns import _COL_HEAT  # noqa: E402


def _waltz(name: str) -> MusicEntry:
    return MusicEntry(path=Path(rf"C:\music\standardcd\{name} (LW 29).mp3"),
                      title=name, dance="LW", bpm=29)


class _Win(QWidget):
    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "full"}


class BackupRowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_a_final_with_backups_loads_and_numbers_them(self):
        slot, spare1, spare2 = _waltz("Slot"), _waltz("Spare One"), _waltz("Spare Two")
        lib = MusicLibrary()
        lib.entries += [slot, spare1, spare2]
        win = _Win()
        t = PlaylistTable()
        t.setParent(win)
        self.addCleanup(reap_widget, win)

        t.load({"Endrunde": [[slot]]}, ["LW"],
               [RoundConfig(name="Endrunde", heats=1, tier="final")],
               "A", play_cb=None, suggester=PlaylistSuggester(lib),
               use_timbre=False, dynamic=True, capacity=[6],
               backups={("Endrunde", 0, 0): [spare1, spare2]})

        heats = [t.item(r, _COL_HEAT).text() for r in range(t.rowCount())
                 if t.item(r, _COL_HEAT) is not None]
        self.assertIn("↳ backup 1", heats)
        self.assertIn("↳ backup 2", heats)


if __name__ == "__main__":
    unittest.main(verbosity=2)
