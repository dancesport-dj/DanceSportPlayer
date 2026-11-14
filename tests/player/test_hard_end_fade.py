"""✂️ How long a title that stops in full sound is faded out is a setting.

The fixed 1.0 s was too short on the floor for a show's abrupt endings; the
default is now 2 s and ⚙ Settings ▸ Sound & player changes it.

Run:  py -m unittest tests.player.test_hard_end_fade -v
"""
import unittest

from PySide6.QtWidgets import QApplication

from player.audio.mix import HARD_END_FADE_DEFAULT_SECS, hard_end_fade_secs
from tests.player.test_resume_mark import TRACK, _FakeWindow, _player_mixin
from tests.qt_test_support import reap_widget


class SettingTest(unittest.TestCase):

    def test_two_seconds_by_default(self):
        self.assertEqual(HARD_END_FADE_DEFAULT_SECS, 2.0)
        self.assertEqual(hard_end_fade_secs({}), 2.0)

    def test_the_pick_is_used(self):
        self.assertEqual(hard_end_fade_secs({"hard_end_fade_secs": 3.5}), 3.5)

    def test_a_broken_value_is_the_default(self):
        self.assertEqual(hard_end_fade_secs({"hard_end_fade_secs": "soon"}), 2.0)
        self.assertEqual(hard_end_fade_secs({"hard_end_fade_secs": None}), 2.0)

    def test_the_value_stays_between_half_a_second_and_five(self):
        self.assertEqual(hard_end_fade_secs({"hard_end_fade_secs": 0.2}), 0.5)
        self.assertEqual(hard_end_fade_secs({"hard_end_fade_secs": 99}), 5.0)

    def test_zero_is_off(self):
        # Marcel: "Off" below the half second — the title ends as its file does.
        self.assertEqual(hard_end_fade_secs({"hard_end_fade_secs": 0}), 0.0)
        self.assertEqual(hard_end_fade_secs({"hard_end_fade_secs": -1}), 0.0)


class LevelTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        class Win(_FakeWindow, _player_mixin()):
            def _looping(self):
                return False
        cls.Win = Win

    def window(self, left_ms, settings=None):
        w = self.Win(pos_ms=180_000 - left_ms, dur_ms=180_000)
        w._playback.hard_ends[str(TRACK)] = True
        w._settings.update(settings or {})
        return w

    def test_the_fade_runs_over_the_chosen_time(self):
        # 1.2 s left: 1.0 s of fade left after the 0.2 s lead, of 2 s by default
        self.assertAlmostEqual(self.window(1200)._hard_end_level(), 0.5, places=2)

    def test_a_longer_pick_starts_the_fade_earlier(self):
        w = self.window(1200, {"hard_end_fade_secs": 4.0})
        self.assertAlmostEqual(w._hard_end_level(), 0.25, places=2)

    def test_off_leaves_the_end_at_full_level(self):
        w = self.window(100, {"hard_end_fade_secs": 0})
        self.assertEqual(w._hard_end_level(), 1.0)

    def test_a_file_that_does_not_stop_in_full_sound_is_left_alone(self):
        w = self.window(1200)
        w._playback.hard_ends[str(TRACK)] = False
        self.assertEqual(w._hard_end_level(), 1.0)


class DialogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_it_shows_the_default(self):
        dlg = self._dialog({})
        self.assertEqual(dlg._hard_end_fade_spin.value(), 2.0)
        self.assertEqual(dlg.values()["hard_end_fade_secs"], 2.0)

    def test_the_pick_is_saved(self):
        dlg = self._dialog({"hard_end_fade_secs": 3.0})
        self.assertEqual(dlg._hard_end_fade_spin.value(), 3.0)
        dlg._hard_end_fade_spin.setValue(4.5)
        self.assertEqual(dlg.values()["hard_end_fade_secs"], 4.5)

    def test_off_is_a_pick_of_its_own(self):
        dlg = self._dialog({"hard_end_fade_secs": 0})
        spin = dlg._hard_end_fade_spin
        self.assertEqual(spin.value(), 0.0)
        self.assertEqual(spin.minimum(), 0.0)
        self.assertEqual(spin.specialValueText(), "off")
        self.assertEqual(dlg.values()["hard_end_fade_secs"], 0.0)

    def test_reset_puts_it_back(self):
        dlg = self._dialog({"hard_end_fade_secs": 4.0})
        dlg._reset_sound_numbers()
        self.assertEqual(dlg._hard_end_fade_spin.value(), 2.0)

    def test_its_text_is_translated(self):
        from planner.i18n.lang_de import CATALOG
        dlg = self._dialog({})
        for text in (dlg._hard_end_fade_spin.toolTip(), dlg._hard_end_fade_lbl.text()):
            with self.subTest(text=text[:20]):
                self.assertIn(text, CATALOG)


if __name__ == "__main__":
    unittest.main()
