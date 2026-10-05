#!/usr/bin/env python3
"""🎯 Hand-set Paso Doble highlights travel to another PC.

Run:  py -m unittest tests.planner.test_pd_manual_transfer -v

A manual mark is the one thing in the database no detection gets back, so
AudioCache.export_manual_pd / import_manual_pd carry it over. Two scratch
databases stand in for the two PCs; the music file is the same bytes at a
different path, as it is on a second machine.
"""

import os
import tempfile
import threading
import unittest
from pathlib import Path

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pdx_"))

import planner.db as pdb  # noqa: E402

_AUDIO = b"ID3 a paso doble, as far as the hash can tell"


class ManualPdTransferTest(unittest.TestCase):

    def setUp(self):
        self._saved = (pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
        self.addCleanup(self._restore)

    def _restore(self):
        self._close()
        pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED = self._saved

    def _close(self):
        """Close a scratch PC's connection — never the one the saved state owns."""
        if pdb._DB_LOCAL is self._saved[1]:
            return
        try:
            pdb._DB_LOCAL.conn.close()
        except Exception:
            pass

    def _pc(self) -> tuple[Path, "pdb.AudioCache"]:
        """A fresh machine: its own folder and database."""
        self._close()
        d = Path(tempfile.mkdtemp(prefix="dp_pdx_pc_"))
        pdb.AUDIO_DB_FILE = d / "scratch.db"
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False
        return d, pdb.AudioCache()

    def _marked_export(self) -> list[dict]:
        d, cache = self._pc()
        marked = d / "Espana Cani PD60.mp3"
        marked.write_bytes(_AUDIO)
        auto = d / "El Gato Montes PD59.mp3"
        auto.write_bytes(b"another paso")
        cache.put_pd_highlights(marked, [47.2, 75.65], manual=True)
        cache.put_pd_highlights(auto, [40.0, 80.0, 120.0])
        return cache.export_manual_pd()

    def test_only_the_hand_set_marks_are_exported(self):
        marks = self._marked_export()
        self.assertEqual(len(marks), 1)
        self.assertEqual(marks[0]["file"], "Espana Cani PD60.mp3")
        self.assertEqual(marks[0]["times"], [47.2, 75.65])
        self.assertTrue(marks[0]["afp"])

    def test_the_same_file_on_another_pc_gets_its_marks(self):
        marks = self._marked_export()
        d, cache = self._pc()
        here = d / "other folder name.mp3"
        here.write_bytes(_AUDIO)
        cache.fingerprint(here)                     # the library load saw it
        self.assertEqual(cache.import_manual_pd(marks), (1, 1))
        self.assertEqual(cache.get_pd_highlights(here), [47.2, 75.65])
        self.assertTrue(cache.is_pd_manual(here))
        # …and it is stored, not only in memory.
        self.assertTrue(pdb.AudioCache().is_pd_manual(here))

    def test_a_retagged_copy_gets_them_through_the_audio_fingerprint(self):
        marks = self._marked_export()
        _, cache = self._pc()
        pdb._db().execute("INSERT INTO audio_fps (fp, afp) VALUES (?, ?)",
                          ("999_retagged", marks[0]["afp"]))
        cache.import_manual_pd(marks)
        row = pdb._db().execute("SELECT times, manual FROM pd_highlights WHERE fp = ?",
                                ("999_retagged",)).fetchone()
        self.assertEqual(row, ("[47.2, 75.65]", 1))

    def test_an_unknown_track_is_imported_but_not_counted_as_found(self):
        marks = self._marked_export()
        _, cache = self._pc()
        self.assertEqual(cache.import_manual_pd(marks), (1, 0))


if __name__ == "__main__":
    unittest.main()
