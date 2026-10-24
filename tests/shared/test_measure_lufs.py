#!/usr/bin/env python3
"""📊 `measure_lufs` stores only a whole-file measurement, and reads silence.

Run:  py -m unittest tests.shared.test_measure_lufs -v

It was the one probe that ignored ffmpeg's exit code: a truncated file still
prints a summary block, measured over the fragment that decoded, and that
value then set the gain sent to the PA. And a digitally silent track reports
`I: -inf LUFS`, which the regex could not read — so it stayed unmeasured and
was decoded again on every pass.
"""

import unittest
from pathlib import Path
from unittest import mock

from shared.audio import audio_probes


def _summary(value: str, peak: str | None = "-0.4") -> str:
    """ebur128's closing block; with peak=true it ends in a true-peak part."""
    out = ("[Parsed_ebur128_0 @ 0x0] Summary:\n\n"
           "  Integrated loudness:\n"
           f"    I:         {value} LUFS\n"
           "    Threshold: -70.0 LUFS\n\n"
           "  Loudness range:\n"
           "    LRA:         6.1 LU\n")
    if peak is not None:
        out += f"\n  True peak:\n    Peak:      {peak} dBFS\n"
    return out


def _probe(returncode: int, stderr: str):
    with mock.patch.object(audio_probes, "_ffmpeg_probe",
                           return_value=(returncode, stderr)) as probe:
        return audio_probes.measure_loudness("ffmpeg", Path("x.mp3")), probe


def _measure(returncode: int, stderr: str):
    return _probe(returncode, stderr)[0]


class MeasureLufsTest(unittest.TestCase):

    def test_a_whole_file_is_measured(self):
        self.assertEqual(_measure(0, _summary("-14.2")), (-14.2, -0.4))

    def test_a_failed_decode_stores_nothing(self):
        stderr = ("[mp3 @ 0x0] Invalid data found when processing input\n"
                  + _summary("-9.8"))
        self.assertIsNone(_measure(1, stderr))

    def test_a_silent_track_reads_as_the_floor(self):
        self.assertEqual(_measure(0, _summary("-inf", "-inf")),
                         (audio_probes.SILENT_LUFS, audio_probes.SILENT_LUFS))


class TruePeakTest(unittest.TestCase):
    """🔝 The same pass reads the true peak: the gain cap's other half."""

    def test_the_filter_asks_for_true_peak(self):
        _res, probe = _probe(0, _summary("-14.2"))
        args = probe.call_args.args[0]
        self.assertEqual(args[args.index("-af") + 1], "ebur128=peak=true")

    def test_a_peak_over_full_scale_is_read(self):
        """ffmpeg 9 prints it unsigned ("Peak:        0.5 dBFS" on a real
        master); a "+" would be read too."""
        self.assertEqual(_measure(0, _summary("-8.0", "1.3")), (-8.0, 1.3))
        self.assertEqual(_measure(0, _summary("-8.0", "+1.3")), (-8.0, 1.3))

    def test_the_per_frame_peaks_are_not_the_summary(self):
        """ffmpeg prints a line per frame even under -nostats, its true peak
        as "TPK:" per channel; only the summary's Peak counts."""
        frames = ("[Parsed_ebur128_0 @ 0x0] t: 0.1  TARGET:-23 LUFS  "
                  "M: -20.0 S:-120.7  I: -20.0 LUFS  LRA: 0.0 LU  "
                  "FTPK: -3.0 dBFS  TPK: -3.0 dBFS\n")
        self.assertEqual(_measure(0, frames + _summary("-14.2", "-0.9")),
                         (-14.2, -0.9))

    def test_no_peak_in_the_summary_is_no_peak_known(self):
        self.assertEqual(_measure(0, _summary("-14.2", None)), (-14.2, None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
