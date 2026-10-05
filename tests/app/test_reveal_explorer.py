#!/usr/bin/env python3
"""Tests for 📂 Show in Explorer (`common.reveal_in_explorer`).

Run:  py -m unittest tests.app.test_reveal_explorer -v

The file has to end up SELECTED, not merely have its folder opened — in a folder
of a few hundred tracks the folder alone is no help. `explorer.exe /select` is
only a request to the shell, and the shell drops it when a window for that
folder is already open, so the shell's own SHOpenFolderAndSelectItems goes
first and the command line is the fallback.

That fallback has a trap of its own: explorer.exe parses its own command line,
so the quotes must sit around the PATH alone. Handing subprocess a LIST quotes
the whole argument as soon as the path holds a space — "/select,F:\\my
music\\tanzcds\\x.mp3" — which explorer reads as one folder name, fails to find,
and answers by opening Documents. The music library lives under "F:\\my music",
so every reveal from it landed there.
"""

import ctypes
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_reveal_"))

from gui import common  # noqa: E402


@unittest.skipUnless(sys.platform == "win32", "explorer.exe is Windows-only")
class _RevealTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp reveal "))   # a space on purpose
        self.file = self.dir / "track one.mp3"
        self.file.write_bytes(b"x")

    def _shell(self, works: bool):
        return mock.patch.object(common, "_select_in_explorer_shell",
                                 return_value=works)


class ShellSelectTest(_RevealTest):
    """The shell API is what actually highlights the file, so it goes first."""

    def test_the_shell_does_it_and_no_process_is_launched(self):
        with self._shell(True) as shell, \
             mock.patch.object(common.subprocess, "Popen") as popen:
            common.reveal_in_explorer(self.file)
        shell.assert_called_once()
        popen.assert_not_called()

    def test_the_ctypes_plumbing_really_works(self):
        """Guards the mock above. ctypes defaults every return to int, which on
        64-bit truncates the ID-list POINTER into an invalid one — and a fully
        stubbed test would never notice. So this drives the real shell32 calls
        and stubs out only the last one, which is the one that opens a window."""
        with mock.patch.object(ctypes.windll.shell32,
                               "SHOpenFolderAndSelectItems") as opened:
            self.assertTrue(common._select_in_explorer_shell(self.file))
        opened.assert_called_once()
        pidl = opened.call_args[0][0]
        self.assertTrue(pidl, "no ID list was built for the file")

    def test_a_path_that_is_not_there_is_reported_not_claimed(self):
        """It answers False rather than pretending, so the caller falls back."""
        with mock.patch.object(ctypes.windll.shell32,
                               "SHOpenFolderAndSelectItems") as opened:
            self.assertFalse(
                common._select_in_explorer_shell(self.dir / "never.mp3"))
        opened.assert_not_called()


class CommandLineFallbackTest(_RevealTest):
    """When the shell call can't be made, the command line still has to be right."""

    def _cmd(self) -> str:
        with self._shell(False), \
             mock.patch.object(common.subprocess, "Popen") as popen:
            common.reveal_in_explorer(self.file)
        self.assertTrue(popen.called, "explorer was never launched")
        return popen.call_args[0][0]

    def test_the_path_is_quoted_on_its_own(self):
        cmd = self._cmd()
        self.assertIsInstance(cmd, str, "a list argument gets quoted as a whole")
        self.assertIn(f'/select,"{self.file}"', cmd)

    def test_it_starts_with_explorer_unquoted(self):
        """`"explorer /select,…"` as one quoted blob is not a program name."""
        self.assertTrue(self._cmd().startswith("explorer /select,"))


class MissingFileTest(_RevealTest):

    def test_a_file_that_is_gone_launches_nothing(self):
        self.file.unlink()
        with mock.patch.object(common.subprocess, "Popen") as popen, \
             mock.patch.object(common, "_select_in_explorer_shell") as shell, \
             mock.patch.object(common.QMessageBox, "warning") as warn:
            common.reveal_in_explorer(self.file)
        popen.assert_not_called()
        shell.assert_not_called()
        warn.assert_called_once()


if __name__ == "__main__":
    unittest.main()
