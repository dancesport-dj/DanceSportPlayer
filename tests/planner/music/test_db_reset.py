#!/usr/bin/env python3
"""🗑 Reset database: each tick empties its own part of the DB, nothing else.

Run:  py -m unittest tests.planner.music.test_db_reset -v

Marcel asked for a button to reset the database, and for the dialog to ask
what goes: the tags read from the files, the audio analysis, the user's own
rows (tag edits, hand-set PD marks, play log). Whatever is picked, the user's
own rows are backed up first, so ♻ Restore can bring them back.
"""

import datetime
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_reset_"))

import planner.music.db as pdb
import planner.music.db_upkeep as upkeep
from tests.db_support import use_scratch_db


class ResetTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_reset_db_"))
        use_scratch_db(self, self.dir / "scratch.db")
        patch = mock.patch.object(upkeep, "_backup_folder", self.dir / "backups")
        patch.start()
        self.addCleanup(patch.stop)
        c = self.conn = pdb._db()
        c.execute("CREATE TABLE IF NOT EXISTS embeddings ("
                  "  fp TEXT NOT NULL, model TEXT NOT NULL, vec BLOB NOT NULL,"
                  "  PRIMARY KEY (fp, model))")
        fid = c.execute("INSERT INTO files (path) VALUES ('C:/a.mp3')").lastrowid
        c.execute("INSERT INTO fingerprints (file_id, mtime, fp) VALUES (?, 1, 'fp')", (fid,))
        c.execute("INSERT INTO scan_meta (ckey) VALUES ('fp::a')")
        c.execute("INSERT INTO global_meta (file_id, mtime) VALUES (?, 1)", (fid,))
        c.execute("INSERT INTO audio_fps (fp, afp) VALUES ('fp', 'afp')")
        c.execute("INSERT INTO playlist_index (root, pl_id, sig, mkeys) "
                  "VALUES ('D:/T', 'D:/T/a.m3u', 's', 'k')")
        c.execute("INSERT INTO app_meta (key, value) VALUES ('playlist_index_dance:D:/T', 'd')")
        c.execute("INSERT INTO app_meta (key, value) VALUES ('custom_source', 'TXXX:Mood')")
        c.execute("INSERT INTO features (fp, bpm) VALUES ('fp', 120)")
        c.execute("INSERT INTO embeddings (fp, model, vec) VALUES ('fp', 'mert', x'00')")
        c.execute("INSERT INTO loudness (fp, lufs) VALUES ('fp', -14)")
        c.execute("INSERT INTO pd_highlights (fp, times, manual) VALUES ('fp', '[1]', 0)")
        c.execute("INSERT INTO pd_highlights (fp, times, manual) VALUES ('fp2', '[2]', 1)")
        c.execute("INSERT INTO silences (fp, spans) VALUES ('fp', '[]')")
        c.execute("INSERT INTO waveforms (fp, peaks) VALUES ('fp', x'00')")
        c.execute("INSERT INTO vocals (fp, vocal_share) VALUES ('fp', 0.1)")
        c.execute("INSERT INTO noise (fp, floor_db) VALUES ('fp', -90)")
        c.execute("INSERT INTO tag_edits (fp, rating) VALUES ('fp', 5)")
        c.execute("INSERT INTO play_log (started_at, path) VALUES ('2026-10-20T20:00', 'C:/a.mp3')")

    def count(self, table, where="1"):
        return self.conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0]

    def test_the_tags_read_go_and_the_analysis_stays(self):
        upkeep.reset_database({"scan"})
        for table in ("files", "fingerprints", "scan_meta", "global_meta",
                      "audio_fps", "playlist_index"):
            self.assertEqual(self.count(table), 0, table)
        self.assertEqual(self.count("app_meta", "key LIKE 'playlist_index_dance:%'"), 0)
        self.assertEqual(self.count("features"), 1)
        self.assertEqual(self.count("tag_edits"), 1)

    def test_the_analysis_goes_and_the_hand_set_marks_stay(self):
        upkeep.reset_database({"analysis"})
        for table in ("features", "embeddings", "loudness", "silences", "waveforms",
                      "vocals", "noise"):
            self.assertEqual(self.count(table), 0, table)
        self.assertEqual(self.count("pd_highlights", "manual = 0"), 0)
        self.assertEqual(self.count("pd_highlights", "manual = 1"), 1)
        self.assertEqual(self.count("files"), 1)

    def test_the_users_own_rows_go_only_when_ticked(self):
        upkeep.reset_database({"scan", "analysis"})
        self.assertEqual(self.count("tag_edits"), 1)
        self.assertEqual(self.count("play_log"), 1)
        removed = upkeep.reset_database({"user"})
        for table in ("tag_edits", "play_log", "pd_highlights"):
            self.assertEqual(self.count(table), 0, table)
        self.assertEqual(removed["tag_edits"], 1)

    def test_settings_kept_in_the_db_survive_everything(self):
        upkeep.reset_database({"scan", "analysis", "user"})
        self.assertEqual(self.count("app_meta", "key = 'custom_source'"), 1)

    def test_the_users_own_rows_are_backed_up_first(self):
        upkeep.reset_database({"user"})
        bak = self.dir / "backups" / (__import__("platform").node() or "this-pc") / \
            f"user-data-{datetime.date.today().isoformat()}.db"
        self.assertTrue(bak.exists())
        with sqlite3.connect(bak) as b:
            self.assertEqual(b.execute("SELECT COUNT(*) FROM tag_edits").fetchone()[0], 1)
            self.assertEqual(b.execute("SELECT COUNT(*) FROM play_log").fetchone()[0], 1)

    def test_a_failed_backup_resets_nothing(self):
        with mock.patch.object(upkeep, "backup_user_data", side_effect=OSError("full")):
            with self.assertRaises(OSError):
                upkeep.reset_database({"user"})
        self.assertEqual(self.count("tag_edits"), 1)

    def test_an_unknown_part_is_refused(self):
        with self.assertRaises(ValueError):
            upkeep.reset_database({"everything"})
        self.assertEqual(self.count("files"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
