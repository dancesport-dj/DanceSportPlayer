#!/usr/bin/env python3
"""Looking up past competitions leaves the library's entries alone.

Run:  py -m unittest tests.planner.test_past_competition_readonly -v

`past_competition_entries` and `past_competition_round_pools` wrote every
match's source lists into the shared `MusicEntry.replay_sources`, which is what
a track's tooltip shows. So a lookup — "Find planned before" on one slot, which
reads every tournament list of every class — rewrote the tooltip of every
matched song in every deck: a normally generated deck suddenly said "In these
matching past lists: …" about lists it was never built from. The labels are
returned instead (the round pools' per-round sources); setting them is the
caller's call.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from dancesport_planner import MusicEntry, MusicLibrary
from planner import config as planner_config
from planner.competition import parse_competition_schedule

_TRACK = r"C:\music\standardcd\Tango One (TG 32).mp3"


class ReadOnlyLookupTest(unittest.TestCase):

    def setUp(self):
        orig = planner_config.PLAYLIST_DIR
        self.dir = Path(tempfile.mkdtemp(prefix="dp_past_ro_"))
        planner_config.set_playlist_dir(self.dir)
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.addCleanup(planner_config.set_playlist_dir, orig)
        (self.dir / "Turnier Hgr B STD.m3u").write_text(
            "#EXTM3U\n" + _TRACK + "\n", encoding="utf-8")
        self.entry = MusicEntry(path=Path(_TRACK), title="Tango One",
                                dance="TG", bpm=32)
        self.lib = MusicLibrary()
        self.lib.entries.append(self.entry)
        self.spec = parse_competition_schedule("HGR B STD 1-1")[0]

    def test_the_round_pools_return_the_labels_without_writing_them(self):
        found, _pools, _n, sources = self.lib.past_competition_round_pools(
            self.spec, [1, 1], 5)
        self.assertEqual(found, [self.entry])
        self.assertIsNone(self.entry.replay_sources)
        labels = {lab for rnd in sources for lab in rnd.get(id(self.entry), [])}
        self.assertEqual(labels, {f"{self.dir.name} / Turnier Hgr B STD"})

    def test_the_planned_before_lookup_leaves_them_alone_too(self):
        self.lib.past_competition_round_pools(None, [1, 1], 5)
        self.assertIsNone(self.entry.replay_sources)

    def test_past_competition_entries_writes_nothing(self):
        found, _n = self.lib.past_competition_entries(self.spec)
        self.assertEqual(found, [self.entry])
        self.assertIsNone(self.entry.replay_sources)


if __name__ == "__main__":
    unittest.main(verbosity=2)
