#!/usr/bin/env python3
"""Tests for ✓ Party check in the 🤸 Eintanzen header.

Run:  py -m unittest tests.gui.test_party_check_ui -v

`planner/party_check.py` has the rules and its own tests. What is checked here
is the part only the GUI can get wrong:

* the button shows on the same lists 🔀 does and nowhere else;
* the two late gates come from the options the list was built with, not from
  the engine's defaults — checking against a gate the operator turned off
  would be inventing a rule they declined;
* a finding's row number is an index into the TITLES, while the panel also
  holds ═══ section headers, so the jump has to go through `song_rows()`.
  Off-by-one here lands the operator on the wrong song, which is worse than
  no link at all.
"""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pcheck_"))

from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QLabel, QToolButton, QWidget,
)

from gui.main_generate import GenerateMixin  # noqa: E402
from gui.main_music import MusicCheckMixin  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from planner import party_check as pc  # noqa: E402
from planner.models import MusicEntry  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

_TAKT = {'LW': 29, 'TG': 32, 'WW': 59, 'SF': 29, 'QS': 51,
         'CC': 31, 'SA': 51, 'RB': 25, 'PD': 59, 'JI': 42}

_BEATS_PER_BAR = {"LW": 3, "TG": 2, "WW": 3, "SF": 4, "QS": 4,
                  "SA": 2, "CC": 4, "RB": 4, "PD": 2, "JI": 4}


def _e(dance, n, **kw):
    return MusicEntry(path=Path(rf"C:\music\{dance}{n}.mp3"),
                      title=kw.pop("title", f"{dance} {n}"), dance=dance,
                      bpm=_TAKT[dance], duration=150, **kw)


class _Win(MusicCheckMixin, QWidget):
    """Enough MainWindow to run the real mixin.

    Deriving from it rather than copying its pieces is the point: a harness
    that restated `_PARTY_GROUPS` would keep passing after the production one
    changed. Only the jump out of the report is stubbed — it reaches for the
    deck machinery a bare QWidget has none of, and what matters here is which
    row it was handed."""

    _BEATS_PER_BAR = _BEATS_PER_BAR

    def __init__(self):
        super().__init__()
        self._settings = {"app_mode": "both"}
        self._warmup_opts = {}
        self._party_dlg = None
        self._warmup_closed = False
        self._warmup_folded = False
        self.jumped = []

    def _reveal_warmup_row(self, row):
        self.jumped.append(row)


class PartyCheckUiTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def table(self, codes, style="", host=None):
        """A party panel holding exactly `codes`, in that order."""
        host = host or _Win()
        self.addCleanup(reap_widget, host)
        t = PlaylistTable()
        t.setParent(host)
        t.load_warmup([_e(d, i) for i, d in enumerate(codes)], "ETDS Party",
                      style, "S", True, lambda _p: None, None)
        host._warmup_table = t
        return host, t

    # ── the button ───────────────────────────────────────────────────────────

    def buttons(self, style=""):
        host, t = self.table(('LW', 'TG', 'QS', 'CC', 'RB', 'JI'), style=style)
        shuffle_btn, check_btn = QToolButton(host), QToolButton(host)
        w = SimpleNamespace(_warmup_table=t, _warmup_shuffle_btn=shuffle_btn,
                            _warmup_check_btn=check_btn)
        return w, t, check_btn

    def test_the_check_button_shows_on_a_party_list(self):
        w, _t, btn = self.buttons()
        GenerateMixin._sync_warmup_shuffle_btn(w)
        self.assertFalse(btn.isHidden())

    def test_the_check_button_is_hidden_on_a_class_warmup(self):
        """A per-class Eintanzen list has a style and follows none of these
        rules — it is one section, round-robin."""
        w, _t, btn = self.buttons(style="Latin")
        GenerateMixin._sync_warmup_shuffle_btn(w)
        self.assertTrue(btn.isHidden())

    def test_the_check_button_is_hidden_on_an_empty_panel(self):
        w, t, btn = self.buttons()
        t.setRowCount(0)
        t._row_meta.clear()
        GenerateMixin._sync_warmup_shuffle_btn(w)
        self.assertTrue(btn.isHidden())

    # ── the switches the list was built under ────────────────────────────────

    def test_the_late_gates_come_from_the_build_options(self):
        codes = ('LW', 'TG', 'QS', 'CC', 'RB', 'JI', 'WW', 'SF', 'LW')
        host, _t = self.table(codes)
        found = host._party_findings()
        self.assertTrue(any("late WW" in f.text for f in found),
                        [f.text for f in found])

        host._warmup_opts = {"etds": {"late_ww": False, "late_pd": True}}
        self.assertEqual(
            [f.text for f in host._party_findings()
             if f.category == pc.SPACING], [])

    def test_a_clean_list_reports_nothing(self):
        host, _t = self.table(('LW', 'TG', 'QS', 'CC', 'RB', 'JI',
                               'TG', 'SF', 'LW', 'SA', 'RB', 'CC'))
        self.assertEqual(host._party_findings(), [])

    # ── the jump ─────────────────────────────────────────────────────────────

    def report(self, host):
        host._show_party_report(
            host._party_findings(),
            len(host._warmup_table._row_meta.song_rows()))
        dlg = host._party_dlg
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_a_row_link_jumps_past_the_section_headers(self):
        """The Latin section opens on Samba instead of Rumba, so the finding
        points at title 4 — which is table row 5, the ═══ headers counted."""
        host, t = self.table(('LW', 'TG', 'QS', 'CC', 'SA', 'JI'))
        dlg = self.report(host)
        song_rows = t._row_meta.song_rows()
        self.assertNotEqual(song_rows, list(range(len(song_rows))),
                            "the panel grew no section headers to jump past")

        labels = [w for w in dlg.findChildren(QLabel) if "<a href=" in w.text()]
        self.assertTrue(labels, "no finding carried a jump link")
        labels[0].linkActivated.emit("0")
        self.assertEqual(len(host.jumped), 1)
        self.assertIn(host.jumped[0], song_rows)
        self.assertEqual(host.jumped[0], song_rows[3],
                         "the link jumped to the wrong title")

    def test_a_clean_list_still_opens_a_report(self):
        """It says so rather than doing nothing — a button that sometimes does
        nothing reads as broken."""
        host, _t = self.table(('LW', 'TG', 'QS', 'CC', 'RB', 'JI',
                               'TG', 'SF', 'LW', 'SA', 'RB', 'CC'))
        dlg = self.report(host)
        texts = " ".join(w.text() for w in dlg.findChildren(QLabel))
        self.assertIn("Nothing to report", texts)

    def test_every_group_with_a_finding_gets_its_own_panel(self):
        host, _t = self.table(('LW', 'SF', 'QS',                 # not LW TG QS
                               'CC', 'RB', 'JI',
                               'WW', 'TG', 'LW'))       # WW on title 7 of 12
        host._warmup_table._row_meta.entries()[0].duration = 400
        dlg = self.report(host)
        texts = " ".join(w.text() for w in dlg.findChildren(QLabel))
        self.assertIn("🔁 Rounds", texts)
        self.assertIn("⏳ Spacing", texts)
        self.assertIn("⏱ Length", texts)
        self.assertNotIn("👯 Duplicates", texts)

    def test_checking_an_empty_panel_opens_nothing(self):
        host, t = self.table(('LW', 'TG', 'QS'))
        t.setRowCount(0)
        t._row_meta.clear()
        host.statusBar = mock.Mock()
        host._check_party_list()
        self.assertIsNone(host._party_dlg)


if __name__ == "__main__":
    unittest.main()
