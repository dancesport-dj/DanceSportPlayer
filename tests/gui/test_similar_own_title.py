#!/usr/bin/env python3
"""The Similar-tracks window never lists the title it was opened for.

Run:  py -m unittest tests.gui.test_similar_own_title -v

Marcel: "especially his own music as 100% thats everytime wrong, filter my
own title in the view". The rankings leave the anchor out by identity only,
so the library's own entry for a playlist row's file (another object) came
back at 100 %, and other copies of the same song near it. The window now
drops the source's file and every copy of its song, whatever the method.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_sim_own_"))

from PySide6.QtWidgets import QApplication  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from gui.similar_dialog import SimilarTracksDialog  # noqa: E402
from planner.models import MusicEntry  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)


def _entry(name: str, folder: str = "standardcd") -> MusicEntry:
    return MusicEntry(path=Path(rf"C:\music\tanzcds\{folder}\{name}.mp3"),
                      title=name, dance="LW", bpm=29)


_SOURCE = _entry("Moon River (LW 29)")
_RESULTS = [(1.0, _entry("Moon River (LW 29)")),            # the library's own entry
            (0.97, _entry("Moon River DJ Ice", "other")),   # another copy
            (0.8, _entry("Alpha (LW 29)"))]


class SimilarOwnTitleTest(unittest.TestCase):

    def _open(self, **kw):
        dlg = SimilarTracksDialog(_SOURCE, list(_RESULTS), **kw)
        self.addCleanup(reap_widget, dlg)
        return [e.title for e in dlg._row_entries]

    def test_its_own_title_is_not_listed(self):
        self.assertEqual(self._open(), ["Alpha (LW 29)"])

    def test_the_history_list_keeps_it(self):
        # 'Planned before' lists past picks for the slot, the current one too.
        shown = self._open(history_title="Planned before")
        self.assertEqual(len(shown), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
