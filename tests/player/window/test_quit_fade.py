#!/usr/bin/env python3
"""✕ with music on: it fades out before the app goes.

Run:  py -m unittest tests.player.window.test_quit_fade -v

Marcel: "if i close the window and a music from cartwall or main player is
still playing fade it out with the configured intervall before closing the
app". The title fades over its list's fade time and HOLDS at silence — a fade
that ended like a timed cut would start the next title on the way out — and
every sounding pad over its own fade or the wall's. The window closes itself
when the longest is done; a second ✕ meanwhile goes at once.
"""

import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_quit_fade_"))

from PySide6.QtMultimedia import QMediaPlayer

from player.audio.fade_now import FadeNow

PLAYING = QMediaPlayer.PlaybackState.PlayingState
PAUSED = QMediaPlayer.PlaybackState.PausedState


class _Player:
    def __init__(self, state):
        self.state = state

    def playbackState(self):
        return self.state


class _Voices:
    def __init__(self, fade_ms):
        self.fade_ms = fade_ms
        self.stopped = 0

    def stop_all(self):
        self.stopped += 1
        return self.fade_ms


class _Timer:
    def __init__(self):
        self.started = 0

    def start(self):
        self.started += 1


class _Out:
    def __init__(self, volume):
        self._volume = volume

    def volume(self):
        return self._volume

    def setVolume(self, v):
        self._volume = v


def _desk(state=PLAYING, fade=3.0, pad_ms=None, filler=None):
    from player.audio.between_dances import BetweenDances
    from player.window.main_player import PlayerControlMixin
    d = PlayerControlMixin.__new__(PlayerControlMixin)
    d._player = _Player(state)
    d._playback = SimpleNamespace(path=Path(r"C:\music\waltz.mp3"))
    d._fade_now = FadeNow()
    d._fade_timer = _Timer()
    d._cart_voices = _Voices(pad_ms) if pad_ms is not None else None
    d._pause_player = _Player(filler) if filler is not None else None
    d._pause_out = _Out(0.8)
    d._between = BetweenDances()
    d._pv = {"fade": fade}.__getitem__
    d._set_fade_indicator = lambda on: None
    d.close = lambda: None              # the window's own close()
    d._show_quit_fade = mock.Mock()     # the "closing" window, a real widget
    return d


def _in_the_pause(d):
    """`d` inside a pause, its tick wired up far enough to reach the fade."""
    d._between.pending = ("deck", 3, Path(r"C:\music\next.mp3"))
    d._is_playing_mode = lambda: True
    d._deck_advance = lambda deck: True
    d._set_countdown = lambda text: None
    d._fire_pending_advance = mock.Mock()
    return d


class FadeOutToQuitTest(unittest.TestCase):

    def test_the_title_fades_over_its_lists_fade_time(self):
        d = _desk(fade=3.0)
        self.assertEqual(d._fade_out_to_quit(), 3000)
        self.assertTrue(d._fade_now.running)
        self.assertEqual(d._fade_timer.started, 1)

    def test_the_fade_holds_instead_of_starting_the_next_title(self):
        d = _desk()
        d._fade_out_to_quit()
        self.assertTrue(d._fade_now.hold)

    def test_a_fade_already_running_is_kept_and_made_to_hold(self):
        d = _desk(fade=3.0)
        d._fade_now.start(8.0)            # 🔉↓ pressed before the ✕
        d._fade_out_to_quit()
        self.assertTrue(d._fade_now.hold)
        self.assertEqual(d._fade_now.total, 8.0)

    def test_sounding_pads_fade_and_the_longest_is_waited_for(self):
        d = _desk(state=PAUSED, pad_ms=4000)
        self.assertEqual(d._fade_out_to_quit(), 4000)
        self.assertEqual(d._cart_voices.stopped, 1)

    def test_title_and_pads_wait_for_the_longer(self):
        d = _desk(fade=3.0, pad_ms=1500)
        self.assertEqual(d._fade_out_to_quit(), 3000)

    def test_nothing_sounding_waits_for_nothing(self):
        d = _desk(state=PAUSED, pad_ms=0)
        self.assertEqual(d._fade_out_to_quit(), 0)
        self.assertFalse(d._fade_now.running)

    def test_the_pause_music_fades_over_the_lists_fade_time(self):
        # Between two titles: the deck holds the next one, the filler sounds.
        d = _desk(state=PAUSED, fade=3.0, filler=PLAYING)
        self.assertAlmostEqual(d._fade_out_to_quit(), 3000, delta=20)
        self.assertIsNotNone(d._between.fade_end)

    def test_pause_music_held_by_hand_is_not_waited_for(self):
        d = _desk(state=PAUSED, filler=PAUSED)
        self.assertEqual(d._fade_out_to_quit(), 0)
        self.assertIsNone(d._between.fade_end)


class PauseMusicQuitFadeTest(unittest.TestCase):
    """The ⏭ filler fade starts the next title when it ends; the quit's must
    stay silent until the window goes."""

    def test_at_its_end_the_quit_fade_starts_no_next_title(self):
        d = _in_the_pause(_desk(state=PAUSED, filler=PLAYING))
        d._fade_out_to_quit()
        d._fade_now.quitting = True
        d._between.fade_end = time.monotonic() - 0.1    # the fade has run out
        d._between_tick(d._player, d._between.pending)
        d._fire_pending_advance.assert_not_called()
        self.assertEqual(d._pause_out.volume(), 0.0)

    def test_the_skip_fade_still_starts_the_next_title(self):
        d = _in_the_pause(_desk(state=PAUSED, filler=PLAYING))
        d._start_pause_skip_fade()
        d._between.fade_end = time.monotonic() - 0.1
        d._between_tick(d._player, d._between.pending)
        d._fire_pending_advance.assert_called_once()


class QuitAfterFadeTest(unittest.TestCase):

    def test_the_close_waits_for_the_fade_then_comes_back(self):
        d = _desk(fade=2.0)
        with mock.patch("player.window.main_player.QTimer.singleShot") as shot:
            self.assertTrue(d._quit_after_fade())
        ms, _ctx, again = shot.call_args.args
        self.assertGreaterEqual(ms, 2000)
        self.assertIs(again, d.close)

    def test_the_second_close_goes_at_once(self):
        d = _desk(fade=2.0)
        with mock.patch("player.window.main_player.QTimer.singleShot"):
            d._quit_after_fade()
        self.assertFalse(d._quit_after_fade())

    def test_with_nothing_sounding_the_close_goes_at_once(self):
        d = _desk(state=PAUSED)
        self.assertFalse(d._quit_after_fade())
        d._show_quit_fade.assert_not_called()

    def test_the_fade_says_the_app_is_closing(self):
        # Marcel: "so the user not think that it stucks".
        d = _desk(fade=2.0)
        with mock.patch("player.window.main_player.QTimer.singleShot"):
            d._quit_after_fade()
        (ms,), _ = d._show_quit_fade.call_args
        self.assertAlmostEqual(ms, 2000, delta=20)


if __name__ == "__main__":
    unittest.main()
