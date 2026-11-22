#!/usr/bin/env python3
"""🎚 The room equalizer's filter (player.audio.eq).

Run:  .venv/Scripts/python.exe -m unittest tests.player.audio.test_eq -v

Pure numpy, no Qt: bands in, frames in, frames out. The pieces fed here are
the size Qt hands over (about 93 ms), as in test_pair_route.
"""
import os
import unittest
from unittest import mock

import numpy as np

from planner.playing import equalizer
from player.audio import eq
from player.audio.eq import Band, EqFilter

_RATE = 48000
_PIECE = 4458


def _sine(freq: float, seconds: float = 1.0, amp: float = 0.5) -> np.ndarray:
    t = np.arange(int(_RATE * seconds)) / _RATE
    mono = (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    return np.column_stack([mono, mono])


def _in_pieces(filt: EqFilter, frames: np.ndarray, piece: int = _PIECE) -> np.ndarray:
    return np.vstack([filt.process(frames[i:i + piece])
                      for i in range(0, len(frames), piece)])


def _db(x: float) -> float:
    return 20 * np.log10(x)


def _rms(frames: np.ndarray) -> float:
    return float(np.sqrt(np.mean(frames[:, 0].astype(np.float64) ** 2)))


def _gain_at(bands, freq: float) -> float:
    """What the filter really does to a steady sine at `freq`, in dB."""
    filt = EqFilter()
    filt.set_bands(bands, _RATE)
    tone = _sine(freq, 1.0)
    out = _in_pieces(filt, tone)
    settled = slice(_RATE // 2, None)   # past the start-up and the fade-in
    return _db(_rms(out[settled]) / _rms(tone[settled]))


class EqFilterTest(unittest.TestCase):

    # ===== Acceptance criteria =====

    def test_flat_bands_leave_the_sound_untouched(self):
        filt = EqFilter()
        filt.set_bands([Band("peak", 1000, 0.0), Band("highshelf", 10000, 0.0)], _RATE)
        noise = np.random.default_rng(1).uniform(-1, 1, (3 * _PIECE, 2)).astype(np.float32)
        self.assertTrue(np.array_equal(_in_pieces(filt, noise), noise))

    def test_a_peak_band_changes_its_frequency_by_its_gain(self):
        # +6 dB at 1 kHz, minus the 6 dB headroom: 0 dB there, −6 dB far away.
        bands = [Band("peak", 1000, 6.0)]
        self.assertAlmostEqual(_gain_at(bands, 1000), 0.0, delta=0.1)
        self.assertAlmostEqual(_gain_at(bands, 100), -6.0, delta=0.3)

    def test_a_cut_needs_no_headroom(self):
        bands = [Band("peak", 250, -6.0)]
        self.assertAlmostEqual(_gain_at(bands, 250), -6.0, delta=0.1)
        self.assertAlmostEqual(_gain_at(bands, 5000), 0.0, delta=0.1)

    def test_no_boost_drives_a_full_scale_title_past_full_scale(self):
        bands = [Band("lowshelf", 100, 12.0), Band("peak", 2500, 12.0),
                 Band("highshelf", 10000, 12.0)]
        for freq in (60, 2500, 14000):
            filt = EqFilter()   # each tone on its own: no jump from the one before
            filt.set_bands(bands, _RATE)
            out = _in_pieces(filt, _sine(freq, 0.5, amp=1.0))
            self.assertLessEqual(float(np.max(np.abs(out))), 1.02, freq)

    def test_pieces_join_without_a_seam(self):
        bands = [Band("lowcut", 30), Band("peak", 250, -4.0), Band("highshelf", 10000, 3.0)]
        noise = np.random.default_rng(2).uniform(-0.5, 0.5, (10 * _PIECE, 2)).astype(np.float32)
        whole, pieced = EqFilter(), EqFilter()
        for filt in (whole, pieced):
            filt.set_bands(bands, _RATE)
            filt.process(np.zeros((1, 2), np.float32))   # the switch-on fade, out of the way
        np.testing.assert_allclose(_in_pieces(pieced, noise, 1000),
                                   whole.process(noise), atol=1e-5)

    # ===== Core behavior =====

    def test_the_low_cut_is_3_db_down_at_its_frequency(self):
        bands = [Band("lowcut", 100, q=1 / np.sqrt(2))]
        self.assertAlmostEqual(_db(abs(eq.response(bands, _RATE, [100])[0])), -3.0, delta=0.1)
        self.assertAlmostEqual(_db(abs(eq.response(bands, _RATE, [1000])[0])), 0.0, delta=0.1)
        self.assertLess(_db(abs(eq.response(bands, _RATE, [25])[0])), -20)

    def test_shelves_reach_their_gain_past_their_corner(self):
        low = [Band("lowshelf", 100, 6.0)]
        high = [Band("highshelf", 10000, -6.0)]
        self.assertAlmostEqual(_db(abs(eq.response(low, _RATE, [20])[0])), 6.0, delta=0.3)
        self.assertAlmostEqual(_db(abs(eq.response(low, _RATE, [2000])[0])), 0.0, delta=0.2)
        self.assertAlmostEqual(_db(abs(eq.response(high, _RATE, [20000])[0])), -6.0, delta=0.5)

    def test_a_change_is_faded_in_without_a_jump(self):
        filt = EqFilter()
        filt.set_bands([], _RATE)
        tone = _sine(80, 2.0)
        first = _in_pieces(filt, tone[:4 * _PIECE])
        filt.set_bands([Band("lowshelf", 100, -12.0)], _RATE)
        second = filt.process(tone[4 * _PIECE:5 * _PIECE])
        joined = np.vstack([first, second])[:, 0]
        # An 80 Hz sine at 0.5 moves at most ~0.005 per sample: a step would be far more.
        self.assertLess(float(np.max(np.abs(np.diff(joined)))), 0.01)
        self.assertLess(_rms(second[-500:]), _rms(tone[:500]))

    def test_changes_between_two_pieces_fade_from_what_was_heard(self):
        """A slider drag: several changes before the next piece. The fade
        starts at the sound last heard, not at one that never was."""
        tone = _sine(80, 1.0)
        heard, dragged = EqFilter(), EqFilter()
        for filt in (heard, dragged):
            filt.set_bands([], _RATE)
            _in_pieces(filt, tone[:4 * _PIECE])
        dragged.set_bands([Band("lowshelf", 100, 12.0)], _RATE)   # never heard
        for filt in (heard, dragged):
            filt.set_bands([Band("lowshelf", 100, -12.0)], _RATE)
        piece = tone[4 * _PIECE:5 * _PIECE]
        np.testing.assert_allclose(dragged.process(piece), heard.process(piece), atol=1e-6)

    def test_a_change_fades_from_the_old_eq_not_from_the_dry_sound(self):
        """A slider step from one boost to the next: the fade starts at the
        old EQ's sound. Faded up from the dry title instead, every step
        would dip the band for one piece."""
        old, new = [Band("lowshelf", 100, -12.0)], [Band("lowshelf", 100, -11.0)]
        tone = _sine(80, 1.0)
        changed, stays_old, was_new = EqFilter(), EqFilter(), EqFilter()
        for filt, bands in ((changed, old), (stays_old, old), (was_new, new)):
            filt.set_bands(bands, _RATE)
            _in_pieces(filt, tone[:4 * _PIECE])
        changed.set_bands(new, _RATE)
        piece = tone[4 * _PIECE:5 * _PIECE]
        before, after = stays_old.process(piece), was_new.process(piece)
        ramp = np.linspace(0.0, 1.0, len(piece), dtype=np.float32)[:, None]
        np.testing.assert_allclose(changed.process(piece),
                                   before + (after - before) * ramp, atol=1e-5)

    def test_reset_forgets_what_came_before(self):
        bands = [Band("peak", 1000, 5.0)]
        used, fresh = EqFilter(), EqFilter()
        used.set_bands(bands, _RATE)
        fresh.set_bands(bands, _RATE)
        used.process(_sine(440, 0.2))
        fresh.process(np.zeros((10, 2), np.float32))   # past its own fade-in
        used.process(np.zeros((10, 2), np.float32))
        used.reset()
        fresh.reset()
        tone = _sine(1000, 0.1)
        np.testing.assert_allclose(used.process(tone), fresh.process(tone), atol=1e-6)

    def test_a_new_sample_rate_rebuilds_the_filter(self):
        bands = [Band("peak", 1000, -6.0)]
        filt = EqFilter()
        filt.set_bands(bands, 44100)
        kernel = filt._kernel
        filt.set_bands(bands, 48000)
        self.assertIsNot(filt._kernel, kernel)
        self.assertAlmostEqual(_gain_at(bands, 1000), -6.0, delta=0.1)

    def test_headroom_is_the_top_of_the_combined_curve(self):
        alone = [Band("peak", 2500, 4.5)]
        self.assertAlmostEqual(eq.headroom_db(alone), 4.5, delta=0.05)
        # A shelf adds to a peak below its corner: more than either band alone.
        stacked = alone + [Band("highshelf", 4000, 4.5)]
        self.assertGreater(eq.headroom_db(stacked), 5.0)
        self.assertEqual(eq.headroom_db([Band("peak", 250, -3.0)]), 0.0)

    # ===== Coverage and null checks =====

    def test_a_band_switched_off_does_nothing(self):
        self.assertTrue(eq.is_flat([Band("peak", 1000, 6.0, on=False),
                                    Band("lowcut", 30, on=False)]))
        self.assertIsNone(eq.design_kernel([Band("peak", 1000, 6.0, on=False)], _RATE))

    def test_gain_is_held_to_12_db(self):
        wild = eq.response([Band("peak", 1000, 40.0)], _RATE, [1000])[0]
        self.assertAlmostEqual(_db(abs(wild)), 12.0, delta=0.05)

    def test_an_empty_piece_comes_back_empty(self):
        filt = EqFilter()
        filt.set_bands([Band("peak", 1000, 3.0)], _RATE)
        self.assertEqual(len(filt.process(np.zeros((0, 2), np.float32))), 0)

    def test_an_unknown_band_kind_is_refused(self):
        with self.assertRaises(ValueError):
            eq.biquad(Band("notch", 1000), _RATE)


class SettingsBridgeTest(unittest.TestCase):
    """🎚 Which backend can have an EQ, and the settings turned into bands."""

    def setUp(self):
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("QT_MEDIA_BACKEND", None)

    def on(self, source, bypass=False):
        cfg = equalizer.eq_of({}, source)
        cfg["on"], cfg["bypass"] = True, bypass
        cfg["bands"][3]["gain"] = 4.0
        return equalizer.with_eq({}, source, cfg)

    # ===== Acceptance criteria =====

    def test_an_eq_that_is_on_gives_its_bands(self):
        bands = eq.bands_for(self.on("music"), "music")
        self.assertEqual(len(bands), 5)
        self.assertEqual(bands[3], Band("peak", 2500.0, 4.0, 1.0))

    def test_bypass_is_the_path_without_a_band(self):
        self.assertEqual(eq.bands_for(self.on("cue", bypass=True), "cue"), ())

    def test_off_is_none(self):
        self.assertIsNone(eq.bands_for({}, "announcer"))

    # ===== Core behavior =====

    def test_only_ffmpeg_has_an_eq(self):
        self.assertTrue(eq.available())
        for native in ("windows", "Darwin ", "gstreamer", "android"):
            os.environ["QT_MEDIA_BACKEND"] = native
            self.assertFalse(eq.available(), native)
        os.environ["QT_MEDIA_BACKEND"] = "ffmpeg"
        self.assertTrue(eq.available())

    def test_a_native_backend_gives_none_even_when_on(self):
        os.environ["QT_MEDIA_BACKEND"] = "windows"
        self.assertIsNone(eq.bands_for(self.on("music"), "music"))


if __name__ == "__main__":
    unittest.main()
