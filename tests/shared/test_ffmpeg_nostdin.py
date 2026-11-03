"""🎚️ Every ffmpeg probe leaves the parent's stdin alone (#20.11).

Launched from a console, an ffmpeg that inherits stdin can read the keys typed
there, and on a Unix terminal stop on SIGTTIN, so the probe sat until its
timeout and reported "probe failed". `-nostdin` keeps it off the input.
"""
import contextlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from player.audio import announce
from shared.audio import audio_probes as ap


class NoStdinTest(unittest.TestCase):

    def setUp(self):
        folder = Path(tempfile.mkdtemp(prefix="dp_nostdin_"))
        self.clip = folder / "clip.mp3"
        self.clip.write_bytes(b"ID3")
        self.calls = []

        def fake(args, *a, **kw):
            self.calls.append(list(args))
            return mock.MagicMock(returncode=1, stdout="", stderr="",
                                  communicate=lambda timeout=None: ("", ""))

        for target in ("subprocess.run", "subprocess.Popen"):
            patch = mock.patch(target, side_effect=fake)
            patch.start()
            self.addCleanup(patch.stop)

    def _asked(self, call):
        with contextlib.suppress(Exception):    # the fake process answers nothing useful
            call()
        self.assertEqual(len(self.calls), 1)
        return self.calls[0]

    def test_each_probe_says_nostdin(self):
        probes = {
            "loudness": lambda: ap.measure_loudness("ffmpeg", self.clip),
            "pcm": lambda: _with_ffmpeg(lambda: ap.decode_pcm_mono(self.clip)),
            "silences": lambda: ap.detect_silences("ffmpeg", self.clip),
            "hard end": lambda: ap.detect_hard_end("ffmpeg", self.clip),
            "noise floor": lambda: ap.measure_noise_floor("ffmpeg", self.clip),
            "announcement trim": lambda: announce._silencedetect("ffmpeg", self.clip),
        }
        for name, probe in probes.items():
            with self.subTest(name):
                self.calls.clear()
                self.assertIn("-nostdin", self._asked(probe))


def _with_ffmpeg(call):
    with mock.patch.object(ap, "find_ffmpeg", return_value="ffmpeg"):
        return call()


if __name__ == "__main__":
    unittest.main()
