#!/usr/bin/env python3
"""🔈 The call in a pause follows the list the next title comes from.

Run:  py -m unittest tests.player.window.test_pause_announce_list -v

No row is marked ▶ during the pause, so the play values fell back to the
list the panel shows. With two decks set differently, a click on the other
deck's tab during the pause decided whether the coming dance was called.
It is the armed advance's own list (`_between.pending[0]`) that counts.
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
                      tempfile.mkdtemp(prefix="dp_pause_announce_list_"))

from player.audio.between_dances import BetweenDances
from player.window.main_pause import PauseMusicMixin
from player.window.main_play_values import PlayValuesMixin


def _deck(announce: bool):
    return SimpleNamespace(_current_play_row=-1,
                           vals={"announce": announce, "advance": True})


class _Desk:
    _maybe_announce_next = PauseMusicMixin._maybe_announce_next
    _skip_to_call = PauseMusicMixin._skip_to_call
    _pending_announces = PauseMusicMixin._pending_announces
    _pv = PlayValuesMixin._pv
    _engine_list = PlayValuesMixin._engine_list
    _panel_list = PlayValuesMixin._panel_list
    _deck_advance = PlayValuesMixin._deck_advance
    _playing_row = PauseMusicMixin._playing_row

    def __init__(self, armed, shown):
        self._deckset = SimpleNamespace(all_tables=[armed, shown])
        self._panel_table = shown          # the tab the operator clicked
        self._between = BetweenDances()
        self._between.pending = (armed, 4, Path(r"C:\music\TG.mp3"))
        self._between.advance_at = time.monotonic() + 60.0
        self._announcer = mock.Mock()
        self._play_panel = mock.Mock()
        self._play_panel.announce_lead.return_value = True
        self._play_panel.announce_heat_only.return_value = False

    def _list_vals(self, table):
        return table.vals

    def _announce_dance_of(self, nxt):
        return "TG", 1

    def _announce_lead(self):
        return 3.0


class PauseAnnounceListTest(unittest.TestCase):

    def test_the_armed_list_calls_though_the_shown_one_is_silent(self):
        desk = _Desk(armed=_deck(True), shown=_deck(False))
        desk._maybe_announce_next()
        desk._announcer.speak.assert_called_once()
        self.assertTrue(_Desk(armed=_deck(True), shown=_deck(False))._skip_to_call())

    def test_a_silent_armed_list_stays_silent(self):
        desk = _Desk(armed=_deck(False), shown=_deck(True))
        desk._maybe_announce_next()
        desk._announcer.speak.assert_not_called()
        self.assertFalse(_Desk(armed=_deck(False), shown=_deck(True))._skip_to_call())


if __name__ == "__main__":
    unittest.main()
