#!/usr/bin/env python3
"""Tests for ✋ Manual in the party list header.

Run:  py -m unittest tests.gui.test_party_manual -v

Tier 4 #16: the button turns the party list (or an Eintanzen / competition
running order) into a flat running order that is edited by hand — every row
dragged anywhere, nothing re-cut or re-rolled — keeping the order it shows.
"""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pmanual_"))

from PySide6.QtWidgets import QApplication, QToolButton, QWidget

from gui.decks.deck_set import DeckSet
from gui.table.playlist_table import PlaylistTable
from gui.window.main_generate import GenerateMixin
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget


def _e(dance, n):
    return MusicEntry(path=Path(rf"C:\music\{dance}{n}.mp3"), title=f"{dance} {n}",
                      dance=dance, duration=150)


class _Host(QWidget):
    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "both"}

    def deck_name(self):
        return "Party"

    def ensure_deck_ready(self):
        pass


class PartyManualTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def window(self, fill=True):
        host = _Host()
        self.addCleanup(reap_widget, host)
        t = PlaylistTable()
        t.setParent(host)
        if fill:
            entries = [_e(d, n) for n in range(1, 3)
                       for d in ("LW", "TG", "WW", "SF", "QS", "SA", "CC", "RB", "PD", "JI")]
            t.load_warmup(entries, "ETDS Party", "", "S", True, lambda _p: None, None)
        btn = QToolButton(host)
        btn.setCheckable(True)
        w = SimpleNamespace(_deckset=DeckSet(),
                            _autosave_playlist=mock.Mock(), statusBar=mock.Mock())
        w._deckset.warmup_table = t
        w._sync_warmup_manual_btn = lambda b: GenerateMixin._sync_warmup_manual_btn(w, b)
        return w, t, btn

    def titles(self, t):
        return [m.entry.title for _r, m in t._row_meta.numbered()]

    def test_button_shows_on_a_party_list(self):
        w, _t, btn = self.window()
        GenerateMixin._sync_warmup_manual_btn(w, btn)
        self.assertFalse(btn.isHidden())

    def test_button_hidden_on_an_empty_panel(self):
        w, _t, btn = self.window(fill=False)
        GenerateMixin._sync_warmup_manual_btn(w, btn)
        self.assertTrue(btn.isHidden())

    def test_click_turns_the_list_manual_in_the_order_it_shows(self):
        w, t, btn = self.window()
        before = self.titles(t)
        GenerateMixin._warmup_to_manual(w, btn)
        self.assertTrue(t._player_list)
        self.assertEqual(self.titles(t), before)
        w._autosave_playlist.assert_called_once()

    def test_button_stays_and_is_pressed_once_the_list_is_manual(self):
        w, t, btn = self.window()
        GenerateMixin._warmup_to_manual(w, btn)
        self.assertFalse(btn.isHidden())
        self.assertTrue(btn.isChecked())

    def test_glyph_is_a_lock_until_the_list_is_manual(self):
        w, t, btn = self.window()
        GenerateMixin._sync_warmup_manual_btn(w, btn)
        self.assertEqual(btn.text(), "🔒")
        GenerateMixin._warmup_to_manual(w, btn)
        self.assertEqual(btn.text(), "✋")

    def test_second_click_gives_the_automatic_list_back(self):
        w, t, btn = self.window()
        w._warmup_to_auto = lambda b: GenerateMixin._warmup_to_auto(w, b)
        w._warmup_to_manual = lambda b: GenerateMixin._warmup_to_manual(w, b)
        before = self.titles(t)
        GenerateMixin._warmup_toggle_manual(w, btn)
        self.assertTrue(t._player_list)
        GenerateMixin._warmup_toggle_manual(w, btn)
        self.assertFalse(t._player_list)
        self.assertFalse(btn.isChecked())
        self.assertEqual(self.titles(t), before)
        self.assertTrue(t._party_swap())


if __name__ == "__main__":
    unittest.main(verbosity=2)
