"""🔊 Fuzz: ffmpeg's and fpcalc's stderr is another program's text.

Its wording changes between builds and a damaged file makes it print half
lines. The probes parse it in worker threads that only log a failure, so a
parser that raises loses the measure silently: each must answer its "no
measure" value instead.
"""
import math
import unittest

from hypothesis import given

from shared.audio import audio_probes, chromaprint
from tests.fuzz_support import fuzz, texts


class ProbeOutputFuzzTest(unittest.TestCase):
    @fuzz(150)
    @given(texts)
    def test_silence_parsers(self, s):
        for parse in (audio_probes.parse_silences, audio_probes.parse_title_silences,
                      audio_probes.parse_lead_silence, audio_probes.parse_tail_silence):
            spans = parse(s)
            self.assertIsInstance(spans, list)

    @fuzz(150)
    @given(texts)
    def test_level_parsers(self, s):
        self.assertIn(audio_probes.parse_hard_end(s), (True, False, None))
        floor = audio_probes.parse_noise_floor(s)
        self.assertTrue(floor is None or isinstance(floor, float))
        if floor is not None:
            self.assertFalse(math.isnan(floor))

    @fuzz(150)
    @given(texts)
    def test_fingerprint_parser(self, s):
        chromaprint.parse_output(s)


if __name__ == "__main__":
    unittest.main()
