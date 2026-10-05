#!/usr/bin/env python3
"""Tests for 🔀 Shuffle in the ETDS party list header.

Run:  py -m unittest tests.gui.test_party_shuffle -v

The button shows only on a party list (a per-class Eintanzen list has a style)
and puts the same titles in a fresh order, as building the list again would.
"""

import os
import random
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pshuffle_"))

from PySide6.QtWidgets import QApplication, QToolButton, QWidget  # noqa: E402

from gui.main_generate import GenerateMixin  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.models import MusicEntry  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


def _e(dance, n):
    return MusicEntry(path=Path(rf"C:\music\{dance}{n}.mp3"), title=f"{dance} {n}",
                      dance=dance, duration=150)


class _Win(QWidget):
    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "both"}


class PartyShuffleTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        random.seed(3)

    def window(self, style=""):
        host = _Win()
        self.addCleanup(reap_widget, host)
        t = PlaylistTable()
        t.setParent(host)
        entries = [_e(d, n) for n in range(1, 4)
                   for d in ("LW", "TG", "WW", "SF", "QS", "SA", "CC", "RB", "PD", "JI")]
        t.load_warmup(entries, "ETDS Party", style, "S", True, lambda _p: None, None)
        btn = QToolButton(host)
        w = SimpleNamespace(_warmup_table=t, _warmup_shuffle_btn=btn,
                            _warmup_check_btn=QToolButton(host),
                            _warmup_opts={}, statusBar=mock.Mock())
        return w, t, btn

    def titles(self, t):
        return [m.entry.title for _r, m in t._row_meta.numbered()]

    def test_button_shows_on_a_party_list(self):
        w, _t, btn = self.window()
        GenerateMixin._sync_warmup_shuffle_btn(w)
        self.assertFalse(btn.isHidden())

    def test_button_hidden_on_a_class_warmup(self):
        w, _t, btn = self.window(style="Latin")
        GenerateMixin._sync_warmup_shuffle_btn(w)
        self.assertTrue(btn.isHidden())

    def test_button_hidden_on_an_empty_panel(self):
        w, t, btn = self.window()
        t.setRowCount(0)
        t._row_meta.clear()
        GenerateMixin._sync_warmup_shuffle_btn(w)
        self.assertTrue(btn.isHidden())

    def test_shuffle_keeps_the_titles_in_a_new_order(self):
        w, t, _btn = self.window()
        before = self.titles(t)
        changed = mock.Mock()
        t.set_change_callback(changed)
        GenerateMixin._shuffle_warmup(w)
        after = self.titles(t)
        self.assertEqual(sorted(after), sorted(before))
        self.assertNotEqual(after, before)
        changed.assert_called()

    def test_shuffle_does_nothing_on_a_class_warmup(self):
        w, t, _btn = self.window(style="Latin")
        before = self.titles(t)
        GenerateMixin._shuffle_warmup(w)
        self.assertEqual(self.titles(t), before)


if __name__ == "__main__":
    unittest.main()
