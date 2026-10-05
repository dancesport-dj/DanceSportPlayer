#!/usr/bin/env python3
"""Tests for planner.gaps — the 📊 library gap dashboard's stats.

Run:  py -m unittest tests.planner.test_gap_stats -v

Entries are built by hand under standardcd/lateincd paths so the style filter
passes; staleness comes from a MusicLibrary subclass whose _playlists_for is a
plain dict lookup (no real playlist index needed).
"""

import unittest
from pathlib import Path

from dancesport_planner import MusicEntry, MusicLibrary
from planner.gaps import (
    ai_prompt,
    gap_reasons,
    gap_stats,
    last_played_year,
    shopping_list,
)


def _lw(name: str, bpm=29, popularity=0, classes_ok=None) -> MusicEntry:
    return MusicEntry(
        path=Path(rf"C:\music\tanzcds\standardcd\lw\{name}.mp3"),
        title=name, dance="LW", bpm=bpm,
        popularity=popularity, classes_ok=classes_ok)


class FakePlaylistLib(MusicLibrary):
    """_playlists_for keyed by entry title — enough for staleness tests."""

    def __init__(self, playlists_by_title=None):
        super().__init__()
        self._by_title = playlists_by_title or {}

    def _playlists_for(self, entry):
        return self._by_title.get(entry.title, set())


def _row(rows, style, cls, dance):
    return next(r for r in rows
                if (r["style"], r["cls"], r["dance"]) == (style, cls, dance))


class GapStatsTest(unittest.TestCase):
    def test_pool_tempo_and_class_filters(self):
        lib = FakePlaylistLib()
        lib.entries.extend([
            _lw("In Tempo", bpm=29, popularity=6),
            _lw("Too Fast", bpm=40),               # outside 28-30 → not in pool
            _lw("No Takt", bpm=None),              # unknown tempo → stays in pool
            _lw("D Only", bpm=29, classes_ok=["D"]),   # excluded from S pool
        ])
        rows = gap_stats(lib, today_year=2026)
        s = _row(rows, "Standard", "S", "LW")
        self.assertEqual(s["total"], 4)
        self.assertEqual(s["tempo_known"], 3)
        self.assertEqual(s["tempo_ok"], 2)     # In Tempo + D Only
        self.assertEqual(s["pool"], 2)         # In Tempo + No Takt (D Only class-cut)
        self.assertEqual(s["proven"], 1)       # popularity 6 ≥ 5
        self.assertEqual(s["fresh"], 1)
        d = _row(rows, "Standard", "D", "LW")
        self.assertEqual(d["pool"], 3)         # D Only allowed again in D class

    def test_staleness_from_playlist_years(self):
        lib = FakePlaylistLib({
            "Old Hit": {r"D:\Turniere\Turnier 2019 Hgr\HGR_S_STD.m3u"},
            "Recent Hit": {r"D:\Turniere\Turnier 2025 Hgr\HGR_S_STD.m3u"},
            "Undated Hit": {r"D:\Turniere\SomeEvent\HGR_S_STD.m3u"},
        })
        lib.entries.extend([
            _lw("Old Hit", popularity=6),
            _lw("Recent Hit", popularity=6),
            _lw("Undated Hit", popularity=6),
            _lw("Never Played", popularity=0),
        ])
        rows = gap_stats(lib, stale_years=3, today_year=2026)
        s = _row(rows, "Standard", "S", "LW")
        self.assertEqual(s["never"], 1)
        # stale = Old Hit (2019 ≤ 2023) + Never Played; Undated gets the benefit
        # of the doubt, Recent is fine.
        self.assertEqual(s["stale"], 2)

    def test_last_played_year(self):
        lib = FakePlaylistLib({
            "Two Events": {r"D:\Turniere\Turnier 2018\X.m3u",
                           r"D:\Turniere\Turnier 2024\X.m3u"},
        })
        self.assertEqual(last_played_year(lib, _lw("Two Events")), 2024)
        self.assertIsNone(last_played_year(lib, _lw("Unknown")))

    def test_gap_reasons_and_shopping_list(self):
        lib = FakePlaylistLib()
        lib.entries.extend(
            [_lw(f"Song {i}", popularity=6) for i in range(20)])
        rows = gap_stats(lib, today_year=2026)
        s = _row(rows, "Standard", "S", "LW")
        self.assertEqual(gap_reasons(s), [])   # 20 in pool, 20 proven → healthy
        cc = _row(rows, "Latin", "S", "CC")    # empty dance → both reasons fire
        self.assertEqual(len(gap_reasons(cc)), 2)
        lines = shopping_list(rows)
        self.assertTrue(any("Cha-Cha" in ln and "Latin S" in ln for ln in lines))
        self.assertFalse(any("(LW" in ln and "Standard S:" in ln for ln in lines))

    def test_ai_prompt_names_the_gap(self):
        lib = FakePlaylistLib()
        rows = gap_stats(lib, today_year=2026)
        s = _row(rows, "Standard", "D", "SF")
        p = ai_prompt(s)
        self.assertIn("D-class", p)
        self.assertIn("28–30", p)
        self.assertIn("fresh", p)


if __name__ == "__main__":
    unittest.main()
