#!/usr/bin/env python3
"""⏱➕ while the filler is ⏯-held: the extension sticks.

Run:  py -m unittest tests.player.test_extend_held_pause -v

A held pause pins its deadline to "now + the seconds left when the hold
began" on every tick. ⏱➕ added its seconds to the deadline only, so the
next tick pinned it back and the next title started on the old deadline.
"""

import os
import tempfile
import time
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_extend_held_"))

from player.audio.between_dances import BetweenDances
from player.window.main_pause import PauseMusicMixin


class _Win:
    _extend_pause = PauseMusicMixin._extend_pause

    def __init__(self):
        self._between = BetweenDances()
        self._between.pending = (None, 0, None)
        self._filler = mock.Mock(total=30.0)
        self._engine_pause_secs = lambda: 20
        self._set_countdown = lambda _text: None
        self.statusBar = lambda: mock.Mock()


class ExtendHeldPauseTest(unittest.TestCase):

    def test_a_held_pause_keeps_the_extension(self):
        w = _Win()
        w._between.held = True
        w._between.hold_remaining = 10.0
        w._between.advance_at = time.monotonic() + 10.0
        w._extend_pause()
        self.assertEqual(w._between.hold_remaining, 30.0)

    def test_a_running_pause_moves_its_deadline(self):
        w = _Win()
        w._between.advance_at = at = time.monotonic() + 10.0
        w._extend_pause()
        self.assertEqual(w._between.advance_at, at + 20)


if __name__ == "__main__":
    unittest.main()
