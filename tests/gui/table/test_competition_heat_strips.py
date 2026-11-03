#!/usr/bin/env python3
"""A competition training list is headed by its rounds, with the heats counted.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.table.test_competition_heat_strips -v

The warm-up rule cuts a fresh strip wherever a dance repeats, which made every
heat of a competition training list a round of its own.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_heatstrips_"))

from PySide6.QtWidgets import QApplication, QWidget

from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget

_DIR = Path(tempfile.mkdtemp(prefix="dp_heatstrips_m_"))
_DANCES = ["SA", "CC", "RB"]


def _entries(passes):
    out = []
    for p in range(passes):
        for d in _DANCES:
            path = _DIR / f"{d}{p}.mp3"
            path.write_bytes(b"x")
            out.append(MusicEntry(path=path, title=f"{d}{p}", dance=d, duration=150))
    return out


class _Win(QWidget):
    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "both"}


class CompetitionHeatStripsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def strips(self, heat_plan):
        win = _Win()
        t = PlaylistTable()
        t.setParent(win)
        t.resize(700, 400)
        self.addCleanup(reap_widget, win)
        t.load_warmup(_entries(4), "Competition Training Latin S", "Latin", "S",
                      True, play_cb=None, suggester=None, heat_plan=heat_plan)
        return [name for name, _songs in t._warmup_sections(t._row_meta.entries())], t

    def test_the_passes_are_grouped_into_rounds_and_a_final(self):
        names, t = self.strips([("Runde 1", 3, 9), ("Finale", 1, 3)])
        self.assertEqual(names, ["Runde 1", "Finale"])
        self.assertIn("3 heats", t._section_title("Runde 1", _entries(3)))
        self.assertIn("1 heat,", t._section_title("Finale", _entries(1)))

    def test_without_a_plan_every_pass_is_a_round(self):
        names, _t = self.strips(None)
        self.assertEqual(len(names), 4)

    def test_a_plan_that_no_longer_fits_the_list_falls_back(self):
        names, _t = self.strips([("Runde 1", 3, 9), ("Finale", 2, 6)])
        self.assertEqual(len(names), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
