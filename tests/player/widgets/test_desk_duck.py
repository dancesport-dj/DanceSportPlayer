#!/usr/bin/env python3
"""Tests for the 🔉 duck button (`player.widgets.player` cards + `_set_desk_duck`).

Run:  py -m unittest tests.player.widgets.test_desk_duck -v

Ducking is what the operator reaches for to talk over the music, so it has to
come down far enough to talk over — 20 %, not the half-volume it used to be —
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
from tests.qt_test_support import reap_widget

from player.audio.mix import OutputMix, desk_duck_level
from player.window.main_audio import AudioLevelMixin
from player.window.main_player import _DESK_DUCK
from player.widgets.player import BigPlayerWidget, PreviewOverlay
from player.presenter.presenter import PresenterWindow
from gui.dialogs.settings_dialog import SettingsDialog


class DuckFactorTest(unittest.TestCase):

    def test_the_duck_goes_down_to_a_fifth(self):
        """Loud enough to keep the floor moving, quiet enough to talk over."""
        self.assertAlmostEqual(_DESK_DUCK, 0.2)


class DuckLevelSettingTest(unittest.TestCase):
    """Marcel: "for the duck in main player make a new setting under
    setting to configure duck %"."""

    def test_without_the_setting_it_is_a_fifth(self):
        self.assertAlmostEqual(desk_duck_level({}), 0.2)

    def test_the_setting_sets_it(self):
        self.assertAlmostEqual(desk_duck_level({"duck_pct": 35}), 0.35)

    def test_it_stays_below_full(self):
        """A duck to 100 % would be no duck — and the controller's toggle
        reads "full" as "not ducked"."""
        self.assertLess(desk_duck_level({"duck_pct": 100}), 1.0)
        self.assertEqual(desk_duck_level({"duck_pct": -5}), 0.0)

    def test_a_broken_value_falls_back(self):
        self.assertAlmostEqual(desk_duck_level({"duck_pct": "loud"}), 0.2)

    def test_the_mix_ducks_to_the_level_given(self):
        mix = OutputMix()
        self.assertAlmostEqual(mix.set_desk_duck(True, 0.35), 0.35)
        self.assertEqual(mix.set_desk_duck(False, 0.35), 1.0)


class _Desk:
    """`_set_desk_duck` with its window around it stubbed."""

    _set_desk_duck = AudioLevelMixin._set_desk_duck
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

    def test_it_starts_at_a_fifth(self):
        self.assertEqual(self.dialog({})._duck_spin.value(), 20)

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
        self.w.duckToggled.connect(got.append)
        self.w._duck_btn.click()
        self.assertEqual(got, [True])
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


class BigPlayerDuckTest(_DuckButtonMixin, unittest.TestCase):

    def _make(self):
        return BigPlayerWidget(QMediaPlayer())


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
