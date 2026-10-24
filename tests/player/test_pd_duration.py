#!/usr/bin/env python3
"""🐂 The Paso Doble stop is armed with the Paso Doble's own length.

The stop is armed while the title is being loaded: `_playback.path` already
names the new file, but the player still holds the one before it (`stop()`
does not unload it). Its `duration()` is the previous title's, and a short
one made the PD's highlight count as the finale — the stop was disarmed and
the Paso Doble ran on into the next heat.

Run:  py -m unittest tests.player.test_pd_duration -v
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pd_duration_"))

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QMediaPlayer

from player.audio.playback_state import PlaybackState
from player.window.main_pd import PdStopMixin
from player.window.main_player import PlayerControlMixin
from planner.models import MusicEntry

BEFORE = Path(r"C:\music\WW\Moon River.mp3")
PD = Path(r"C:\music\PD\Espana Cani.mp3")


class _Player:
    def __init__(self, source, ms):
        self._source, self._ms = source, ms

    def source(self):
        return QUrl.fromLocalFile(str(self._source))

    def duration(self):
        return self._ms


class _Win(PdStopMixin):
    def __init__(self, source, ms):
        self._player = _Player(source, ms)
        self._playback = PlaybackState()
        self._playback.path = PD

    def _pd_highlight(self):
        # No round in play: the panel's highlight stop is the one.
        return self._play_panel.pd_highlight_stop(), self._play_panel.pd_highlight_n()

    def _resolve_entry(self, path):
        return MusicEntry(path=Path(path), title="x", dance="PD", bpm=60,
                          duration=150)


class TrackDurationTest(unittest.TestCase):

    def test_the_title_before_does_not_lend_its_length(self):
        """Still holding a 1:30 waltz: the PD's own 2:30 counts."""
        self.assertEqual(_Win(BEFORE, 90_000)._track_duration(PD), 150.0)

    def test_the_loaded_pd_reports_its_own(self):
        self.assertEqual(_Win(PD, 151_200)._track_duration(PD), 151.2)


class RearmOnLoadTest(unittest.TestCase):
    """Once the PD is open its exact length is known: the stop is set again."""

    class _Panel:
        def pd_highlight_stop(self):
            return True

        def pd_highlight_n(self):
            return 2

    def _win(self, dance):
        win = _Win(PD, 151_200)
        win._playback.dance = dance
        win._play_panel = self._Panel()
        win.armed = []
        win._arm_pd_stop = win.armed.append
        win._deckset = type("D", (), {"all_tables": ()})()
        win._play_ready_logged = True
        win._resume_seek_ms = None
        return win

    def test_a_pd_is_rearmed_when_it_has_loaded(self):
        win = self._win("PD")
        PlayerControlMixin._on_media_status(win, QMediaPlayer.MediaStatus.LoadedMedia)
        self.assertEqual(win.armed, [PD])

    def test_another_dance_is_left_alone(self):
        win = self._win("SA")
        PlayerControlMixin._on_media_status(win, QMediaPlayer.MediaStatus.LoadedMedia)
        self.assertEqual(win.armed, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
