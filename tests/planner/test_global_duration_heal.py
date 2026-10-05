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

import planner.db as pdb  # noqa: E402
import planner.library as plib  # noqa: E402
from planner.db import AudioCache, GlobalScanCache  # noqa: E402
from planner.library import MusicLibrary  # noqa: E402


class GlobalDurationHealTest(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dp_gdur_"))
        # The scan writes cache rows, and `AUDIO_DB_FILE` has no env override —
        # point it at a scratch DB so nothing lands in the real one.
        self._saved = (pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
        pdb.AUDIO_DB_FILE = self.root / "scratch.db"
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
        pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED = self._saved

    def _scan(self, secs):
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
                     analyze=False, global_cache=GlobalScanCache(), interactive=False)
        return lib.entries[0], probes

    def test_a_reused_row_without_a_length_gets_one(self):
        entry, _ = self._scan(0)                 # written with no length, like the old rows
        self.assertEqual(entry.duration, 0)
        entry, _ = self._scan(185)
        self.assertEqual(entry.duration, 185)
        self.assertEqual(GlobalScanCache().get(self.song)["duration"], 185)

    def test_a_row_with_a_length_is_not_probed_again(self):
        self._scan(185)
        entry, probes = self._scan(999)
        self.assertEqual(entry.duration, 185)
        self.assertNotIn(self.song, probes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
