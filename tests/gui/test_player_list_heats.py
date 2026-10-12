#!/usr/bin/env python3
"""A player list says which heat a title is played in.

Run:  .venv\\Scripts\\python.exe -m unittest tests.gui.test_player_list_heats -v

A WDSF running order restored from the session (seven Waltzes, then seven
Tangos, … in the Vorrunde) came back as a flat player list, and the Heat
column stayed blank: only the grid filled it. The heat of a title is its
place among the same dance in its round, so the list derives it from its own
order, the way it derives the ─── strips.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_player_heats_"))

from PySide6.QtWidgets import QApplication

from gui.playlist_table import PlaylistTable
from planner.models import MusicEntry
from shared.columns import _COL_HEAT
from tests.qt_test_support import reap_widget


def _e(name, dance):
    return MusicEntry(path=Path(rf"C:\music\{name}.mp3"), title=name, dance=dance)


def _round(name, dances, heats):
    """Dance-major, as the app writes an m3u: every LW heat, then every TG …"""
    return [(name, _e(f"{name}-{d}{h}", d)) for d in dances for h in range(1, heats + 1)]


class PlayerListHeatsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def table(self, rounds):
        entries = [e for _, e in rounds]
        t = PlaylistTable()
        self.addCleanup(reap_widget, t)
        t.load_player_list(entries, "WDSF", play_cb=lambda *a: None,
                           sections={str(e.path): name for name, e in rounds})
        return t

    def heats(self, t):
        """{title: Heat cell} of every song row."""
        return {meta.entry.title: t.item(row, _COL_HEAT).text()
                for row, meta in t._row_meta.numbered()}

    def test_a_restored_running_order_shows_its_heats(self):
        t = self.table(_round("Vorrunde", ["LW", "TG"], 3)
                       + _round("Finale", ["LW", "TG"], 1))
        heats = self.heats(t)
        self.assertEqual(heats["Vorrunde-LW1"], "Heat 1")
        self.assertEqual(heats["Vorrunde-LW3"], "Heat 3")
        self.assertEqual(heats["Vorrunde-TG2"], "Heat 2")
        # One heat per dance: nothing to tell apart.
        self.assertEqual(heats["Finale-LW1"], "")

    def test_a_list_without_rounds_names_no_heats(self):
        """Without known rounds the strips name dances, and a run of seven
        Paso Dobles is seven Paso Dobles, not seven heats."""
        entries = [_e(f"PD{i}", "PD") for i in range(1, 4)]
        t = PlaylistTable()
        self.addCleanup(reap_widget, t)
        t.load_player_list(entries, "Paso", play_cb=lambda *a: None)
        t._player_sections = {}
        t._reload_warmup()
        self.assertEqual(set(self.heats(t).values()), {""})

    def test_a_dropped_title_renumbers_its_round(self):
        rounds = _round("Vorrunde", ["LW", "TG"], 2)
        t = self.table(rounds)
        entries = t._row_meta.entries()
        extra = _e("Dropped-LW", "LW")
        t._reload_warmup(entries[:1] + [extra] + entries[1:])
        heats = self.heats(t)
        self.assertEqual(heats["Vorrunde-LW1"], "Heat 1")
        self.assertEqual(heats["Dropped-LW"], "Heat 2")
        self.assertEqual(heats["Vorrunde-LW2"], "Heat 3")


if __name__ == "__main__":
    unittest.main(verbosity=2)
