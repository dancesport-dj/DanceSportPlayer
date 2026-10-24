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

import planner.music.db as pdb
import planner.music.db_upkeep as upkeep
from tests.db_support import use_scratch_db


class UserBackupTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_user_backup_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
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
        out = upkeep.backup_user_data(today=dt.date(2026, 10, 9))
        self.assertEqual(out, self.backups / "user-data-2026-10-09.db")
        got = self.tables(out)
        self.assertEqual(got["tag_edits"], [("fp1", 5, *[None] * 10)])
        self.assertEqual(got["pd_highlights"], [("fp2", "[1,2,3]", 1)])
        self.assertEqual(got["audio_fps"], [("fp2", "a2")])
        self.assertNotIn("loudness", got)

    def test_nothing_to_keep_writes_nothing(self):
        self.assertIsNone(upkeep.backup_user_data(today=dt.date(2026, 10, 9)))
        self.assertFalse(self.backups.exists())

    def test_one_backup_per_day(self):
        self.fill()
        first = upkeep.backup_user_data(today=dt.date(2026, 10, 9))
        stamp = first.stat().st_mtime_ns
        self.assertIsNone(upkeep.backup_user_data(today=dt.date(2026, 10, 9)))
        self.assertEqual(first.stat().st_mtime_ns, stamp)

    def test_a_refresh_rewrites_todays_backup(self):
        """At quit the day's backup is written again, with what the session
        added: an evening's plays are safe the moment the app closes."""
        from planner.playing import play_log
        self.fill()
        first = upkeep.backup_user_data(today=dt.date(2026, 10, 9))
        play_log.record(dt.datetime(2026, 10, 9, 21, 5), "C:/m/a.mp3", "A", "a", "PD",
                        "Deck A", 120.0)
        again = upkeep.backup_user_data(today=dt.date(2026, 10, 9), refresh=True)
        self.assertEqual(again, first)
        self.assertEqual(len(self.tables(again)["play_log"]), 1)
        self.assertEqual(len(list(self.backups.glob("user-data-*"))), 1)

    def test_a_failed_backup_leaves_no_part_file(self):
        self.fill()
        replace = mock.patch.object(upkeep.os, "replace", side_effect=OSError("locked"))
        with replace, self.assertRaises(OSError):
            upkeep.backup_user_data(today=dt.date(2026, 10, 9))
        self.assertEqual(list(self.backups.glob("*.part")), [])

    def test_a_failed_backup_never_stops_the_app(self):
        with mock.patch.object(upkeep, "backup_user_data", side_effect=OSError("disk full")), \
                self.assertLogs("dancesport.db", "WARNING"):
            upkeep.backup_safely(refresh=True)

    def test_rotation_keeps_the_newest_seven(self):
        self.fill()
        for day in range(1, 11):
            upkeep.backup_user_data(today=dt.date(2026, 10, day))
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
        out = upkeep.backup_user_data(today=dt.date(2026, 10, 9))
        c = self.conn
        c.execute("DELETE FROM tag_edits")
        c.execute("DELETE FROM pd_highlights")
        # A re-tagged copy of fp2 on this PC: same audio, new content key.
        c.execute("INSERT INTO audio_fps (fp, afp) VALUES ('fp2b', 'a2')")
        c.execute("INSERT INTO tag_edits (fp, rating) VALUES ('other', 3)")
        self.assertEqual(upkeep.restore_user_data(out), (1, 1, 0))
        rows = dict(c.execute("SELECT fp, rating FROM tag_edits").fetchall())
        self.assertEqual(rows, {"fp1": 5, "other": 3})
        pd = {fp: (json.loads(t), m) for fp, t, m in
              c.execute("SELECT fp, times, manual FROM pd_highlights")}
        self.assertEqual(pd, {"fp2": ([1, 2, 3], 1), "fp2b": ([1, 2, 3], 1)})

    def test_the_play_log_is_backed_up_and_merged_back_once(self):
        from planner.playing import play_log
        when = dt.datetime(2026, 10, 3, 20, 0)
        play_log.record(when, "C:/m/a.mp3", "A", "a", "LW", "Deck A", 180.0)
        out = upkeep.backup_user_data(today=dt.date(2026, 10, 9))
        self.assertIsNotNone(out)
        self.assertEqual(len(self.tables(out)["play_log"]), 1)
        play_log.record(when.replace(hour=21), "C:/m/b.mp3", "B", "b", "TG", "Deck A", 180.0)
        # Already here: counted as nothing new, and not doubled.
        self.assertEqual(upkeep.restore_user_data(out), (0, 0, 0))
        titles = [p.title for e in play_log.evenings() for p in play_log.plays(e)]
        self.assertEqual(titles, ["a", "b"])
        pdb._db().execute("DELETE FROM play_log WHERE title = 'a'")
        self.assertEqual(upkeep.restore_user_data(out), (0, 0, 1))

    def test_the_composer_goes_into_the_backup_and_back(self):
        from planner.playing import play_log
        play_log.record(dt.datetime(2026, 10, 3, 20, 0), "C:/m/a.mp3", "A", "a", "LW",
                        "Deck A", 180.0, composer="Gade")
        out = upkeep.backup_user_data(today=dt.date(2026, 10, 9))
        pdb._db().execute("DELETE FROM play_log")
        self.assertEqual(upkeep.restore_user_data(out), (0, 0, 1))
        got = [p.composer for e in play_log.evenings() for p in play_log.plays(e)]
        self.assertEqual(got, ["Gade"])

    def test_restore_reads_a_backup_from_before_the_composer(self):
        from planner.playing import play_log
        play_log.record(dt.datetime(2026, 10, 3, 20, 0), "C:/m/a.mp3", "A", "a", "LW",
                        "Deck A", 180.0)
        out = upkeep.backup_user_data(today=dt.date(2026, 10, 9))
        with contextlib.closing(sqlite3.connect(out)) as c:
            c.execute("ALTER TABLE play_log DROP COLUMN composer")
            c.commit()
        pdb._db().execute("DELETE FROM play_log")
        self.assertEqual(upkeep.restore_user_data(out), (0, 0, 1))

    def test_restore_reads_a_backup_from_before_the_play_log(self):
        self.fill()
        out = upkeep.backup_user_data(today=dt.date(2026, 10, 9))
        with contextlib.closing(sqlite3.connect(out)) as c:
            c.execute("DROP TABLE play_log")
            c.commit()
        self.assertEqual(upkeep.restore_user_data(out), (1, 1, 0))

    def test_restore_refuses_a_file_that_is_no_backup(self):
        bad = self.dir / "bad.db"
        bad.write_text("not a database")
        with self.assertRaises(ValueError):
            upkeep.restore_user_data(bad)


class BackupFolderTest(unittest.TestCase):
    """Settings can send the backups to a folder of one's own - a Dropbox
    folder, so they live off this PC."""

    setUp = UserBackupTest.setUp
    fill = UserBackupTest.fill

    def configure(self, folder):
        self.addCleanup(upkeep.apply_settings, {})
        upkeep.apply_settings({"backup_dir": str(folder)})

    def test_a_configured_folder_takes_the_backups(self):
        dropbox = self.dir / "Dropbox" / "DancePlaylist"
        self.configure(dropbox)
        self.fill()
        with mock.patch.object(upkeep.platform, "node", return_value="LAPTOP"):
            out = upkeep.backup_user_data(today=dt.date(2026, 10, 9))
        self.assertEqual(out, dropbox / "LAPTOP" / "user-data-2026-10-09.db")
        self.assertFalse(self.backups.exists())

    def test_two_pcs_sharing_the_folder_keep_their_own(self):
        """Dropbox syncs the folder to every PC: one PC's backup of the day must
        not overwrite another's, nor its rotation delete them."""
        dropbox = self.dir / "Dropbox"
        self.configure(dropbox)
        self.fill()
        with mock.patch.object(upkeep.platform, "node", return_value="DESKTOP"):
            theirs = upkeep.backup_user_data(today=dt.date(2026, 10, 9))
        with mock.patch.object(upkeep.platform, "node", return_value="LAPTOP"):
            for day in range(9, 20):
                upkeep.backup_user_data(today=dt.date(2026, 10, day))
        self.assertTrue(theirs.exists())
        self.assertEqual(len(list((dropbox / "LAPTOP").glob("user-data-*.db"))),
                         upkeep.BACKUPS_KEPT)

    def test_an_empty_setting_keeps_them_next_to_the_database(self):
        self.configure("  ")
        self.fill()
        out = upkeep.backup_user_data(today=dt.date(2026, 10, 9))
        self.assertEqual(out, self.backups / "user-data-2026-10-09.db")


if __name__ == "__main__":
    unittest.main()
