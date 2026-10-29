#!/usr/bin/env python3
"""Tests for the 🔉 duck button (`player.widgets.player` cards + `_set_desk_duck`).

Run:  py -m unittest tests.player.widgets.test_desk_duck -v

Ducking is what the operator reaches for to talk over the music, so it has to
come down far enough to talk over — 10 %, not the half-volume it used to be —
and the button has to *look* held down while it is on: the emoji alone is far
too small a difference to read across a hall from the desk.

Both player UIs carry the same button, so both are pinned here.
"""

import os
import tempfile
import unittest
from types import SimpleNamespace

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_duck_"))

from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QApplication

from gui.dialogs.settings_dialog import SettingsDialog
from player.audio.mix import DESK_DUCK_PCT, OutputMix, desk_duck_level
from player.presenter.presenter import PresenterWindow
from player.widgets.player import BigPlayerWidget, PreviewOverlay
from player.window.main_audio import AudioLevelMixin
from player.window.main_player import DESK_DUCK
from tests.qt_test_support import reap_widget


class DuckFactorTest(unittest.TestCase):

    def test_the_duck_goes_down_to_a_tenth(self):
        """Loud enough to keep the floor moving, quiet enough to talk over."""
        self.assertAlmostEqual(DESK_DUCK, 0.1)


class DuckLevelSettingTest(unittest.TestCase):
    """Marcel: "for the duck in main player make a new setting under
    setting to configure duck %"."""

    def test_without_the_setting_it_is_a_tenth(self):
        self.assertAlmostEqual(desk_duck_level({}), 0.1)

    def test_the_setting_sets_it(self):
        self.assertAlmostEqual(desk_duck_level({"duck_pct": 35}), 0.35)

    def test_it_stays_below_full(self):
        """A duck to 100 % would be no duck — and the controller's toggle
        reads "full" as "not ducked"."""
        self.assertLess(desk_duck_level({"duck_pct": 100}), 1.0)
        self.assertEqual(desk_duck_level({"duck_pct": -5}), 0.0)

    def test_a_broken_value_falls_back(self):
        self.assertAlmostEqual(desk_duck_level({"duck_pct": "loud"}), 0.1)

    def test_the_mix_ducks_to_the_level_given(self):
        mix = OutputMix()
        self.assertAlmostEqual(mix.set_desk_duck(True, 0.35), 0.35)
        self.assertEqual(mix.set_desk_duck(False, 0.35), 1.0)


class _Desk:
    """`_set_desk_duck` with its window around it stubbed."""

    _set_desk_duck = AudioLevelMixin._set_desk_duck
    _set_desk_mute = AudioLevelMixin._set_desk_mute
    _cycle_desk_duck = AudioLevelMixin._cycle_desk_duck
    _show_desk_duck = AudioLevelMixin._show_desk_duck
    apply_duck_level = AudioLevelMixin.apply_duck_level

    def __init__(self, pct):
        self._settings = {"duck_pct": pct}
        self._mix = OutputMix()
        self._big_player = self._preview = self._presenter = None
        self.applied = 0

    def _apply_volume(self):
        self.applied += 1


class DuckLevelWindowTest(unittest.TestCase):

    def test_the_button_ducks_to_the_set_level(self):
        desk = _Desk(35)
        desk._set_desk_duck(True)
        self.assertAlmostEqual(desk._mix.desk, 0.35)

    def test_a_new_level_reaches_a_running_duck(self):
        desk = _Desk(35)
        desk._set_desk_duck(True)
        desk._settings["duck_pct"] = 50
        desk.apply_duck_level()
        self.assertAlmostEqual(desk._mix.desk, 0.5)

    def test_a_new_level_does_not_duck_by_itself(self):
        desk = _Desk(35)
        desk.apply_duck_level()
        self.assertEqual(desk._mix.desk, 1.0)

    def test_the_buttons_name_the_level(self):
        seen = []
        card = SimpleNamespace(set_duck_level=seen.append)
        desk = _Desk(35)
        desk._big_player = desk._preview = desk._presenter = card
        desk.apply_duck_level()
        self.assertEqual(seen, [35, 35, 35])


class DeskCycleTest(unittest.TestCase):
    """Marcel: "Three-state mute button: 100% → duck → muted → 100%, with the
    correct icon for each state." """

    def setUp(self):
        self.desk = _Desk(35)
        self.shown = []
        card = SimpleNamespace(
            set_ducked=lambda on, muted=False: self.shown.append((on, muted)),
            set_duck_level=lambda pct: None)
        self.desk._big_player = self.desk._preview = self.desk._presenter = card

    def test_full_then_duck_then_mute_then_full(self):
        mix = self.desk._mix
        self.desk._cycle_desk_duck()
        self.assertAlmostEqual(mix.desk, 0.35)
        self.assertFalse(mix.desk_muted)
        self.desk._cycle_desk_duck()
        self.assertEqual(mix.desk, 0.0)
        self.assertTrue(mix.desk_muted)
        self.desk._cycle_desk_duck()
        self.assertEqual(mix.desk, 1.0)
        self.assertFalse(mix.desk_muted)

    def test_every_button_is_told_the_state(self):
        self.desk._cycle_desk_duck()
        self.desk._cycle_desk_duck()
        self.desk._cycle_desk_duck()
        self.assertEqual(self.shown, [(True, False)] * 3 + [(True, True)] * 3
                         + [(False, False)] * 3)

    def test_a_new_duck_level_leaves_a_mute_alone(self):
        self.desk._cycle_desk_duck()
        self.desk._cycle_desk_duck()
        self.desk._settings["duck_pct"] = 50
        self.desk.apply_duck_level()
        self.assertEqual(self.desk._mix.desk, 0.0)
        self.assertTrue(self.desk._mix.desk_muted)

    def test_a_silent_duck_level_is_still_a_duck(self):
        """0 % ducks to silence, but the next press still mutes, not lifts."""
        self.desk._settings["duck_pct"] = 0
        self.desk._cycle_desk_duck()
        self.assertFalse(self.desk._mix.desk_muted)
        self.desk._cycle_desk_duck()
        self.assertTrue(self.desk._mix.desk_muted)

    def test_the_controller_toggle_lifts_a_mute(self):
        """The 🎛 controller's duck is still a two-way toggle: from mute it
        goes back to full, like from a duck."""
        self.desk._set_desk_mute(True)
        self.desk._set_desk_duck(self.desk._mix.desk == 1.0)
        self.assertEqual(self.desk._mix.desk, 1.0)
        self.assertFalse(self.desk._mix.desk_muted)

    def test_the_mix_mutes_and_unmutes(self):
        mix = OutputMix()
        mix.set_desk_mute(True)
        self.assertEqual(mix.deck(), 0.0)
        self.assertEqual(mix.cartwall(), 0.0)
        mix.set_desk_mute(False)
        self.assertEqual(mix.desk, 1.0)
        mix.set_desk_mute(True)
        mix.set_desk_duck(True, 0.2)
        self.assertFalse(mix.desk_muted)


class DuckLevelDialogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def dialog(self, settings):
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_it_shows_the_saved_level(self):
        self.assertEqual(self.dialog({"duck_pct": 35})._duck_spin.value(), 35)

    def test_it_starts_at_a_tenth(self):
        self.assertEqual(self.dialog({})._duck_spin.value(), 10)

    def test_it_is_saved(self):
        dlg = self.dialog({})
        dlg._duck_spin.setValue(40)
        self.assertEqual(dlg.values()["duck_pct"], 40)


class _DuckButtonMixin:
    """The same two rules for whichever card `_make()` builds."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.w = self._make()
        self.addCleanup(reap_widget, self.w)

    def test_the_button_stays_pressed_while_ducked(self):
        got = []
        self.w.duckPressed.connect(lambda: got.append(1))
        self.w._duck_btn.click()
        self.assertEqual(got, [1])
        self.w.set_ducked(True)                   # MainWindow reports back
        self.assertTrue(self.w._duck_btn.isChecked())

    def test_it_comes_back_up_when_the_duck_ends(self):
        self.w.set_ducked(True)
        self.w.set_ducked(False)
        self.assertFalse(self.w._duck_btn.isChecked())

    def test_its_tooltip_names_the_level(self):
        self.w.set_duck_level(35)
        self.assertIn("35 %", self.w._duck_btn.toolTip())

    def test_the_click_alone_does_not_leave_it_pressed(self):
        """A checkable button toggles itself on click — but the duck is only
        really on once MainWindow has applied it, so the click must hand the
        state straight back to `_ducked`."""
        self.w._duck_btn.click()                  # nobody listening
        self.assertFalse(self.w._duck_btn.isChecked())

    def test_it_stays_pressed_while_muted(self):
        self.w.set_ducked(True, muted=True)
        self.assertTrue(self.w._duck_btn.isChecked())

    def test_each_state_has_its_own_icon(self):
        def look():
            return self.w._duck_btn.icon().pixmap(16, 16).toImage()
        full = look()
        self.w.set_ducked(True)
        duck = look()
        self.w.set_ducked(True, muted=True)
        mute = look()
        self.assertNotEqual(full, duck)
        self.assertNotEqual(duck, mute)
        self.assertNotEqual(full, mute)
        self.w.set_ducked(False)
        self.assertEqual(look(), full)

    def test_its_tooltip_names_the_mute_step(self):
        self.w.set_duck_level(35)
        self.assertIn("mute", self.w._duck_btn.toolTip())

    def test_it_names_the_default_level_before_any_setting(self):
        """No left-over "20 %" from before the level became a setting."""
        self.assertIn(f"{DESK_DUCK_PCT} %", self.w._duck_btn.toolTip())


class BigPlayerDuckTest(_DuckButtonMixin, unittest.TestCase):

    def _make(self):
        return BigPlayerWidget(QMediaPlayer())

    def test_the_readout_says_duck_or_mute(self):
        self.w.set_ducked(True)
        self.assertEqual(self.w._vol_lbl.text(), "duck")
        self.w.set_ducked(True, muted=True)
        self.assertEqual(self.w._vol_lbl.text(), "mute")
        self.w.set_ducked(False)
        self.assertTrue(self.w._vol_lbl.text().endswith("%"))

    def _fill(self):
        """The colour of the pressed button's face, above its icon."""
        btn = self.w._duck_btn
        btn.resize(40, 28)
        return btn.grab().toImage().pixelColor(20, 3).name()

    def test_the_button_is_orange_ducked_and_red_muted(self):
        # Marcel: the readout said "mute" in red, the button stayed orange.
        self.w.set_ducked(True)
        self.assertEqual(self._fill(), "#d98f3a")
        self.w.set_ducked(True, muted=True)
        self.assertEqual(self._fill(), "#d9534f")
        self.w.set_ducked(True)
        self.assertEqual(self._fill(), "#d98f3a")


class PreviewOverlayDuckTest(_DuckButtonMixin, unittest.TestCase):

    def _make(self):
        return PreviewOverlay(QMediaPlayer(), QAudioOutput())


class PresenterDuckTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_its_tooltip_names_the_level(self):
        w = PresenterWindow(lambda: ("LW", "Titel", ("00:10", "− 02:00", False, 0.1),
                                     [("TG", "Zweiter")], ("", "")))
        self.addCleanup(reap_widget, w)
        w.set_duck_level(35)
        self.assertIn("35 %", w.duck_btn.toolTip())
        self.assertIn("mute", w.duck_btn.toolTip())

    def test_it_asks_and_follows_the_three_states(self):
        w = PresenterWindow(lambda: ("LW", "Titel", ("00:10", "− 02:00", False, 0.1),
                                     [("TG", "Zweiter")], ("", "")))
        self.addCleanup(reap_widget, w)
        got = []
        w.duckPressed.connect(lambda: got.append(1))
        w.duck_btn.click()
        self.assertEqual(got, [1])
        self.assertFalse(w.duck_btn.isChecked())
        w.set_ducked(True, muted=True)
        self.assertTrue(w.duck_btn.isChecked())
        w.set_ducked(False)
        self.assertFalse(w.duck_btn.isChecked())


if __name__ == "__main__":
    unittest.main(verbosity=2)
