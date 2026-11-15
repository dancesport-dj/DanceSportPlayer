#!/usr/bin/env python3
"""⏸ A pause running when Planning is opened is held, not lost.

Run:  .venv\\Scripts\\python.exe -m unittest tests.player.audio.test_pause_across_planning -v

The first tick outside Playing mode used to cancel the pause: it dropped the
armed advance and released the preloaded next title, while the card still read
"Auto-advance…". Back in Playing the pause seemed loaded, but its next title
was gone (Marcel, 2026-11-14). Now Planning holds the pause: nothing starts by
itself there, and back in Playing it counts on from the seconds it had left,
into the same next title.
"""

import unittest
from unittest import mock

from PySide6.QtWidgets import QApplication

from tests.player.audio.test_fade_indicator import _PausingDesk
from tests.qt_test_support import reap_widget


class _ModeDesk(_PausingDesk):
    def __init__(self):
        super().__init__()
        self.playing_mode = True
        self.countdown = ""
        self.released = []
        self._player.setSource = self.released.append

    def _is_playing_mode(self):
        return self.playing_mode

    def _set_countdown(self, text):
        self.countdown = text


class _Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@mock.patch("player.window.main_player.live_target", side_effect=lambda nxt: nxt)
class PauseAcrossPlanningTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.clock = _Clock()
        patcher = mock.patch("player.window.main_player.time.monotonic", self.clock)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.desk = _ModeDesk()
        self.addCleanup(reap_widget, self.desk)
        self.desk._set_pause(0)
        self.desk._between.advance_at = self.clock.now + 10

    def to_planning_and_back(self, away_secs):
        self.desk._on_play_tick()
        self.desk.playing_mode = False
        self.desk._on_play_tick()
        self.clock.now += away_secs
        self.desk._on_play_tick()
        self.desk.playing_mode = True

    def test_planning_keeps_the_pause_and_its_next_title(self, _live):
        self.to_planning_and_back(3)
        self.assertIsNotNone(self.desk._between.pending)
        self.assertEqual(self.desk._between.pending[2], "next.mp3")
        self.assertEqual(self.desk.released, [], "the preloaded title stays loaded")

    def test_nothing_starts_while_planning(self, _live):
        self.to_planning_and_back(60)     # far past the pause's end
        self.assertEqual(self.desk.fired, [])

    def test_back_in_playing_it_counts_on_from_where_it_was(self, _live):
        self.to_planning_and_back(60)
        self.desk._on_play_tick()
        self.assertEqual(self.desk.countdown, "⏸  10 s")
        self.assertTrue(self.desk._big_player.fading)
        self.clock.now += 10.1
        self.desk._on_play_tick()
        self.assertEqual(self.desk.fired, ["next.mp3"])

    def test_the_card_stops_blinking_while_it_is_held(self, _live):
        self.desk._on_play_tick()
        self.desk.playing_mode = False
        self.desk._on_play_tick()
        self.assertFalse(self.desk._big_player.fading)

    def test_a_new_pause_holds_its_own_seconds(self, _live):
        """The seconds held for one pause are not carried into the next."""
        self.to_planning_and_back(1)
        self.desk._stop_play_timer()
        self.desk._set_pause(0)
        self.desk._between.advance_at = self.clock.now + 4
        self.desk.playing_mode = False     # switched before the first tick
        self.desk._on_play_tick()
        self.desk.playing_mode = True
        self.desk._on_play_tick()
        self.assertEqual(self.desk.countdown, "⏸  4 s")

    def test_switching_auto_advance_off_still_cancels(self, _live):
        self.desk.playing_mode = False
        self.desk.advancing = False
        self.desk._on_play_tick()
        self.assertIsNone(self.desk._between.pending)


if __name__ == "__main__":
    unittest.main(verbosity=2)
