#!/usr/bin/env python3
"""🎯 A highlight marked by hand outlives the 🐂 detection still running.

▶ on a Paso Doble with nothing stored starts the detection in the background.
The operator may mark a highlight by hand before it lands. The database never
lets a detection overwrite a hand mark; the session's copy, which the stop is
armed from, must not let it either — else the stop moves off the mark (or goes)
and the next play reads the detection's guess again.

Run:  py -m unittest tests.player.test_pd_manual_kept -v
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pd_kept_"))

from player.main_pd import PdStopMixin
from player.playback_state import PlaybackState

PATH = Path(r"C:\music\espana.mp3")


class _Panel:
    def pd_editing(self):
        return False

    def pd_highlight_stop(self):
        return True

    def pd_highlight_n(self):
        return 1

    def set_pd_marks(self, marks):
        self.marks = marks


class _Cache:
    """The database's rule: a detection never overwrites a hand mark."""

    def __init__(self):
        self.times = {}
        self.manual = set()

    def put_pd_highlights(self, path, times, manual=False):
        if not manual and str(path) in self.manual:
            return
        self.times[str(path)] = list(times)
        if manual:
            self.manual.add(str(path))

    def is_pd_manual(self, path):
        return str(path) in self.manual

    def save(self):
        pass


class _Library:
    def __init__(self):
        self.cache = _Cache()


class _Player:
    def duration(self):
        return 0

    def position(self):
        return 6000


class _Status:
    def showMessage(self, *_a):
        pass


class _Desk(PdStopMixin):
    """Just enough MainWindow for a hand mark and a detection result."""

    def __init__(self):
        self._playback = PlaybackState()
        self._playback.path = PATH
        self._playback.dance = "PD"
        self._play_panel = _Panel()
        self._library = _Library()
        self._player = _Player()
        self._pd_highlights = {}
        self._pd_stop_at = None

    def statusBar(self):
        return _Status()

    def _resolve_entry(self, _path):
        return None

    def _sync_big_player_limit(self):
        pass


class HandMarkKeptTest(unittest.TestCase):

    def setUp(self):
        self.desk = _Desk()
        self.desk._learn_pd_highlight()   # 🎯 at 0:06
        self.assertEqual(self.desk._pd_highlights[str(PATH)], [6.0])
        self.assertEqual(self.desk._pd_stop_at, 6.0)

    def test_a_detection_landing_later_keeps_the_hand_mark(self):
        self.desk._on_pd_highlights(str(PATH), [])
        self.assertEqual(self.desk._pd_highlights[str(PATH)], [6.0])
        self.assertEqual(self.desk._pd_stop_at, 6.0)

    def test_a_detection_failing_later_keeps_the_hand_mark(self):
        self.desk._on_pd_error(str(PATH), "ffmpeg died")
        self.assertEqual(self.desk._pd_highlights[str(PATH)], [6.0])

    def test_a_detection_without_a_hand_mark_still_lands(self):
        other = r"C:\music\other.mp3"
        self.desk._on_pd_highlights(other, [12.0, 40.0])
        self.assertEqual(self.desk._pd_highlights[other], [12.0, 40.0])


if __name__ == "__main__":
    unittest.main()
