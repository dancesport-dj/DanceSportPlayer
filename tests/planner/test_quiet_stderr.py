#!/usr/bin/env python3
"""Muting the decoders' stderr from several threads gives stderr back.

Run:  py -m unittest tests.planner.test_quiet_stderr -v

Each decode pointed fd 2 at the null device and put back what it had saved.
The analysis pass decodes on a thread pool, so two decodes overlap: the second
one "saves" the null device the first had put there, the first restores the
real stderr, and then the second restores the null device — and every warning
and traceback of the rest of the session goes nowhere. The mute is now shared:
the first decode in redirects, the last one out restores.
"""

import os
import sys
import tempfile
import unittest

from planner.embeddings import _quiet_native_stderr


class QuietStderrTest(unittest.TestCase):

    def setUp(self):
        fd, self.log = tempfile.mkstemp(prefix="dp_stderr_")
        saved = os.dup(2)
        os.dup2(fd, 2)
        os.close(fd)
        self.addCleanup(os.remove, self.log)
        self.addCleanup(os.close, saved)
        self.addCleanup(os.dup2, saved, 2)

    def _written(self) -> bytes:
        with open(self.log, "rb") as f:
            return f.read()

    def test_overlapping_mutes_that_end_out_of_order_restore_stderr(self):
        first, second = _quiet_native_stderr(), _quiet_native_stderr()
        first.__enter__()
        second.__enter__()
        os.write(2, b"muted ")
        first.__exit__(None, None, None)
        second.__exit__(None, None, None)
        os.write(2, b"heard")
        self.assertEqual(self._written(), b"heard")

    @unittest.skipUnless(sys.platform == "win32", "Win32 STD_ERROR_HANDLE")
    def test_overlapping_mutes_restore_the_win32_stderr_handle(self):
        # ffmpeg, spawned by audioread, writes to the inherited Win32 handle. The
        # old restore put back a handle the fd-2 dup2 had already closed.
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        k32.GetStdHandle.restype = wintypes.HANDLE

        def write_win32(data: bytes) -> None:
            n = wintypes.DWORD()
            k32.WriteFile(wintypes.HANDLE(k32.GetStdHandle(-12)), data, len(data),
                          ctypes.byref(n), None)

        first, second = _quiet_native_stderr(), _quiet_native_stderr()
        first.__enter__()
        second.__enter__()
        write_win32(b"muted ")
        first.__exit__(None, None, None)
        second.__exit__(None, None, None)
        write_win32(b"heard")
        self.assertEqual(self._written(), b"heard")

    def test_a_single_mute_restores_stderr(self):
        with _quiet_native_stderr():
            os.write(2, b"muted ")
        os.write(2, b"heard")
        self.assertEqual(self._written(), b"heard")


if __name__ == "__main__":
    unittest.main(verbosity=2)
