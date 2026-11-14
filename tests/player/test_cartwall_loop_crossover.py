"""A looping pad blends its end into its next round instead of jumping.

Marcel: a pad with loop on should "behave more like a cross over". The restart
at the end of the file used to be a hard setPosition(0); now, shortly before
the end, a second voice starts the file from the top while the running one
fades out, over the pad's own crossover time (or the wall's). The pad keeps one key
and stays one pad to the wall: it never reports stopped, ended or fading.

Runs on the stub players of test_cartwall_voices.
"""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_loopxf_"))

from PySide6.QtWidgets import QApplication

from player.audio import cart_voices
from tests.player.test_cartwall_voices import _factory, _pad

_app = QApplication.instance() or QApplication(sys.argv)

KEY = (0, 0, 0)


class LoopCrossoverTest(unittest.TestCase):

    def setUp(self):
        self.v = cart_voices.CartVoices(voices=4, factory=_factory)
        self.v.set_level(1.0)
        self.v.set_wall_fade(1000)
        self.stopped, self.ended, self.fading = [], [], []
        self.v.padStopped.connect(self.stopped.append)
        self.v.padEnded.connect(self.ended.append)
        self.v.padFading.connect(lambda k, on: self.fading.append((k, on)))

    def tearDown(self):
        self.v.shutdown()

    def _near_the_end(self, voice, left_ms=900):
        voice.player.setPosition(voice.player.duration() - left_ms)
        self.v._emit_tick()

    def _settle(self):
        for _ in range(400):
            self.v._step_fades()

    def _live(self):
        return [x for x in self.v._pool if x.busy]

    def test_near_the_end_the_next_round_starts_on_a_second_voice(self):
        self.v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        first = self.v._voice_for(KEY)
        self._near_the_end(first)
        second = self.v._voice_for(KEY)
        self.assertIsNot(second, first)
        self.assertIn(("play", None), second.player.calls)
        self.assertEqual(len(self._live()), 1, "one pad, one live voice")

    def test_the_old_round_fades_out_and_the_new_one_fades_in(self):
        self.v.fire(KEY, _pad("bed.mp3", loop=True, duck=False, volume=0.8))
        first = self.v._voice_for(KEY)
        self._near_the_end(first)
        second = self.v._voice_for(KEY)
        self.v._step_fades()
        self.assertLess(first.out.volume(), 0.8)
        self.assertGreater(first.out.volume(), 0.0)
        self.assertGreater(second.out.volume(), 0.0)
        self.assertLess(second.out.volume(), 0.8)
        self._settle()
        self.assertAlmostEqual(second.out.volume(), 0.8)
        self.assertEqual(first.out.volume(), 0.0)
        self.assertFalse(first.busy)

    def test_the_blend_holds_the_power_steady_like_the_main_player(self):
        """Marcel: the loop should blend like the main player's crossover, so
        no end is heard. Two straight ramps dip to half the power in the middle;
        the equal-power curve (shared.audio.playback.crossfade_levels) keeps
        the sum of the two levels' squares at the pad's level squared."""
        self.v.fire(KEY, _pad("bed.mp3", loop=True, duck=False, volume=0.8))
        first = self.v._voice_for(KEY)
        self._near_the_end(first)
        second = self.v._voice_for(KEY)
        steps = round(1.0 / second.rise_step)
        for done in range(1, steps):
            self.v._step_fades()
            if done in (steps // 4, steps // 2, 3 * steps // 4):
                power = first.out.volume() ** 2 + second.out.volume() ** 2
                self.assertAlmostEqual(power, 0.8 ** 2, places=2,
                                       msg=f"step {done} of {steps}")

    def test_a_tap_during_the_blend_does_not_jump_the_new_round(self):
        self.v.fire(KEY, _pad("bed.mp3", loop=True, duck=False, volume=0.8))
        first = self.v._voice_for(KEY)
        self._near_the_end(first)
        second = self.v._voice_for(KEY)
        for _ in range(round(0.5 / second.rise_step)):
            self.v._step_fades()
        before = second.out.volume()
        self.v.stop(KEY)
        self.assertAlmostEqual(second.out.volume(), before, places=2)

    def test_the_wall_hears_nothing_of_it(self):
        self.v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        self._near_the_end(self.v._voice_for(KEY))
        self._settle()
        self.assertEqual((self.stopped, self.ended, self.fading), ([], [], []))
        self.assertTrue(self.v.is_playing(KEY))

    def test_it_goes_round_again_and_again(self):
        self.v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        for _ in range(3):
            self._near_the_end(self.v._voice_for(KEY))
            self._settle()
        self.assertEqual(len(self._live()), 1)
        self.assertTrue(self.v.is_playing(KEY))

    def test_far_from_the_end_nothing_happens(self):
        self.v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        first = self.v._voice_for(KEY)
        self._near_the_end(first, left_ms=5000)
        self.assertIs(self.v._voice_for(KEY), first)

    def test_a_pad_without_loop_is_left_alone(self):
        self.v.fire(KEY, _pad("tusch.mp3", duck=False))
        first = self.v._voice_for(KEY)
        self._near_the_end(first)
        self.assertIs(self.v._voice_for(KEY), first)

    def test_the_tail_ending_by_itself_does_not_loop_again(self):
        self.v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        first = self.v._voice_for(KEY)
        self._near_the_end(first)
        before = list(first.player.calls)
        cart_voices.CartVoices._on_status(
            self.v, first, __import__("PySide6.QtMultimedia", fromlist=["x"])
            .QMediaPlayer.MediaStatus.EndOfMedia)
        self.assertEqual(first.player.calls[len(before):].count(("play", None)), 0)
        self.assertFalse(first.busy)
        self.assertEqual(len(self._live()), 1)

    def test_a_pad_with_a_zero_crossover_wraps_as_before(self):
        self.v.fire(KEY, _pad("bed.mp3", loop=True, duck=False, cross_ms=0))
        first = self.v._voice_for(KEY)
        self._near_the_end(first)
        self.assertIs(self.v._voice_for(KEY), first)

    def test_the_pads_own_crossover_sets_the_length(self):
        self.v.fire(KEY, _pad("bed.mp3", loop=True, duck=False, cross_ms=400))
        first = self.v._voice_for(KEY)
        self._near_the_end(first, left_ms=300)
        self.assertIsNot(self.v._voice_for(KEY), first)

    def test_with_no_voice_free_the_old_hard_wrap_stays(self):
        for i in range(1, 4):
            self.v.fire((0, 1, i), _pad(f"b{i}.mp3", loop=True, duck=False))
        self.v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        first = self.v._voice_for(KEY)
        self._near_the_end(first)
        self.assertIs(self.v._voice_for(KEY), first)

    def test_tapped_again_the_pad_still_fades_out(self):
        self.v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        self._near_the_end(self.v._voice_for(KEY))
        self.v.stop(KEY)
        self._settle()
        self.assertFalse(self.v.is_playing(KEY))
        self.assertEqual(self.stopped, [KEY])
        self.assertEqual(self._live(), [])

    def test_a_ducking_loop_pad_keeps_its_duck_across_the_round(self):
        """The new voice inherits the tap: a pad the operator tapped goes on
        ducking, the tail does not count as a second pad."""
        ducks = []
        self.v.duckChanged.connect(ducks.append)
        self.v.fire(KEY, _pad("bed.mp3", loop=True, duck=True))
        self._near_the_end(self.v._voice_for(KEY))
        self._settle()
        self.assertEqual(ducks, [True])


class LoopFadeRestartTest(unittest.TestCase):
    """Mode "fade": the pad fades itself out over its fade time before the file
    ends, then starts again at full level from the top, on the same voice."""

    def setUp(self):
        self.v = cart_voices.CartVoices(voices=4, factory=_factory)
        self.v.set_level(1.0)
        self.v.set_wall_fade(1000)
        self.v.set_loop_mode("fade")
        self.stopped, self.ended, self.fading = [], [], []
        self.v.padStopped.connect(self.stopped.append)
        self.v.padEnded.connect(self.ended.append)
        self.v.padFading.connect(lambda k, on: self.fading.append((k, on)))
        self.v.fire(KEY, _pad("bed.mp3", loop=True, duck=False, volume=0.8))
        self.voice = self.v._voice_for(KEY)

    def tearDown(self):
        self.v.shutdown()

    def _near_the_end(self, left_ms=900):
        self.voice.player.setPosition(self.voice.player.duration() - left_ms)
        self.v._emit_tick()

    def _settle(self):
        for _ in range(400):
            self.v._step_fades()

    def test_near_the_end_it_fades_down_on_the_same_voice(self):
        self._near_the_end()
        self.v._step_fades()
        self.assertIs(self.v._voice_for(KEY), self.voice)
        self.assertEqual(len([x for x in self.v._pool if x.busy]), 1)
        self.assertLess(self.voice.out.volume(), 0.8)
        self.assertGreater(self.voice.out.volume(), 0.0)

    def test_it_restarts_from_the_top_at_full_level(self):
        self._near_the_end()
        self._settle()
        self.assertEqual(self.voice.player.position(), 0)
        self.assertAlmostEqual(self.voice.out.volume(), 0.8)
        self.assertTrue(self.v.is_playing(KEY))

    def test_the_wall_hears_nothing_of_it(self):
        self._near_the_end()
        self._settle()
        self.assertEqual((self.stopped, self.ended, self.fading), ([], [], []))

    def test_it_goes_round_again_and_again(self):
        for _ in range(3):
            self._near_the_end()
            self._settle()
        self.assertTrue(self.v.is_playing(KEY))
        self.assertAlmostEqual(self.voice.out.volume(), 0.8)

    def test_far_from_the_end_nothing_happens(self):
        self._near_the_end(left_ms=5000)
        self.v._step_fades()
        self.assertAlmostEqual(self.voice.out.volume(), 0.8)

    def test_tapped_while_fading_down_the_pad_still_ends(self):
        self._near_the_end()
        self.v._step_fades()
        self.v.stop(KEY)
        self._settle()
        self.assertFalse(self.v.is_playing(KEY))
        self.assertEqual(self.stopped, [KEY])
        self.assertFalse(self.voice.busy)

    def test_a_pad_without_loop_is_left_alone(self):
        self.v.stop(KEY)
        self._settle()
        self.v.fire((0, 0, 1), _pad("tusch.mp3", duck=False))
        one = self.v._voice_for((0, 0, 1))
        one.player.setPosition(one.player.duration() - 900)
        self.v._emit_tick()
        self.v._step_fades()
        self.assertAlmostEqual(one.out.volume(), 1.0)

    def test_a_zero_crossover_wraps_as_before(self):
        self.v.stop(KEY)
        self._settle()
        self.v.fire((0, 0, 2), _pad("hard.mp3", loop=True, duck=False, cross_ms=0))
        one = self.v._voice_for((0, 0, 2))
        one.player.setPosition(one.player.duration() - 900)
        self.v._emit_tick()
        self.v._step_fades()
        self.assertAlmostEqual(one.out.volume(), 1.0)


class LoopModeTest(unittest.TestCase):
    """Marcel: a choice between crossover, fade out and restart, and hard -
    read as one global dropdown in Settings > Cartwall."""

    def _voices(self, mode=None):
        v = cart_voices.CartVoices(voices=4, factory=_factory)
        self.addCleanup(v.shutdown)
        v.set_level(1.0)
        v.set_wall_fade(1000)
        if mode:
            v.set_loop_mode(mode)
        v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        first = v._voice_for(KEY)
        first.player.setPosition(first.player.duration() - 900)
        v._emit_tick()
        return v, first

    def test_crossover_is_the_default(self):
        v, first = self._voices()
        self.assertIsNot(v._voice_for(KEY), first)

    def test_hard_wraps_on_the_same_voice_without_a_dip(self):
        v, first = self._voices("hard")
        v._step_fades()
        self.assertIs(v._voice_for(KEY), first)
        self.assertAlmostEqual(first.out.volume(), 1.0)

    def test_fade_stays_on_the_voice_and_dips(self):
        v, first = self._voices("fade")
        v._step_fades()
        self.assertIs(v._voice_for(KEY), first)
        self.assertLess(first.out.volume(), 1.0)

    def test_an_odd_mode_falls_back_to_crossover(self):
        v, first = self._voices("sideways")
        self.assertIsNot(v._voice_for(KEY), first)

    def test_the_setting_helper(self):
        from planner.playing import cartwall as pc
        self.assertEqual(pc.loop_mode({}), "crossover")
        for mode in ("crossover", "fade", "hard"):
            self.assertEqual(pc.loop_mode({"cart_loop_mode": mode}), mode)
        self.assertEqual(pc.loop_mode({"cart_loop_mode": "x"}), "crossover")
        self.assertEqual(pc.loop_mode({"cart_loop_mode": False}), "crossover")

    def test_the_settings_tab_has_a_dropdown_for_it(self):
        from gui.dialogs.settings_dialog import SettingsDialog
        from tests.qt_test_support import reap_widget
        dlg = SettingsDialog({}, None)
        self.addCleanup(reap_widget, dlg)
        box = dlg._cart_loop_mode_combo
        self.assertEqual([box.itemData(i) for i in range(box.count())],
                         ["crossover", "fade", "hard"])
        self.assertEqual([box.itemText(i) for i in range(box.count())],
                         ["Crossover", "Fade out and restart",
                          "Hard stop and restart"])
        self.assertEqual(dlg.values()["cart_loop_mode"], "crossover")
        box.setCurrentIndex(box.findData("hard"))
        self.assertEqual(dlg.values()["cart_loop_mode"], "hard")

    def test_a_saved_mode_shows_and_reset_goes_back(self):
        from gui.dialogs.settings_dialog import SettingsDialog
        from tests.qt_test_support import reap_widget
        dlg = SettingsDialog({"cart_loop_mode": "fade"}, None)
        self.addCleanup(reap_widget, dlg)
        self.assertEqual(dlg._cart_loop_mode_combo.currentData(), "fade")
        dlg._reset_cartwall_values()
        self.assertEqual(dlg._cart_loop_mode_combo.currentData(), "crossover")

    def test_the_window_hands_it_to_the_wall(self):
        from types import SimpleNamespace
        from typing import Any, cast

        from player.audio.mix import OutputMix
        from player.window.main_cartwall import CartwallMixin
        voices = cart_voices.CartVoices(voices=2, factory=_factory)
        self.addCleanup(voices.shutdown)
        host = cast(Any, SimpleNamespace(
            _settings={"cart_loop_mode": "hard"},
            _mix=OutputMix(), _cart_voices=voices,
            _set_duck_reason=lambda r, on: None))
        CartwallMixin.apply_cart_settings(host)
        self.assertEqual(voices._loop_mode, "hard")
        host._settings = {}
        CartwallMixin.apply_cart_settings(host)
        self.assertEqual(voices._loop_mode, "crossover")


class CrossoverLengthTest(unittest.TestCase):
    """Marcel: "Crossover length for pad make it configurable like the fade
    is" - a wall default in Settings > Cartwall and an override per pad, and
    no longer borrowed from the fade-out of a tapped pad."""

    def _voices(self):
        v = cart_voices.CartVoices(voices=4, factory=_factory)
        self.addCleanup(v.shutdown)
        v.set_level(1.0)
        return v

    @staticmethod
    def _tick_at(v, voice, left_ms):
        voice.player.setPosition(voice.player.duration() - left_ms)
        v._emit_tick()

    def test_the_setting_helper(self):
        from planner.playing import cartwall as pc
        self.assertEqual(pc.cross_ms({}), pc.DEFAULT_CROSS_MS)
        self.assertEqual(pc.cross_ms({"cart_cross_ms": 2500}), 2500)
        self.assertEqual(pc.cross_ms({"cart_cross_ms": 0}), 0)
        self.assertEqual(pc.cross_ms({"cart_cross_ms": 10 ** 9}), pc.MAX_CROSS_MS)
        self.assertEqual(pc.cross_ms({"cart_cross_ms": -5}), 0)
        self.assertEqual(pc.cross_ms({"cart_cross_ms": "x"}), pc.DEFAULT_CROSS_MS)

    def test_each_mode_has_its_own_default(self):
        """Marcel: "make for crossover default 3s but when switched to fade it
        should go to default 1s" - an unset length is the mode's, a saved one
        wins in either mode."""
        from planner.playing import cartwall as pc
        self.assertEqual(pc.default_cross_ms("crossover"), 3000)
        self.assertEqual(pc.default_cross_ms("fade"), 1000)
        self.assertEqual(pc.cross_ms({"cart_loop_mode": "crossover"}), 3000)
        self.assertEqual(pc.cross_ms({"cart_loop_mode": "fade"}), 1000)
        self.assertEqual(pc.cross_ms({"cart_loop_mode": "fade", "cart_cross_ms": 2500}), 2500)
        self.assertEqual(pc.cross_ms({"cart_loop_mode": "fade", "cart_cross_ms": "x"}), 1000)

    def test_the_settings_spin_follows_the_mode_while_it_sits_on_a_default(self):
        from gui.dialogs.settings_dialog import SettingsDialog
        from tests.qt_test_support import reap_widget
        dlg = SettingsDialog({}, None)
        self.addCleanup(reap_widget, dlg)
        combo = dlg._cart_loop_mode_combo
        self.assertAlmostEqual(dlg._cart_cross_spin.value(), 3.0)
        combo.setCurrentIndex(combo.findData("fade"))
        self.assertAlmostEqual(dlg._cart_cross_spin.value(), 1.0)
        combo.setCurrentIndex(combo.findData("crossover"))
        self.assertAlmostEqual(dlg._cart_cross_spin.value(), 3.0)
        dlg._cart_cross_spin.setValue(2.5)
        combo.setCurrentIndex(combo.findData("fade"))
        self.assertAlmostEqual(dlg._cart_cross_spin.value(), 2.5, msg="own value stays")

    def test_the_settings_open_on_the_modes_default(self):
        from gui.dialogs.settings_dialog import SettingsDialog
        from planner.playing import cartwall as pc
        from tests.qt_test_support import reap_widget
        dlg = SettingsDialog({"cart_loop_mode": "fade"}, None)
        self.addCleanup(reap_widget, dlg)
        self.assertAlmostEqual(dlg._cart_cross_spin.value(), 1.0)
        dlg._reset_cartwall_values()
        self.assertEqual(dlg.values()["cart_loop_mode"], "crossover")
        self.assertEqual(dlg.values()["cart_cross_ms"], pc.default_cross_ms("crossover"))

    def test_a_pad_follows_the_wall_until_it_has_its_own(self):
        from planner.playing import cartwall as pc
        self.assertEqual(pc.cross_for(pc.CartPad(path="a"), 3000), 3000)
        self.assertEqual(pc.cross_for(pc.CartPad(path="a", cross_ms=0), 3000), 0)
        self.assertEqual(pc.cross_for(pc.CartPad(path="a", cross_ms=700), 3000), 700)
        self.assertEqual(pc.cross_for(None, 3000), 3000)

    def test_the_pad_file_keeps_it_only_when_it_is_set(self):
        from planner.playing import cartwall as pc
        plain = pc._pad_to_dict(pc.CartPad(path="a"))
        self.assertNotIn("cross_ms", plain)
        self.assertIsNone(pc._pad_from_dict(plain).cross_ms)
        own = pc._pad_to_dict(pc.CartPad(path="a", cross_ms=0))
        self.assertEqual(own["cross_ms"], 0)
        self.assertEqual(pc._pad_from_dict(own).cross_ms, 0)
        self.assertIsNone(pc._pad_from_dict({"path": "a", "cross_ms": "x"}).cross_ms)
        self.assertEqual(
            pc._pad_from_dict({"path": "a", "cross_ms": 10 ** 9}).cross_ms,
            pc.MAX_CROSS_MS)

    def test_the_fade_out_no_longer_decides_the_crossover(self):
        v = self._voices()
        v.set_wall_fade(0)
        v.fire(KEY, _pad("bed.mp3", loop=True, duck=False, fade_ms=0))
        first = v._voice_for(KEY)
        self._tick_at(v, first, 900)
        self.assertIsNot(v._voice_for(KEY), first)

    def test_the_wall_length_starts_the_crossover_earlier(self):
        v = self._voices()
        v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        first = v._voice_for(KEY)
        self._tick_at(v, first, 3500)
        self.assertIs(v._voice_for(KEY), first, "3 s default: too early")
        v = self._voices()
        v.set_wall_cross(1000)
        v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        first = v._voice_for(KEY)
        self._tick_at(v, first, 2900)
        self.assertIs(v._voice_for(KEY), first, "1 s wall: too early")
        self._tick_at(v, first, 900)
        self.assertIsNot(v._voice_for(KEY), first)

    def test_the_default_is_three_seconds(self):
        from planner.playing import cartwall as pc
        self.assertEqual(pc.DEFAULT_CROSS_MS, 3000)
        v = self._voices()
        v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        first = v._voice_for(KEY)
        self._tick_at(v, first, 2900)
        self.assertIsNot(v._voice_for(KEY), first, "a fresh wall blends over 3 s")

    def test_the_pads_own_length_beats_the_wall(self):
        v = self._voices()
        v.set_wall_cross(3000)
        v.fire(KEY, _pad("bed.mp3", loop=True, duck=False, cross_ms=400))
        first = v._voice_for(KEY)
        self._tick_at(v, first, 2900)
        self.assertIs(v._voice_for(KEY), first)
        self._tick_at(v, first, 300)
        self.assertIsNot(v._voice_for(KEY), first)

    def test_the_length_is_still_capped_at_a_third_of_the_file(self):
        v = self._voices()
        v.set_wall_cross(8000)      # the stub file is 10 s: a third is 3.3 s
        v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        first = v._voice_for(KEY)
        self._tick_at(v, first, 5000)
        self.assertIs(v._voice_for(KEY), first)
        self._tick_at(v, first, 3300)
        self.assertIsNot(v._voice_for(KEY), first)

    def test_the_fade_mode_dips_over_the_same_length(self):
        v = self._voices()
        v.set_loop_mode("fade")
        v.set_wall_cross(3000)
        v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        first = v._voice_for(KEY)
        self._tick_at(v, first, 2900)
        self.assertGreater(first.dip_step, 0)
        # 100 ms inside the span by the tick: it dips over what is left.
        self.assertAlmostEqual(first.dip_step, cart_voices._RAMP_MS / 2900.0)

    def test_a_late_crossover_blends_in_the_time_left(self):
        """Review F4: a tick that came late still rose over the full span, so
        the new round was not at full when the old one ran out."""
        v = self._voices()
        v.fire(KEY, _pad("bed.mp3", loop=True, duck=False, volume=0.8))
        first = v._voice_for(KEY)
        self._tick_at(v, first, 1500)            # 3 s span, 1.5 s left
        second = v._voice_for(KEY)
        self.assertIsNot(second, first)
        self.assertAlmostEqual(second.rise_step, cart_voices._RAMP_MS / 1500.0)
        self.assertAlmostEqual(first.fade_step, cart_voices._RAMP_MS / 1500.0)
        for _ in range(1500 // cart_voices._RAMP_MS):
            v._step_fades()
        self.assertAlmostEqual(second.out.volume(), 0.8)
        self.assertFalse(first.busy)

    def test_a_late_fade_dips_in_the_time_left(self):
        v = self._voices()
        v.set_loop_mode("fade")
        v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        first = v._voice_for(KEY)
        self._tick_at(v, first, 1500)
        self.assertAlmostEqual(first.dip_step, cart_voices._RAMP_MS / 1500.0)

    def test_the_pad_dialog_follows_the_wall_until_given_its_own(self):
        from planner.playing import cartwall as pc
        from player.dialogs import cart_pad_dialog as cpd
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3", loop=True),
                                wall_cross_ms=2000)
        self.addCleanup(dlg.deleteLater)
        self.assertFalse(dlg._cross_own.isChecked())
        self.assertFalse(dlg._cross.isEnabled())
        self.assertEqual(dlg._cross.value(), 2000)
        self.assertIn("(wall)", dlg._cross_lbl.text())
        self.assertIsNone(dlg.pad().cross_ms)
        dlg._cross_own.setChecked(True)
        dlg._cross.setValue(4500)
        self.assertEqual(dlg.pad().cross_ms, 4500)
        self.assertNotIn("(wall)", dlg._cross_lbl.text())
        dlg._cross_own.setChecked(False)
        self.assertIsNone(dlg.pad().cross_ms)
        self.assertEqual(dlg._cross.value(), 2000)

    def test_a_pad_dialog_keeps_an_own_zero(self):
        from planner.playing import cartwall as pc
        from player.dialogs import cart_pad_dialog as cpd
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3", loop=True, cross_ms=0))
        self.addCleanup(dlg.deleteLater)
        self.assertTrue(dlg._cross_own.isChecked())
        self.assertEqual(dlg._cross_lbl.text(), "0.0 s")
        self.assertEqual(dlg.pad().cross_ms, 0)

    def test_the_settings_tab_has_a_spin_for_it(self):
        from gui.dialogs.settings_dialog import SettingsDialog
        from planner.playing import cartwall as pc
        from tests.qt_test_support import reap_widget
        dlg = SettingsDialog({"cart_cross_ms": 2500}, None)
        self.addCleanup(reap_widget, dlg)
        self.assertAlmostEqual(dlg._cart_cross_spin.value(), 2.5)
        self.assertEqual(dlg.values()["cart_cross_ms"], 2500)
        dlg._reset_cartwall_values()
        self.assertEqual(dlg.values()["cart_cross_ms"], pc.DEFAULT_CROSS_MS)

    def test_the_window_hands_it_to_the_voices_and_the_wall(self):
        from types import SimpleNamespace
        from typing import Any, cast

        from player.audio.mix import OutputMix
        from player.widgets import cartwall as gc
        from player.window.main_cartwall import CartwallMixin
        from tests.qt_test_support import reap_widget
        voices = cart_voices.CartVoices(voices=2, factory=_factory)
        self.addCleanup(voices.shutdown)
        wall = gc.CartwallWidget()
        self.addCleanup(reap_widget, wall)
        host = cast(Any, SimpleNamespace(
            _settings={"cart_cross_ms": 3000},
            _mix=OutputMix(), _cart_voices=voices, _cartwall=wall,
            _set_duck_reason=lambda r, on: None))
        CartwallMixin.apply_cart_settings(host)
        self.assertEqual(voices._wall_cross, 3000)
        self.assertEqual(wall._cross_ms, 3000)

    def test_the_wall_hands_its_length_to_the_dialog(self):
        from unittest import mock

        from planner.playing import cartwall as pc
        from player.widgets import cartwall as gc
        from tests.qt_test_support import reap_widget
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        w.set_wall(pc.DEFAULT_GRID, [pc.Page(pads={(0, 0): pc.CartPad(path="a.mp3")})])
        w.set_cross_ms(2500)
        with mock.patch.object(gc, "CartPadDialog") as dialog:
            dialog.return_value.exec.return_value = 0   # Cancel
            w._on_edit((0, 0, 0))
        self.assertEqual(dialog.call_args.kwargs["wall_cross_ms"], 2500)


class PadSilenceCutTest(unittest.TestCase):
    """Marcel: "do we have a silence cut for the pads implemented? i still cant
    hear much difference by using crossover" - the La Piazza file ends in 2.3 s
    of near-silence (and starts with some), so a 1 s blend counted back from
    the last sample overlapped nothing but stillness. Like the main player, a
    pad's crossover runs from its last audible point into the first audible
    point of the next round, using the same probe's spans. Stub file: 10 s."""

    PATH = r"C:\samples\bed.mp3"

    def _voices(self, spans=None):
        v = cart_voices.CartVoices(voices=4, factory=_factory)
        self.addCleanup(v.shutdown)
        v.set_level(1.0)
        v.set_wall_cross(1000)   # the spans below are worked out for a 1 s blend
        if spans is not None:
            v.set_silences(self.PATH, spans)
        v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        return v, v._voice_for(KEY)

    @staticmethod
    def _tick_at(v, voice, pos_ms):
        voice.player.setPosition(pos_ms)
        v._emit_tick()

    def test_a_silent_tail_starts_the_crossover_where_the_music_stops(self):
        v, first = self._voices([[8.0, 10.0]])
        self._tick_at(v, first, 6500)
        self.assertIs(v._voice_for(KEY), first, "music still going: too early")
        self._tick_at(v, first, 7400)
        self.assertIsNot(v._voice_for(KEY), first, "1 s before the music stops")

    def test_without_spans_it_is_the_end_of_the_file_as_before(self):
        v, first = self._voices()
        self._tick_at(v, first, 8000)
        self.assertIs(v._voice_for(KEY), first)
        self._tick_at(v, first, 9000)
        self.assertIsNot(v._voice_for(KEY), first)

    def test_a_silent_intro_is_skipped_when_the_next_round_starts(self):
        v, first = self._voices([[0.0, 3.0]])
        self._tick_at(v, first, 9000)
        second = v._voice_for(KEY)
        self.assertIsNot(second, first)
        self.assertEqual(second.player.position(), 2800, "200 ms before the music")

    def test_a_break_in_the_middle_is_left_alone(self):
        v, first = self._voices([[4.0, 6.0]])
        self._tick_at(v, first, 4500)
        self.assertIs(v._voice_for(KEY), first)
        self._tick_at(v, first, 9000)
        second = v._voice_for(KEY)
        self.assertIsNot(second, first)
        self.assertEqual(second.player.position(), 0)

    def test_a_short_stillness_is_not_cut(self):
        v, first = self._voices([[9.0, 10.0]])
        self._tick_at(v, first, 8100)
        self.assertIs(v._voice_for(KEY), first, "1 s of quiet is no dead air")

    def test_the_fade_mode_dips_before_the_silent_tail_too(self):
        v = cart_voices.CartVoices(voices=4, factory=_factory)
        self.addCleanup(v.shutdown)
        v.set_level(1.0)
        v.set_loop_mode("fade")
        v.set_silences(self.PATH, [[8.0, 10.0]])
        v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        first = v._voice_for(KEY)
        self._tick_at(v, first, 7400)
        self.assertGreater(first.dip_step, 0)

    def test_a_looping_pad_asks_for_its_spans_once_a_plain_one_never(self):
        v = cart_voices.CartVoices(voices=4, factory=_factory)
        self.addCleanup(v.shutdown)
        v.set_level(1.0)
        asked = []
        v.wantsSilences.connect(asked.append)
        v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        v.stop(KEY)
        v.fire(KEY, _pad("bed.mp3", loop=True, duck=False))
        v.fire((0, 0, 1), _pad("tusch.mp3", duck=False))
        self.assertEqual(asked, [self.PATH])

    def test_the_window_hands_cached_spans_to_the_voices(self):
        from pathlib import Path
        from types import SimpleNamespace
        from typing import Any, cast

        from player.window.main_cartwall import CartwallMixin
        voices = cart_voices.CartVoices(voices=2, factory=_factory)
        self.addCleanup(voices.shutdown)
        cache = SimpleNamespace(get_silences=lambda p: [[8.0, 10.0]])
        host = cast(Any, SimpleNamespace(
            _cart_voices=voices,
            _library=SimpleNamespace(cache=cache)))
        CartwallMixin._arm_pad_silences(host, Path(self.PATH))
        self.assertEqual(voices._silences[self.PATH], [(8.0, 10.0)])


if __name__ == "__main__":
    unittest.main()
