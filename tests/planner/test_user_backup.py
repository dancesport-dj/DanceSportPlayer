"""The rows no rescan can rebuild (in-app tag edits, hand-set PD marks) get a
small dated backup at start and again at quit, and a backup merges back in."""
import contextlib
import datetime as dt
import json
import shutil
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import planner.db as pdb


class UserBackupTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_user_backup_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        saved = (pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
        pdb.AUDIO_DB_FILE = self.dir / "scratch.db"
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False

        def restore():
            try:
                pdb._DB_LOCAL.conn.close()
            except Exception:
                pass
            pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED = saved
        self.addCleanup(restore)
        self.conn = pdb._db()
        self.backups = self.dir / "backups"

    def fill(self):
        c = self.conn
        c.execute("INSERT INTO tag_edits (fp, rating) VALUES ('fp1', 5)")
        c.execute("INSERT INTO pd_highlights (fp, times, manual) VALUES ('fp2', '[1,2,3]', 1)")
        c.execute("INSERT INTO pd_highlights (fp, times, manual) VALUES ('fp3', '[4,5,6]', 0)")
        c.execute("INSERT INTO audio_fps (fp, afp) VALUES ('fp2', 'a2')")
        c.execute("INSERT INTO audio_fps (fp, afp) VALUES ('fp9', 'a9')")
        c.execute("INSERT INTO loudness (fp, lufs) VALUES ('fp1', -18.0)")

    def tables(self, path: Path) -> dict:
        with contextlib.closing(sqlite3.connect(path)) as c:
            names = [r[0] for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            return {n: sorted(c.execute(f"SELECT * FROM {n}").fetchall()) for n in names}

    def test_backup_holds_only_the_rows_no_rescan_rebuilds(self):
        self.fill()
        out = pdb.backup_user_data(today=dt.date(2026, 10, 9))
        self.assertEqual(out, self.backups / "user-data-2026-10-09.db")
        got = self.tables(out)
        self.assertEqual(got["tag_edits"], [("fp1", 5, None, None, None, None)])
        self.assertEqual(got["pd_highlights"], [("fp2", "[1,2,3]", 1)])
        self.assertEqual(got["audio_fps"], [("fp2", "a2")])
        self.assertNotIn("loudness", got)

    def test_nothing_to_keep_writes_nothing(self):
        self.assertIsNone(pdb.backup_user_data(today=dt.date(2026, 10, 9)))
        self.assertFalse(self.backups.exists())

    def test_one_backup_per_day(self):
        self.fill()
        first = pdb.backup_user_data(today=dt.date(2026, 10, 9))
        stamp = first.stat().st_mtime_ns
        self.assertIsNone(pdb.backup_user_data(today=dt.date(2026, 10, 9)))
        self.assertEqual(first.stat().st_mtime_ns, stamp)

    def test_a_refresh_rewrites_todays_backup(self):
        """At quit the day's backup is written again, with what the session
        added: an evening's plays are safe the moment the app closes."""
        from planner import play_log
        self.fill()
        first = pdb.backup_user_data(today=dt.date(2026, 10, 9))
        play_log.record(dt.datetime(2026, 10, 9, 21, 5), "C:/m/a.mp3", "A", "a", "PD",
                        "Deck A", 120.0)
        again = pdb.backup_user_data(today=dt.date(2026, 10, 9), refresh=True)
        self.assertEqual(again, first)
        self.assertEqual(len(self.tables(again)["play_log"]), 1)
        self.assertEqual(len(list(self.backups.glob("user-data-*"))), 1)

    def test_a_failed_backup_never_stops_the_app(self):
        with mock.patch.object(pdb, "backup_user_data", side_effect=OSError("disk full")), \
                self.assertLogs("dancesport.db", "WARNING"):
            pdb.backup_safely(refresh=True)

    def test_rotation_keeps_the_newest_seven(self):
        self.fill()
        for day in range(1, 11):
            pdb.backup_user_data(today=dt.date(2026, 10, day))
        kept = sorted(p.name for p in self.backups.glob("user-data-*.db"))
        self.assertEqual(kept, [f"user-data-2026-10-{d:02d}.db" for d in range(4, 11)])

    def test_first_start_of_the_day_backs_up(self):
        self.fill()
        pdb._DB_LOCAL.conn.close()
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False
        pdb._db()
        self.assertEqual(len(list(self.backups.glob("user-data-*.db"))), 1)

    def test_restore_merges_and_follows_the_audio(self):
        self.fill()
        out = pdb.backup_user_data(today=dt.date(2026, 10, 9))
        c = self.conn
        c.execute("DELETE FROM tag_edits")
        c.execute("DELETE FROM pd_highlights")
        # A re-tagged copy of fp2 on this PC: same audio, new content key.
        c.execute("INSERT INTO audio_fps (fp, afp) VALUES ('fp2b', 'a2')")
        c.execute("INSERT INTO tag_edits (fp, rating) VALUES ('other', 3)")
        self.assertEqual(pdb.restore_user_data(out), (1, 1, 0))
        rows = dict(c.execute("SELECT fp, rating FROM tag_edits").fetchall())
        self.assertEqual(rows, {"fp1": 5, "other": 3})
        pd = {fp: (json.loads(t), m) for fp, t, m in
              c.execute("SELECT fp, times, manual FROM pd_highlights")}
        self.assertEqual(pd, {"fp2": ([1, 2, 3], 1), "fp2b": ([1, 2, 3], 1)})

    def test_the_play_log_is_backed_up_and_merged_back_once(self):
        from planner import play_log
        when = dt.datetime(2026, 10, 3, 20, 0)
        play_log.record(when, "C:/m/a.mp3", "A", "a", "LW", "Deck A", 180.0)
        out = pdb.backup_user_data(today=dt.date(2026, 10, 9))
        self.assertIsNotNone(out)
        self.assertEqual(len(self.tables(out)["play_log"]), 1)
        play_log.record(when.replace(hour=21), "C:/m/b.mp3", "B", "b", "TG", "Deck A", 180.0)
        # Already here: counted as nothing new, and not doubled.
        self.assertEqual(pdb.restore_user_data(out), (0, 0, 0))
        titles = [p.title for e in play_log.evenings() for p in play_log.plays(e)]
        self.assertEqual(titles, ["a", "b"])
        pdb._db().execute("DELETE FROM play_log WHERE title = 'a'")
        self.assertEqual(pdb.restore_user_data(out), (0, 0, 1))

    def test_restore_reads_a_backup_from_before_the_play_log(self):
        self.fill()
        out = pdb.backup_user_data(today=dt.date(2026, 10, 9))
        with contextlib.closing(sqlite3.connect(out)) as c:
            c.execute("DROP TABLE play_log")
            c.commit()
        self.assertEqual(pdb.restore_user_data(out), (1, 1, 0))

    def test_restore_refuses_a_file_that_is_no_backup(self):
        bad = self.dir / "bad.db"
        bad.write_text("not a database")
        with self.assertRaises(ValueError):
            pdb.restore_user_data(bad)


if __name__ == "__main__":
    unittest.main()
