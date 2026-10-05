#!/usr/bin/env python3
"""The built-in folder defaults, which cannot be the same on every OS.

Run:  py -m unittest tests.planner.test_platform_defaults -v

`C:\\Users\\…` and `D:\\Dropbox\\Turniere` name volumes of the Windows
PC. A Mac has no drive letters at all, so a default written that way is not
merely wrong there — it is unreachable, and every fallback built on top of it
(the file dialogs, the library browser, the Referenzpfad) starts from a folder
that can never exist. The same library lives under the home folder there.

Settings and the environment still win: these are only what is used when
nothing has been configured yet.
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

from planner.config import _default_music_dir, _default_playlist_dir


class MusicDirDefaultTest(unittest.TestCase):

    def test_windows_reads_it_out_of_the_home_folder(self):
        """Documents/datein/my music/tanzcds under whoever is logged in, not
        one machine's user name spelled into the source."""
        home = Path(r"C:\Users\someone")
        with mock.patch.object(sys, "platform", "win32"), \
             mock.patch.object(Path, "home", return_value=home):
            self.assertEqual(_default_music_dir(),
                             home / "Documents" / "datein" / "my music" / "tanzcds")

    def test_the_mac_reads_it_out_of_the_home_folder(self):
        """/Users/<user>/Music/my music/tanzcds — where Marcel's Mac keeps it."""
        with mock.patch.object(sys, "platform", "darwin"):
            got = _default_music_dir()
        self.assertEqual(got, Path.home() / "Music" / "my music" / "tanzcds")

    def test_the_mac_default_is_built_from_the_home_folder(self):
        """Not a literal path of any machine: it has to follow whoever is
        logged in. (Run on Windows, `Path.home()` is still a C: path — the
        point is where the default comes FROM, not how it is spelled.)"""
        with mock.patch.object(sys, "platform", "darwin"):
            got = _default_music_dir()
        self.assertTrue(got.is_absolute())
        self.assertTrue(got.is_relative_to(Path.home()))
        self.assertNotIn("Marcel", got.relative_to(Path.home()).parts)


class PlaylistDirDefaultTest(unittest.TestCase):

    def test_windows_keeps_the_drive_it_has(self):
        with mock.patch.object(sys, "platform", "win32"):
            self.assertEqual(_default_playlist_dir(), Path(r"D:\Dropbox\Turniere"))

    def test_the_mac_reads_it_out_of_the_home_folder(self):
        with mock.patch.object(sys, "platform", "darwin"):
            self.assertEqual(_default_playlist_dir(),
                             Path.home() / "Dropbox" / "Turniere")


if __name__ == "__main__":
    unittest.main(verbosity=2)
