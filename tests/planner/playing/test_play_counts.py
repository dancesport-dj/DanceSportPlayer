"""🔁 How often a title has played today, in any list.

Run:  py -m unittest tests.planner.playing.test_play_counts -v

A tester: "Zähler zur Anzeige wie oft (heute) schon ein bestimmter Titel
gespielt wurde … Ein Reset soll ebenfalls möglich sein. Der Zähler soll auch
dann hochzählen wenn ein bestimmter Titel in einer anderen Playlist gespielt
wurde - also Titel-spezifisch". The count is read off the 📜 play log, so a
play is what the log calls one (heard 10 s in playing mode). Marcel: "play
count for day is 24h not 4h" — today is the last 24 hours, not the log's
evening.
"""
import datetime as dt
import shutil
import tempfile
import unittest
from pathlib import Path

from planner.playing import play_counts, play_log
from tests.db_support import use_scratch_db

NOW = dt.datetime(2026, 10, 24, 0, 30)


def ago(minutes):
    return NOW - dt.timedelta(minutes=minutes)


def track(name):
    return Path(rf"C:\music\{name}.mp3")


class PlayCountsTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_play_counts_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
        self.addCleanup(play_counts.clear)

    def play(self, when, name, list_name="Deck A"):
        play_log.record(when, track(name), "", name, "LW", list_name, 180.0)

    def test_every_list_counts_for_the_same_title(self):
        self.play(ago(90), "waltz", "Deck A")
        self.play(ago(60), "waltz", "Deck B")
        self.play(ago(30), "tango", "Party")
        play_counts.load(NOW)
        self.assertEqual(play_counts.count(track("waltz"), NOW), 2)
        self.assertEqual(play_counts.count(track("tango"), NOW), 1)
        self.assertEqual(play_counts.count(track("samba"), NOW), 0)

    def test_the_file_is_the_title_whatever_its_spelling(self):
        self.play(ago(30), "waltz")
        play_counts.load(NOW)
        self.assertEqual(play_counts.count(Path(r"c:\MUSIC\Waltz.mp3"), NOW), 1)

    def test_a_long_break_inside_the_day_still_counts(self):
        # Not the log's 4 h evening: a morning play and an evening play are
        # the same day.
        self.play(ago(60 * 10), "waltz")
        self.play(ago(10), "waltz")
        play_counts.load(NOW)
        self.assertEqual(play_counts.count(track("waltz"), NOW), 2)

    def test_a_play_over_24_hours_old_does_not_count(self):
        self.play(ago(60 * 24 + 1), "waltz")
        self.play(ago(60 * 23), "tango")
        play_counts.load(NOW)
        self.assertEqual(play_counts.count(track("waltz"), NOW), 0)
        self.assertEqual(play_counts.count(track("tango"), NOW), 1)

    def test_a_play_counts_up_at_once(self):
        play_counts.load(NOW)
        play_counts.bump(track("waltz"), ago(5))
        play_counts.bump(track("waltz"), NOW)
        self.assertEqual(play_counts.count(track("waltz"), NOW), 2)

    def test_a_play_drops_out_a_day_after_it_ran(self):
        play_counts.load(NOW)
        play_counts.bump(track("waltz"), NOW)
        later = NOW + dt.timedelta(hours=24, minutes=1)
        self.assertEqual(play_counts.count(track("waltz"), later), 0)
        self.assertFalse(play_counts.any_counted(later))

    def test_reset_sets_every_counter_back_to_zero(self):
        self.play(ago(30), "waltz")
        play_counts.load(NOW)
        play_counts.reset(NOW)
        self.assertEqual(play_counts.count(track("waltz"), NOW), 0)
        self.assertFalse(play_counts.any_counted(NOW))

    def test_reset_keeps_the_play_log(self):
        # The log is the music-rights report; the counter is only a display.
        self.play(ago(30), "waltz")
        play_counts.load(NOW)
        play_counts.reset(NOW)
        self.assertEqual(play_log.evenings()[0].count, 1)

    def test_a_reset_survives_a_restart(self):
        self.play(ago(30), "waltz")
        play_counts.reset(ago(20))
        self.play(ago(10), "waltz")
        play_counts.clear()
        play_counts.load(NOW)
        self.assertEqual(play_counts.count(track("waltz"), NOW), 1)

    def test_without_a_database_nothing_is_counted(self):
        play_counts.clear()
        self.assertEqual(play_counts.count(track("waltz"), NOW), 0)


if __name__ == "__main__":
    unittest.main()
