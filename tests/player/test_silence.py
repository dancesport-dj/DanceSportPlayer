"""Tests for the ffmpeg silencedetect stderr parser (shared.audio_probes.parse_silences)
and the playback 🔇 stillness skip (player.main_player._maybe_skip_silence)."""
import os
import tempfile
import unittest
from pathlib import Path

from shared.audio_probes import parse_silences  # does NOT import gui.dialogs
from player.playback_state import PlaybackState


class ParseSilencesTest(unittest.TestCase):

    def test_closed_spans(self):
        text = ("  Duration: 00:03:20.00, start: 0.000000\n"
                "[x] silence_start: 10.5\n"
                "[x] silence_end: 14.0 | silence_duration: 3.5\n"
                "[x] silence_start: 60\n"
                "[x] silence_end: 65.25 | silence_duration: 5.25\n")
        self.assertEqual(parse_silences(text), [[10.5, 14.0], [60.0, 65.25]])

    def test_trailing_silence_closed_at_duration(self):
        # A file that ENDS silent has no final silence_end — the span must be
        # closed at the stream duration (the Da Doo Ron Ron case).
        text = ("  Duration: 00:01:50.76, start: 0.000000, bitrate: 195 kb/s\n"
                "[x] silence_start: 104.996122\n")
        spans = parse_silences(text)
        self.assertEqual(len(spans), 1)
        self.assertAlmostEqual(spans[0][0], 104.996122)
        self.assertAlmostEqual(spans[0][1], 110.76, places=2)

    def test_no_silence(self):
        self.assertEqual(parse_silences("  Duration: 00:02:00.00\n"), [])
        self.assertEqual(parse_silences(""), [])

    def test_unclosed_span_without_duration_dropped(self):
        # No Duration line to close the open span with → drop it rather than
        # invent an end time.
        self.assertEqual(parse_silences("[x] silence_start: 5.0\n"), [])

    def test_negative_start_clamped(self):
        # silencedetect can report a tiny negative start on leading silence.
        text = ("  Duration: 00:02:00.00\n"
                "[x] silence_start: -0.01\n"
                "[x] silence_end: 4.0 | silence_duration: 4.01\n")
        self.assertEqual(parse_silences(text), [[0.0, 4.0]])


class _FakePlayer:
    def __init__(self, pos_secs: float, dur_secs: float):
        self._pos = int(pos_secs * 1000)
        self._dur = int(dur_secs * 1000)
        self.seeks = []

    def position(self):
        return self._pos

    def duration(self):
        return self._dur

    def setPosition(self, ms):
        self.seeks.append(ms)
        self._pos = ms


class _FakeStatusBar:
    def showMessage(self, *_a):
        pass


# player.main_player pulls in gui.dialogs, which resolves the state files at
# import time — keep the import at TEST time (not module load), so during
# discovery test_state_files still gets to set its own DANCEPLAYLIST_STATE_DIR
# first. Standalone runs get a temp dir so the real settings stay untouched.
def _player_mixin():
    os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                          tempfile.mkdtemp(prefix="dp_silence_"))
    from player.main_player import PlayerControlMixin
    return PlayerControlMixin


class _FakeWindow:
    """Just enough MainWindow for _maybe_skip_silence."""

    def __init__(self, pos_secs, dur_secs, spans):
        self._player = _FakePlayer(pos_secs, dur_secs)
        self._playback = PlaybackState()
        self._playback.path = Path(r"C:\music\track.mp3")
        self._silences = {str(self._playback.path): spans}
        self._playback.offset_ms = 0
        self.ended = False

    def statusBar(self):
        return _FakeStatusBar()

    def _on_timed_end(self, reason: str = "play length"):
        self.ended = True

    def _sync_big_player_limit(self):
        pass


class SilenceSkipTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        class Win(_FakeWindow, _player_mixin()):
            pass
        cls.Win = Win

    def test_leading_silence_is_skipped(self):
        w = self.Win(pos_secs=1.0, dur_secs=180.0, spans=[[0.0, 8.0]])
        self.assertTrue(w._maybe_skip_silence())
        self.assertEqual(w._player.seeks, [8_000 - 200])
        self.assertFalse(w.ended)
        # The jumped-over dead air is booked as "not danced to", so the timed
        # cut still gives a full play length of music.
        self.assertEqual(w._playback.offset_ms, 6_800)

    def test_mid_track_silence_does_not_book_an_offset(self):
        w = self.Win(pos_secs=31.0, dur_secs=180.0, spans=[[30.0, 40.0]])
        w._maybe_skip_silence()
        self.assertEqual(w._playback.offset_ms, 0)

    def test_mid_track_silence_is_left_alone(self):
        # Only the EDGES are skipped — a break in the middle may be deliberate.
        w = self.Win(pos_secs=31.0, dur_secs=180.0, spans=[[30.0, 40.0]])
        self.assertFalse(w._maybe_skip_silence())
        self.assertEqual(w._player.seeks, [])
        self.assertFalse(w.ended)

    def test_trailing_silence_ends_the_song(self):
        # The Da Doo Ron Ron case: silent from 105.0 s to the end of the file.
        w = self.Win(pos_secs=106.0, dur_secs=110.76,
                     spans=[[105.0, 110.76]])
        self.assertTrue(w._maybe_skip_silence())
        self.assertTrue(w.ended)
        self.assertEqual(w._player.seeks, [])

    def test_short_gap_is_musical_not_skipped(self):
        # A Paso Doble stop pose (~3 s) must never be skipped.
        w = self.Win(pos_secs=51.0, dur_secs=180.0, spans=[[50.0, 53.0]])
        self.assertFalse(w._maybe_skip_silence())
        self.assertFalse(w.ended)

    def test_short_silent_intro_is_skipped(self):
        # Ella Vos - Temporary: 3.8 s of dead air before the first note. The
        # length floor that protects mid-track stops has no business at the edge.
        w = self.Win(pos_secs=1.0, dur_secs=159.81,
                     spans=[[0.0, 3.801429], [152.194014, 159.805147]])
        self.assertTrue(w._maybe_skip_silence())
        self.assertEqual(w._player.seeks, [3_801 - 200])
        self.assertFalse(w.ended)

    def test_short_silent_outro_ends_the_song(self):
        w = self.Win(pos_secs=178.5, dur_secs=180.0, spans=[[178.0, 180.0]])
        self.assertTrue(w._maybe_skip_silence())
        self.assertTrue(w.ended)

    def test_playhead_outside_span_does_nothing(self):
        w = self.Win(pos_secs=10.0, dur_secs=180.0, spans=[[30.0, 40.0]])
        self.assertFalse(w._maybe_skip_silence())

    def test_no_retrigger_after_landing(self):
        # After the seek the playhead sits within the tail guard — the next
        # tick must not skip again.
        w = self.Win(pos_secs=1.0, dur_secs=180.0, spans=[[0.0, 8.0]])
        self.assertTrue(w._maybe_skip_silence())
        self.assertFalse(w._maybe_skip_silence())


if __name__ == "__main__":
    unittest.main()
