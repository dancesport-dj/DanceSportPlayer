#!/usr/bin/env python3
"""Tests that the Similar-Tracks window only ever stops its OWN preview.

Run:  py -m unittest tests.gui.test_similar_preview_stop -v

The window previews through the same player as the decks. It used to
remember only "I started something", so once the operator had started a deck
title the window's close, a new search, a pick or its ■ button stopped the live
music. It must stop the player only while the player is still on the title the
window itself started.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_sim_stop_"))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from gui.similar_dialog import SimilarTracksDialog  # noqa: E402
from planner.models import MusicEntry  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)


def _entry(title: str) -> MusicEntry:
    return MusicEntry(path=Path(rf"C:\music\tanzcds\standardcd\{title} (LW 29).mp3"),
                      title=title, dance="LW", bpm=29)


_SOURCE = _entry("source")
_RESULTS = [(0.9, _entry("alpha")), (0.8, _entry("beta"))]
_DECK_TITLE = Path(r"C:\music\tanzcds\standardcd\live on the deck (LW 29).mp3")


class _Host(QWidget):
    """The main window as far as the dialog sees it: one player, whose play
    callback it shares, and `deck_path()` naming what that player is on."""

    def __init__(self):
        super().__init__()
        self.now: Path | None = None
        self.calls: list = []

    def play(self, path):
        self.calls.append(path)
        self.now = path

    def deck_path(self):
        return self.now


class SimilarPreviewStopTest(unittest.TestCase):

    def setUp(self):
        self.host = _Host()
        self.addCleanup(reap_widget, self.host)
        self.picked = []
        self.dlg = SimilarTracksDialog(_SOURCE, _RESULTS, self.host,
                                       play_cb=self.host.play,
                                       pick_cb=self.picked.append)
        self.addCleanup(reap_widget, self.dlg)

    def _preview_then_deck_takes_over(self):
        self.dlg._toggle_play(0)
        self.assertEqual(self.host.now, _RESULTS[0][1].path)
        self.host.now = _DECK_TITLE          # the operator starts a deck title
        self.host.calls.clear()

    def test_closing_leaves_the_deck_playing(self):
        self._preview_then_deck_takes_over()
        self.dlg.close()
        self.assertEqual(self.host.calls, [])

    def test_the_rows_stop_button_leaves_the_deck_playing(self):
        self._preview_then_deck_takes_over()
        self.dlg._toggle_play(0)             # ■ on the row it had started
        self.assertEqual(self.host.calls, [])
        self.assertEqual(self.dlg._cur_row, -1)

    def test_a_new_search_leaves_the_deck_playing(self):
        self._preview_then_deck_takes_over()
        self.dlg._populate(_SOURCE, _RESULTS)
        self.assertEqual(self.host.calls, [])

    def test_picking_leaves_the_deck_playing(self):
        self._preview_then_deck_takes_over()
        self.dlg._pick_row(1)
        self.assertEqual(self.host.calls, [])
        self.assertEqual(len(self.picked), 1)

    def test_the_base_preview_leaves_the_deck_playing(self):
        self.dlg._toggle_play_base()
        self.assertEqual(self.host.now, _SOURCE.path)
        self.host.now = _DECK_TITLE
        self.host.calls.clear()
        self.dlg.close()
        self.assertEqual(self.host.calls, [])

    def test_its_own_preview_is_still_stopped_on_close(self):
        self.dlg._toggle_play(0)
        self.host.calls.clear()
        self.dlg.close()
        self.assertEqual(self.host.calls, [None])

    def test_its_own_preview_is_still_stopped_by_the_row_button(self):
        self.dlg._toggle_play(1)
        self.host.calls.clear()
        self.dlg._toggle_play(1)
        self.assertEqual(self.host.calls, [None])


if __name__ == "__main__":
    unittest.main(verbosity=2)
