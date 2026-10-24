#!/usr/bin/env python3
"""🎶 A background pad under the between-songs pause music.

Run:  py -m unittest tests.player.test_cartwall_filler -v

Marcel: "if pause between active with a song put beneath and we have a pad in
background modus both is playing, in this case the pause song should
winning". The pause music is music like a title: a 🎶 pad gives way to it the
same way, muted or paused as ⚙ Settings ▸ 🎛 Cartwall says.
"""

import unittest

from PySide6.QtMultimedia import QMediaPlayer

from player.window.main_cartwall import CartwallMixin

_PLAYING = QMediaPlayer.PlaybackState.PlayingState
_PAUSED = QMediaPlayer.PlaybackState.PausedState
_STOPPED = QMediaPlayer.PlaybackState.StoppedState


class _Player:
    def __init__(self, state=_STOPPED):
        self.state = state

    def playbackState(self):
        return self.state


class _Voices:
    def __init__(self):
        self.told = []

    def set_music_playing(self, playing):
        self.told.append(playing)


class FillerBeatsBackgroundPadTest(unittest.TestCase):

    def desk(self, deck, filler):
        d = CartwallMixin.__new__(CartwallMixin)
        d._cart_voices = _Voices()
        d._player = _Player(deck)
        d._pause_player = _Player(filler) if filler is not None else None
        return d

    def test_the_pause_music_starting_takes_the_pads_down(self):
        d = self.desk(_STOPPED, _PLAYING)
        d._cart_follow_deck(_PLAYING)
        self.assertEqual(d._cart_voices.told, [True])

    def test_the_deck_stopping_for_the_pause_does_not_lift_them(self):
        """The title ends and the filler is already on: no gap for the bed."""
        d = self.desk(_STOPPED, _PLAYING)
        d._cart_follow_deck(_STOPPED)
        self.assertEqual(d._cart_voices.told, [True])

    def test_the_pause_music_stopping_with_nothing_else_lifts_them(self):
        d = self.desk(_STOPPED, _PAUSED)
        d._cart_follow_deck(_PAUSED)
        self.assertEqual(d._cart_voices.told, [False])

    def test_the_deck_alone_still_counts(self):
        d = self.desk(_PLAYING, _STOPPED)
        d._cart_follow_deck(_PLAYING)
        self.assertEqual(d._cart_voices.told, [True])

    def test_a_build_without_pause_music_follows_the_deck(self):
        d = self.desk(_PLAYING, None)
        d._cart_follow_deck(_PLAYING)
        self.assertEqual(d._cart_voices.told, [True])


if __name__ == "__main__":
    unittest.main(verbosity=2)
