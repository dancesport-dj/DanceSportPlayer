#!/usr/bin/env python3
"""🧹 Clean up database: what it must throw away, and what it must not.

Run:  py -m unittest tests.planner.test_db_maintenance -v

The cleanup deletes rows and then VACUUMs, so it points at a scratch database
here — `AUDIO_DB_FILE` is a module global with no env override, and the real one
is the user's whole analysed library.

The rule it follows: a row is stale when nothing on disk points at it any more.
For the content-addressed tables that means "no live fingerprint", for the
playlist index "no such folder", and the expensive rows of a file that is still
there must survive untouched — re-measuring them costs hours.
"""

import os
import tempfile
import threading
import unittest
from pathlib import Path

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_maint_"))

import planner.db as pdb  # noqa: E402


class MaintenanceTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_maint_db_"))
        self._saved = (pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
        pdb.AUDIO_DB_FILE = self.dir / "scratch.db"
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False
        self.addCleanup(self._restore)
        self.conn = pdb._db()
        # embeddings lives in planner/embeddings.py, so a bare DB has no such table
        self.conn.execute("CREATE TABLE IF NOT EXISTS embeddings ("
                          "  fp TEXT NOT NULL, model TEXT NOT NULL, vec BLOB NOT NULL,"
                          "  PRIMARY KEY (fp, model))")

    def _restore(self):
        try:
            pdb._DB_LOCAL.conn.close()
        except Exception:
            pass
        pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED = self._saved

    # ── fixtures ────────────────────────────────────────────────────────────
    def _track(self, name: str, fp: str, on_disk: bool = True) -> str:
        """A registered file, with the analysis a real one accumulates."""
        path = self.dir / name
        if on_disk:
            path.write_bytes(b"music")
        fid = self.conn.execute("INSERT INTO files (path) VALUES (?)",
                                (str(path),)).lastrowid
        self.conn.execute(
            "INSERT INTO fingerprints (file_id, mtime, fp) VALUES (?, ?, ?)",
            (fid, 1.0, fp))
        self.conn.execute("INSERT INTO features (fp, bpm, centroid, rms, mfcc) "
                          "VALUES (?, ?, ?, ?, ?)", (fp, 120.0, 1.0, 0.5, b"\x00" * 8))
        self.conn.execute("INSERT INTO loudness (fp, lufs) VALUES (?, ?)", (fp, -14.0))
        self.conn.execute("INSERT INTO audio_fps (fp, afp) VALUES (?, ?)",
                          (fp, f"audio-of-{fp}"))
        self.conn.execute("INSERT INTO embeddings (fp, model, vec) VALUES (?, ?, ?)",
                          (fp, "chroma", b"\x00" * 16))
        return str(path)

    def _playlist_root(self, name: str, on_disk: bool) -> str:
        root = self.dir / name
        if on_disk:
            root.mkdir()
        self.conn.execute(
            "INSERT INTO playlist_index (root, pl_id, sig, cls, mkeys) "
            "VALUES (?, ?, ?, ?, ?)", (str(root), f"{root}/a.m3u", "sig", None, "k"))
        self.conn.execute("INSERT INTO app_meta (key, value) VALUES (?, ?)",
                          (f"playlist_index_dance:{root}", "3:digest"))
        return str(root)

    def _rows(self, table: str) -> list:
        return self.conn.execute(f"SELECT * FROM {table}").fetchall()

    def _digest_keys(self) -> list:
        return [k for (k,) in self.conn.execute(
            "SELECT key FROM app_meta WHERE key LIKE 'playlist_index_dance:%'")]

    # ── content-addressed side of the DB ────────────────────────────────────
    def test_a_deleted_track_takes_its_whole_analysis_with_it(self):
        self._track("gone.mp3", "fp-dead", on_disk=False)
        res = pdb.db_maintenance()
        for table in ("features", "loudness", "embeddings", "fingerprints", "files"):
            self.assertEqual(self._rows(table), [], f"{table} kept a dead row")
        self.assertEqual(res["removed"]["files"], 1)

    def test_the_audio_fingerprint_of_a_deleted_track_goes_too(self):
        """It only exists to re-attach that fp's rows, which have just been dropped."""
        self._track("gone.mp3", "fp-dead", on_disk=False)
        res = pdb.db_maintenance()
        self.assertEqual(self._rows("audio_fps"), [])
        self.assertEqual(res["removed"]["audio_fps"], 1)

    def test_a_track_that_is_still_there_keeps_everything(self):
        """Re-measuring costs hours — over-deleting is the expensive mistake here."""
        self._track("here.mp3", "fp-live")
        pdb.db_maintenance()
        for table in ("features", "loudness", "embeddings", "audio_fps",
                      "fingerprints", "files"):
            self.assertEqual(len(self._rows(table)), 1, f"{table} lost a live row")

    # ── playlist index ──────────────────────────────────────────────────────
    def test_a_playlist_folder_that_is_gone_loses_its_index(self):
        self._playlist_root("old_tournaments", on_disk=False)
        res = pdb.db_maintenance()
        self.assertEqual(self._rows("playlist_index"), [])
        self.assertEqual(res["removed"]["playlist_index"], 1)

    def test_the_dance_digest_does_not_outlive_the_index_it_belongs_to(self):
        """The immortal row: the digest key is only ever cleaned by walking the
        roots still present IN playlist_index, so one whose rows were already
        dropped could never be reached again (1,285 of these had piled up)."""
        root = self.dir / "vanished"
        self.conn.execute("INSERT INTO app_meta (key, value) VALUES (?, ?)",
                          (f"playlist_index_dance:{root}", "3:digest"))
        res = pdb.db_maintenance()
        self.assertEqual(self._digest_keys(), [])
        self.assertEqual(res["removed"]["app_meta"], 1)

    def test_a_playlist_folder_that_is_still_there_is_left_alone(self):
        self._playlist_root("turniere", on_disk=True)
        pdb.db_maintenance()
        self.assertEqual(len(self._rows("playlist_index")), 1)
        self.assertEqual(len(self._digest_keys()), 1)

    def test_settings_rows_are_not_playlist_keys(self):
        """app_meta also holds real settings — only the path-keyed ones are pruned."""
        self.conn.execute("INSERT OR REPLACE INTO app_meta (key, value) VALUES (?, ?)",
                          ("dance_detect_version", "7"))
        pdb.db_maintenance()
        self.assertEqual(
            self.conn.execute("SELECT value FROM app_meta WHERE key = ?",
                              ("dance_detect_version",)).fetchone()[0], "7")

    def test_an_unplugged_drive_is_not_a_deleted_folder(self):
        """The playlist tree lives on an external drive — "not there" while the
        drive is out must not throw away a whole tournament index."""
        free = next((d for d in "QYZ" if not Path(f"{d}:\\").exists()), None)
        if free is None:
            self.skipTest("no free drive letter to stand in for an unplugged disk")
        self.assertFalse(pdb._vanished(Path(f"{free}:\\Turniere")))
        self.assertTrue(pdb._vanished(self.dir / "definitely-not-here"))

    def test_build_all_keeps_the_rows_of_a_track_on_an_unplugged_drive(self):
        """🔨 Build ALL runs cleanup_orphans with no abort guard, and it took
        "not there" for "deleted" — every file, fingerprint and metadata row
        of the music drive went the moment it was run with F: out."""
        free = next((d for d in "QYZ" if not Path(f"{d}:\\").exists()), None)
        if free is None:
            self.skipTest("no free drive letter to stand in for an unplugged disk")
        fid = self.conn.execute("INSERT INTO files (path) VALUES (?)",
                                (f"{free}:\\tanzcds\\LW\\Mondschein.mp3",)).lastrowid
        self.conn.execute(
            "INSERT INTO fingerprints (file_id, mtime, fp) VALUES (?, ?, ?)",
            (fid, 1.0, "fp-away"))
        self._track("gone.mp3", "fp-dead", on_disk=False)
        removed = pdb.cleanup_orphans()
        self.assertEqual(removed["files"], 1)
        self.assertEqual([fp for (_i, _m, fp) in
                          self.conn.execute("SELECT file_id, mtime, fp FROM fingerprints")],
                         ["fp-away"])

    # ── the guard that protects the whole library ───────────────────────────
    def test_an_unmounted_music_drive_aborts_instead_of_wiping_the_library(self):
        for i in range(200):
            self._track(f"gone{i}.mp3", f"fp{i}", on_disk=False)
        with self.assertRaises(RuntimeError):
            pdb.db_maintenance()
        self.assertEqual(len(self._rows("features")), 200)

    def test_it_reports_what_it_freed(self):
        self._track("here.mp3", "fp-live")
        res = pdb.db_maintenance()
        self.assertGreater(res["size_before"], 0)
        self.assertGreater(res["size_after"], 0)
        self.assertIn("audio_fps", res["removed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
