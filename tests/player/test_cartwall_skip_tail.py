"""🔇 A pad that skips its silence skips it at the end of the file too.

Marcel on the start skip (5f234132): "apply it to start and end". A flagged
pad is over where its music stops: a one-shot ends there (the queue's next
pad follows without the dead air, the duck lets go), its countdown runs to
that point, and a loop goes round from there in every loop mode. The tail
is probed like the lead: the last ten seconds, silencedetect at d=0.05.

Runs on the stub players of test_cartwall_voices (files of 10 s).
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_skiptail_"))

from PySide6.QtWidgets import QApplication

from player.audio import cart_voices
from shared.audio import audio_probes
from tests.player.test_cartwall_voices import _factory, _pad

_app = QApplication.instance() or QApplication(sys.argv)

KEY = (0, 0, 0)
RELEASE = cart_voices._TAIL_RELEASE_MS
PREROLL = cart_voices._LEAD_PREROLL_MS
TAIL = [6.0, 10.0]          # the music of the 10 s stub file stops at 6 s
MUSIC_END = 6000 + RELEASE


def _last_position(voice):
    return [c[1] for c in voice.player.calls if c[0] == "setPosition"][-1]


class SkipTailVoicesTest(unittest.TestCase):

    def setUp(self):
        self.v = cart_voices.CartVoices(voices=4, factory=_factory)
        self.addCleanup(self.v.shutdown)
        self.v.set_level(1.0)
        self.ended = []
        self.v.padEnded.connect(self.ended.append)

    def _fire(self, pad, spans):
        self.v.set_edges(pad.path, spans)
        self.v.fire(KEY, pad)
        return self.v._voice_for(KEY)

    def test_a_one_shot_ends_where_its_music_stops(self):
        voice = self._fire(_pad(skip_silence=True), [TAIL])
        voice.player.setPosition(MUSIC_END)
        self.v._emit_tick()
        self.assertEqual(self.ended, [KEY])
        self.assertFalse(voice.busy, "the voice is free for the next pad")

    def test_before_that_it_plays_on(self):
        voice = self._fire(_pad(skip_silence=True), [TAIL])
        voice.player.setPosition(MUSIC_END - 200)
        self.v._emit_tick()
        self.assertEqual(self.ended, [])
        self.assertTrue(voice.busy)

    def test_an_unflagged_pad_plays_to_the_end_of_its_file(self):
        voice = self._fire(_pad(), [TAIL])
        voice.player.setPosition(MUSIC_END + 1000)
        self.v._emit_tick()
        self.assertEqual(self.ended, [])
        self.assertTrue(voice.busy)

    def test_its_countdown_runs_to_the_music_end(self):
        rows = []
        self.v.padTick.connect(rows.extend)
        voice = self._fire(_pad(skip_silence=True), [TAIL])
        voice.player.setPosition(1000)
        self.v._emit_tick()
        self.assertEqual(rows[-1][1], MUSIC_END - 1000)

    def test_a_hard_loop_goes_round_from_the_music_end(self):
        self.v.set_loop_mode("hard")
        voice = self._fire(_pad(loop=True, duck=False, skip_silence=True),
                           [[0.0, 0.3], TAIL])
        voice.player.setPosition(MUSIC_END)
        self.v._emit_tick()
        self.assertIs(self.v._voice_for(KEY), voice, "the same voice goes round again")
        self.assertEqual(_last_position(voice), 300 - PREROLL)
        self.assertEqual(self.ended, [])

    def test_a_crossover_ends_at_the_music_end(self):
        voice = self._fire(_pad(loop=True, duck=False, skip_silence=True, cross_ms=1000),
                           [TAIL])
        voice.player.setPosition(MUSIC_END - 1000)
        self.v._emit_tick()
        self.assertTrue(voice.tail, "the next round already took over")

    def test_both_edges_are_kept(self):
        pad = _pad(skip_silence=True)
        voice = self._fire(pad, [[0.0, 0.3], TAIL])
        self.assertEqual([c[1] for c in voice.player.calls if c[0] == "setPosition"][-1],
                         300 - PREROLL)
        self.assertEqual(self.v._last_ms(pad, 10_000), MUSIC_END)


class TailProbeParseTest(unittest.TestCase):

    def _err(self, *lines, duration="00:00:04.00"):
        return "\n".join([f"  Duration: {duration}, start: 0.000000, bitrate: 320 kb/s",
                          *lines])

    def test_a_short_file_reports_the_stretch_as_it_is(self):
        """-sseof past the start of the file is ignored: times are the file's."""
        err = self._err("[silencedetect @ 0x1] silence_start: 3.7",
                        "[silencedetect @ 0x1] silence_end: 4 | silence_duration: 0.3")
        self.assertEqual(audio_probes.parse_tail_silence(err), [[3.7, 4.0]])

    def test_a_long_file_counts_from_the_window_start(self):
        """ffmpeg times the last ten seconds from 0 (checked on ffmpeg 9)."""
        err = self._err("[silencedetect @ 0x1] silence_start: 0",
                        "[silencedetect @ 0x1] silence_end: 0.084 | silence_duration: 0.084",
                        "[silencedetect @ 0x1] silence_start: 9.7",
                        "[silencedetect @ 0x1] silence_end: 10 | silence_duration: 0.3",
                        duration="00:03:00.00")
        self.assertEqual(audio_probes.parse_tail_silence(err), [[179.7, 180.0]])

    def test_music_to_the_last_sample_has_no_tail(self):
        err = self._err("[silencedetect @ 0x1] silence_start: 0",
                        "[silencedetect @ 0x1] silence_end: 0.084 | silence_duration: 0.084",
                        duration="00:03:00.00")
        self.assertEqual(audio_probes.parse_tail_silence(err), [])

    def test_silence_in_the_middle_is_no_tail(self):
        err = self._err("[silencedetect @ 0x1] silence_start: 2.0",
                        "[silencedetect @ 0x1] silence_end: 2.5 | silence_duration: 0.5")
        self.assertEqual(audio_probes.parse_tail_silence(err), [])

    def test_a_silent_window_is_not_skipped(self):
        """Nothing heard in the last ten seconds: where the music stops is
        unknown, so the pad plays to the end of its file."""
        err = self._err("[silencedetect @ 0x1] silence_start: 0", duration="00:03:00.00")
        self.assertEqual(audio_probes.parse_tail_silence(err), [])


class EdgeProbeTest(unittest.TestCase):

    def test_it_reports_both_edges(self):
        with mock.patch.object(audio_probes, "detect_lead_silence", return_value=[[0.0, 0.3]]), \
                mock.patch.object(audio_probes, "detect_tail_silence", return_value=[TAIL]):
            self.assertEqual(audio_probes.detect_edge_silence("ffmpeg", "a.mp3"),
                             [[0.0, 0.3], TAIL])

    def test_one_failed_pass_keeps_the_other(self):
        with mock.patch.object(audio_probes, "detect_lead_silence", return_value=None), \
                mock.patch.object(audio_probes, "detect_tail_silence", return_value=[TAIL]):
            self.assertEqual(audio_probes.detect_edge_silence("ffmpeg", "a.mp3"), [TAIL])

    def test_two_failed_passes_fail(self):
        with mock.patch.object(audio_probes, "detect_lead_silence", return_value=None), \
                mock.patch.object(audio_probes, "detect_tail_silence", return_value=None):
            self.assertIsNone(audio_probes.detect_edge_silence("ffmpeg", "a.mp3"))


if __name__ == "__main__":
    unittest.main()
