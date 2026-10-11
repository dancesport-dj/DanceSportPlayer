#!/usr/bin/env python3
"""〰 A title's waveform is decoded once and then kept in the database.

Run:  py -m unittest tests.planner.test_waveform_cache -v

Marcel: "cache it in databse, currently it feels liek a second till wave
comes". The outline is content-addressed like the 🔇 silence spans, so a
copy or a renamed file finds it too.
"""
import os
import tempfile
import threading
import unittest
from pathlib import Path

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_wave_cache_"))

import planner.db as pdb


class WaveformCacheTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_wave_cache_db_"))
        self._saved = (pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
        pdb.AUDIO_DB_FILE = self.dir / "scratch.db"
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False
        self.addCleanup(self._restore)
        self.song = self.dir / "song.mp3"
        self.song.write_bytes(b"ID3" + bytes(range(256)) * 40)

    def _restore(self):
        try:
            pdb._DB_LOCAL.conn.close()
        except Exception:
            pass
        pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED = self._saved

    def test_never_decoded_is_none(self):
        self.assertIsNone(pdb.AudioCache().get_waveform(self.song))

    def test_the_peaks_survive_a_new_session(self):
        peaks = [round(i / 599, 4) for i in range(600)]
        pdb.AudioCache().put_waveform(self.song, peaks)
        self.assertEqual(pdb.AudioCache().get_waveform(self.song), peaks)

    def test_a_copy_of_the_file_finds_them_too(self):
        pdb.AudioCache().put_waveform(self.song, [0.5, 1.0])
        copy = self.dir / "copy.mp3"
        copy.write_bytes(self.song.read_bytes())
        self.assertEqual(pdb.AudioCache().get_waveform(copy), [0.5, 1.0])

    def test_it_is_small(self):
        pdb.AudioCache().put_waveform(self.song, [0.25] * 600)
        (blob,) = pdb._db().execute("SELECT peaks FROM waveforms").fetchone()
        self.assertEqual(len(blob), 600 * 4)        # float32, ~2.4 KB a title

    def test_it_travels_with_a_retagged_file_and_is_pruned_with_it(self):
        self.assertIn("waveforms", pdb._FP_TABLES)


if __name__ == "__main__":
    unittest.main()
