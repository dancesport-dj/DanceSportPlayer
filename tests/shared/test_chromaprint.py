"""fpcalc discovery and its output, without the real binary."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from shared.audio import chromaprint as cp

OUT = "DURATION=215\nFINGERPRINT=-1,0,4294967295,7\n"


class FakeProc:
    def __init__(self, out=OUT, code=0):
        self._out, self.returncode = out, code

    def communicate(self, timeout=None):
        return self._out, ""

    def poll(self):
        return self.returncode

    def kill(self):
        pass


class ParseTests(unittest.TestCase):
    def test_duration_and_words(self):
        got = cp.parse_output(OUT)
        self.assertEqual(got.duration, 215.0)
        self.assertEqual(list(got.words), [0xFFFFFFFF, 0, 0xFFFFFFFF, 7])

    def test_no_fingerprint_line_is_none(self):
        self.assertIsNone(cp.parse_output("DURATION=3\n"))
        self.assertIsNone(cp.parse_output(""))

    def test_empty_fingerprint_is_none(self):
        self.assertIsNone(cp.parse_output("DURATION=3\nFINGERPRINT=\n"))


class RunTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.song = Path(self.dir.name) / "song.mp3"
        self.song.write_bytes(b"x")

    def test_runs_raw_with_the_length_limit(self):
        with mock.patch.object(cp.subprocess, "Popen",
                               return_value=FakeProc()) as popen:
            got = cp.fingerprint_file("fpcalc", self.song)
        args = popen.call_args.args[0]
        self.assertEqual(args[:4], ["fpcalc", "-raw", "-length", str(cp.LENGTH_SECS)])
        self.assertTrue(args[4].endswith("song.mp3"))
        self.assertEqual(got.duration, 215.0)

    def test_failed_run_is_none(self):
        with mock.patch.object(cp.subprocess, "Popen",
                               return_value=FakeProc("", code=2)):
            self.assertIsNone(cp.fingerprint_file("fpcalc", self.song))

    def test_missing_file_never_reaches_fpcalc(self):
        with mock.patch.object(cp.subprocess, "Popen") as popen:
            self.assertIsNone(cp.fingerprint_file("fpcalc", self.song.with_name("no.mp3")))
        popen.assert_not_called()

    def test_url_is_refused(self):
        with mock.patch.object(cp.subprocess, "Popen") as popen:
            self.assertIsNone(cp.fingerprint_file("fpcalc", "http://example.com/a.mp3"))
        popen.assert_not_called()

    def test_hands_the_process_to_on_proc(self):
        seen = []
        with mock.patch.object(cp.subprocess, "Popen", return_value=FakeProc()):
            cp.fingerprint_file("fpcalc", self.song, on_proc=seen.append)
        self.assertEqual(len(seen), 1)

    def test_os_error_is_none(self):
        with mock.patch.object(cp.subprocess, "Popen", side_effect=OSError("nope")):
            self.assertIsNone(cp.fingerprint_file("fpcalc", self.song))

    def test_a_timeout_kills_fpcalc_and_gives_none(self):
        proc = FakeProc()
        proc.communicate = mock.Mock(side_effect=[
            cp.subprocess.TimeoutExpired("fpcalc", 1), ("", "")])
        proc.kill = mock.Mock()
        with mock.patch.object(cp.subprocess, "Popen", return_value=proc):
            self.assertIsNone(cp.fingerprint_file("fpcalc", self.song))
        proc.kill.assert_called_once()

    def test_an_unreadable_path_is_none(self):
        with mock.patch.object(cp.Path, "is_file", side_effect=OSError("denied")), \
                mock.patch.object(cp.subprocess, "Popen") as popen:
            self.assertIsNone(cp.fingerprint_file("fpcalc", self.song))
        popen.assert_not_called()


class MalformedOutputTests(unittest.TestCase):
    def test_a_garbled_duration_counts_as_zero(self):
        got = cp.parse_output("DURATION=abc\nFINGERPRINT=1,2\n")
        self.assertEqual(got.duration, 0.0)
        self.assertEqual(list(got.words), [1, 2])

    def test_a_garbled_fingerprint_is_none(self):
        self.assertIsNone(cp.parse_output("DURATION=3\nFINGERPRINT=1,x,3\n"))


class FindTests(unittest.TestCase):
    def test_bundled_beats_path_and_cwd_is_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d) / "fpcalc.exe"
            exe.write_bytes(b"")
            with mock.patch.object(cp, "_BUNDLED_FPCALC", (exe,)):
                self.assertEqual(cp.find_fpcalc(), str(exe))
            with mock.patch.object(cp, "_BUNDLED_FPCALC", ()), \
                    mock.patch.object(cp, "_FPCALC_CANDIDATES", ()), \
                    mock.patch.object(cp.shutil, "which", return_value=str(Path.cwd() / "fpcalc.exe")):
                self.assertIsNone(cp.find_fpcalc())

    def test_fpcalc_on_path_is_used(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d) / "fpcalc.exe"
            exe.write_bytes(b"")
            with mock.patch.object(cp, "_BUNDLED_FPCALC", ()), \
                    mock.patch.object(cp, "_FPCALC_CANDIDATES", ()), \
                    mock.patch.object(cp.shutil, "which", return_value=str(exe)):
                self.assertEqual(cp.find_fpcalc(), str(exe))

    def test_a_package_manager_prefix_is_the_last_resort(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d) / "fpcalc"
            exe.write_bytes(b"")
            with mock.patch.object(cp, "_BUNDLED_FPCALC", ()), \
                    mock.patch.object(cp, "_FPCALC_CANDIDATES", (exe,)), \
                    mock.patch.object(cp.shutil, "which", return_value=None):
                self.assertEqual(cp.find_fpcalc(), str(exe))

    def test_none_when_nowhere(self):
        with mock.patch.object(cp, "_BUNDLED_FPCALC", ()), \
                mock.patch.object(cp, "_FPCALC_CANDIDATES", ()), \
                mock.patch.object(cp.shutil, "which", return_value=None):
            self.assertIsNone(cp.find_fpcalc())


if __name__ == "__main__":
    unittest.main()
