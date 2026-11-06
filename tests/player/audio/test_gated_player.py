#!/usr/bin/env python3
"""⏯ The gate in front of play(): held back when the gate says so.

Run:  .venv\\Scripts\\python.exe -m unittest tests.player.audio.test_gated_player -v
"""
import unittest
from unittest import mock

from PySide6.QtMultimedia import QMediaPlayer

from player.audio.gated_player import GatedMediaPlayer
from tests.qt_test_support import qapp


class GatedPlayerTest(unittest.TestCase):
    def setUp(self):
        qapp()
        self.player = GatedMediaPlayer()

    def test_a_held_play_never_reaches_the_player(self):
        self.player.gate = lambda: True
        with mock.patch.object(QMediaPlayer, "play") as real:
            self.player.play()
        real.assert_not_called()

    def test_an_open_gate_plays(self):
        self.player.gate = lambda: False
        with mock.patch.object(QMediaPlayer, "play") as real:
            self.player.play()
        real.assert_called_once()

    def test_without_a_gate_it_plays(self):
        with mock.patch.object(QMediaPlayer, "play") as real:
            self.player.play()
        real.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
