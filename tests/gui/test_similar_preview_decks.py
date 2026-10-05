#!/usr/bin/env python3
"""Tests that a Similar-Tracks preview takes the decks' ■ away.

Run:  py -m unittest tests.gui.test_similar_preview_decks -v

Marcel: "ich starte einen titel dann schau ich nach ähnlichen und starte da
einen zum vorhören — dann ist in der playlist der button falsch". The window
plays through the decks' shared player, but the deck row that was running
kept its ■ (and its running row) while the preview played, so the row lied and
its button paused the preview instead of starting its own title. It has to go
back to ▶, exactly as when another deck or the library pane starts a title.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_sim_decks_"))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from gui.main_decks import DeckLayoutMixin  # noqa: E402
from gui.similar_dialog import SimilarTracksDialog  # noqa: E402
from planner.models import MusicEntry  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)


def _entry(title: str) -> MusicEntry:
    return MusicEntry(path=Path(rf"C:\music\tanzcds\standardcd\{title} (LW 29).mp3"),
                      title=title, dance="LW", bpm=29)


_SOURCE = _entry("source")
_RESULTS = [(0.9, _entry("alpha")), (0.8, _entry("beta"))]


class _Main(QWidget):
    """The main window as far as a preview window reaches: the shared player,
    the decks and the library pane whose ▶/■ it has to take over."""

    release_play_markers = DeckLayoutMixin.release_play_markers
    _reset_aux_play_markers = DeckLayoutMixin._reset_aux_play_markers

    def __init__(self):
        super().__init__()
        self.events: list = []
        self.deck = mock.Mock()
        self.deck.on_playback_stopped.side_effect = (
            lambda: self.events.append("deck ▶"))
        self._all_tables = [self.deck]
        self._lib_browser = mock.Mock()
        self.now = None

    def _play_or_stop(self, path):
        self.events.append(path)
        self.now = path

    def deck_path(self):
        return self.now


class SimilarPreviewDecksTest(unittest.TestCase):

    def setUp(self):
        self.main = _Main()
        self.addCleanup(reap_widget, self.main)
        self.dlg = SimilarTracksDialog(_SOURCE, _RESULTS, self.main,
                                       play_cb=self.main._play_or_stop)
        self.addCleanup(reap_widget, self.dlg)

    def test_a_row_preview_gives_the_deck_its_play_button_back(self):
        self.dlg._toggle_play(0)
        self.assertEqual(self.main.events, ["deck ▶", _RESULTS[0][1].path])
        self.main._lib_browser.on_playback_stopped.assert_called()

    def test_the_base_preview_gives_the_deck_its_play_button_back(self):
        self.dlg._toggle_play_base()
        self.assertEqual(self.main.events, ["deck ▶", _SOURCE.path])

    def test_stopping_the_preview_leaves_the_decks_alone(self):
        self.dlg._toggle_play(1)
        self.main.events.clear()
        self.dlg._toggle_play(1)             # ■ on its own row
        self.assertEqual(self.main.events, [None])


if __name__ == "__main__":
    unittest.main(verbosity=2)
