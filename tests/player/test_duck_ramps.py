#!/usr/bin/env python3
"""🔈 How fast the music gets out of the way of a voice or a pad, and comes back.

Run:  py -m unittest tests.player.test_duck_ramps -v

Item 23b: the announcer's and the 🎛 pads' duck went down over a fixed 180 ms
and back up over 600 ms. ⚙ Settings ▸ Sound & player now sets both.
Marcel (F18): the way down defaults to 0.2 s, and both rows read in seconds
like the fade rows beside them; the settings file keeps milliseconds.
"""

import math
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_duck_ramps_"))

from PySide6.QtWidgets import QApplication

from player.audio.mix import (
    DUCK_DOWN_MS,
    DUCK_UP_MS,
    OutputMix,
    duck_ramp_ms,
)
from player.window.main_audio import AudioLevelMixin
from tests.qt_test_support import reap_widget


class SettingTest(unittest.TestCase):

    def test_the_defaults_unless_set(self):
        self.assertEqual(duck_ramp_ms({}), (DUCK_DOWN_MS, DUCK_UP_MS))
        self.assertEqual((DUCK_DOWN_MS, DUCK_UP_MS), (200, 600))

    def test_the_times_set(self):
        self.assertEqual(
            duck_ramp_ms({"duck_down_ms": 400, "duck_up_ms": 2000}), (400, 2000))

    def test_a_broken_value_is_its_default(self):
        self.assertEqual(
            duck_ramp_ms({"duck_down_ms": "fast", "duck_up_ms": None}),
            (DUCK_DOWN_MS, DUCK_UP_MS))

    def test_bounded(self):
        # Under one ramp step is a jump, and the ramp divides by it.
        self.assertEqual(duck_ramp_ms({"duck_down_ms": 0, "duck_up_ms": 99999}),
                         (OutputMix.step_ms, 5000))


class MixTest(unittest.TestCase):

    def steps_to_settle(self, mix):
        for n in range(1, 1000):
            mix.step()
            if mix.settled:
                return n
        self.fail("the ramp never settled")

    def test_the_duck_takes_the_times_set(self):
        mix = OutputMix()
        mix.set_duck_ramps(500, 1000)
        down = math.ceil(500 / OutputMix.step_ms)
        up = math.ceil(1000 / OutputMix.step_ms)
        for reason in ("announce", "cartwall"):
            with self.subTest(reason):
                mix.duck_reason(reason, True)
                self.assertIn(self.steps_to_settle(mix), (down, down + 1))
                mix.duck_reason(reason, False)
                self.assertIn(self.steps_to_settle(mix), (up, up + 1))


class _Desk:
    """`apply_duck_level` with its window around it stubbed."""

    _set_desk_duck = AudioLevelMixin._set_desk_duck
    _show_desk_duck = AudioLevelMixin._show_desk_duck
    apply_duck_level = AudioLevelMixin.apply_duck_level

    def __init__(self, settings):
        self._settings = settings
        self._mix = OutputMix()
        self._big_player = self._preview = self._presenter = None

    def _apply_volume(self):
        pass


class WindowTest(unittest.TestCase):

    def test_settings_reach_the_mix(self):
        desk = _Desk({"duck_down_ms": 300, "duck_up_ms": 1500})
        desk.apply_duck_level()
        self.assertEqual((desk._mix.duck_down_ms, desk._mix.duck_up_ms),
                         (300, 1500))


class DialogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_the_defaults_by_default(self):
        values = self._dialog({}).values()
        self.assertEqual((values["duck_down_ms"], values["duck_up_ms"]),
                         (DUCK_DOWN_MS, DUCK_UP_MS))

    def test_the_pick_is_saved(self):
        dlg = self._dialog({"duck_down_ms": 300, "duck_up_ms": 1200})
        self.assertEqual(dlg._duck_down_spin.value(), 0.3)
        self.assertEqual(dlg._duck_up_spin.value(), 1.2)
        dlg._duck_up_spin.setValue(2.0)
        self.assertEqual(dlg.values()["duck_up_ms"], 2000)

    def test_in_seconds_like_the_fade_rows(self):
        dlg = self._dialog({})
        for name in ("_duck_down_spin", "_duck_up_spin"):
            spin = getattr(dlg, name)
            with self.subTest(spin=name):
                self.assertEqual(spin.suffix(), dlg._fade_in_spin.suffix())
                self.assertEqual(spin.decimals(), dlg._fade_in_spin.decimals())
        self.assertEqual(dlg._duck_down_spin.value(), 0.2)
        self.assertEqual(dlg._duck_up_spin.value(), 0.6)

    def test_its_text_is_translated(self):
        from planner.i18n.lang_de import CATALOG
        dlg = self._dialog({})
        for text in (dlg._duck_down_lbl.text(), dlg._duck_up_lbl.text(),
                     dlg._duck_down_spin.toolTip()):
            with self.subTest(text=text[:20]):
                self.assertIn(text, CATALOG)


if __name__ == "__main__":
    unittest.main()
