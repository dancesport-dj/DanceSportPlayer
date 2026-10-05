"""Tests for the 🔇 hiss check: the ffmpeg astats noise-floor parser
(shared.audio_probes.parse_noise_floor), the content-addressed cache that keeps each
measurement (AudioCache.get/put_noise_floor) and the ImportMixin wrapper that
probes only when the user asked for the check.

The rule itself (when a floor counts as hissy) lives in test_checks.
"""
import math
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from shared.audio_probes import parse_noise_floor  # does NOT import gui.dialogs

_ASTATS = (
    "[Parsed_astats_0 @ 0000] Overall\n"
    "[Parsed_astats_0 @ 0000] Peak level dB: 0.360039\n"
    "[Parsed_astats_0 @ 0000] RMS level dB: -17.064172\n"
    "[Parsed_astats_0 @ 0000] Noise floor dB: {}\n"
    "[Parsed_astats_0 @ 0000] Noise floor count: 500.000000\n"
)


class ParseNoiseFloorTest(unittest.TestCase):

    def test_value(self):
        self.assertAlmostEqual(parse_noise_floor(_ASTATS.format("-69.575105")),
                               -69.575105)

    def test_digital_silence_is_minus_inf(self):
        """A track that reaches true silence has no floor at all — −inf sorts
        below every threshold, which is exactly right: it is not hissy."""
        self.assertEqual(parse_noise_floor(_ASTATS.format("-inf")), -math.inf)

    def test_a_hissy_floor_survives_the_regex(self):
        self.assertAlmostEqual(parse_noise_floor(_ASTATS.format("-35.5")), -35.5)

    def test_nothing_measured(self):
        self.assertIsNone(parse_noise_floor(""))
        self.assertIsNone(parse_noise_floor("Peak level dB: 0.36\n"))


class NoiseCacheTest(unittest.TestCase):
    """Round-trip through the real SQLite side table (temp state dir)."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                              tempfile.mkdtemp(prefix="dp_noise_"))
        from planner.db import AudioCache
        cls.cache = AudioCache()
        cls.file = Path(tempfile.mkdtemp(prefix="dp_noise_f_")) / "hiss.mp3"
        cls.file.write_bytes(b"not really audio, but it hashes")

    def test_unprobed_track_is_unknown(self):
        other = self.file.with_name("never_probed.mp3")
        other.write_bytes(b"another one")
        self.assertIsNone(self.cache.get_noise_floor(other))

    def test_roundtrip(self):
        self.cache.put_noise_floor(self.file, -37.25)
        self.assertAlmostEqual(self.cache.get_noise_floor(self.file), -37.25)

    def test_minus_inf_survives_the_database(self):
        """A clean track stores −inf — it must come back as −inf and not as
        None, or every re-check would probe it again."""
        p = self.file.with_name("clean.mp3")
        p.write_bytes(b"digital silence somewhere")
        self.cache.put_noise_floor(p, -math.inf)
        self.assertEqual(self.cache.get_noise_floor(p), -math.inf)


class ProbeWiringTest(unittest.TestCase):
    """`_track_noise_floor` measures at most once per track, and only when the
    🔇 checkbox in the Music-check window is on."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                              tempfile.mkdtemp(prefix="dp_noise_"))
        from gui.main_import import ImportMixin
        cls.ImportMixin = ImportMixin

    def win(self, *, on: bool, cached=None):
        calls = []

        class _Cache:
            def get_noise_floor(_self, path, touch_disk=True):
                return cached

            def put_noise_floor(_self, path, db):
                calls.append(("put", db))

            def save(_self):
                pass

        class Win(self.ImportMixin):
            _NOISE_FLOOR_DB = -50.0
            _settings = {}
            _cache = _Cache()
            _check_noise = on

        return Win(), calls

    def test_off_never_probes(self):
        win, calls = self.win(on=False)
        with mock.patch("gui.main_music.measure_noise_floor") as measure:
            self.assertIsNone(win._track_noise_floor(_entry()))
        measure.assert_not_called()
        self.assertEqual(calls, [])

    def test_cached_value_is_reused(self):
        win, calls = self.win(on=True, cached=-41.0)
        with mock.patch("gui.main_music.measure_noise_floor") as measure:
            self.assertEqual(win._track_noise_floor(_entry()), -41.0)
        measure.assert_not_called()
        self.assertEqual(calls, [])

    def test_unknown_track_is_measured_and_cached(self):
        win, calls = self.win(on=True)
        with mock.patch("gui.main_music.find_ffmpeg", return_value="ffmpeg"), \
             mock.patch("gui.main_music.measure_noise_floor",
                        return_value=-33.0) as measure:
            self.assertEqual(win._track_noise_floor(_entry()), -33.0)
        measure.assert_called_once()
        self.assertEqual(calls, [("put", -33.0)])

    def test_the_live_grid_marks_do_not_probe(self):
        """probe=False is the deck's on-every-edit re-check — it may read the
        cache but must never start an ffmpeg run."""
        win, _ = self.win(on=True)
        with mock.patch("gui.main_music.measure_noise_floor") as measure:
            self.assertIsNone(win._track_noise_floor(_entry(), probe=False))
        measure.assert_not_called()

    def test_a_failed_probe_stays_unknown(self):
        win, calls = self.win(on=True)
        with mock.patch("gui.main_music.find_ffmpeg", return_value="ffmpeg"), \
             mock.patch("gui.main_music.measure_noise_floor", return_value=None):
            self.assertIsNone(win._track_noise_floor(_entry()))
        self.assertEqual(calls, [])

    def test_without_ffmpeg_nothing_happens(self):
        win, calls = self.win(on=True)
        with mock.patch("gui.main_music.find_ffmpeg", return_value=None):
            self.assertIsNone(win._track_noise_floor(_entry()))
        self.assertEqual(calls, [])

    def test_the_threshold_comes_from_settings(self):
        win, _ = self.win(on=True)
        self.assertEqual(win._check_noise_db(), -50.0)
        win._settings = {"check_noise_floor_db": -42}
        self.assertEqual(win._check_noise_db(), -42.0)


def _entry():
    from types import SimpleNamespace
    return SimpleNamespace(path=Path(r"C:\music\hiss.mp3"), title="Hiss")


if __name__ == "__main__":
    unittest.main()
