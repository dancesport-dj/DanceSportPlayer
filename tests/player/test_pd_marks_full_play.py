#!/usr/bin/env python3
"""🐂 A Paso Doble played in full still shows its highlights.

Run:  py -m unittest tests.player.test_pd_marks_full_play -v

A final's pick plays the Paso Doble to its end (Settings → 🎛 Play sets, "full
for finals"), so no stop is armed. The card drew no marks then, and the ✏️ chip
row read "no marks" — the stored highlights are only loaded for a stop, so a
title with three detected highlights looked as if it had none, and a hand mark
set on that belief wiped them. The marks are shown either way; only the stop
follows the pick.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pd_full_"))

from gui.decks.deck_set import DeckSet
from player.audio.playback_state import PlaybackState

PATH = Path(r"F:\music\15 Espana Cani (PD 60).mp3")
STORED = [43.65, 78.69, 121.67]


class _Big:
    def __init__(self):
        self.marks = None
        self.armed = "untouched"

    def set_limit(self, *_a, **_k):
        pass

    def set_pd_marks(self, marks, armed=None):
        self.marks = marks
        self.armed = armed

    def set_wave_overlay(self, *_a, **_k):
        pass


class _Panel:
    def timed_enabled(self):
        return False

    def play_secs(self):
        return 0

    def play_set(self):
        return {"secs": 0, "fade": 0, "fade_inside": False}

    def pd_editing(self):
        return True

    def set_pd_marks(self, marks):
        self.chips = marks


class _Cache:
    def __init__(self, stored):
        self.stored = stored

    def get_pd_highlights(self, _path):
        return self.stored


class _Library:
    def __init__(self, stored):
        self.cache = _Cache(stored)


def _win(dance="PD", stored=STORED):
    from player.window.main_player import PlayerControlMixin

    class Win(PlayerControlMixin):
        def _pd_highlight(self):
            return False, 2     # the final's pick: played in full

        def _track_duration(self, _path):
            return 150.0

    w = Win()
    w._big_player = _Big()
    w._playback = PlaybackState()
    w._playback.path = PATH
    w._playback.dance = dance
    w._playback.offset_ms = 0
    w._silences = {}
    w._settings = {}
    w._play_panel = _Panel()
    w._deckset = DeckSet()
    w._deckset.all_tables = ()
    w._player = None
    w._library = _Library(stored)
    w._pd_highlights = {}
    w._pd_stop_at = None
    return w


class FullPlayMarksTest(unittest.TestCase):

    def test_the_card_draws_the_stored_marks_without_a_stop(self):
        w = _win()
        w._sync_big_player_limit()
        self.assertEqual(w._big_player.marks, STORED)
        self.assertIsNone(w._big_player.armed)

    def test_the_edit_chips_show_the_stored_marks(self):
        w = _win()
        w._refresh_pd_chips()
        self.assertEqual(w._play_panel.chips, STORED)

    def test_an_undetected_highlight_is_left_out(self):
        w = _win(stored=[None, 78.69, 121.67])
        w._sync_big_player_limit()
        self.assertEqual(w._big_player.marks, [78.69, 121.67])

    def test_a_title_never_analyzed_shows_none(self):
        w = _win(stored=None)
        w._sync_big_player_limit()
        self.assertEqual(w._big_player.marks, [])
        # …and is not remembered as "no highlights": a later stop still detects.
        self.assertNotIn(str(PATH), w._pd_highlights)

    def test_another_dance_draws_no_marks(self):
        w = _win(dance="SA")
        w._sync_big_player_limit()
        self.assertEqual(w._big_player.marks, [])


if __name__ == "__main__":
    unittest.main()
