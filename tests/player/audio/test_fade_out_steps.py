#!/usr/bin/env python3
"""The bottom of a fade-out is a slope, not a stair.

Run:  py -m unittest tests.player.audio.test_fade_out_steps -v

"in main player with 3 seconds the fadeout sometimes seems to be a bit hart at
end" (Marcel, 2026-11-14). The fade-out level moved only on the 200 ms play
tick: on a 3 s ramp the last step before silence was up to a fifteenth of full
level, about -23 dB, and where it fell depended on how the tick happened to sit
against the end of the ramp - hence "sometimes". The ramp now moves on the
mix's fine step while it runs; the tick still decides when the title ends.

Driven through the real `_on_play_tick` on a virtual clock, at every tick
phase, for the ⏳ timed fade, the 🔉↓ fade by hand and the ✂️ hard-end fade.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_fadesteps_"))

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication, QWidget

from gui.decks.deck_set import DeckSet
from player.audio.between_dances import BetweenDances
from player.audio.fade_now import FadeNow
from player.audio.mix import OutputMix
from player.audio.playback_state import PlaybackState
from player.audio.resume_marks import ResumeMarks
from player.window.main_player import PlayerControlMixin
from tests.qt_test_support import reap_widget

TICK = 0.2
# One fine step of a 2 s ramp is 0.0125 (-38 dB); one 200 ms tick of a 3 s
# ramp was 0.067 (-23.5 dB).
QUIET = 0.013


class _Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class _Media:
    def __init__(self, clock, start_secs, duration_ms=0):
        self.clock = clock
        self.t0 = clock.now - start_secs
        self.duration_ms = duration_ms

    def playbackState(self):
        return QMediaPlayer.PlaybackState.PlayingState

    def position(self):
        return int((self.clock.now - self.t0) * 1000)

    def duration(self):
        return self.duration_ms

    def playbackRate(self):
        return 1.0


class _Timer:
    def __init__(self):
        self.running = False

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def isActive(self):
        return self.running


class _Desk(PlayerControlMixin, QWidget):
    """The play tick with everything around the fade stubbed out."""

    def __init__(self, clock, start_secs, limit=90.0, fade=3.0, duration_ms=0):
        QWidget.__init__(self)
        self._player = _Media(clock, start_secs, duration_ms)
        self._deckset = DeckSet()
        self._deckset.all_tables = ()
        self._fade_timer = _Timer()
        self._ramp_timer = _Timer()
        self._big_player = None
        self._playback = PlaybackState()
        self._playback.path = Path("C:/music/SW.mp3")
        self._mix = OutputMix()
        self._fade_now = FadeNow()
        self._between = BetweenDances()
        self._resume = ResumeMarks()
        self._pd_stop_at = None
        self._played_marked = True
        self._settings = {}
        self._limit = limit
        self._fade = fade
        self.levels = []
        self.ended = None

    # The tick's surroundings, each tested elsewhere.
    def _is_playing_mode(self):
        return True

    def _maybe_skip_silence(self):
        return False

    def _watch_stall(self):
        return False

    def _closing_tick(self):
        return False

    def _note_on_air(self):
        pass

    def _celebration_tick(self):
        return False

    def _begin_celebration(self):
        return False

    def _maybe_crossfade(self):
        pass

    def _pd_runs_to_its_highlight(self):
        return False

    def _play_limit_secs(self):
        return int(self._limit)

    def _play_end_secs(self):
        return self._limit

    def _pv(self, key):
        return self._fade if key == "fade" else 0

    def _looping(self):
        return False

    def _set_countdown(self, text):
        pass

    def _set_fade_indicator(self, on):
        pass

    def _apply_volume(self):
        if self.ended is None:
            self.levels.append(self._mix.fade)

    def _show_pull(self):
        pass

    def _on_timed_end(self, why):
        self.ended = why

    @property
    def _play_panel(self):
        return mock.Mock(stop_fade_due=lambda *_a: False)


def _run(desk, clock, phase_ms, secs):
    """Ticks every 200 ms from `phase_ms`, fine steps every 25 ms while their
    timer runs, for `secs` of virtual time or until the title ends."""
    base = clock.now
    tick_ms = int(TICK * 1000)
    step_ms = OutputMix.step_ms
    next_tick = phase_ms
    ms = 0
    while ms < secs * 1000 and desk.ended is None:
        ms += 5
        clock.now = base + ms / 1000
        if ms >= next_tick:
            desk._on_play_tick()
            next_tick += tick_ms
        elif ms % step_ms == 0 and desk._ramp_timer.running:
            desk._step_volume_ramp()


def _last_sound(levels):
    """The last level above silence before the music went to nothing."""
    loud = [lv for lv in levels if lv > 0.0001]
    return loud[-1] if loud else 0.0


class FadeOutStepTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def phases(self):
        return range(5, 205, 10)

    def desk(self, clock, **kw):
        d = _Desk(clock, **kw)
        self.addCleanup(reap_widget, d)
        return d

    def test_the_timed_fade_ends_quietly_at_every_tick_phase(self):
        worst = 0.0
        for phase in self.phases():
            clock = _Clock()
            with mock.patch("time.monotonic", clock):
                desk = self.desk(clock, start_secs=86.5)
                _run(desk, clock, phase, 6.0)
            self.assertEqual(desk.ended, "play length reached", phase)
            worst = max(worst, _last_sound(desk.levels))
        self.assertLessEqual(worst, QUIET)

    def test_the_fade_by_hand_ends_quietly_at_every_tick_phase(self):
        worst = 0.0
        for phase in self.phases():
            clock = _Clock()
            with mock.patch("time.monotonic", clock):
                desk = self.desk(clock, start_secs=10.0)
                desk._fade_now.start(3.0)
                _run(desk, clock, phase, 6.0)
            self.assertEqual(desk.ended, "fade-out finished", phase)
            worst = max(worst, _last_sound(desk.levels))
        self.assertLessEqual(worst, QUIET)

    def test_the_hard_end_fade_reaches_silence_quietly(self):
        worst = 0.0
        for phase in self.phases():
            clock = _Clock()
            with mock.patch("time.monotonic", clock):
                desk = self.desk(clock, start_secs=96.0, limit=0,
                                 duration_ms=100_000)
                desk._playback.hard_ends[str(desk._playback.path)] = True
                _run(desk, clock, phase, 4.5)
            self.assertIn(0.0, desk.levels, phase)
            worst = max(worst, _last_sound(desk.levels))
        self.assertLessEqual(worst, QUIET)

    def test_the_fine_steps_stop_with_the_ramp(self):
        clock = _Clock()
        with mock.patch("time.monotonic", clock):
            desk = self.desk(clock, start_secs=86.5)
            _run(desk, clock, 5, 6.0)
            desk._stop_play_timer()
            desk._step_volume_ramp()
        self.assertIsNone(desk._fade_now.follow)
        self.assertFalse(desk._ramp_timer.running)

    def test_no_fine_steps_while_the_title_plays_at_full(self):
        clock = _Clock()
        with mock.patch("time.monotonic", clock):
            desk = self.desk(clock, start_secs=30.0)
            _run(desk, clock, 5, 1.0)
        self.assertFalse(desk._ramp_timer.running)
        self.assertIsNone(desk.ended)

    def test_a_pause_holds_the_level_between_ticks(self):
        """The ramp goes on by the clock, and a paused title's clock stands."""
        clock = _Clock()
        with mock.patch("time.monotonic", clock):
            desk = self.desk(clock, start_secs=88.0)
            desk._on_play_tick()
            held = desk._mix.fade
            desk._player.playbackState = lambda: QMediaPlayer.PlaybackState.PausedState
            clock.now += 0.15
            desk._step_volume_ramp()
        self.assertEqual(desk._mix.fade, held)
        self.assertIsNone(desk._fade_now.follow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
