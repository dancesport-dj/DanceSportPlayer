#!/usr/bin/env python3
"""⏱ Track lengths heal in the whole-repo cache too.

Run:  py -m unittest tests.planner.test_global_duration_heal -v

The duration column was added to `global_meta` after most of its rows were
written, so those rows carry 0. The library scan re-probes a 0 on every cache
hit (`_make_entry`), but a file the whole-repo scan reused straight from
`GlobalScanCache` only had its bpm healed — 53k of 54k rows never got a length,
Discofox / Salsa / … included.
"""

import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_gdur_state_"))

import planner.db as pdb
from planner import config as planner_config
import planner.library as plib
from planner.db import AudioCache, GlobalScanCache
from planner.library import MusicLibrary


class GlobalDurationHealTest(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dp_gdur_"))
        # The scan writes cache rows, and `AUDIO_DB_FILE` has no env override —
        # point it at a scratch DB so nothing lands in the real one.
        self._saved = (planner_config.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
        planner_config.AUDIO_DB_FILE = self.root / "scratch.db"
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False
        self.addCleanup(self._restore)
        self.song = self.root / "discofox" / "Atemlos (DF 30).mp3"
        self.song.parent.mkdir(parents=True)
        self.song.write_bytes(b"not really an mp3")

    def _restore(self):
        try:
            pdb._DB_LOCAL.conn.close()
        except Exception:
            pass
        planner_config.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED = self._saved

    def _scan(self, secs, whole_repo=True):
        probes = []

        def probe(path):
            probes.append(path)
            return secs

        def tags_once(path):             # a file new to the scan reads its length here
            probes.append(path)
            return None, secs
        lib = MusicLibrary()
        with mock.patch.object(plib, "_read_duration", probe), \
                mock.patch.object(plib, "_read_tags_once", tags_once):
            lib.scan(AudioCache(), music_dir=self.root, skip_special=False, learn=False,
                     analyze=False, interactive=False,
                     global_cache=GlobalScanCache() if whole_repo else None)
        return lib.entries[0], probes

    def test_a_reused_row_without_a_length_gets_one(self):
        entry, _ = self._scan(0)
        self.assertEqual(entry.duration, 0)
        cache = GlobalScanCache()                # a row from before the duration column
        cache.put(self.song, {**cache.get(self.song), "duration": 0})
        entry, _ = self._scan(185)
        self.assertEqual(entry.duration, 185)
        self.assertEqual(GlobalScanCache().get(self.song)["duration"], 185)

    def test_a_row_with_a_length_is_not_probed_again(self):
        self._scan(185)
        entry, probes = self._scan(999)
        self.assertEqual(entry.duration, 185)
        self.assertNotIn(self.song, probes)

    # A header that gives no length was probed again on every start.
    def test_a_file_without_a_length_is_probed_once(self):
        self._scan(0, whole_repo=False)
        entry, probes = self._scan(0, whole_repo=False)
        self.assertEqual(entry.duration, 0)
        self.assertNotIn(self.song, probes)

    def test_nor_in_the_whole_repo_cache(self):
        self._scan(0)
        entry, probes = self._scan(0)
        self.assertEqual(entry.duration, 0)
        self.assertNotIn(self.song, probes)

    def test_a_changed_file_is_probed_again(self):
        self._scan(0, whole_repo=False)
        self.song.write_bytes(b"a re-encoded file, longer than before")
        later = self.song.stat().st_mtime + 60      # the fingerprint is cached per mtime
        os.utime(self.song, (later, later))
        entry, _ = self._scan(185, whole_repo=False)
        self.assertEqual(entry.duration, 185)


if __name__ == "__main__":
    unittest.main(verbosity=2)
