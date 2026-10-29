#!/usr/bin/env python3
"""⏭ Next dance in the pause cuts the wait, not the call.

Run:  py -m unittest tests.player.test_next_dance_keeps_call -v

Marcel: "when i click next dance i miss the announcement, i only want skip
the play lenht of the pause music". ⏭ (and the card's "Next dance") stopped
the announcer and went straight into the title. With the call still to
come, it now moves the end of the pause up to where the voice comes in, and
the title starts once the call is through.
"""

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_next_keeps_call_"))

from player.audio.between_dances import BetweenDances
from player.window.main_pause import PauseMusicMixin
from player.window.main_player import PlayerControlMixin

LEAD = 3.0


class _Desk:
    _on_player_next = PlayerControlMixin._on_player_next
    _skip_to_call = PauseMusicMixin._skip_to_call

    def __init__(self, announce=True):
        self._between = BetweenDances()
        self._between.pending = ("table", 4, Path(r"C:\music\TG.mp3"))
        self._between.advance_at = time.monotonic() + 60.0
        self._announcer = mock.Mock()
        self._values = {"announce": announce}
        self.calls = []

    def _pv(self, key):
        return self._values[key]

    def _deck_advance(self, table):
        return True

    def _announce_dance_of(self, nxt):
        return "TG", 1

    def _announce_lead(self):
        return LEAD

    def _fire_pending_advance(self):
        self.calls.append("advance")

    def left(self):
        return self._between.advance_at - time.monotonic()


class NextDanceKeepsTheCallTest(unittest.TestCase):

    def test_the_wait_is_cut_to_where_the_call_comes_in(self):
        desk = _Desk()
        desk._on_player_next()
        self.assertEqual(desk.calls, [])
        desk._announcer.stop.assert_not_called()
        self.assertAlmostEqual(desk.left(), LEAD, delta=0.2)

    def test_a_pause_nearly_over_is_not_made_longer(self):
        desk = _Desk()
        desk._between.advance_at = time.monotonic() + 1.0
        desk._on_player_next()
        self.assertEqual(desk.calls, [])
        self.assertLess(desk.left(), 1.1)

    def test_once_the_call_is_spoken_it_goes_on_at_once(self):
        # The second press: the hall has its call, so ⏭ goes on at once.
        desk = _Desk()
        desk._between.announced = True
        desk._on_player_next()
        self.assertEqual(desk.calls, ["advance"])
        desk._announcer.stop.assert_called_once()

    def test_without_announcements_it_goes_on_at_once(self):
        desk = _Desk(announce=False)
        desk._on_player_next()
        self.assertEqual(desk.calls, ["advance"])


if __name__ == "__main__":
    unittest.main()
