#!/usr/bin/env python3
"""✖ Remove heat moves the heat's titles up into empty slots of their dance.

Run:  .venv\\Scripts\\python.exe -m unittest tests.gui.test_remove_heat_moves_titles_up -v

Marcel's "Jug A STD" Vorrunde had grown to 5 heats: the Slowfox slots of heats
1-2 were empty and the two Slowfox titles sat in heats 3-4. He removed heats
5, 4 and 3 to get back to 2, and both Slowfox titles were gone — the heats
went with everything in them although heats 1-2 had room for them.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_heatup_"))

from PySide6.QtWidgets import QApplication  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.models import MusicEntry, RoundConfig  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)


def _e(dance: str, n: int) -> MusicEntry:
    return MusicEntry(path=Path(rf"C:\music\{dance}{n}.mp3"),
                      title=f"{dance} {n}", dance=dance, bpm=None)


class RemoveHeatMovesTitlesUpTest(unittest.TestCase):

    def setUp(self):
        self.t = PlaylistTable()
        self.addCleanup(reap_widget, self.t)
        self.t._confirm_delete = lambda *_a: True

    def _load(self, heats):
        self.t.load({"Vorrunde": heats}, ["LW", "SF"],
                    [RoundConfig(name="Vorrunde", heats=len(heats), tier="semi")],
                    "A", play_cb=lambda *a: None, suggester=None,
                    use_timbre=False, dynamic=True, capacity=[6])

    def _row_of_heat(self, h_idx: int) -> int:
        for r in range(self.t.rowCount()):     # an all-empty heat has no track
            m = self.t._row_meta.at(r)
            if m and not m.backup and m.round_name == "Vorrunde" and m.h_idx == h_idx:
                return r
        raise AssertionError(f"no row for heat {h_idx}")

    def _grid(self):
        return [[e.title if e else None for e in h]
                for h in self.t._playlist["Vorrunde"]]

    def test_the_marcel_case_keeps_both_slowfox_titles(self):
        self._load([[_e("LW", 1), None], [_e("LW", 2), None],
                    [None, _e("SF", 1)], [None, _e("SF", 2)], [None, None]])
        for h in (4, 3, 2):
            self.t._remove_dynamic_heat(self._row_of_heat(h))
        grid = self._grid()
        self.assertEqual([h[0] for h in grid], ["LW 1", "LW 2"])
        self.assertCountEqual([h[1] for h in grid], ["SF 1", "SF 2"])

    def test_a_title_takes_the_first_empty_slot_of_its_dance(self):
        self._load([[_e("LW", 1), _e("SF", 1)], [_e("LW", 2), None],
                    [_e("LW", 3), _e("SF", 3)]])
        self.t._remove_dynamic_heat(self._row_of_heat(2))
        self.assertEqual(self._grid(), [["LW 1", "SF 1"], ["LW 2", "SF 3"]])

    def test_a_title_with_no_room_leaves_with_its_heat(self):
        self._load([[_e("LW", 1), _e("SF", 1)], [_e("LW", 2), _e("SF", 2)]])
        self.t._remove_dynamic_heat(self._row_of_heat(1))
        self.assertEqual(self._grid(), [["LW 1", "SF 1"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
