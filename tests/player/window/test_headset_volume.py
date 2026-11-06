#!/usr/bin/env python3
"""🎧 The window stops, asks and remembers on a loud headset volume.

Run:  .venv\\Scripts\\python.exe -m unittest tests.player.window.test_headset_volume -v
"""
import os
import unittest
from unittest import mock

from player.audio.headset_guard import LOWER, LOWER_FULL, SAFE, SAFE_FULL
from player.window import main_audio
from player.window.main_audio import AudioLevelMixin


def _host(output="Headphones (Realtek)", base=1.0, master=1.0, form=None):
    host = mock.Mock()
    host._audio_device.music_output_state.return_value = (master, form)
    host._audio_device.music_output_name.return_value = output
    host._mix.base = base

    def set_base(v):
        host._mix.base = v
    host._set_base_volume.side_effect = set_base
    host._warn_loud_headset.side_effect = lambda n, m: AudioLevelMixin._warn_loud_headset(host, n, m)
    return host


def _box(keep_it: bool, lower: bool = False):
    """A QMessageBox whose user pressed Keep, the lower Reduce, or Reduce."""
    box = mock.Mock()
    reduce_, lower_, keep = (mock.Mock(name="reduce"), mock.Mock(name="lower"),
                             mock.Mock(name="keep"))
    box.addButton.side_effect = [lower_, reduce_, keep]   # left to right
    box.clickedButton.return_value = keep if keep_it else lower_ if lower else reduce_
    return box


class HeadsetVolumeTest(unittest.TestCase):
    def guard(self, host, box, start=True):
        env = {"DANCEPLAYLIST_NO_HEADSET_GUARD": ""}
        with mock.patch.dict(os.environ, env),                 mock.patch.object(main_audio, "QMessageBox", return_value=box) as cls:
            cls.Icon = mock.MagicMock()
            cls.ButtonRole = mock.MagicMock()
            AudioLevelMixin._guard_headset_volume(host, start)

    def test_the_volume_is_untouched_while_the_question_is_open(self):
        host = _host()
        box = _box(False)
        box.exec.side_effect = lambda: self.assertEqual(host._mix.base, 1.0)
        self.guard(host, box)
        box.exec.assert_called_once()
        self.assertEqual(host._mix.base, SAFE_FULL)

    def test_playing_music_is_never_stopped_only_warned_once_per_level(self):
        host = _host()
        host._player.playbackState.return_value = main_audio.QMediaPlayer.PlaybackState.PlayingState
        box = _box(False)
        with mock.patch.object(main_audio, "show_toast") as toast:
            self.guard(host, box, start=False)
            self.guard(host, box, start=False)   # same level: no second warning
        box.exec.assert_not_called()
        host._player.pause.assert_not_called()
        host._set_base_volume.assert_not_called()
        toast.assert_called_once()
        self.assertTrue(toast.call_args.kwargs["error"])

    def test_an_idle_player_is_not_bothered_by_a_fader_move(self):
        host = _host()
        host._player.playbackState.return_value = main_audio.QMediaPlayer.PlaybackState.StoppedState
        box = _box(False)
        with mock.patch.object(main_audio, "show_toast") as toast:
            self.guard(host, box, start=False)
        box.exec.assert_not_called()
        toast.assert_not_called()

    def test_stopped_music_is_not_started_by_the_guard(self):
        host = _host()
        host._player.playbackState.return_value = main_audio.QMediaPlayer.PlaybackState.StoppedState
        self.guard(host, _box(False), start=False)
        host._player.play.assert_not_called()

    def test_below_full_the_button_offers_70_at_full_it_offers_50(self):
        for base, want in ((1.0, SAFE_FULL), (0.9, SAFE)):
            host = _host(base=base)
            box = _box(False)
            self.guard(host, box)
            label = box.addButton.call_args_list[1].args[0]
            self.assertIn("%d" % round(want * 100), label, base)
            self.assertAlmostEqual(host._mix.base, want)

    def test_the_box_has_no_warning_icon_because_that_icon_plays_a_sound(self):
        """Probed on Windows: a QMessageBox with the Warning icon plays the
        alert sound on the app's own audio session (the System Sounds mute
        does not catch it), at the headset's volume. No icon, no sound; the
        red heading carries the warning."""
        host = _host()
        box = _box(False)
        with mock.patch.dict(os.environ, {"DANCEPLAYLIST_NO_HEADSET_GUARD": ""}),                 mock.patch.object(main_audio, "QMessageBox", return_value=box) as cls:
            cls.Icon = mock.MagicMock()
            cls.ButtonRole = mock.MagicMock()
            AudioLevelMixin._guard_headset_volume(host, True)
        box.setIcon.assert_called_once_with(cls.Icon.NoIcon)

    def test_only_one_question_is_open_at_a_time(self):
        host = mock.Mock(spec=[])
        host.__dict__.update(_host().__dict__)
        box = _box(False)
        seen = {}

        def inside():
            seen["flag"] = vars(host).get("_headset_dialog")
            # a second play() while the box is open: held, nothing scheduled
            with mock.patch.object(main_audio.QTimer, "singleShot") as single:
                seen["held"] = AudioLevelMixin._headset_play_gate(host)
                seen["scheduled"] = single.called
                # and its question, were it to run, opens no second box
                before = host._player.play.call_count
                AudioLevelMixin._guard_headset_volume(host, True)
                seen["played"] = host._player.play.call_count - before
        box.exec.side_effect = inside
        self.guard(host, box)
        self.assertTrue(seen["flag"])
        self.assertTrue(seen["held"])
        self.assertFalse(seen["scheduled"])
        self.assertEqual(seen["played"], 0)
        self.assertFalse(vars(host).get("_headset_dialog"))   # closed again
        host._player.play.assert_called_once()                # only the answer plays

    def test_a_third_button_goes_lower_still(self):
        for base, want in ((1.0, LOWER_FULL), (0.9, LOWER)):
            host = _host(base=base)
            box = _box(False)
            self.guard(host, box)
            labels = [c.args[0] for c in box.addButton.call_args_list]
            self.assertEqual(len(labels), 3, base)
            self.assertIn("%d" % round(want * 100), labels[0], base)   # the lowest is the left one

    def test_labels_show_the_level_not_the_fader(self):
        for base, master, want in ((1.0, 0.73, (30, 50)), (1.0, 0.9, (30, 50)),
                                   (0.9, 0.9, (50, 70))):
            host = _host(base=base, master=master)
            box = _box(False)
            self.guard(host, box)
            labels = [c.args[0] for c in box.addButton.call_args_list]
            self.assertIn("%d" % want[0], labels[0], (base, master))
            self.assertIn("%d" % want[1], labels[1], (base, master))

    def test_the_lower_button_sets_the_lower_level(self):
        for base, master, want in ((1.0, 1.0, LOWER_FULL), (0.9, 1.0, LOWER),
                                   (1.0, 0.9, LOWER_FULL)):
            host = _host(base=base, master=master)
            self.guard(host, _box(False, lower=True))
            self.assertAlmostEqual(host._mix.base * master, want, msg=(base, master))
            host._player.play.assert_called_once()

    def test_keeping_the_volume_puts_it_back(self):
        host = _host(base=0.9)
        self.guard(host, _box(True))
        self.assertEqual(host._mix.base, 0.9)

    def test_a_low_windows_slider_makes_full_app_volume_fine(self):
        host = _host(base=1.0, master=0.07)
        box = _box(False)
        self.guard(host, box)
        box.exec.assert_not_called()
        host._set_base_volume.assert_not_called()

    def test_the_windows_slider_is_counted_in_the_safe_level(self):
        host = _host(base=1.0, master=0.9)
        self.guard(host, _box(False))
        self.assertAlmostEqual(host._mix.base * 0.9, SAFE_FULL)

    def test_keeping_it_is_remembered_for_that_level(self):
        host = _host(base=0.9)
        self.guard(host, _box(True))
        box = _box(False)
        self.guard(host, box)       # same level: not asked twice
        box.exec.assert_not_called()

    def test_a_louder_level_asks_again_a_raise_back_only_warns(self):
        host = _host(base=0.9)
        self.guard(host, _box(True))
        host._mix.base = 1.0       # the fader goes all the way up: louder, asks
        box = _box(False)
        self.guard(host, box)
        box.exec.assert_called_once()
        self.assertEqual(host._mix.base, SAFE_FULL)
        self.guard(host, _box(False), start=False)   # the settled fader at 70 %
        host._mix.base = 1.0       # raised back up to the level asked about
        box = _box(False)
        with mock.patch.object(main_audio, "show_toast") as toast:
            self.guard(host, box)  # a toast, no dialog, the music starts
        box.exec.assert_not_called()
        toast.assert_called_once()
        host._player.play.assert_called()
        self.assertEqual(host._mix.base, 1.0)

    def test_the_mac_jack_asks_at_100_on_both_only(self):
        for base, asked in ((0.9, False), (1.0, True)):
            host = _host("External Headphones", base)
            box = _box(False)
            self.guard(host, box)
            self.assertEqual(box.exec.called, asked, base)

    def test_a_line_level_interface_is_left_alone(self):
        host = _host("Maya44 USB (Headphones out)", 1.0, form=2)
        box = _box(False)
        self.guard(host, box)
        box.exec.assert_not_called()

    def test_speakers_and_quiet_volumes_are_left_alone(self):
        for host in (_host("Speakers (Realtek)", 1.0), _host(base=0.4)):
            box = _box(False)
            self.guard(host, box)
            box.exec.assert_not_called()
            host._set_base_volume.assert_not_called()


class PlayGateTest(unittest.TestCase):
    """Pressing play on a loud headset starts nothing and changes nothing."""

    def gate(self, host):
        with mock.patch.dict(os.environ, {"DANCEPLAYLIST_NO_HEADSET_GUARD": ""}),                 mock.patch.object(main_audio.QTimer, "singleShot") as single:
            held = AudioLevelMixin._headset_play_gate(host)
        return held, single

    def test_loud_play_is_held_back_and_the_volume_untouched(self):
        host = _host()
        held, single = self.gate(host)
        self.assertTrue(held)
        single.assert_called_once()
        host._set_base_volume.assert_not_called()
        host._player.play.assert_not_called()

    def test_a_second_press_does_not_ask_twice(self):
        host = mock.Mock(spec=[])
        host.__dict__.update(_host().__dict__)
        held, single = self.gate(host)
        held2, single2 = self.gate(host)
        self.assertTrue(held and held2)
        single2.assert_not_called()

    def test_a_safe_play_goes_through(self):
        held, single = self.gate(_host(base=0.4))
        self.assertFalse(held)
        single.assert_not_called()

    def test_the_answer_starts_the_held_music_at_the_chosen_level(self):
        host = _host()
        host._player.playbackState.return_value = main_audio.QMediaPlayer.PlaybackState.StoppedState
        with mock.patch.dict(os.environ, {"DANCEPLAYLIST_NO_HEADSET_GUARD": ""}),                 mock.patch.object(main_audio, "QMessageBox", return_value=_box(False)) as cls:
            cls.Icon = cls.ButtonRole = mock.MagicMock()
            box = cls.return_value
            box.exec.side_effect = lambda: (
                self.assertEqual(host._mix.base, 1.0),
                host._player.play.assert_not_called())
            AudioLevelMixin._guard_headset_volume(host, True)
        self.assertEqual(host._mix.base, SAFE_FULL)
        host._player.play.assert_called_once()


class TriggerTest(unittest.TestCase):
    """The check is not only for start-up: play and a settled fader run it too."""

    def test_the_deck_player_has_the_gate(self):
        with open("dancesport_gui.py", encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("self._player = GatedMediaPlayer(self)", src)
        self.assertIn("self._player.gate = self._headset_play_gate", src)

    def test_a_settled_fader_runs_the_check(self):
        with open("dancesport_gui.py", encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("_vol_save_timer.timeout.connect(self._guard_headset_volume)", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
