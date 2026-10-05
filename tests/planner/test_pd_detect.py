"""Tests for the ffmpeg-based PD highlight decoding in shared.audio_probes.

The player build ships no librosa, so `detect_pd_highlights` decodes through
ffmpeg and computes the RMS envelope itself. Both replacements have to behave
exactly like the librosa calls they stand in for — the highlight thresholds
were tuned against real Espana Cani recordings and mean nothing if the
envelope underneath them shifts.
"""
import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from shared import audio_probes as gw

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

HAS_FFMPEG = gw.find_ffmpeg() is not None


def write_sine(path: Path, seconds: float, sr: int = 44100, freq: float = 440.0):
    """A mono 16-bit sine — something ffmpeg can decode without a codec."""
    frames = bytearray()
    for i in range(int(seconds * sr)):
        frames += struct.pack("<h", int(0.5 * 32767 * math.sin(2 * math.pi * freq * i / sr)))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(bytes(frames))


@unittest.skipUnless(HAS_NUMPY, "needs numpy")
class RmsEnvelopeTest(unittest.TestCase):
    """`_rms_envelope` reproduces librosa.feature.rms at its defaults."""

    def test_frame_count_is_librosas(self):
        """Centred frames: half a frame of zero padding each side, so the count
        is 1 + len(y) // hop and not something shorter."""
        for n in (1, 511, 512, 2048, 50000):
            with self.subTest(n=n):
                y = np.zeros(n, dtype=np.float32)
                self.assertEqual(gw._rms_envelope(y).shape, (1 + n // 512,))

    def test_constant_signal_reads_its_own_level(self):
        """A steady 0.5 amplitude has RMS 0.5 everywhere the frame is full —
        the edge frames are lower, because half of them is the zero padding."""
        env = gw._rms_envelope(np.full(20000, 0.5, dtype=np.float32))
        self.assertAlmostEqual(float(env[10]), 0.5, places=5)
        self.assertLess(float(env[0]), 0.5)

    def test_first_frame_is_half_padding(self):
        """Frame 0 is centred on sample 0, so exactly half of its 2048 samples
        are padding: RMS = level / sqrt(2)."""
        env = gw._rms_envelope(np.ones(20000, dtype=np.float32))
        self.assertAlmostEqual(float(env[0]), 1.0 / math.sqrt(2), places=4)

    def test_silence_stays_silent(self):
        env = gw._rms_envelope(np.zeros(20000, dtype=np.float32))
        self.assertTrue(bool((env == 0).all()))

    def test_nothing_in_nothing_out(self):
        self.assertEqual(gw._rms_envelope(np.empty(0, dtype=np.float32)).size, 0)


@unittest.skipUnless(HAS_NUMPY and HAS_FFMPEG, "needs numpy + ffmpeg")
class DecodePcmMonoTest(unittest.TestCase):
    """`decode_pcm_mono` is librosa.load's replacement: samples at one rate."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="dp_pcm_"))

    def test_length_matches_the_requested_rate(self):
        src = self._tmp / "sine.wav"
        write_sine(src, 2.0)
        y = gw.decode_pcm_mono(src, sr=22050)
        # Resamplers pad by a few samples; 2 s at 22050 is 44100 of them.
        self.assertAlmostEqual(y.size / 22050, 2.0, delta=0.05)

    def test_samples_are_float32_in_range(self):
        src = self._tmp / "sine.wav"
        write_sine(src, 0.5)
        y = gw.decode_pcm_mono(src, sr=22050)
        self.assertEqual(y.dtype, np.dtype("<f4"))
        self.assertLessEqual(float(np.abs(y).max()), 1.0)
        self.assertGreater(float(np.abs(y).max()), 0.4)   # the 0.5 sine is there

    def test_a_missing_file_is_empty_not_an_error(self):
        """Every caller reads an empty array as 'no data' — a raise here would
        take down the background worker instead."""
        self.assertEqual(gw.decode_pcm_mono(self._tmp / "nope.mp3").size, 0)

    def test_a_url_is_refused(self):
        """ffmpeg would fetch an http:// input; imported .m3u lines carry them."""
        self.assertEqual(gw.decode_pcm_mono(Path("http://example.com/x.mp3")).size, 0)


@unittest.skipUnless(HAS_NUMPY and HAS_FFMPEG, "needs numpy + ffmpeg")
class DetectHighlightsTest(unittest.TestCase):
    """The detector end to end, on audio with no crash in it."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="dp_pd_"))

    def test_a_steady_tone_has_no_highlight_but_still_ends(self):
        """No dip anywhere, so h1/h2 stay None and h3 falls back to the end."""
        src = self._tmp / "flat.wav"
        write_sine(src, 8.0)
        h1, h2, h3 = gw.detect_pd_highlights(src)
        self.assertIsNone(h1)
        self.assertIsNone(h2)
        self.assertAlmostEqual(h3, 8.0, delta=0.2)

    def test_an_unreadable_file_yields_no_highlights(self):
        self.assertEqual(gw.detect_pd_highlights(self._tmp / "nope.mp3"), [])


class PhrasedHighlightsTest(unittest.TestCase):
    """Highlights the crash search can't hear, counted back from the end.

    Marcel: "32 Espana Cani Concertante (Intro, Espana Cani Phrasing, 3
    Highlights) (Paso Doble 59)" — "check why we automiss the highlight". The
    arrangement plays on through highlights 1 and 2, so there is no dip to
    find; only the final crash at 137.9 s is. He marked highlight 2 by hand
    at 94.07 s.
    """

    CONCERTANTE = ("32 Espana Cani Concertante (Intro, Espana Cani Phrasing, "
                   "3 Highlights) (Paso Doble 59).mp3")

    def fill(self, times, name=CONCERTANTE, final_crash=True):
        return gw.fill_phrased_highlights(times, name, final_crash)

    def test_both_missing_highlights_are_counted_back_from_the_end(self):
        h1, h2, h3 = self.fill([None, None, 137.9])
        self.assertAlmostEqual(h2, 94.07, delta=0.3)   # his own mark
        self.assertAlmostEqual(h1, 58.6, delta=0.3)    # where the accent hits
        self.assertEqual(h3, 137.9)

    def test_a_highlight_the_crash_search_found_is_kept(self):
        # A plain tournament edit at 60, as the detector reads it.
        h1, h2, h3 = self.fill(
            [43.65, None, 121.67],
            "PD Espana Cani (_Espana Cani_ Phrasing, 3 Highlights) (Paso Doble 60).mp3")
        self.assertEqual(h1, 43.65)
        self.assertAlmostEqual(h2, 78.69, delta=0.3)   # where it found it elsewhere

    def test_a_crash_more_than_a_bar_off_the_phrasing_is_not_the_highlight(self):
        # Marcel, by ear: "schema ist meist korrekt, erkannt da kaum". The
        # search picks an earlier accent (34.4 s, 70.0 s); the phrasing from
        # the final crash lands on the highlights he hears.
        h1, h2, h3 = self.fill(
            [34.4, 70.0, 123.5],
            "PD Espana Cani (_Espana Cani_ Phrasing, 3 Highlights) (Paso Doble 59).mp3")
        self.assertAlmostEqual(h2, 79.77, delta=0.1)
        self.assertAlmostEqual(h1, 44.18, delta=0.1)
        self.assertEqual(h3, 123.5)

    def test_spanish_gipsy_dance_is_the_same_phrasing_untagged(self):
        # Marcel: "Spanish Gipsy Dance is also espani cani phrasin" — the
        # English title of the same piece, mostly without the tag in its name.
        h1, h2, h3 = self.fill([57.03, None, 125.92],
                               "13 Spanish Gipsy Dance (PD 60).mp3")
        self.assertAlmostEqual(h2, 82.92, delta=0.1)
        self.assertAlmostEqual(h1, 47.92, delta=0.1)

    def test_a_short_spanish_gipsy_dance_is_left_alone(self):
        times = [None, None, 83.22]
        for name in ("50 Spanish Gipsy Dance (short version) (Paso Doble 58).mp3",
                     "50 Spanish Gipsy Dance (Espana Cani Phrasing, 2 Highlights) "
                     "(Paso Doble 58).mp3"):
            with self.subTest(name=name):
                self.assertEqual(self.fill(times, name), times)

    def test_a_highlight_on_the_phrasing_shows_an_untagged_track_follows_it(self):
        # Marcel: "el bailador is wrong". Highlight 1 lands within 0.02 s of
        # the count from the final crash; the search's highlight 2 is a later
        # accent, 16 s off. 35 bars on from highlight 1 is the real one.
        h1, h2, h3 = self.fill(
            [44.68, 96.5, 124.02],
            "15-Boris Myagkov Big Band _ El Bailador (Paso Doble 59).mp3")
        self.assertEqual(h1, 44.68)
        self.assertAlmostEqual(h2, 80.27, delta=0.1)
        self.assertEqual(h3, 124.02)

    def test_a_highlight_2_on_the_phrasing_counts_highlight_1_back(self):
        h1, h2, _ = self.fill([30.86, 78.37, 121.3], "091 PA Vamos Amigos T60.mp3")
        self.assertEqual(h2, 78.37)
        self.assertAlmostEqual(h1, 43.37, delta=0.1)

    def test_the_count_runs_from_the_highlight_it_confirmed(self):
        # Both highlights sit ~1 s before the count from the end: the final
        # crash reads a little late. 35 bars apart they agree, so both stay.
        times = [43.37, 78.76, 122.6]
        self.assertEqual(self.fill(times, "2-19 Carmen De Sevilla (PD 60).mp3"), times)

    def test_an_untagged_track_off_the_phrasing_is_left_alone(self):
        times = [30.0, 95.0, 121.5]
        self.assertEqual(self.fill(times, "Some Paso (PD 60).mp3"), times)

    def test_only_the_three_highlight_phrasing_has_this_shape(self):
        times = [None, None, 84.4]
        name = ("49 Espana Cani (short version) (Espana Cani Phrasing, "
                "2 Highlights) (Paso Doble 59).mp3")
        self.assertEqual(self.fill(times, name), times)

    def test_another_paso_doble_is_left_alone(self):
        times = [None, None, 124.62]
        self.assertEqual(self.fill(times, "DJ ICE Espana Cani - pd60.mp3"), times)

    def test_without_a_final_crash_there_is_nothing_to_count_from(self):
        # h3 is then only the end of the file, not the last highlight.
        times = [None, None, 141.0]
        self.assertEqual(self.fill(times, final_crash=False), times)

    def test_without_a_tempo_there_is_no_bar_length(self):
        times = [None, None, 137.9]
        name = "Espana Cani (Espana Cani Phrasing, 3 Highlights).mp3"
        self.assertEqual(self.fill(times, name), times)


if __name__ == "__main__":
    unittest.main()
