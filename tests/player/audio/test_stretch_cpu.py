#!/usr/bin/env python3
"""⏩ What each tempo engine costs in CPU, per second of music.

Run:  .venv/Scripts/python.exe -m unittest tests.player.audio.test_stretch_cpu -v

Rubber Band runs in an ffmpeg child, so its time is the child's own,
read from Windows (GetProcessTimes; the handle still answers after ffmpeg
has exited, so the drained tail counts too). Signalsmith and numpy run on
the calling thread: their time is that thread's.

Measured on the dev PC (2026-11-21), 20 s of tone + noise + beat clicks:

    engine        0.92 / 1.08, fed in real time (fed at once)
    Rubber Band   54 / 41 ms per s  (55 / 38)   + ~5 ms in the app's process
    Signalsmith   33 / 24 ms per s  (22 / 20)
    numpy         22 / 28 ms per s  (20 / 16)

so Rubber Band takes about twice Signalsmith's, some 5 % of one core. The
budget below is generous on purpose (a slower PC, a busy suite); it is
there to catch a stretch gone runaway (a loop, a filter chain doubled),
not a few percent.
"""
import sys
import time
import unittest

import numpy as np

from player.audio import stretch, stretch_ffmpeg, stretch_signalsmith

_SR = 48000
_PIECE = 4458   # frames Qt hands the tap at a time
_SECONDS = 10.0
# CPU seconds per second of music, at most (measured 0.02-0.055).
_BUDGET = 0.25


def _music(seconds: float) -> np.ndarray:
    rng = np.random.default_rng(1)
    t = np.arange(int(seconds * _SR)) / _SR
    x = 0.2 * np.sin(2 * np.pi * 220 * t) + 0.1 * np.sin(2 * np.pi * 330 * t + 1)
    x += 0.05 * rng.standard_normal(len(t))
    beat = (t % 0.5) < 0.02
    x[beat] += 0.4 * rng.standard_normal(beat.sum())
    return np.stack([x, np.roll(x, 37)], axis=1).astype(np.float32)


def _feed(s, audio: np.ndarray) -> int:
    out = 0
    for i in range(0, len(audio), _PIECE):
        out += len(s.process(audio[i:i + _PIECE]))
    return out + len(s.flush())


def _process_cpu(handle) -> float:
    """Kernel + user seconds of the process behind a Windows handle."""
    import ctypes
    from ctypes import wintypes
    times = [wintypes.FILETIME() for _ in range(4)]
    ok = ctypes.windll.kernel32.GetProcessTimes(
        wintypes.HANDLE(int(handle)), *(ctypes.byref(t) for t in times))
    if not ok:
        raise OSError("GetProcessTimes failed")
    return sum((t.dwHighDateTime << 32 | t.dwLowDateTime) / 1e7 for t in times[2:])


class StretchCpuTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.audio = _music(_SECONDS)

    def assert_within_budget(self, cpu: float, out: int, rate: float, engine: str):
        self.assertAlmostEqual(out / _SR, _SECONDS / rate, delta=0.05,
                               msg="%s left music out" % engine)
        self.assertGreater(cpu, 0.0, "no time read: the budget would pass unmeasured")
        self.assertLess(cpu / _SECONDS, _BUDGET,
                        "%s at %.2f: %.0f ms CPU per second of music"
                        % (engine, rate, 1000 * cpu / _SECONDS))

    # ===== Acceptance criteria =====

    @unittest.skipUnless(sys.platform == "win32", "reads the child's time from Windows")
    def test_rubber_band_stays_within_budget(self):
        if not stretch_ffmpeg.available():
            self.skipTest("no ffmpeg with Rubber Band")
        for rate in (0.92, 1.08):
            with self.subTest(rate=rate):
                rb = stretch_ffmpeg.FfmpegStretch(_SR)
                self.addCleanup(rb.close)
                rb.set_rate(rate)
                self.assertTrue(rb.ready(5), "ffmpeg did not start")
                child = rb._spare.proc
                out = _feed(rb, self.audio)
                self.assertFalse(rb.failed, "Rubber Band handed over to its stand-in")
                child.wait(5)
                self.assert_within_budget(_process_cpu(child._handle), out, rate, "Rubber Band")

    # ===== Core behavior =====

    def test_the_in_process_engines_stay_within_budget(self):
        for engine, make in (("Signalsmith", stretch_signalsmith.SignalsmithStretch),
                             ("numpy", stretch.TimeStretch)):
            for rate in (0.92, 1.08):
                with self.subTest(engine=engine, rate=rate):
                    try:
                        s = make(_SR)
                    except (RuntimeError, OSError) as exc:
                        self.skipTest("%s not available: %s" % (engine, exc))
                    s.set_rate(rate)
                    start = time.thread_time()
                    out = _feed(s, self.audio)
                    self.assert_within_budget(time.thread_time() - start, out, rate, engine)


if __name__ == "__main__":
    unittest.main()
