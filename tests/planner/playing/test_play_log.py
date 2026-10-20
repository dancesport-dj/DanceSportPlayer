"""📜 The play log: what actually ran, grouped into evenings, as a CSV report."""
import contextlib
import csv
import datetime as dt
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from planner.playing import play_log
from tests.db_support import use_scratch_db


def at(day, hh, mm, ss=0):
    return dt.datetime(2026, 10, day, hh, mm, ss)


class PlayLogTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_play_log_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")

    def play(self, when, title, dance="LW", length=180.0, list_name="Deck A",
             composer=""):
        play_log.record(when, Path(rf"C:\music\{title}.mp3"), "Artist " + title,
                        title, dance, list_name, length, composer=composer)

    def test_an_evening_past_midnight_stays_one_evening(self):
        self.play(at(3, 20, 0), "a")
        self.play(at(3, 23, 50), "b")
        self.play(at(4, 0, 40), "c")
        self.play(at(4, 19, 0), "d")      # 18 h later: the next evening
        got = play_log.evenings()
        self.assertEqual([(e.start, e.end, e.count) for e in got],
                         [(at(4, 19, 0), at(4, 19, 0), 1),
                          (at(3, 20, 0), at(4, 0, 40), 3)])
        self.assertEqual([p.title for p in play_log.plays(got[1])], ["a", "b", "c"])

    def test_the_same_play_is_logged_once(self):
        self.play(at(3, 20, 0), "a")
        self.play(at(3, 20, 0), "a")
        self.assertEqual(play_log.evenings()[0].count, 1)

    def test_duration_is_the_gap_to_the_next_title_at_most_the_track(self):
        self.play(at(3, 20, 0, 0), "cut", length=180.0)    # cut at 1:30
        self.play(at(3, 20, 1, 30), "pause", length=100.0)  # 10 min break after
        self.play(at(3, 20, 11, 30), "last", length=95.5)
        plays = play_log.plays(play_log.evenings()[0])
        self.assertEqual(play_log.durations(plays), [90.0, 100.0, 95.5])

    def test_delete_removes_only_that_evening(self):
        self.play(at(3, 20, 0), "a")
        self.play(at(4, 20, 0), "b")
        play_log.delete(play_log.evenings()[0])
        self.assertEqual([p.title for e in play_log.evenings()
                          for p in play_log.plays(e)], ["a"])

    def test_csv_for_excel(self):
        self.play(at(3, 20, 0, 0), "Moon River", dance="WW", length=150.0,
                  list_name="Hauptgruppe S", composer="Henry Mancini")
        self.play(at(3, 20, 3, 5), "Señorita; live", dance="SA", length=65.0)
        out = self.dir / "evening.csv"
        play_log.to_csv(play_log.plays(play_log.evenings()[0]), out)
        raw = out.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        with out.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f, delimiter=";"))
        self.assertEqual(rows[0], ["Date", "Start", "Artist", "Title", "Composer",
                                   "Dance", "List", "Duration"])
        self.assertEqual(rows[1][:5], ["2026-10-03", "20:00:00", "Artist Moon River",
                                       "Moon River", "Henry Mancini"])
        self.assertEqual(rows[1][6:], ["Hauptgruppe S", "2:30"])
        self.assertEqual(rows[2][3:5], ["Señorita; live", ""])
        self.assertEqual(rows[2][7], "1:05")

    def test_the_composer_is_kept_with_the_play(self):
        """A GEMA report names who wrote each title, not only who played it."""
        self.play(at(3, 20, 0), "Moon River", composer="Henry Mancini")
        self.play(at(3, 20, 3), "b")
        got = play_log.plays(play_log.evenings()[0])
        self.assertEqual([p.composer for p in got], ["Henry Mancini", ""])


class OldPlayLogTest(unittest.TestCase):
    """A database from before the composer column keeps its plays."""

    def test_the_column_is_added_and_the_plays_stay(self):
        folder = Path(tempfile.mkdtemp(prefix="dp_play_log_old_"))
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        db = folder / "old.db"
        with contextlib.closing(sqlite3.connect(db)) as c:
            c.execute("CREATE TABLE play_log ("
                      "  id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, path TEXT NOT NULL,"
                      "  artist TEXT, title TEXT, dance TEXT, list_name TEXT, length REAL,"
                      "  UNIQUE (started_at, path))")
            c.execute("INSERT INTO play_log (started_at, path, artist, title, dance, "
                      "list_name, length) VALUES ('2026-10-03T20:00:00', 'C:/m/a.mp3', "
                      "'A', 'a', 'LW', 'Deck A', 180)")
            c.commit()
        use_scratch_db(self, db)
        play_log.record(at(3, 20, 3), "C:/m/b.mp3", "B", "b", "TG", "Deck A", 120.0,
                        composer="Gade")
        got = play_log.plays(play_log.evenings()[0])
        self.assertEqual([(p.title, p.composer) for p in got], [("a", ""), ("b", "Gade")])


if __name__ == "__main__":
    unittest.main()
