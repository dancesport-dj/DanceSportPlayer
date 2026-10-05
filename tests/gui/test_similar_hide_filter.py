#!/usr/bin/env python3
"""Titles the replacement picker hides stay hidden however the window ranks.

Run:  py -m unittest tests.gui.test_similar_hide_filter -v

Marcel: "similiar dialog still shows me title that are open in another
playlist". 🔁 Check duplicates filtered the list it handed the Similar-tracks
window (866e919), but the window ranks anew as it opens — "combined" is its
default — and again on every method switch, so the filter was gone before
the list was ever seen. The window now applies the caller's filter itself.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_sim_hide_"))

from PySide6.QtWidgets import QApplication  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from gui.similar_dialog import SimilarTracksDialog  # noqa: E402
from planner.models import MusicEntry  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)


def _entry(title: str) -> MusicEntry:
    return MusicEntry(path=Path(rf"C:\music\tanzcds\standardcd\{title} (LW 29).mp3"),
                      title=title, dance="LW", bpm=29)


_SOURCE = _entry("source")
_RANKED = [(0.9, _entry("gamma")), (0.8, _entry("zeta"))]


def _hide_gamma(results):
    return [r for r in results if r[1].title != "gamma"]


class SimilarHideFilterTest(unittest.TestCase):

    def _open(self, hide_fn):
        lib = mock.Mock()
        lib.similar_tracks.return_value = list(_RANKED)
        with mock.patch.object(SimilarTracksDialog, "_sound_alike",
                               lambda _self: lambda *a, **k: list(_RANKED)):
            dlg = SimilarTracksDialog(_SOURCE, [(0.8, _entry("zeta"))], lib=lib,
                                      cache=mock.Mock(), hide_fn=hide_fn)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def _shown(self, dlg):
        return [e.title for e in dlg._row_entries]

    def test_the_default_ranking_keeps_them_hidden(self):
        dlg = self._open(_hide_gamma)
        self.assertEqual(dlg._method_combo.currentData(), "combined")
        self.assertEqual(self._shown(dlg), ["zeta"])

    def test_another_method_keeps_them_hidden(self):
        dlg = self._open(_hide_gamma)
        combo = dlg._method_combo
        combo.setCurrentIndex(combo.findData("gaussian_kl"))
        self.assertEqual(self._shown(dlg), ["zeta"])

    def test_without_a_filter_the_window_shows_everything(self):
        dlg = self._open(None)
        self.assertEqual(self._shown(dlg), ["gamma", "zeta"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
