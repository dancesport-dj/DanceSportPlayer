#!/usr/bin/env python3
"""The crossfade's spare player becomes the deck, so it carries the headset gate too.

Run:  .venv/Scripts/python.exe -m unittest tests.player.window.test_spare_deck_gate -v
"""
import unittest
from unittest import mock

from player.window import main_xfade
from player.window.main_xfade import CrossfadeMixin


class SpareDeckGateTest(unittest.TestCase):
    def test_the_spare_deck_is_a_gated_player_with_the_hosts_gate(self):
        host = mock.Mock()
        host._between.xfade.player = None
        with mock.patch.object(main_xfade, "HAS_MULTIMEDIA", True),                 mock.patch.object(main_xfade, "GatedMediaPlayer") as gated,                 mock.patch.object(main_xfade, "QAudioOutput"),                 mock.patch.object(main_xfade, "QTimer"),                 mock.patch.object(main_xfade, "prime_disconnect_notify"):
            CrossfadeMixin._spare_deck(host)
        gated.assert_called_once()
        self.assertIs(gated.return_value.gate, host._headset_play_gate)


if __name__ == "__main__":
    unittest.main()
