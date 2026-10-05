#!/usr/bin/env python3
"""How long a track really plays, once the 🔇 stillness skip has had its say.

Run:  py -m unittest tests.planner.test_audible_secs -v

A file like `hochzeit_aktuell_v9.mp3` carries a minute of dead air behind the
last note. The tag says 5:30, the floor hears 4:20 — the player ends the song
when only stillness is left. `audible_track_secs` is that number, computed from
the silence spans the ffmpeg probe stored, and it follows the same edge rules
the skip does: the head and the tail go, a pause in the MIDDLE is played as
recorded because the dancers may know it.
"""

import unittest

from planner.checks import audible_track_secs


class AudibleTrackSecsTest(unittest.TestCase):

    def test_a_track_without_spans_plays_its_full_length(self):
        self.assertEqual(audible_track_secs(330, []), 330)
        self.assertEqual(audible_track_secs(330, None), 330)

    def test_dead_air_at_the_end_does_not_count_as_play_time(self):
        self.assertEqual(audible_track_secs(330, [[260, 330]]), 260)

    def test_a_silent_intro_does_not_count_either(self):
        self.assertEqual(audible_track_secs(330, [[0, 8]]), 322)

    def test_a_pause_in_the_middle_is_played_as_recorded(self):
        self.assertEqual(audible_track_secs(330, [[120, 130]]), 330)

    def test_a_stretch_too_short_for_the_skip_is_ignored(self):
        self.assertEqual(audible_track_secs(330, [[328.5, 330]]), 330)

    def test_both_edges_go(self):
        self.assertEqual(audible_track_secs(330, [[0, 5], [300, 330]]), 295)

    def test_a_span_ending_just_shy_of_the_end_still_counts_as_the_tail(self):
        """The skip treats anything within 1.5 s of the end as trailing."""
        self.assertEqual(audible_track_secs(330, [[300, 329]]), 300)

    def test_an_all_silent_file_plays_nothing(self):
        self.assertEqual(audible_track_secs(330, [[0, 330]]), 0)

    def test_an_unknown_length_stays_unknown(self):
        self.assertEqual(audible_track_secs(0, [[0, 5]]), 0)


class EdgeSilenceSecsTest(unittest.TestCase):
    """The two ends reported apart, so the ⏱ flag can ask "is ONE of them
    long?" instead of "did anything at all get trimmed?" — see
    FLAG_EDGE_SILENCE."""

    def test_the_head_and_the_tail_are_reported_separately(self):
        from planner.checks import edge_silence_secs
        self.assertEqual(edge_silence_secs(330, [[0, 5], [300, 330]]), (5, 30))

    def test_the_middle_belongs_to_neither_end(self):
        from planner.checks import edge_silence_secs
        self.assertEqual(edge_silence_secs(330, [[120, 180]]), (0.0, 0.0))

    def test_a_track_that_was_never_probed_has_no_edges(self):
        from planner.checks import edge_silence_secs
        self.assertEqual(edge_silence_secs(330, None), (0.0, 0.0))

    def test_a_stretch_too_short_for_the_skip_is_no_edge(self):
        from planner.checks import edge_silence_secs
        self.assertEqual(edge_silence_secs(330, [[328.5, 330]]), (0.0, 0.0))

    def test_it_agrees_with_the_play_time_it_backs(self):
        from planner.checks import edge_silence_secs
        spans = [[0, 4], [310, 330]]
        head, tail = edge_silence_secs(330, spans)
        self.assertEqual(330 - head - tail, audible_track_secs(330, spans))

    def test_five_seconds_is_the_flag_threshold(self):
        """Pinned because it is a user-facing decision, not an implementation
        detail: below this the ⏱ cell stays black."""
        from planner.checks import FLAG_EDGE_SILENCE
        self.assertEqual(FLAG_EDGE_SILENCE, 5.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
