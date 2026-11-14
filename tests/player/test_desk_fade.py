"""🔇 The desk duck, the desk mute and the cartwall's 🔊 take a short fade.

An instant cut on running music clicks and startles the hall. The span is a
setting (⚙ Settings ▸ Sound & player), 0.3 s by default; 0 keeps the old cut.

Run:  .venv\\Scripts\\python.exe -m unittest tests.player.test_desk_fade -v
"""
import unittest

from PySide6.QtWidgets import QApplication

from player.audio.mix import (
    DESK_FADE_DEFAULT_MS,
    OutputMix,
    desk_fade_ms,
)
from tests.qt_test_support import reap_widget


def settle(mix: OutputMix, limit=500) -> int:
    """Steps until nothing moves; returns how many it took."""
    n = 0
    while not mix.settled and n < limit:
        mix.step()
        n += 1
    return n


class SettingTest(unittest.TestCase):

    def test_a_third_of_a_second_by_default(self):
        self.assertEqual(DESK_FADE_DEFAULT_MS, 300)
        self.assertEqual(desk_fade_ms({}), 300)

    def test_the_pick_is_used_and_zero_means_the_old_cut(self):
        self.assertEqual(desk_fade_ms({"desk_fade_ms": 800}), 800)
        self.assertEqual(desk_fade_ms({"desk_fade_ms": 0}), 0)

    def test_a_broken_value_is_the_default(self):
        self.assertEqual(desk_fade_ms({"desk_fade_ms": "soon"}), 300)
        self.assertEqual(desk_fade_ms({"desk_fade_ms": None}), 300)

    def test_the_value_stays_between_zero_and_two_seconds(self):
        self.assertEqual(desk_fade_ms({"desk_fade_ms": -5}), 0)
        self.assertEqual(desk_fade_ms({"desk_fade_ms": 99999}), 2000)


class DeskMuteTest(unittest.TestCase):

    def mix(self, ms=300):
        mix = OutputMix()
        mix.set_desk_fade(ms)
        return mix

    def test_no_fade_is_the_old_cut(self):
        mix = self.mix(0)
        mix.set_desk_mute(True)
        self.assertEqual(mix.deck(), 0.0)
        self.assertTrue(mix.settled)

    def test_a_mute_is_not_heard_at_once(self):
        mix = self.mix()
        mix.set_desk_mute(True)
        self.assertEqual(mix.deck(), 1.0)
        self.assertFalse(mix.settled)

    def test_it_goes_down_over_the_span(self):
        mix = self.mix(300)
        mix.set_desk_mute(True)
        steps = settle(mix)
        self.assertEqual(mix.deck(), 0.0)
        self.assertAlmostEqual(steps * mix.step_ms, 300, delta=mix.step_ms)

    def test_it_is_part_way_in_the_middle(self):
        mix = self.mix(300)
        mix.set_desk_mute(True)
        for _ in range(int(150 / mix.step_ms)):
            mix.step()
        self.assertTrue(0.3 < mix.deck() < 0.7, mix.deck())

    def test_the_cartwall_and_the_mini_players_follow(self):
        mix = self.mix()
        mix.set_desk_mute(True)
        settle(mix)
        self.assertEqual(mix.cartwall(), 0.0)
        self.assertEqual(mix.mini(), 0.0)

    def test_the_state_flags_answer_at_once(self):
        mix = self.mix()
        mix.set_desk_mute(True)
        self.assertTrue(mix.desk_muted)
        self.assertEqual(mix.desk, 0.0)

    def test_it_comes_back_the_same_way(self):
        mix = self.mix()
        mix.set_desk_mute(True)
        settle(mix)
        mix.set_desk_mute(False)
        self.assertEqual(mix.deck(), 0.0)
        mix.step()
        self.assertTrue(0.0 < mix.deck() < 1.0)
        settle(mix)
        self.assertEqual(mix.deck(), 1.0)

    def test_a_duck_goes_down_to_its_level_and_stops(self):
        mix = self.mix()
        mix.set_desk_duck(True, 0.4)
        settle(mix)
        self.assertAlmostEqual(mix.deck(), 0.4)


class CartMuteTest(unittest.TestCase):

    def test_the_wall_fades_out_and_back(self):
        mix = OutputMix()
        mix.set_desk_fade(300)
        mix.cart_muted = True
        self.assertEqual(mix.cartwall(), 1.0)
        settle(mix)
        self.assertEqual(mix.cartwall(), 0.0)
        mix.cart_muted = False
        settle(mix)
        self.assertEqual(mix.cartwall(), 1.0)

    def test_no_fade_is_the_old_cut(self):
        mix = OutputMix()
        mix.cart_muted = True
        self.assertEqual(mix.cartwall(), 0.0)


class _Timer:
    def __init__(self):
        self.running = False

    def isActive(self):
        return self.running

    def start(self):
        self.running = True

    def stop(self):
        self.running = False


class WindowTest(unittest.TestCase):
    """The buttons start the ramp that walks the level, and it stops on arrival."""

    def desk(self):
        from player.window.main_audio import AudioLevelMixin

        class Desk:
            _set_desk_mute = AudioLevelMixin._set_desk_mute
            _set_desk_duck = AudioLevelMixin._set_desk_duck
            _set_cart_muted = AudioLevelMixin._set_cart_muted
            _show_desk_duck = AudioLevelMixin._show_desk_duck
            _start_mix_ramp = AudioLevelMixin._start_mix_ramp
            _step_volume_ramp = AudioLevelMixin._step_volume_ramp
            _show_pull = AudioLevelMixin._show_pull

            def __init__(self):
                self._settings = {}
                self._mix = OutputMix()
                self._mix.set_desk_fade(300)
                self._ramp_timer = _Timer()
                self._big_player = self._preview = self._presenter = None

            def _apply_volume(self):
                pass
        return Desk()

    def test_the_desk_mute_walks_down_and_the_timer_stops(self):
        d = self.desk()
        d._set_desk_mute(True)
        self.assertTrue(d._ramp_timer.running)
        while d._ramp_timer.running:
            d._step_volume_ramp()
        self.assertEqual(d._mix.deck(), 0.0)

    def test_the_duck_walks_too(self):
        d = self.desk()
        d._set_desk_duck(True)
        self.assertTrue(d._ramp_timer.running)

    def test_the_cartwall_mute_walks_too(self):
        d = self.desk()
        d._set_cart_muted(True)
        self.assertTrue(d._ramp_timer.running)
        while d._ramp_timer.running:
            d._step_volume_ramp()
        self.assertEqual(d._mix.cartwall(), 0.0)

    def test_the_cartwall_mute_lifts_a_pad_s_duck(self):
        """The wall's 🔇 button reaches the mix as a duck: a muted pad is not
        heard, so the music it was holding down comes back up."""
        d = self.desk()
        d._mix.duck_reason("cartwall", True)
        self.assertLess(d._mix.duck_target, 1.0)
        d._set_cart_muted(True)
        self.assertEqual(d._mix.duck_target, 1.0)
        d._set_cart_muted(False)
        self.assertLess(d._mix.duck_target, 1.0)

    def test_without_a_fade_no_timer_runs(self):
        d = self.desk()
        d._mix.set_desk_fade(0)
        d._set_desk_mute(True)
        self.assertFalse(d._ramp_timer.running)
        self.assertEqual(d._mix.deck(), 0.0)


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
        self.assertEqual(dlg._desk_fade_spin.value(), 0.3)
        self.assertEqual(dlg.values()["desk_fade_ms"], 300)

    def test_the_pick_is_saved(self):
        dlg = self._dialog({"desk_fade_ms": 500})
        self.assertEqual(dlg._desk_fade_spin.value(), 0.5)
        dlg._desk_fade_spin.setValue(1.2)
        self.assertEqual(dlg.values()["desk_fade_ms"], 1200)

    def test_reset_puts_it_back(self):
        dlg = self._dialog({"desk_fade_ms": 900})
        dlg._reset_sound_numbers()
        self.assertEqual(dlg._desk_fade_spin.value(), 0.3)

    def test_its_text_is_translated(self):
        from planner.i18n.lang_de import CATALOG
        dlg = self._dialog({})
        for text in (dlg._desk_fade_spin.toolTip(), dlg._desk_fade_lbl.text()):
            with self.subTest(text=text[:20]):
                self.assertIn(text, CATALOG)


if __name__ == "__main__":
    unittest.main()
