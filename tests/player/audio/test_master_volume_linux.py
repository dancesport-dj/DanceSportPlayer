#!/usr/bin/env python3
"""🐧 The Linux sink volume as wpctl / pactl print it.

Run:  .venv\\Scripts\\python.exe -m unittest tests.player.audio.test_master_volume_linux -v
"""
import unittest
from unittest import mock

from player.audio import master_volume_linux as linux


class ParseVolumeTest(unittest.TestCase):
    def test_wpctl(self):
        self.assertEqual(linux.parse_volume("Volume: 0.47\n"), 0.47)
        self.assertEqual(linux.parse_volume("Volume: 0.07 [MUTED]\n"), 0.07)

    def test_pactl(self):
        out = "Volume: front-left: 30801 /  47% / -19.50 dB,   front-right: 30801 /  47%"
        self.assertEqual(linux.parse_volume(out.replace("Volume: ", "", 1)), 0.47)

    def test_garbage(self):
        self.assertIsNone(linux.parse_volume(""))


class MasterVolumeTest(unittest.TestCase):
    def test_falls_back_to_pactl_when_wpctl_is_missing(self):
        done = mock.Mock(returncode=0, stdout="front-left: 1 / 12% / -1 dB")
        with mock.patch.object(linux.subprocess, "run",
                               side_effect=[FileNotFoundError, done]):
            self.assertEqual(linux.master_volume(), 0.12)

    def test_nothing_answers(self):
        with mock.patch.object(linux.subprocess, "run", side_effect=FileNotFoundError):
            self.assertIsNone(linux.master_volume())


if __name__ == "__main__":
    unittest.main(verbosity=2)
