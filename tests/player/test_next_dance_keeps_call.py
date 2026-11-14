#!/usr/bin/env python3
"""⏭ Next dance in the pause cuts the wait, not the call.

Run:  py -m unittest tests.player.test_next_dance_keeps_call -v

Marcel: "when i click next dance i miss the announcement, i only want skip
the play lenht of the pause music". ⏭ (and the card's "Next dance") stopped
the announcer and went straight into the title. With the call still to
come, it now moves the end of the pause up to where the voice comes in, and
the title starts once the call is through.

Then: "why does the cut the pause short goes down to 5s pause? not fade out
and play immediatly?" The call is no longer put off to a lead before the
title: it starts at once, the pause music fades out under it, and the title
follows when the voice is through.
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
        self._cart_voices = mock.Mock()
        self._values = {"announce": announce}
        self.calls = []

    def _pending_announces(self):
        return self._values["announce"]

    def _deck_advance(self, table):
        return True

    def _announce_dance_of(self, nxt):
        return "TG", 1

    def _announce_lead(self):
        return LEAD

    def _maybe_announce_next(self):
        self._between.announced = True
        self.calls.append("announce")

    def _fire_pending_advance(self):
        self.calls.append("advance")

    def left(self):
        return self._between.advance_at - time.monotonic()


class NextDanceKeepsTheCallTest(unittest.TestCase):

    def test_the_call_starts_at_once_not_after_a_lead(self):
        desk = _Desk()
        desk._on_player_next()
        self.assertEqual(desk.calls, ["announce"],
                         "spoken now; the title waits for the tick")
        desk._announcer.stop.assert_not_called()
        self.assertLessEqual(desk.left(), 0.05, "no 3 s of pause left")

    def test_the_pause_music_fades_out_for_the_call(self):
        desk = _Desk()
        desk._on_player_next()
        desk._cart_voices.set_music_playing.assert_called_once_with(True)

    def test_a_wall_without_voices_still_calls(self):
        desk = _Desk()
        desk._cart_voices = None
        desk._on_player_next()
        self.assertEqual(desk.calls, ["announce"])

    def test_a_pause_nearly_over_is_not_made_longer(self):
        desk = _Desk()
        desk._between.advance_at = time.monotonic() + 1.0
        desk._on_player_next()
        self.assertEqual(desk.calls, ["announce"])
        self.assertLess(desk.left(), 1.1)

    def test_once_the_call_is_spoken_it_goes_on_at_once(self):
        # The second press: the hall has its call, so ⏭ goes on at once.
        desk = _Desk()
        desk._between.announced = True
        desk._on_player_next()
        self.assertEqual(desk.calls, ["advance"])
        desk._announcer.stop.assert_called_once()
        desk._cart_voices.set_music_playing.assert_not_called()

    def test_without_announcements_it_goes_on_at_once(self):
        desk = _Desk(announce=False)
        desk._on_player_next()
        self.assertEqual(desk.calls, ["advance"])


if __name__ == "__main__":
    unittest.main()
