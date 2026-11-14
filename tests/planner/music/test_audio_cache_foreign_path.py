#!/usr/bin/env python3
"""The audio cache never touches a path on someone else's share (review 7.A).

Run:  py -m unittest tests.planner.music.test_audio_cache_foreign_path -v

A red row from someone else's list or pack keeps its `\\\\host\\share` path,
and every drop, the Similar window and Check music hand that path to the
cache. Its key stat-ed the file and its fingerprint read it, which offers the
Windows login to that host and hangs the GUI thread on a dead one. A share
the user configured is still read.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_foreign_cache_state_"))

from planner.music import paths
from planner.music.db import AudioCache
from tests.db_support import use_scratch_db

GHOST = Path(r"\\10.255.255.1\share\LW - Song.mp3")


def _refuse_network(real):
    """`real` (a Path method), failing the test for any UNC path."""
    def guarded(self, *args, **kwargs):
        if str(self).startswith("\\\\"):
            raise AssertionError(f"touched {self}")
        return real(self, *args, **kwargs)
    return guarded


class ForeignPathTest(unittest.TestCase):

    def setUp(self):
        use_scratch_db(self, Path(tempfile.mkdtemp(prefix="dp_foreign_cache_")) / "s.db")
        self.addCleanup(paths.set_own_shares, {})
        paths.set_own_shares({})
        for name in ("stat", "open", "exists", "is_file"):
            patcher = mock.patch.object(Path, name, _refuse_network(getattr(Path, name)))
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_no_entry_point_touches_the_ghost_path(self):
        cache = AudioCache()
        self.assertIsNone(cache.fingerprint(GHOST))
        self.assertIsNone(cache.known_fingerprint(GHOST))
        self.assertIsNone(cache.get_silences(GHOST))
        self.assertIsNone(cache.get_noise_floor(GHOST))
        self.assertIsNone(cache.get(GHOST))

    def test_an_own_share_is_still_stat_ed(self):
        paths.set_own_shares({"library_dir": r"\\10.255.255.1\share"})
        with self.assertRaisesRegex(AssertionError, "touched"):
            AudioCache().fingerprint(GHOST)


if __name__ == "__main__":
    unittest.main()
