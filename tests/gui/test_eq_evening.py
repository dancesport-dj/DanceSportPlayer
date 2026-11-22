#!/usr/bin/env python3
"""🎚 The music EQ on through a whole evening, the real window.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_eq_evening -v

The parts are tested one by one (test_pair_route, test_eq_card); this walks
the window through what an evening does with the EQ on and checks that the
music never leaves the EQ path, nor stays on it once the EQ is off:
startup, crossfades both ways (the tail keeps its filter while it fades),
the idle sound-device hand-back and the next title taking it back, the EQ
switched off and on again mid-evening, bypass, and new bands.

"On the EQ path" means: the player feeds its tap and has no Qt output
(PairRoute._attach), and the route filters with the settings' bands.
"""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_eq_evening_"))

from PySide6.QtWidgets import QApplication

from planner.playing import equalizer as eqs
from player.audio import eq, pair_route, stretch_engines
from tests.qt_test_support import reap_widget, stub_window_startup

MAIN_SETTINGS = json.loads(
    (Path(__file__).parent / "golden" / "main_era_settings.json").read_text("utf-8"))


def _music_eq(on: bool = True, bypass: bool = False, gain: float = 4.0) -> dict:
    cfg = eqs.default_eq("music")
    cfg["on"], cfg["bypass"] = on, bypass
    cfg["bands"][1]["gain"] = gain
    return cfg


class EqEveningTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        settings = dict(MAIN_SETTINGS, equalizer={"music": _music_eq()},
                        **{eqs.PITCH_OK_KEY: True})
        cls.dg = stub_window_startup(cls, settings=settings)

    def setUp(self):
        self.addCleanup(stretch_engines.set_engine, stretch_engines.chosen())
        patcher = mock.patch.object(eq, "available", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.win = self.dg.MainWindow()
        self.addCleanup(reap_widget, self.win)
        # As on quit (aboutToQuit): the audio thread ends before the window goes.
        self.addCleanup(pair_route.stop_audio_thread)
        self.device = self.win._audio_device
        self.device.sync_eq()

    def set_eq(self, **kw):
        self.win._settings["equalizer"] = {"music": _music_eq(**kw)}
        self.device.sync_eq()

    def route(self, player):
        return self.device._routes.get(id(player))

    def assert_filtered(self, player, out, bands=None):
        """On the EQ path, filtering with `bands` (default: the settings')."""
        route = self.route(player)
        self.assertIsNotNone(route, "no route: the player is on Qt's output")
        self.assertIsNotNone(player.audioBufferOutput(), "the tap is off")
        self.assertIsNone(player.audioOutput(), "Qt's output plays alongside")
        want = eq.bands_for(self.win._settings, "music") if bands is None else bands
        self.assertEqual(route._eq_bands, want)

    def assert_qts_own(self, player, out):
        self.assertIs(player.audioOutput(), out)
        self.assertIsNone(player.audioBufferOutput())

    def deck(self):
        return self.win._player, self.win._audio_out

    def spare(self):
        xf = self.win._between.xfade
        return xf.player, xf.out

    # ===== Acceptance criteria =====

    def test_the_deck_starts_on_the_eq_path(self):
        self.assert_filtered(*self.deck())
        self.assertTrue(self.win._big_player._tools_btn.property("lit"))

    def test_a_crossfade_keeps_both_titles_filtered(self):
        """The new title comes in filtered, the old one fades out filtered:
        no jump in the sound halfway through the crossfade."""
        self.win._spare_deck()
        self.win._swap_decks()
        self.assert_filtered(*self.deck())
        self.assert_filtered(*self.spare())
        self.win._swap_decks()
        self.assert_filtered(*self.deck())
        self.assert_filtered(*self.spare())

    def test_the_idle_hand_back_and_the_next_title_keep_the_eq(self):
        # The spare gets the EQ when it becomes the deck (swap_deck).
        self.win._spare_deck()
        self.win._swap_decks()
        self.device.release()
        self.assertIsNone(self.win._player.audioOutput())
        self.device.ensure()
        self.assert_filtered(*self.deck())
        self.assert_filtered(*self.spare())

    def test_switching_the_eq_off_mid_evening_hands_both_decks_to_qt(self):
        self.win._spare_deck()
        self.win._swap_decks()
        self.set_eq(on=False)
        self.assert_qts_own(*self.deck())
        self.assert_qts_own(*self.spare())

    # ===== Core behavior =====

    def test_on_again_after_off_filters_both_decks_again(self):
        self.win._spare_deck()
        self.set_eq(on=False)
        self.set_eq(on=True)
        self.assert_filtered(*self.deck())
        self.assert_filtered(*self.spare())

    def test_bypass_stays_on_the_path_without_filtering(self):
        self.set_eq(bypass=True)
        self.assert_filtered(*self.deck(), bands=())

    def test_new_bands_reach_the_deck_and_the_spare(self):
        self.win._spare_deck()
        self.set_eq(gain=-6.0)
        bands = eq.bands_for(self.win._settings, "music")
        self.assertTrue(any(abs(b.gain + 6.0) < 1e-9 for b in bands))
        self.assert_filtered(*self.deck(), bands=bands)
        self.assert_filtered(*self.spare(), bands=bands)

    def test_an_edit_in_settings_is_heard_on_the_title_playing(self):
        """⚙ Settings sends every EQ edit (SettingsDialog eq_live_cb)."""
        self.win._spare_deck()
        heard = {"equalizer": {"music": _music_eq(gain=-6.0)}, eqs.PITCH_OK_KEY: True}
        self.win._hear_eq(heard)
        bands = eq.bands_for(heard, "music")
        self.assertTrue(any(abs(b.gain + 6.0) < 1e-9 for b in bands))
        self.assert_filtered(*self.deck(), bands=bands)
        self.assert_filtered(*self.spare(), bands=bands)

    def test_cancel_in_settings_without_a_stored_eq_hands_back_to_qt(self):
        self.win._hear_eq({"equalizer": None, eqs.PITCH_OK_KEY: None})
        self.assert_qts_own(*self.deck())

    def test_an_edit_in_settings_is_not_saved_before_ok(self):
        """Heard at once, but kept out of the window's settings: anything
        that saves them while the dialog is open (a deck autosave) would
        write an edit that Cancel is still to take back."""
        stored = copy.deepcopy(self.win._settings.get("equalizer"))
        self.win._hear_eq({"equalizer": {"music": _music_eq(gain=-6.0)},
                           eqs.PITCH_OK_KEY: True})
        self.assertEqual(self.win._settings.get("equalizer"), stored)
        self.win._end_eq_preview()   # Cancel: the stored EQ is heard again
        self.assert_filtered(*self.deck(), bands=eq.bands_for(self.win._settings, "music"))

    def test_a_crossfade_after_the_eq_went_off_stays_on_qt(self):
        self.win._spare_deck()
        self.set_eq(on=False)
        self.win._swap_decks()
        self.assert_qts_own(*self.deck())
        self.assert_qts_own(*self.spare())


if __name__ == "__main__":
    unittest.main()
