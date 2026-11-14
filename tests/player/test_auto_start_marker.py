#!/usr/bin/env python3
"""A ↩ time marker is only picked up where the operator asks for it.

Run:  py -m unittest tests.player.test_auto_start_marker -v

Marcel: "if a title has a time marker and we are in auto mode we play it from
the beginning, only if clicked single we asks". A click on ▶ (or Space, or a
double-click) asks where the marked title starts (`_ask_resume_mark`). The list
walking on by itself has nobody to ask, so a title it starts — after the pause,
by the crossfade, or as the failover for a title that would not play — starts
from the top and its marker goes, exactly as "From the beginning" does.
"""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_automark_"))

from player.audio.between_dances import BetweenDances
from player.audio.resume_marks import ResumeMarks

MARKED = Path(r"C:\music\marked.mp3")
OTHER = Path(r"C:\music\other.mp3")


def _mixin():
    from player.window.main_player import PlayerControlMixin
    return PlayerControlMixin


class _Table:
    """The deck's table: records what the ▶ route would find at the moment the
    title is started (the load reads the marker there)."""

    def __init__(self, host):
        self.host = host
        self.started = []
        self._row_meta = SimpleNamespace(
            at=lambda row: SimpleNamespace(path_str=str(MARKED)),
            numbered=lambda: [(1, SimpleNamespace(path_str=str(MARKED)))])

    def _on_play_click(self, row, path):
        self.started.append((row, path, self.host._resume_mark_for(path)))

    def scroll_row_into_play_view(self, row):
        pass


class _Host:
    def __init__(self):
        mixin = _mixin()
        for name in ("_fire_pending_advance", "_start_failover", "_clear_resume",
                     "_resume_mark_for", "remember_pos"):
            setattr(self, name, getattr(mixin, name).__get__(self))
        self._settings = {"remember_pos": True}
        self._resume = ResumeMarks()
        self._between = BetweenDances()
        self.table = _Table(self)
        self._big_player = None
        self.refreshed = []

    def _is_playing_mode(self):
        return True

    def _set_fade_indicator(self, on):
        pass

    def _refresh_resume_marks(self, path=None):
        self.refreshed.append(path)

    def statusBar(self):
        return SimpleNamespace(showMessage=lambda *a, **k: None)

    def mark(self, path):
        self._resume.note(path, 60_000, 180_000)
        assert self._resume.get(path) == 60_000


class AutoStartDropsTheMarkerTest(unittest.TestCase):

    def setUp(self):
        self.host = _Host()
        self.host.mark(MARKED)

    def test_the_advance_after_the_pause_starts_from_the_top(self):
        self.host._between.pending = (self.host.table, 1, MARKED)
        self.host._fire_pending_advance()
        self.assertEqual(self.host.table.started, [(1, MARKED, None)])
        self.assertIsNone(self.host._resume.get(MARKED))

    def test_the_failover_starts_from_the_top(self):
        self.host._start_failover((self.host.table, 1, MARKED))
        self.assertEqual(self.host.table.started, [(1, MARKED, None)])
        self.assertIsNone(self.host._resume.get(MARKED))

    def test_the_badge_follows(self):
        self.host._between.pending = (self.host.table, 1, MARKED)
        self.host._fire_pending_advance()
        self.assertIn(MARKED, self.host.refreshed)

    def test_the_other_titles_keep_their_markers(self):
        self.host.mark(OTHER)
        self.host._between.pending = (self.host.table, 1, MARKED)
        self.host._fire_pending_advance()
        self.assertEqual(self.host._resume.get(OTHER), 60_000)

    def test_a_title_without_a_marker_starts_as_before(self):
        host = _Host()
        host._between.pending = (host.table, 1, MARKED)
        host._fire_pending_advance()
        self.assertEqual(host.table.started, [(1, MARKED, None)])

    def test_a_click_is_not_the_engine_so_the_marker_stands_for_the_question(self):
        # The ▶ route asks first (`_confirm_marked_start`) and only then clears
        # on "From the beginning"; nothing here may spend the marker before that.
        self.assertEqual(self.host._resume_mark_for(MARKED), 60_000)


if __name__ == "__main__":
    unittest.main()
