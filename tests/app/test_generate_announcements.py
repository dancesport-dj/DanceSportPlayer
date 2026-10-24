#!/usr/bin/env python3
"""The announcement generator says so when clips are missing.

Run:  py -m unittest tests.app.test_generate_announcements -v

L25: one clip made and twenty failed still ended with exit code 0, so a
build script or a shell loop read the run as done and shipped the gaps.
"""

import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from speech import generate_announcements as gen


class _FlakyTTS:
    """The first clip comes back, every later one fails."""

    def __init__(self):
        self.calls = 0

    def convert(self, **_kw):
        self.calls += 1
        if self.calls > 1:
            raise RuntimeError("quota exceeded")
        return [b"ID3"]


class ExitCodeTest(unittest.TestCase):

    def setUp(self):
        self.out = Path(tempfile.mkdtemp(prefix="dp_tts_"))
        self.addCleanup(shutil.rmtree, self.out, True)
        self.tts = _FlakyTTS()
        client_mod = types.ModuleType("elevenlabs.client")
        client_mod.ElevenLabs = lambda api_key: types.SimpleNamespace(
            text_to_speech=self.tts)
        patches = [
            mock.patch.dict(sys.modules, {"elevenlabs": types.ModuleType("elevenlabs"),
                                          "elevenlabs.client": client_mod}),
            mock.patch.object(gen, "get_api_key", return_value="test"),
            mock.patch.object(gen, "SPEEDS", {}),
            mock.patch.object(gen, "announcement_jobs", return_value=[
                ("male", f"german/{code}", code, self.out / f"{code}.mp3")
                for code in ("LW", "TG", "WW")]),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def run_main(self) -> int:
        with mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            return gen.main()

    def test_one_clip_made_and_two_failed_is_not_success(self):
        self.assertNotEqual(self.run_main(), 0)
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), ["LW.mp3"])

    def test_every_clip_made_is_success(self):
        self.tts.calls = -10            # nothing fails
        self.assertEqual(self.run_main(), 0)

    def test_nothing_left_to_make_is_success(self):
        for code in ("LW", "TG", "WW"):
            (self.out / f"{code}.mp3").write_bytes(b"ID3")
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(self.tts.calls, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
