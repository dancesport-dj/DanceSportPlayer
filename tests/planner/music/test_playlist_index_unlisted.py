#!/usr/bin/env python3
"""A playlist folder the learner could not list is not a folder gone.

Run:  py -m unittest tests.planner.music.test_playlist_index_unlisted -v

`_playlist_tree` swallows an OSError from a folder, so none of its playlists
reached `seen` and `PlaylistIndexCache.prune` deleted their cached rows: a
re-read of every one of them on the next start. A walk that lost a folder
prunes nothing.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pl_unlisted_state_"))

from planner import config as planner_config
from planner.music import playlist_index
from planner.music.library import MusicLibrary
from planner.music.playlist_index import PlaylistIndexCache
from tests.db_support import use_scratch_db


class UnlistedPlaylistFolderTest(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dp_pl_unlisted_"))
        self.addCleanup(shutil.rmtree, self.root, True)
        use_scratch_db(self, self.root / "scratch.db")
        self.lists = self.root / "lists"
        orig = planner_config.PLAYLIST_DIR
        planner_config.set_playlist_dir(self.lists)
        self.addCleanup(planner_config.set_playlist_dir, orig)
        self.kept = self.lists / "A" / "kept.m3u"
        self.lost = self.lists / "B" / "lost.m3u"
        for m3u in (self.kept, self.lost):
            m3u.parent.mkdir(parents=True)
            m3u.write_text("#EXTM3U\nC:/music/Moon River (LW 29).mp3\n", encoding="utf-8")
        self.real_scandir = os.scandir

    def learn(self):
        lib = MusicLibrary()
        lib._learn_playlists()

    def rows(self):
        cache = PlaylistIndexCache(self.lists, MusicLibrary()._dance_map_digest())
        return set(cache._rows)

    def refuse(self, folder):
        def scandir(path):
            if str(path) == str(folder):
                raise PermissionError("share went away")
            return self.real_scandir(path)
        return mock.patch("planner.music.playlist_index.os.scandir", scandir)

    def test_the_walk_names_the_folder_it_could_not_list(self):
        unlisted = []
        with self.refuse(self.lost.parent):
            m3us, _ = playlist_index._playlist_tree(unlisted)
        self.assertEqual([p for p, _ in m3us], [self.kept])
        self.assertEqual(unlisted, [str(self.lost.parent)])

    def test_a_folder_that_could_not_be_listed_keeps_its_cached_rows(self):
        self.learn()
        self.assertEqual(self.rows(), {str(self.kept), str(self.lost)})
        with self.refuse(self.lost.parent):
            self.learn()
        self.assertEqual(self.rows(), {str(self.kept), str(self.lost)})

    def test_a_playlist_really_gone_is_still_pruned(self):
        """The control: a clean walk that does not see a playlist drops its row."""
        self.learn()
        self.lost.unlink()
        self.learn()
        self.assertEqual(self.rows(), {str(self.kept)})


if __name__ == "__main__":
    unittest.main()
