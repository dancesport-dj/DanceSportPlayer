"""🔒 tools/audio/make_lw_snippets.py must find ffmpeg the guarded way.

Run:  py -m unittest tests.app.test_make_lw_snippets -v

The tool is pointed at music folders from other people. Windows looks in the
current folder before PATH, so a planted ffmpeg.exe there would run with the
user's rights. The project's own find_ffmpeg refuses that; the tool must use it
instead of keeping a copy that does not.
"""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from shared.audio import audio_probes
from tools.audio import make_lw_snippets


class FindFfmpegTest(unittest.TestCase):

    def test_the_tool_uses_the_guarded_lookup(self):
        self.assertIs(make_lw_snippets.find_ffmpeg, audio_probes.find_ffmpeg)


class MainTest(unittest.TestCase):

    def run_main(self, folder, names, ok):
        for n in names:
            (folder / n).write_bytes(b"x")
        cut = mock.Mock(side_effect=lambda *a, **k: (ok, "" if ok else "boom"))
        with (mock.patch.object(make_lw_snippets, "find_ffmpeg", return_value="ffmpeg"),
              mock.patch.object(make_lw_snippets, "cut_snippet", cut),
              mock.patch("sys.argv", ["x", str(folder), "-o", str(folder)])):
            return make_lw_snippets.main(), cut

    def test_every_cut_failing_is_not_success(self):
        """#66"""
        with tempfile.TemporaryDirectory() as d:
            code, _cut = self.run_main(Path(d), ["a LW.mp3"], ok=False)
        self.assertEqual(code, 1)

    def test_its_own_snippets_are_not_cut_again(self):
        with tempfile.TemporaryDirectory() as d:
            code, cut = self.run_main(Path(d), ["a LW.mp3", "a LW_snippet.mp3"], ok=True)
        self.assertEqual(code, 0)
        self.assertEqual(cut.call_count, 1)

    def test_the_docstring_names_the_real_default_limit(self):
        """#67"""
        self.assertIn("at most 100 files", make_lw_snippets.__doc__)


if __name__ == "__main__":
    unittest.main()
