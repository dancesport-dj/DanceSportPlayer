#!/usr/bin/env python3
"""Tests for 🔇 handing the sound device back while nothing plays.

Run:  py -m unittest tests.player.test_audio_idle -v

An onboard sound card un-mutes its analogue output stage the moment an app
opens it, and the PA carries that hiss across the hall — it starts with the app
and stops when the app closes, whether or not anything is playing. It is added
after the converter, downstream of every sample the app produces, so no filter
can reach it. Not holding the device open is the only cure.

The danger of letting go is a title that starts silently because some play path
forgot to ask for the device back. That is why taking it back hangs on the
players' own state signal, and why the wall takes it back inside `fire`.
"""

import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_idle_"))

from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from shared.playback import _AUDIO_IDLE_S  # noqa: E402
from player.audio_device import AudioDevice  # noqa: E402
from player.mix import OutputMix  # noqa: E402
from player.system_sounds import SystemSoundGuard  # noqa: E402


class _Voices:
    """Stands in for the cartwall pool: does it still hold the device?"""

    def __init__(self, playing=()):
        self.playing = list(playing)
        self.held = True

    def playing_keys(self):
        return self.playing

    def release_outputs(self):
        self.held = False

    def restore_outputs(self):
        self.held = True

    def set_level(self, level):
        pass


class _Desk:
    """The window's side of it: real players and a mix, around the device."""

    def __init__(self, release: bool = True, voices=None):
        self.settings = {"release_audio_idle": release}
        self.mix = OutputMix(0.9)
        self.player = QMediaPlayer()
        self.audio_out = QAudioOutput()
        self.player.setAudioOutput(self.audio_out)
        self.pause_player = QMediaPlayer()
        self.pause_out = QAudioOutput()
        self.pause_player.setAudioOutput(self.pause_out)
        self.voices = voices
        self.applied = 0
        self.device = AudioDevice(
            self.player, self.audio_out, self.pause_player, self.pause_out,
            mix=self.mix,
            settings=lambda: self.settings,
            cart_voices=lambda: self.voices,
            is_playing_mode=lambda: False,
            apply_volume=self.apply_volume,
            system_sounds=SystemSoundGuard())   # a no-op under the suite

    def apply_volume(self):
        self.applied += 1


class _IdleTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def idle_out(self, desk: _Desk):
        """Let the watchdog see silence for longer than the idle window."""
        desk.device.watch_idle()                 # first tick: starts the clock
        if desk.device.idle_since is not None:
            desk.device.idle_since -= _AUDIO_IDLE_S + 1
        desk.device.watch_idle()                 # second tick: past the window
        return desk

    def held(self, desk: _Desk) -> bool:
        return desk.player.audioOutput() is not None


class ReleaseTest(_IdleTest):

    def test_silence_hands_the_device_back(self):
        desk = self.idle_out(_Desk(voices=_Voices()))
        self.assertTrue(desk.device.released)
        self.assertFalse(self.held(desk))
        self.assertIsNone(desk.pause_player.audioOutput())
        self.assertFalse(desk.voices.held, "the wall kept the card open")

    def test_one_tick_of_silence_is_not_enough(self):
        """The gap between an announcement and the music must not close and
        re-open the card."""
        desk = _Desk()
        desk.device.watch_idle()
        self.assertTrue(self.held(desk))

    def test_switched_off_it_never_lets_go(self):
        desk = self.idle_out(_Desk(release=False))
        self.assertTrue(self.held(desk))

    def test_switching_it_off_takes_the_device_straight_back(self):
        desk = self.idle_out(_Desk(voices=_Voices()))
        desk.settings["release_audio_idle"] = False
        desk.device.watch_idle()
        self.assertTrue(self.held(desk))
        self.assertTrue(desk.voices.held)


class BusyTest(_IdleTest):
    """Nothing is handed back while anything is, or is about to be, audible."""

    def test_a_ringing_cartwall_pad_holds_the_device(self):
        desk = _Desk(voices=_Voices(playing=["A1"]))
        self.assertTrue(desk.device.busy())
        self.assertTrue(self.held(self.idle_out(desk)))

    def test_an_announcement_holds_the_device(self):
        desk = _Desk()
        desk.mix.duck_reason("announce", True)
        self.assertTrue(desk.device.busy())
        self.assertTrue(self.held(self.idle_out(desk)))

    def test_silence_alone_is_idle(self):
        self.assertFalse(_Desk().device.busy())


class TakeBackTest(_IdleTest):

    def test_the_state_signal_takes_the_device_back(self):
        """The safety net: whatever calls play(), the device is back before the
        first sample of the title is due."""
        desk = self.idle_out(_Desk(voices=_Voices()))
        desk.device.on_playback_state(QMediaPlayer.PlaybackState.PlayingState)
        self.assertTrue(self.held(desk))
        self.assertIs(desk.player.audioOutput(), desk.audio_out)
        self.assertIs(desk.pause_player.audioOutput(), desk.pause_out)
        self.assertTrue(desk.voices.held)
        self.assertFalse(desk.device.released)

    def test_stopping_does_not_take_it_back(self):
        desk = self.idle_out(_Desk())
        desk.device.on_playback_state(QMediaPlayer.PlaybackState.StoppedState)
        self.assertFalse(self.held(desk))

    def test_the_level_survives_the_round_trip(self):
        """The output object is kept — only the player lets go of it — so the
        master volume is not reset by an evening of idle releases — and the
        desk is asked to push the mix's level into it once more."""
        desk = _Desk()
        desk.audio_out.setVolume(0.42)
        self.idle_out(desk)
        desk.device.on_playback_state(QMediaPlayer.PlaybackState.PlayingState)
        self.assertIs(desk.player.audioOutput(), desk.audio_out)
        self.assertAlmostEqual(desk.audio_out.volume(), 0.42, places=5)
        self.assertEqual(desk.applied, 1)


class ClockTest(_IdleTest):

    def test_the_window_is_a_few_seconds(self):
        """Long enough to sit through the gap before the next title, short
        enough that the hiss is gone before anyone notices it."""
        self.assertGreaterEqual(_AUDIO_IDLE_S, 3.0)
        self.assertLessEqual(_AUDIO_IDLE_S, 15.0)

    def test_the_clock_restarts_when_something_plays(self):
        desk = _Desk(voices=_Voices())
        desk.device.watch_idle()
        self.assertIsNotNone(desk.device.idle_since)
        desk.voices.playing = ["A1"]
        desk.device.watch_idle()
        self.assertIsNone(desk.device.idle_since)


class CartwallTest(unittest.TestCase):
    """The wall's own half of the handover."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def voices(self):
        from player.cartwall import CartVoices

        def factory():
            player = QMediaPlayer()
            out = QAudioOutput()
            player.setAudioOutput(out)
            return player, out

        v = CartVoices(voices=2, factory=factory)
        self.addCleanup(v.shutdown)
        return v

    def test_it_lets_go_and_takes_back(self):
        v = self.voices()
        v.release_outputs()
        self.assertTrue(all(x.player.audioOutput() is None for x in v._pool))
        v.restore_outputs()
        self.assertTrue(all(x.player.audioOutput() is x.out for x in v._pool))

    def test_firing_a_pad_hands_the_WHOLE_desk_the_device_back(self):
        """The wall takes its own voices back inside `fire`. Doing that behind
        the desk's back would leave `released` set for good: the deck
        would keep its output detached and the evening's music stays silent."""
        from planner.cartwall import CartPad

        v = self.voices()
        desk = _Desk(voices=v)
        v.wantsDevice.connect(desk.device.ensure)   # as _build_cartwall does
        desk.device.release()
        self.assertIsNone(desk.player.audioOutput())

        v.fire(("A", 0, 0), CartPad(path=r"C:\samples\fanfare.mp3"))
        self.assertFalse(desk.device.released)
        self.assertIs(desk.player.audioOutput(), desk.audio_out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
