#!/usr/bin/env python3
"""Tests for the volume readouts you can type into (item 25).

Run:  py -m unittest tests.player.widgets.test_volume_controls -v

Marcel: "Double-click on the percentage value to type it in (main player and
pad volume slider)." A level that is already known — the hall's sound check
said 72 % — is quicker typed than aimed at with a slider.
"""

import os
import tempfile
import unittest
from types import SimpleNamespace

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_volume_"))

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

from gui.dialogs.settings_dialog import SettingsDialog
from player.audio.mix import OutputMix
from player.widgets.cartwall import CartwallWidget
from player.widgets.player import BigPlayerWidget
from player.widgets.player_parts import VOL_STEP
from player.window.main_audio import AudioLevelMixin
from player.window.main_player import PlayerControlMixin
from tests.qt_test_support import reap_widget


def _type(label, text):
    """Double-click the readout, type `text`, press Enter."""
    label.double_clicked.emit()
    label._edit.setText(text)
    label._commit()


class _QtCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])


class MainVolumeTypingTest(_QtCase):

    def setUp(self):
        self.set = []
        self.w = BigPlayerWidget(QMediaPlayer(), get_vol=lambda: 0.5,
                                 set_vol=self.set.append)
        self.addCleanup(reap_widget, self.w)

    def test_a_typed_volume_moves_the_slider_and_the_music(self):
        _type(self.w._vol_lbl, "72")
        self.assertEqual(self.w._vol.value(), 72)
        self.assertEqual(self.set, [0.72])
        self.assertEqual(self.w._vol_lbl.text(), "72%")

    def test_the_field_starts_from_the_bare_number(self):
        self.w._vol_lbl.double_clicked.emit()
        self.assertEqual(self.w._vol_lbl._edit.text(), "50")

    def test_the_unit_may_be_typed_along(self):
        _type(self.w._vol_lbl, "35 %")
        self.assertEqual(self.w._vol.value(), 35)

    def test_nonsense_leaves_the_volume_alone(self):
        _type(self.w._vol_lbl, "loud")
        self.assertEqual(self.w._vol.value(), 50)
        self.assertEqual(self.set, [])

    def test_too_much_is_clamped_to_full(self):
        _type(self.w._vol_lbl, "250")
        self.assertEqual(self.w._vol.value(), 100)


class CartwallLevelTypingTest(_QtCase):

    def setUp(self):
        self.w = CartwallWidget()
        self.addCleanup(reap_widget, self.w)
        self.got = []
        self.w.levelChanged.connect(self.got.append)

    def test_a_typed_level_moves_the_wall(self):
        _type(self.w._level_lbl, "40")
        self.assertEqual(self.w._level.value(), 40)
        self.assertEqual(self.got, [0.4])
        self.assertEqual(self.w._level_lbl.text(), "40 %")

    def test_a_level_set_elsewhere_still_shows(self):
        self.w.set_level(0.25)
        self.assertEqual(self.w._level_lbl.text(), "25 %")
        self.assertEqual(self.got, [])


class VolumeStepButtonsTest(_QtCase):
    """Marcel: "Optional +/- buttons, with a setting to disable them." """

    def setUp(self):
        self.set = []
        self.w = BigPlayerWidget(QMediaPlayer(), get_vol=lambda: 0.5,
                                 set_vol=self.set.append)
        self.addCleanup(reap_widget, self.w)

    def test_plus_and_minus_step_the_volume(self):
        self.w._vol_up_btn.click()
        self.assertEqual(self.w._vol.value(), 50 + VOL_STEP)
        self.w._vol_down_btn.click()
        self.w._vol_down_btn.click()
        self.assertEqual(self.w._vol.value(), 50 - VOL_STEP)
        self.assertEqual(len(self.set), 3)

    def test_they_stop_at_the_ends(self):
        self.w._vol.setValue(100)
        self.w._vol_up_btn.click()
        self.assertEqual(self.w._vol.value(), 100)
        self.w._vol.setValue(0)
        self.w._vol_down_btn.click()
        self.assertEqual(self.w._vol.value(), 0)

    def test_held_they_glide(self):
        self.assertTrue(self.w._vol_up_btn.autoRepeat())
        self.assertTrue(self.w._vol_down_btn.autoRepeat())

    def test_the_setting_hides_them(self):
        self.w.set_vol_buttons_shown(False)
        self.assertTrue(self.w._vol_up_btn.isHidden())
        self.assertTrue(self.w._vol_down_btn.isHidden())
        self.w.set_vol_buttons_shown(True)
        self.assertFalse(self.w._vol_up_btn.isHidden())


class PanicButtonPlaceTest(_QtCase):
    """Marcel: with − / + on, 🛑 Fade out and hold goes up beside 🔉↓ Fade
    this song out now; the volume row is crowded enough."""

    def setUp(self):
        self.w = BigPlayerWidget(QMediaPlayer())
        self.addCleanup(reap_widget, self.w)

    def row_of(self, btn):
        for box in (self.w._aux_box, self.w._vol_box):
            if box.layout().indexOf(btn) >= 0:
                return box
        return None

    def test_with_the_buttons_it_sits_right_of_the_fade(self):
        self.w.set_vol_buttons_shown(True)
        aux = self.w._aux_box.layout()
        self.assertIs(self.row_of(self.w._panic_btn), self.w._aux_box)
        self.assertEqual(aux.indexOf(self.w._panic_btn),
                         aux.indexOf(self.w._fade_btn) + 1)

    def test_without_them_it_stays_in_the_volume_row(self):
        self.w.set_vol_buttons_shown(True)
        self.w.set_vol_buttons_shown(False)
        self.assertIs(self.row_of(self.w._panic_btn), self.w._vol_box)
        self.assertEqual(self.w._vol_box.layout().indexOf(self.w._panic_btn), 0)
        self.assertFalse(self.w._panic_btn.isHidden())

    def test_up_there_it_shows_with_the_fade_only_while_a_title_plays(self):
        self.w.set_vol_buttons_shown(True)
        self.assertTrue(self.w._panic_btn.isHidden())
        self.w.set_now("Rumba")
        self.assertFalse(self.w._panic_btn.isHidden())
        self.assertFalse(self.w._fade_btn.isHidden())
        self.w.set_now("")
        self.assertTrue(self.w._panic_btn.isHidden())


class CartwallStepButtonsTest(_QtCase):
    """Marcel: "cartwall and main player +- buttons are configured with same
    setting"."""

    def setUp(self):
        self.w = CartwallWidget()
        self.addCleanup(reap_widget, self.w)
        self.got = []
        self.w.levelChanged.connect(self.got.append)
        self.w.set_level(0.5)

    def test_plus_and_minus_step_the_wall(self):
        self.w._level_up_btn.click()
        self.assertEqual(self.w._level.value(), 50 + VOL_STEP)
        self.w._level_down_btn.click()
        self.w._level_down_btn.click()
        self.assertEqual(self.w._level.value(), 50 - VOL_STEP)
        self.assertEqual(len(self.got), 3)

    def test_held_they_glide(self):
        self.assertTrue(self.w._level_up_btn.autoRepeat())
        self.assertTrue(self.w._level_down_btn.autoRepeat())

    def test_the_setting_hides_them(self):
        self.w.set_vol_buttons_shown(False)
        self.assertTrue(self.w._level_up_btn.isHidden())
        self.assertTrue(self.w._level_down_btn.isHidden())
        self.w.set_vol_buttons_shown(True)
        self.assertFalse(self.w._level_up_btn.isHidden())


class CartwallMuteTest(_QtCase):
    """Marcel: "a click of the speaker icon there mute the cartwall player
    volume"."""

    def setUp(self):
        self.w = CartwallWidget()
        self.addCleanup(reap_widget, self.w)
        self.muted = []
        self.levels = []
        self.w.muteChanged.connect(self.muted.append)
        self.w.levelChanged.connect(self.levels.append)
        self.w.set_level(0.6)

    def test_a_click_mutes_and_the_next_brings_it_back(self):
        self.w._mute_btn.click()
        self.assertTrue(self.w.is_muted())
        self.assertEqual(self.w._mute_btn.text(), "🔇")
        self.assertEqual(self.w._level_lbl.text(), "mute")
        self.w._mute_btn.click()
        self.assertFalse(self.w.is_muted())
        self.assertEqual(self.w._mute_btn.text(), "🔊")
        self.assertEqual(self.w._level_lbl.text(), "60 %")
        self.assertEqual(self.muted, [True, False])

    def test_the_fader_keeps_its_level(self):
        """The saved cartwall_volume comes from the fader: a mute must not
        send 0 down that path."""
        self.w._mute_btn.click()
        self.assertEqual(self.w._level.value(), 60)
        self.assertEqual(self.levels, [])

    def test_the_readout_is_red_while_muted(self):
        self.w._mute_btn.click()
        self.assertIn("#d9534f", self.w._level_lbl.styleSheet())
        self.w._mute_btn.click()
        self.assertNotIn("#d9534f", self.w._level_lbl.styleSheet())

    def test_a_level_set_elsewhere_keeps_the_mute_shown(self):
        self.w._mute_btn.click()
        self.w.set_level(0.3)
        self.assertEqual(self.w._level_lbl.text(), "mute")


class CartMuteMixTest(unittest.TestCase):

    def test_muted_the_pads_are_silent_and_the_fader_kept(self):
        mix = OutputMix(cart=0.8)
        mix.cart_muted = True
        self.assertEqual(mix.cartwall(), 0.0)
        self.assertEqual(mix.cart, 0.8)
        mix.cart_muted = False
        self.assertAlmostEqual(mix.cartwall(), 0.8)

    def test_the_music_is_not_touched(self):
        mix = OutputMix(base=0.7)
        mix.cart_muted = True
        self.assertAlmostEqual(mix.deck(), 0.7)

    def test_the_window_applies_it(self):
        applied = []
        win = SimpleNamespace(_mix=OutputMix(), _apply_volume=lambda: applied.append(1))
        AudioLevelMixin._set_cart_muted(win, True)
        self.assertTrue(win._mix.cart_muted)
        self.assertEqual(applied, [1])


class VolumeStepWindowTest(unittest.TestCase):
    """⚙ Sound & player → the card and the cartwall, at start and on every
    settings save."""

    def test_they_are_on_unless_switched_off(self):
        seen = []
        wall = []
        win = SimpleNamespace(
            _big_player=SimpleNamespace(set_vol_buttons_shown=seen.append),
            _cartwall=SimpleNamespace(set_vol_buttons_shown=wall.append))
        PlayerControlMixin._set_vol_buttons_shown(win, True)
        PlayerControlMixin._set_vol_buttons_shown(win, False)
        self.assertEqual(seen, [True, False])
        self.assertEqual(wall, [True, False])

    def test_no_card_no_harm(self):
        PlayerControlMixin._set_vol_buttons_shown(SimpleNamespace(_big_player=None), True)
        PlayerControlMixin._set_vol_buttons_shown(
            SimpleNamespace(_big_player=None, _cartwall=None), True)


class VolumeStepDialogTest(_QtCase):

    def dialog(self, settings):
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_on_by_default(self):
        dlg = self.dialog({})
        self.assertTrue(dlg._vol_buttons_chk.isChecked())
        self.assertIs(dlg.values()["vol_buttons"], True)

    def test_switched_off_is_saved(self):
        dlg = self.dialog({"vol_buttons": False})
        self.assertFalse(dlg._vol_buttons_chk.isChecked())
        self.assertIs(dlg.values()["vol_buttons"], False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
