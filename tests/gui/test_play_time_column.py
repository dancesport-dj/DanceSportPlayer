#!/usr/bin/env python3
"""The ⏱ column keeps the file's own length, amber when it will not all play.

Run:  py -m unittest tests.gui.test_play_time_column -v

`hochzeit_aktuell_v9.mp3` is 5:30 in the tag and 4:20 on the floor: the last
seventy seconds are dead air, and the 🔇 stillness skip ends the song there.
The cell keeps saying 5:30 — that is the number on the file, and replacing it
hides what happened — but it turns orange, which is the flag that silence was
found. The time it really plays is in the tooltip, and on the player, where it
is acted on.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_playtime_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.common import _C_LEN_WARN_FG  # noqa: E402
from shared.columns import _COL_LEN, _COL_TITLE
from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.models import MusicEntry  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

_TRIMMED = MusicEntry(path=Path(r"C:\music\hochzeit_aktuell_v9.mp3"),
                      title="Hochzeit aktuell v9", dance="DISCOFOX",
                      duration=330)
_WHOLE = MusicEntry(path=Path(r"C:\music\df2.mp3"), title="Kein Leerlauf",
                    dance="DISCOFOX", duration=200)


class PlayTimeColumnTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _table(self, play_secs=None, edge=None):
        t = PlaylistTable()
        self.addCleanup(reap_widget, t)
        if play_secs is not None:
            t._play_secs_cb = play_secs
            # Default: whatever was trimmed came off one edge, so the old
            # single-argument cases still describe a flag-worthy track.
            t._edge_silence_cb = edge or (
                lambda e: float(max(0, (e.duration or 0)
                                    - (play_secs(e) or e.duration or 0))))
        t.load_warmup([_TRIMMED, _WHOLE], "Party", style="", dance_class="S",
                      relax=True, play_cb=None, suggester=None)
        return t

    def _len_cell(self, t: PlaylistTable, title: str):
        for row in range(t.rowCount()):
            it = t.item(row, _COL_TITLE)
            if it is not None and title in it.text():
                return t.item(row, _COL_LEN)
        self.fail(f"no row for {title!r}")

    def test_the_file_length_is_shown_not_the_playing_time(self):
        t = self._table(lambda e: 260 if "hochzeit" in e.path.name else None)
        self.assertEqual(self._len_cell(t, "Hochzeit aktuell v9").text(), "5:30")

    def test_a_trimmed_track_reads_amber(self):
        t = self._table(lambda e: 260 if "hochzeit" in e.path.name else None)
        cell = self._len_cell(t, "Hochzeit aktuell v9")
        self.assertEqual(cell.foreground().color(), _C_LEN_WARN_FG)

    def test_the_playing_time_is_what_the_tooltip_says(self):
        t = self._table(lambda e: 260 if "hochzeit" in e.path.name else None)
        tip = self._len_cell(t, "Hochzeit aktuell v9").toolTip()
        self.assertIn("4:20", tip)

    def test_a_track_that_plays_in_full_is_left_alone(self):
        t = self._table(lambda e: 200 if "df2" in e.path.name else None)
        cell = self._len_cell(t, "Kein Leerlauf")
        self.assertEqual(cell.text(), "3:20")
        self.assertNotEqual(cell.foreground().color(), _C_LEN_WARN_FG)

    def test_an_unprobed_track_shows_its_file_length_in_black(self):
        t = self._table()
        cell = self._len_cell(t, "Hochzeit aktuell v9")
        self.assertEqual(cell.text(), "5:30")
        self.assertNotEqual(cell.foreground().color(), _C_LEN_WARN_FG)


class ShortEdgesAreNotWorthFlaggingTest(unittest.TestCase):
    """The flag means "this will not all play". Nearly every mastered file has
    a second or two of room tone at an edge, and flagging those painted the
    party list end to end — so it starts at five seconds on ONE edge."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _cell(self, play, edge):
        t = PlaylistTable()
        self.addCleanup(reap_widget, t)
        t._play_secs_cb = lambda e: play if "hochzeit" in e.path.name else None
        t._edge_silence_cb = lambda e: edge if "hochzeit" in e.path.name else 0.0
        t.load_warmup([_TRIMMED, _WHOLE], "Party", style="", dance_class="S",
                      relax=True, play_cb=None, suggester=None)
        for row in range(t.rowCount()):
            it = t.item(row, _COL_TITLE)
            if it is not None and "Hochzeit" in it.text():
                return t.item(row, _COL_LEN)
        self.fail("no row for the trimmed track")

    def test_three_seconds_of_room_tone_stays_black(self):
        self.assertNotEqual(self._cell(327, 3.0).foreground().color(), _C_LEN_WARN_FG)

    def test_five_seconds_is_where_the_flag_starts(self):
        self.assertEqual(self._cell(325, 5.0).foreground().color(), _C_LEN_WARN_FG)

    def test_a_minute_of_dead_air_is_still_flagged(self):
        self.assertEqual(self._cell(260, 70.0).foreground().color(), _C_LEN_WARN_FG)

    def test_the_tooltip_reports_the_trim_even_when_it_is_not_flagged(self):
        """The cell is black, but the playing time is still worth knowing."""
        self.assertIn("5:27", self._cell(327, 3.0).toolTip())

    def test_two_short_edges_do_not_add_up_to_a_flag(self):
        """Three seconds at each end is two ordinary edges, not a track that
        stops early — the rule is five seconds on ONE of them."""
        self.assertNotEqual(self._cell(324, 3.0).foreground().color(), _C_LEN_WARN_FG)


class EdgeSilenceFromTheCacheTest(unittest.TestCase):
    """The callback the window hands the table: longest edge, cached only."""

    def _win(self, spans):
        from gui.main_music import MusicCheckMixin

        class Win(MusicCheckMixin):
            pass
        w = Win()
        w._cache = PlaySecsFromTheCacheTest._Cache(spans)
        return w

    def test_the_tail_is_measured(self):
        self.assertAlmostEqual(self._win([[260, 330]])._track_edge_silence(_TRIMMED),
                               70.0)

    def test_the_longer_of_the_two_ends_wins(self):
        got = self._win([[0, 6], [310, 330]])._track_edge_silence(_TRIMMED)
        self.assertAlmostEqual(got, 20.0)

    def test_stillness_in_the_middle_is_not_an_edge(self):
        self.assertEqual(self._win([[120, 180]])._track_edge_silence(_TRIMMED), 0.0)

    def test_a_track_that_was_never_probed_flags_nothing(self):
        self.assertEqual(self._win(None)._track_edge_silence(_TRIMMED), 0.0)


class PlaySecsFromTheCacheTest(unittest.TestCase):
    """The callback the window hands the table: cached spans only, no probe."""

    class _Cache:
        def __init__(self, spans):
            self.spans = spans
            self.asked = []

        def get_silences(self, path, touch_disk=True):
            self.asked.append(Path(path))
            self.touched_disk = touch_disk
            return self.spans

    def _win(self, spans):
        from gui.main_music import MusicCheckMixin

        class Win(MusicCheckMixin):
            pass
        w = Win()
        w._cache = self._Cache(spans)
        return w

    def test_dead_air_at_the_end_comes_off_the_play_time(self):
        self.assertEqual(self._win([[260, 330]])._track_play_secs(_TRIMMED), 260)

    def test_the_repaint_lookup_does_not_touch_the_disk(self):
        w = self._win([[260, 330]])
        w._track_play_secs(_TRIMMED)
        self.assertFalse(w._cache.touched_disk)

    def test_a_track_that_was_never_probed_has_no_play_time(self):
        self.assertIsNone(self._win(None)._track_play_secs(_TRIMMED))

    def test_without_a_cache_nothing_is_claimed(self):
        w = self._win([[260, 330]])
        w._cache = None
        self.assertIsNone(w._track_play_secs(_TRIMMED))


if __name__ == "__main__":
    unittest.main(verbosity=2)
