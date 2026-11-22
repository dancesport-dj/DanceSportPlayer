#!/usr/bin/env python3
"""🔊 With settings as main wrote them, the music plays exactly main's way.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_default_playback_path -v

Main (before the equalizer branch) had every player straight on Qt's own
output: no tap, no audio thread, Qt's own pitch-kept tempo. A settings file
from main has no equalizer and no ⏩ Tempo key, so every EQ is off and the
tempo is Qt's: nothing of the branch's tapped path may be built, on the deck,
the crossfade's second deck, the pre-listen or the announcer — not at
startup, not after an output event, not across a crossfade.

`tests/gui/golden/main_era_settings.json` is main's own load_settings()
(669ebbe2, the per-machine paths blanked).
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_default_path_"))

from PySide6.QtWidgets import QApplication

from player.audio import pair_route, stretch_engines
from tests.qt_test_support import reap_widget, stub_window_startup

MAIN_SETTINGS = json.loads(
    (Path(__file__).parent / "golden" / "main_era_settings.json").read_text("utf-8"))


class DefaultPlaybackPathTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.dg = stub_window_startup(cls, settings=MAIN_SETTINGS)

    def setUp(self):
        self.addCleanup(stretch_engines.set_engine, stretch_engines.chosen())
        self.addCleanup(pair_route.stop_audio_thread)
        self.win = self.dg.MainWindow()
        self.addCleanup(reap_widget, self.win)
        self.device = self.win._audio_device

    def assert_mains_path(self):
        """Nothing tapped anywhere; the deck on its own Qt output."""
        self.assertEqual(self.device._routes, {}, "a music route was built")
        self.assertIsNone(self.device._music_eq)
        self.assertIsNone(pair_route._thread, "the audio thread was started")
        self.assertIs(self.win._player.audioOutput(), self.win._audio_out)
        cue = self.device.cue
        if cue is not None:
            self.assertFalse(cue._route.tapped, "the pre-listen is tapped")
        announcer = getattr(self.win, "_announcer", None)
        if announcer is not None:
            self.assertIsNone(announcer._eq, "the announcer has an EQ")

    # ===== Acceptance criteria =====

    def test_at_startup_nothing_is_tapped(self):
        self.assert_mains_path()

    def test_an_output_event_taps_nothing(self):
        """sync runs on every device change, settings save and swap."""
        self.device.sync()
        self.device.sync_eq()
        self.assert_mains_path()

    def test_a_crossfade_taps_neither_deck(self):
        self.win._spare_deck()
        self.win._swap_decks()
        self.assert_mains_path()
        spare = self.win._between.xfade
        self.assertIs(spare.player.audioOutput(), spare.out)
        self.win._swap_decks()
        self.assert_mains_path()

    # ===== Core behavior =====

    def test_the_tempo_is_qts_own(self):
        self.assertEqual(stretch_engines.chosen(), stretch_engines.QT)
        self.assertFalse(stretch_engines.taps_music())

    def test_a_tempo_change_goes_to_the_player_alone(self):
        """As on main: the rate reaches Qt, no stretch of the app's is made."""
        self.win._player.setPlaybackRate(1.08)
        self.device.sync()
        self.assert_mains_path()


if __name__ == "__main__":
    unittest.main()
