#!/usr/bin/env python3
"""🍎 The Mac output volume as osascript prints it.

Run:  .venv\\Scripts\\python.exe -m unittest tests.player.audio.test_master_volume_mac -v
"""
import unittest
from unittest import mock

from player.audio import master_volume_mac as mac


class ParseVolumeTest(unittest.TestCase):
    def test_a_percentage_becomes_a_fraction(self):
        self.assertEqual(mac.parse_volume("47\n"), 0.47)
        self.assertEqual(mac.parse_volume("100"), 1.0)

    def test_missing_value_is_unreadable(self):
        self.assertIsNone(mac.parse_volume("missing value\n"))
        self.assertIsNone(mac.parse_volume(""))


class MasterVolumeTest(unittest.TestCase):
    def test_no_osascript_is_unreadable(self):
        with mock.patch.object(mac.subprocess, "run", side_effect=FileNotFoundError):
            self.assertIsNone(mac.master_volume())

    def test_reads_the_script_output(self):
        done = mock.Mock(returncode=0, stdout="7\n")
        with mock.patch.object(mac.subprocess, "run", return_value=done):
            self.assertEqual(mac.master_volume(), 0.07)


if __name__ == "__main__":
    unittest.main(verbosity=2)
