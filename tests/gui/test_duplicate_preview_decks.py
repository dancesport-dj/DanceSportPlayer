#!/usr/bin/env python3
"""Tests that a Check-duplicates preview and the decks agree on who plays.

Run:  py -m unittest tests.gui.test_duplicate_preview_decks -v

The dialog previews through the decks' shared player. Since it stays open
beside the decks on its drag-in tabs (1ee3fdd), both ways round matter:
a preview has to take the running deck row's ■ away, as the Similar-tracks
window does (d43e186), and the dialog must not stop a title the operator
started on a deck since — not with its ■, and not when it closes.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_dup_preview_"))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from gui.duplicate_dialog import DuplicateResolveDialog  # noqa: E402
from gui.main_decks import DeckLayoutMixin  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)

_PREVIEW = r"C:\music\tanzcds\standardcd\alpha (LW 29).mp3"
_DECK_TITLE = Path(r"C:\music\tanzcds\standardcd\deck (LW 29).mp3")


class _Main(QWidget):
    """The main window as far as the dialog's preview reaches: the shared
    player, the decks and the panes whose ▶/■ it has to take over."""

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


class DuplicatePreviewDecksTest(unittest.TestCase):

    def setUp(self):
        self.main = _Main()
        self.addCleanup(reap_widget, self.main)
        self.dlg = DuplicateResolveDialog({"within": [], "cross": []}, self.main,
                                          pick_fn=lambda e: None,
                                          play_cb=self.main._play_or_stop)
        self.addCleanup(reap_widget, self.dlg)
        self.btn = self.dlg._make_play_btn(_PREVIEW)

    def _preview(self):
        self.dlg._toggle_play(_PREVIEW, self.btn)

    def _deck_starts_a_title(self):
        self.main.now = _DECK_TITLE
        self.main.events.clear()

    def test_a_preview_gives_the_deck_its_play_button_back(self):
        self._preview()
        self.assertEqual(self.main.events, ["deck ▶", Path(_PREVIEW)])
        self.main._lib_browser.on_playback_stopped.assert_called()

    def test_stopping_the_preview_leaves_the_decks_alone(self):
        self._preview()
        self.main.events.clear()
        self._preview()                       # ■ on its own button
        self.assertEqual(self.main.events, [None])
        self.assertEqual(self.btn.text(), "▶")

    def test_its_stop_button_leaves_a_deck_title_playing(self):
        self._preview()
        self._deck_starts_a_title()
        self._preview()
        self.assertEqual(self.main.events, [])
        self.assertEqual(self.btn.text(), "▶")

    def test_closing_it_stops_its_own_preview(self):
        self._preview()
        self.main.events.clear()
        self.dlg.reject()
        self.assertEqual(self.main.events, [None])

    def test_closing_it_leaves_a_deck_title_playing(self):
        self._preview()
        self._deck_starts_a_title()
        self.dlg.reject()
        self.assertEqual(self.main.events, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
