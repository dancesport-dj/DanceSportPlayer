"""A pad that pulls the OTHER PADS down while it plays.

Marcel: a title running on a pad should be suppressed while a certain other
jingle (a Tusch) is started, and come back to its set base volume afterwards.
"Make it choosable between main and pad": `duck` pulls the main player,
`duck_pads` pulls the pads, a pad may do either or both.

Runs on the stub players of test_cartwall_voices, so only the pool's policy is
under test, not the backend.
"""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_padduck_"))

from PySide6.QtWidgets import QApplication

from planner.playing import cartwall as pc
from player.audio import cart_voices
from player.dialogs import cart_pad_dialog as cpd
from tests.player.test_cartwall_voices import _factory, _pad

_app = QApplication.instance() or QApplication(sys.argv)

DEPTH = 0.2


class PadDuckTest(unittest.TestCase):

    def setUp(self):
        self.v = cart_voices.CartVoices(voices=4, factory=_factory)
        self.v.set_level(1.0)
        self.v.set_pad_duck_level(DEPTH)
        self.ducks = []
        self.v.duckChanged.connect(self.ducks.append)

    def tearDown(self):
        self.v.shutdown()

    def _heard(self, key):
        return self.v._voice_for(key).out.volume()

    def _settle(self):
        for _ in range(400):
            if self.v._pad_duck == self.v._pad_duck_target:
                return
            self.v._step_pad_duck()
        self.fail("the pad duck never settled")

    def _tusch(self, **kw):
        return _pad("tusch.mp3", duck=False, duck_pads=True, **kw)

    def test_a_title_on_a_pad_goes_down_under_the_tusch(self):
        self.v.fire((0, 0, 0), _pad("title.mp3", volume=0.8, duck=False))
        self.assertAlmostEqual(self._heard((0, 0, 0)), 0.8)
        self.v.fire((0, 0, 1), self._tusch())
        self._settle()
        self.assertAlmostEqual(self._heard((0, 0, 0)), 0.8 * DEPTH)

    def test_the_title_comes_back_to_its_base_volume_when_the_tusch_ends(self):
        self.v.fire((0, 0, 0), _pad("title.mp3", volume=0.8, duck=False))
        self.v.fire((0, 0, 1), self._tusch())
        self._settle()
        self.v._on_status(self.v._voice_for((0, 0, 1)), _end_of_media())
        self._settle()
        self.assertAlmostEqual(self._heard((0, 0, 0)), 0.8)

    def test_the_tusch_itself_is_not_pulled_down(self):
        self.v.fire((0, 0, 0), _pad("title.mp3", duck=False))
        self.v.fire((0, 0, 1), self._tusch(volume=0.9))
        self._settle()
        self.assertAlmostEqual(self._heard((0, 0, 1)), 0.9)

    def test_a_title_fired_while_the_tusch_runs_starts_down(self):
        self.v.fire((0, 0, 1), self._tusch())
        self._settle()
        self.v.fire((0, 0, 0), _pad("title.mp3", volume=0.5, duck=False))
        self.assertAlmostEqual(self._heard((0, 0, 0)), 0.5 * DEPTH)

    def test_turning_the_depth_to_full_mid_duck_lifts_it_in_one_up_span(self):
        """Review F4: the step was taken from the depth setting, not from the
        way still to go. Set to 100 % while pulled down, the step was 0: the
        duck never lifted and the 25 ms timer ran for good."""
        self.v.fire((0, 0, 0), _pad("title.mp3", duck=False))
        self.v.fire((0, 0, 1), self._tusch())
        self._settle()
        self.v.set_pad_duck_level(1.0)
        ticks = cart_voices._PAD_DUCK_UP_MS // cart_voices._RAMP_MS
        for _ in range(ticks + 1):
            self.v._step_pad_duck()
        self.assertEqual(self.v._pad_duck, 1.0)
        self.assertFalse(self.v._pad_duck_ramp.isActive())

    def test_a_turn_back_mid_ramp_takes_its_own_span(self):
        """A duck lifting half-way and pulled down again goes down in the
        down span, not at a pace left over from the depth."""
        self.v.fire((0, 0, 0), _pad("title.mp3", duck=False))
        self.v.fire((0, 0, 1), self._tusch())
        self._settle()
        self.v._on_status(self.v._voice_for((0, 0, 1)), _end_of_media())
        for _ in range(10):
            self.v._step_pad_duck()
        self.assertGreater(self.v._pad_duck, DEPTH)
        self.v.fire((0, 0, 2), self._tusch())       # another one: no double-tap guard
        for _ in range(cart_voices._PAD_DUCK_DOWN_MS // cart_voices._RAMP_MS + 1):
            self.v._step_pad_duck()
        self.assertAlmostEqual(self.v._pad_duck, DEPTH)

    def test_shutdown_stops_the_duck_ramp(self):
        self.v.fire((0, 0, 0), _pad("title.mp3", duck=False))
        self.v.fire((0, 0, 1), self._tusch())
        self.assertTrue(self.v._pad_duck_ramp.isActive())
        self.v.shutdown()
        self.assertFalse(self.v._pad_duck_ramp.isActive())

    def test_a_pad_that_only_ducks_the_main_player_leaves_the_pads_alone(self):
        self.v.fire((0, 0, 0), _pad("title.mp3", duck=False))
        self.v.fire((0, 0, 1), _pad("tusch.mp3", duck=True))
        self._settle()
        self.assertAlmostEqual(self._heard((0, 0, 0)), 1.0)
        self.assertEqual(self.ducks, [True])        # the main player still ducks

    def test_a_pad_that_only_ducks_the_pads_leaves_the_main_player_alone(self):
        self.v.fire((0, 0, 1), self._tusch())
        self.assertEqual(self.ducks, [])

    def test_a_pad_may_pull_both_down(self):
        self.v.fire((0, 0, 0), _pad("title.mp3", duck=False))
        self.v.fire((0, 0, 1), _pad("tusch.mp3", duck=True, duck_pads=True))
        self._settle()
        self.assertEqual(self.ducks, [True])
        self.assertAlmostEqual(self._heard((0, 0, 0)), DEPTH)

    def test_a_pad_the_queue_started_does_not_pull_the_others_down(self):
        """Like the main duck: only a tap by hand ducks."""
        self.v.fire((0, 0, 0), _pad("title.mp3", duck=False))
        self.v.fire((0, 0, 1), self._tusch(), tapped=False)
        self._settle()
        self.assertAlmostEqual(self._heard((0, 0, 0)), 1.0)

    def test_a_muted_wall_pulls_nothing_down(self):
        self.v.fire((0, 0, 0), _pad("title.mp3", duck=False))
        self.v.fire((0, 0, 1), self._tusch())
        self.v.set_muted(True)
        self._settle()
        self.assertEqual(self.v._pad_duck_target, 1.0)

    def test_a_stopped_tusch_lets_the_title_back_up(self):
        self.v.fire((0, 0, 0), _pad("title.mp3", duck=False))
        self.v.fire((0, 0, 1), self._tusch())
        self._settle()
        self.v.stop((0, 0, 1))
        for _ in range(400):
            self.v._step_fades()
        self._settle()
        self.assertAlmostEqual(self._heard((0, 0, 0)), 1.0)

    def test_a_new_depth_moves_a_duck_that_is_on(self):
        self.v.fire((0, 0, 0), _pad("title.mp3", duck=False))
        self.v.fire((0, 0, 1), self._tusch())
        self._settle()
        self.v.set_pad_duck_level(0.5)
        self._settle()
        self.assertAlmostEqual(self._heard((0, 0, 0)), 0.5)

    def test_the_duck_is_a_ramp_not_a_step(self):
        self.v.fire((0, 0, 0), _pad("title.mp3", duck=False))
        self.v.fire((0, 0, 1), self._tusch())
        self.v._step_pad_duck()
        self.assertGreater(self._heard((0, 0, 0)), DEPTH)
        self.assertLess(self._heard((0, 0, 0)), 1.0)


def _end_of_media():
    from PySide6.QtMultimedia import QMediaPlayer
    return QMediaPlayer.MediaStatus.EndOfMedia


class PadDuckStorageTest(unittest.TestCase):

    def test_off_is_the_default_and_is_not_written(self):
        self.assertFalse(pc.CartPad(path="a.mp3").duck_pads)
        self.assertNotIn("duck_pads", pc._pad_to_dict(pc.CartPad(path="a.mp3")))

    def test_it_survives_a_save_and_a_load(self):
        data = pc._pad_to_dict(pc.CartPad(path="a.mp3", duck_pads=True))
        self.assertTrue(data["duck_pads"])
        self.assertTrue(pc._pad_from_dict(data).duck_pads)

    def test_an_old_wall_without_the_field_loads_with_it_off(self):
        self.assertFalse(pc._pad_from_dict({"path": "a.mp3"}).duck_pads)


class PadDuckDialogTest(unittest.TestCase):

    def test_the_box_round_trips_the_choice(self):
        pad = pc.CartPad(path="a.mp3", duck=False, duck_pads=True)
        self.assertEqual(cpd.CartPadDialog(pad).pad(), pad)

    def test_the_two_boxes_are_independent(self):
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3"))
        self.assertTrue(dlg.pad().duck)
        self.assertFalse(dlg.pad().duck_pads)
        dlg._duck_pads.setChecked(True)
        self.assertTrue(dlg.pad().duck)
        self.assertTrue(dlg.pad().duck_pads)

    def test_a_loop_pad_does_not_pull_the_pads_down_either(self):
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3", duck_pads=True))
        dlg._loop.setChecked(True)
        self.assertFalse(dlg.pad().duck_pads)

    def test_a_background_pad_does_not_pull_the_pads_down(self):
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3", duck_pads=True))
        dlg._background.setChecked(True)
        self.assertFalse(dlg.pad().duck_pads)


class PadDuckSettingTest(unittest.TestCase):
    """Marcel: "make sure we also have a global setting to adjust this duck
    volume" - its own, apart from how far a pad pulls the main music."""

    def test_the_default_is_the_standard_pad_duck(self):
        from player.audio.mix import CART_DUCK, CART_DUCK_PCT, cart_pad_duck_level, cart_pad_duck_pct
        self.assertEqual(cart_pad_duck_pct({}), CART_DUCK_PCT)
        self.assertAlmostEqual(cart_pad_duck_level({}), CART_DUCK)

    def test_it_is_read_bounded_and_independent_of_the_main_duck(self):
        from player.audio.mix import cart_duck_pct, cart_pad_duck_pct
        self.assertEqual(cart_pad_duck_pct({"cart_pad_duck_pct": 35}), 35)
        self.assertEqual(cart_pad_duck_pct({"cart_pad_duck_pct": 100}), 90)
        self.assertEqual(cart_pad_duck_pct({"cart_pad_duck_pct": -5}), 0)
        self.assertEqual(cart_pad_duck_pct({"cart_pad_duck_pct": "x"}), 10)
        self.assertEqual(cart_pad_duck_pct({"cart_duck_pct": 60}), 10)
        self.assertEqual(cart_duck_pct({"cart_pad_duck_pct": 60}), 10)

    def test_the_settings_tab_has_a_box_for_it(self):
        from gui.dialogs.settings_dialog import SettingsDialog
        from tests.qt_test_support import reap_widget
        dlg = SettingsDialog({"cart_pad_duck_pct": 40, "cart_duck_pct": 15}, None)
        self.addCleanup(reap_widget, dlg)
        self.assertEqual(dlg._cart_pad_duck_spin.value(), 40)
        self.assertEqual(dlg._cart_duck_spin.value(), 15)
        dlg._cart_pad_duck_spin.setValue(25)
        self.assertEqual(dlg.values()["cart_pad_duck_pct"], 25)
        self.assertEqual(dlg.values()["cart_duck_pct"], 15)

    def test_reset_puts_it_back_on_the_default(self):
        from gui.dialogs.settings_dialog import SettingsDialog
        from tests.qt_test_support import reap_widget
        dlg = SettingsDialog({"cart_pad_duck_pct": 40}, None)
        self.addCleanup(reap_widget, dlg)
        dlg._reset_cartwall_values()
        self.assertEqual(dlg._cart_pad_duck_spin.value(), 10)

    def test_the_window_hands_it_to_the_wall(self):
        from types import SimpleNamespace
        from typing import Any, cast

        from player.audio.mix import OutputMix
        from player.window.main_cartwall import CartwallMixin
        voices = cart_voices.CartVoices(voices=2, factory=_factory)
        self.addCleanup(voices.shutdown)
        host = cast(Any, SimpleNamespace(
            _settings={"cart_pad_duck_pct": 45, "cart_duck_pct": 20},
            _mix=OutputMix(), _cart_voices=voices,
            _set_duck_reason=lambda r, on: None))
        CartwallMixin.apply_cart_settings(host)
        self.assertAlmostEqual(voices._pad_duck_level, 0.45)
        self.assertAlmostEqual(host._mix.cart_duck, 0.2)


if __name__ == "__main__":
    unittest.main()
