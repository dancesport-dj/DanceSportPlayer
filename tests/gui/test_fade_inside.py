#!/usr/bin/env python3
"""🔉 The fade-out inside the play length, or after it.

Run:  py -m unittest tests.gui.test_fade_inside -v

A play length of 1:45 with a 3 s fade used to mean: the ramp starts at 1:42
and the title is silent at 1:45. Marcel wanted the other reading too — the
title plays its full 1:45 and then fades — as a tick box beside the fade-out,
on the ▶ Playing panel and in each play set (⚙ Settings → 🎛 Play sets), so
the 🏆 set's per-dance lengths follow it as well. The 🎉 set fades inside by
default, the 🏆 set after the length (see test_play_set_defaults).
"""

import os
import tempfile
import unittest
from unittest import mock

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_fadeinside_"))

from pathlib import Path

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

from gui.decks.running_order import Row
from planner.playing.play_sets import DANCE_SECS_KEY, play_set_of
from tests.qt_test_support import reap_widget, stub_window_startup


class PlaySetTest(unittest.TestCase):

    def test_a_heat_fades_after_the_length_a_party_inside_by_default(self):
        self.assertIs(play_set_of({}, "tournament")["fade_inside"], False)
        self.assertIs(play_set_of({}, "party")["fade_inside"], True)

    def test_a_set_can_fade_after_the_length(self):
        got = play_set_of({"tournament_set": {"fade_inside": False}}, "tournament")
        self.assertIs(got["fade_inside"], False)


class _WindowCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_fadeinside_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.panel = self.win._play_panel
        self.b = self.win._deckset.tableB
        # The 🏆 set pinned to a 3 s fade inside 1:45, so the sums below don't
        # move with the shipped defaults.
        self.win._settings["tournament_set"] = {"fade": 3.0, "fade_inside": True}
        self.win._settings[DANCE_SECS_KEY] = {}   # …and one length for all
        self.win._on_table_focused(self.b)   # first use: the 🏆 set

    def play(self, dance="LW"):
        self.win._on_deck_play(self.b)
        if not len(self.b._row_meta):
            self.b._row_meta.append(Row(dance=dance))
        self.b._current_play_row = 0
        self.win._playback.path = Path("C:/music/title.mp3")
        self.win._playback.dance = dance

    def tick_at(self, played):
        """One heartbeat with `played` seconds of music heard."""
        with mock.patch("player.window.main_player.audible_played_secs",
                        return_value=played), \
                mock.patch.object(self.win._player, "playbackState",
                                  return_value=QMediaPlayer.PlaybackState.PlayingState), \
                mock.patch.object(self.win, "_is_playing_mode", return_value=True), \
                mock.patch.object(self.win, "_on_timed_end") as end:
            self.win._on_play_tick()
        return end.called


class PanelTest(_WindowCase):

    def test_it_is_a_tick_box_again(self):
        """Marcel first had it made a switch like 🔈 Announce next dance, then:
        "make within the length toggle back to checkbox"."""
        from PySide6.QtWidgets import QCheckBox
        self.assertIsInstance(self.panel.fade_inside_check, QCheckBox)

    def test_the_box_follows_the_set(self):
        self.assertTrue(self.panel.fade_inside_check.isChecked())
        self.assertIs(self.panel.play_set()["fade_inside"], True)

    def test_nothing_stored_a_heat_starts_with_it_off(self):
        del self.win._settings["tournament_set"]
        self.win._apply_tournament_set()
        self.assertFalse(self.panel.fade_inside_check.isChecked())

    def test_unticked_it_is_the_lists_value(self):
        self.panel.fade_inside_check.setChecked(False)
        self.assertIs(self.win._list_vals(self.b)["fade_inside"], False)
        self.assertFalse(self.panel.tournament_btn.isChecked(),
                         "no longer the 🏆 set")

    def test_a_set_applied_says_where_the_fade_goes(self):
        changed = self.panel.apply_play_set(secs=105, advance=False,
                                            pause_off=True, fade_inside=False)
        self.assertIn("fade-out → after the length", changed)
        self.assertFalse(self.panel.fade_inside_check.isChecked())


class PlaybackTest(_WindowCase):

    def test_inside_the_fade_ends_at_the_length(self):
        self.play()
        self.assertEqual(self.win._play_end_secs(), 105)
        self.assertFalse(self.tick_at(103.5))
        self.assertAlmostEqual(self.win._mix.fade, 0.5)
        self.assertTrue(self.tick_at(105))

    def test_after_the_title_plays_its_full_length_then_fades(self):
        self.panel.fade_inside_check.setChecked(False)
        self.play()
        self.assertEqual(self.win._play_end_secs(), 108)
        self.assertFalse(self.tick_at(104))
        self.assertEqual(self.win._mix.fade, 1.0, "full volume up to 1:45")
        self.assertFalse(self.tick_at(106.5))
        self.assertAlmostEqual(self.win._mix.fade, 0.5)
        self.assertTrue(self.tick_at(108))

    def test_a_dances_own_length_fades_after_it_too(self):
        self.win._settings[DANCE_SECS_KEY] = {"WW": 90}
        self.win._settings["tournament_set"] = {"fade": 3.0, "fade_inside": False}
        self.win._apply_tournament_set()
        self.play("WW")
        self.assertEqual(self.win._play_end_secs(), 93)

    def test_full_length_has_no_cut_either_way(self):
        self.panel.fade_inside_check.setChecked(False)
        self.win._list_vals(self.b)["secs"] = 0
        self.play()
        self.assertEqual(self.win._play_end_secs(), 0)


class SettingsTabTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_each_set_has_the_box_and_saves_it(self):
        dlg = self._dlg({"tournament_set": {"fade_inside": False}})
        box = dlg._set_widgets["tournament"]["boxes"]["fade_inside"]
        self.assertFalse(box.isChecked())
        self.assertTrue(dlg._set_widgets["party"]["boxes"]["fade_inside"].isChecked())
        box.setChecked(True)
        self.assertIs(dlg.values()["tournament_set"]["fade_inside"], True)


if __name__ == "__main__":
    unittest.main()
