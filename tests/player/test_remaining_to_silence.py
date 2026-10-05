#!/usr/bin/env python3
"""While the music runs, the countdown ends where the music does.

Run:  py -m unittest tests.player.test_remaining_to_silence -v

`hochzeit_aktuell_v9.mp3` carries a minute of dead air behind the last note,
and the 🔇 stillness skip ends the song there — but the big player counted
down to the end of the FILE, so the operator saw a minute that would never be
danced. The trailing silence is a stop like any other: it arms the same limit
the ⏳ timed cut uses, and the earlier of the two wins.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_remain_"))

from planner.checks import trailing_silence_secs  # noqa: E402
from player.playback_state import PlaybackState  # noqa: E402


class TrailingSilenceTest(unittest.TestCase):
    """Where the last note is — the same edge the 🔇 skip acts on."""

    def test_dead_air_behind_the_last_note_is_where_it_ends(self):
        self.assertEqual(trailing_silence_secs(330, [[260, 330]]), 260)

    def test_a_span_that_stops_just_short_of_the_end_still_counts(self):
        # The probe rarely runs dead to the last sample; _TAIL_GAP covers it.
        self.assertEqual(trailing_silence_secs(330, [[260, 329]]), 260)

    def test_stillness_in_the_middle_is_played_as_recorded(self):
        self.assertIsNone(trailing_silence_secs(330, [[120, 160]]))

    def test_a_silent_intro_is_not_an_ending(self):
        self.assertIsNone(trailing_silence_secs(330, [[0, 8]]))

    def test_a_blink_of_quiet_at_the_end_is_not_worth_stopping_for(self):
        self.assertIsNone(trailing_silence_secs(330, [[329, 330]]))

    def test_a_track_that_was_never_probed_ends_where_it_ends(self):
        self.assertIsNone(trailing_silence_secs(330, None))
        self.assertIsNone(trailing_silence_secs(330, []))

    def test_no_length_no_answer(self):
        self.assertIsNone(trailing_silence_secs(0, [[260, 330]]))


class BigPlayerLimitTest(unittest.TestCase):
    """What `_sync_big_player_limit` arms on the card."""

    class _Big:
        def __init__(self):
            self.limit = ("untouched",)
            self.marks = None

        def set_limit(self, ms, glyph="hourglass", to_end=False):
            self.limit = (ms, glyph, to_end)

        def set_pd_marks(self, marks, armed=None):
            self.marks = marks

    class _Panel:
        def __init__(self, timed, secs):
            self._timed = timed
            self._secs = secs

        def timed_enabled(self):
            return self._timed

        def play_secs(self):
            return self._secs

        def play_set(self):
            return {"secs": self._secs if self._timed else 0}

    def _win(self, *, timed=False, play_secs=180, spans=None, duration=330.0):
        from player.main_player import PlayerControlMixin

        class Win(PlayerControlMixin):
            def _pd_runs_to_its_highlight(self):
                return False

            def _track_duration(self, _path):
                return duration

        w = Win()
        w._big_player = self._Big()
        w._playback = PlaybackState()
        w._playback.path = "hochzeit_aktuell_v9.mp3"
        w._silences = {"hochzeit_aktuell_v9.mp3": spans} if spans else {}
        w._play_panel = self._Panel(timed, play_secs)
        w._all_tables = ()    # no list: the panel's values are the ones
        w._playback.offset_ms = 0
        w._player = None
        return w

    def test_the_countdown_ends_at_the_last_note(self):
        w = self._win(spans=[[260, 330]])
        w._sync_big_player_limit()
        self.assertEqual(w._big_player.limit[0], 260_000)

    def test_an_earlier_timed_cut_still_wins(self):
        w = self._win(timed=True, play_secs=180, spans=[[260, 330]])
        w._sync_big_player_limit()
        self.assertEqual(w._big_player.limit[0], 180_000)

    def test_the_silence_wins_over_a_later_timed_cut(self):
        w = self._win(timed=True, play_secs=300, spans=[[260, 330]])
        w._sync_big_player_limit()
        self.assertEqual(w._big_player.limit[0], 260_000)

    def test_a_track_without_dead_air_runs_to_its_own_end(self):
        w = self._win()
        w._sync_big_player_limit()
        self.assertEqual(w._big_player.limit[0], None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
