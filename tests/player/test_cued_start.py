#!/usr/bin/env python3
"""⏯ on a cued title starts it the way ▶ on its row does.

Run:  py -m unittest tests.player.test_cued_start -v

At start-up the first title of a deck is CUED: loaded, shown on the card,
silent. ⏯ (or Space, the presenter, the taskbar) then only told the backend to
play — the start itself was skipped: no spoken call, no TSO pitch, no Paso
Doble hold, no watchdog. The first title of the evening came in unannounced
while every title after it was called.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_cuedstart_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from player.main_player import PlayerControlMixin  # noqa: E402
from player.playback_state import PlaybackState  # noqa: E402
from player.between_dances import BetweenDances  # noqa: E402


class _Desk(PlayerControlMixin):
    PATH = Path(r"C:\music\walzer.mp3")

    def __init__(self, *, cued=True, stopped=True):
        self._playback = PlaybackState()
        self._playback.path = self.PATH
        self._cued = cued
        self._stopped = stopped
        self._pd_hold = None
        self._between = BetweenDances()
        self._between.round_start = None
        self._playback.token = 1
        self._all_tables = ()   # no deck: the start names none as live
        self.loads = []

    def _is_player_stopped(self):
        return self._stopped

    def _play_or_stop(self, path, start=True):
        self.loads.append((path, start))


class CuedStartTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_play_on_a_cued_title_runs_the_full_start(self):
        desk = _Desk()
        self.assertTrue(desk._resume_tap())
        self.assertEqual(desk.loads, [(_Desk.PATH, True)])

    def test_a_title_that_already_started_is_left_to_the_player(self):
        # Stopped after it ran (or held for its call): ⏯ restarts the file, as
        # before — a second start would call the dance a second time.
        desk = _Desk(cued=False)
        self.assertFalse(desk._resume_tap())
        self.assertEqual(desk.loads, [])

    def test_a_cued_title_is_only_started_from_a_stop(self):
        desk = _Desk(stopped=False)
        self.assertFalse(desk._resume_tap())
        self.assertEqual(desk.loads, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
