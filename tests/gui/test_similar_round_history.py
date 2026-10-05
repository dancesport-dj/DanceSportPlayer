#!/usr/bin/env python3
"""📜 The Similar window narrowed to what past competitions played in this round.

Run:  .venv\\Scripts\\python.exe -m unittest tests.gui.test_similar_round_history -v

Marcel: a checkbox in the Similar-to window, so that with it on only titles
show that I played in this same round before — for a final, what else I
played in finals; for round 2, anything from any heat of past second rounds.
It is the 📜 Find planned before history, still ranked by similarity.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_simround_"))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

import gui.table_actions as table_actions  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from gui.similar_dialog import SimilarTracksDialog  # noqa: E402
from planner import library as planner_library  # noqa: E402
from planner.library import MusicLibrary  # noqa: E402
from planner.models import MusicEntry, RoundConfig  # noqa: E402
from planner.parsing import _song_title_key  # noqa: E402
from planner.suggester import PlaylistSuggester  # noqa: E402


def _tango(i: int, name: str | None = None) -> MusicEntry:
    name = name or f"Tango {i:03d}"
    return MusicEntry(path=Path(rf"C:\music\standardcd\{name} (TG 32).mp3"),
                      title=name, dance="TG", bpm=32)


_SOURCE = _tango(0, "The Source")
# 150 tangos, best match first — more than the window's usual top 100.
_POOL = [_tango(i) for i in range(1, 151)]
_POOL[11] = _tango(12, "Blue Moon")      # a title with a key: "Tango 012" has none


class _Lib:
    """similar_tracks as the library does it: the top n above min_display."""

    def similar_tracks(self, entry, n=10, same_dance=True, min_display=0.0,
                       method=None):
        scored = [(1.0 - i / 200, e) for i, e in enumerate(_POOL)]
        return [(s, e) for s, e in scored if s >= min_display][:n]


class DialogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self, history=None, **kw):
        self.calls = 0

        def cb():
            self.calls += 1
            return history
        lib = _Lib()
        dlg = SimilarTracksDialog(_SOURCE, lib.similar_tracks(_SOURCE, 100, min_display=0.5),
                                  lib=lib, round_history_cb=cb if history else None,
                                  round_name="Endrunde", **kw)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_no_checkbox_without_a_round(self):
        self.assertIsNone(self._dialog()._round_chk)

    def test_no_checkbox_in_history_mode(self):
        dlg = self._dialog(({"x"}, set()), history_title="📜  Planned before")
        self.assertIsNone(dlg._round_chk)

    def test_off_by_default_and_asks_for_nothing(self):
        dlg = self._dialog(({str(_POOL[3].path)}, set()))
        self.assertFalse(dlg._round_chk.isChecked())
        self.assertEqual(len(dlg._row_entries), 100)
        self.assertEqual(self.calls, 0, "the history is looked up on the first tick")

    def test_on_it_keeps_the_round_history_ranked_by_similarity(self):
        late = _POOL[140]                   # below 50 % and past the top 100
        dlg = self._dialog(({str(late.path), str(_POOL[7].path)}, set()))
        dlg._round_chk.setChecked(True)
        self.assertEqual(dlg._row_entries, [_POOL[7], late])
        self.assertIn("📜", dlg._head.text())
        dlg._round_chk.setChecked(False)
        dlg._round_chk.setChecked(True)
        self.assertEqual(self.calls, 1)

    def test_another_copy_of_the_song_counts(self):
        copy = r"D:\Turniere\2024\Blue Moon DJ Ice.mp3"
        dlg = self._dialog(({copy}, {_song_title_key(copy)}))
        dlg._round_chk.setChecked(True)
        self.assertEqual(dlg._row_entries, [_POOL[11]])

    def test_off_again_it_is_the_top_100(self):
        dlg = self._dialog(({str(_POOL[3].path)}, set()))
        dlg._round_chk.setChecked(True)
        dlg._round_chk.setChecked(False)
        self.assertEqual(len(dlg._row_entries), 100)


class _Win(QWidget):
    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "full"}


class _FakeDialog:
    """Stands in for SimilarTracksDialog and keeps what it was given."""
    kwargs = []

    def __init__(self, source, results, *a, **kw):
        _FakeDialog.kwargs.append(kw)

    def __getattr__(self, name):
        return lambda *a, **kw: None


class DeckTest(unittest.TestCase):
    """The deck hands the window its slot's round history."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        orig = planner_library.PLAYLIST_DIR
        self.dir = Path(tempfile.mkdtemp(prefix="dp_simround_lists_"))
        planner_library.PLAYLIST_DIR = self.dir
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.addCleanup(setattr, planner_library, "PLAYLIST_DIR", orig)
        self.played = _tango(1, "Played In A Final")
        (self.dir / "Turnier Hgr S STD.m3u").write_text(
            "#EXTM3U\n" + str(self.played.path) + "\n", encoding="utf-8")

        orig_dlg = table_actions.SimilarTracksDialog
        table_actions.SimilarTracksDialog = _FakeDialog
        self.addCleanup(setattr, table_actions, "SimilarTracksDialog", orig_dlg)
        _FakeDialog.kwargs = []

        self.lib = MusicLibrary()
        self.source = _tango(2, "On The Deck")
        self.source.features = [0.0]
        self.lib.entries += [self.played, self.source]
        self.lib.similar_tracks = lambda *a, **kw: [(0.9, self.played)]
        win = _Win()
        self.t = PlaylistTable()
        self.t.setParent(win)
        self.addCleanup(reap_widget, win)
        self.t.load({"Endrunde": [[self.source]]}, ["TG"],
                    [RoundConfig(name="Endrunde", heats=1, tier="final")],
                    "S", play_cb=None, suggester=PlaylistSuggester(self.lib),
                    use_timbre=False)

    def test_the_round_history_is_what_planned_before_finds(self):
        paths, keys = self.t._round_history_keys("TG", "Endrunde")
        self.assertEqual(paths, {str(self.played.path)})
        self.assertEqual(keys, {_song_title_key(str(self.played.path))})

    def test_a_slot_gives_the_window_its_round(self):
        self.t._show_similar(self.source, slot=("TG", "Endrunde"))
        kw = _FakeDialog.kwargs[0]
        self.assertEqual(kw["round_name"], "Endrunde")
        self.assertEqual(kw["round_history_cb"]()[0], {str(self.played.path)})

    def test_no_round_no_history(self):
        self.t._show_similar(self.source)
        self.assertIsNone(_FakeDialog.kwargs[0]["round_history_cb"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
