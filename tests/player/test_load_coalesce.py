#!/usr/bin/env python3
"""Tests for the media-load rate limit behind ⏭ (`PlayerControlMixin._play_or_stop`).

Run:  py -m unittest tests.player.test_load_coalesce -v

Skipping as fast as the finger goes used to hand Windows Media Foundation a full
media-session teardown + rebuild per keypress, which it does not reliably
survive (see the reload watchdog in `_check_playback`, and the access violations
that came with fast skipping). Loads are now coalesced: the first press goes
through at once, presses inside `_LOAD_MIN_GAP_MS` only move the target, and one
load follows when the burst settles.

Only the gate is under test, so `_load_track` — everything that talks to the
backend — is replaced by a recorder on a bare mixin instance.
"""

import os
import tempfile
import unittest
from pathlib import Path

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_load_"))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from player.main_player import PlayerControlMixin, _LOAD_MIN_GAP_MS  # noqa: E402


class _Desk(PlayerControlMixin):
    """A player desk stripped to the load gate: same attributes MainWindow sets
    up, and a `_load_track` that records instead of touching the backend."""

    def __init__(self):
        self._player = object()          # only tested for truthiness
        self._last_load_at = 0.0
        self._pending_load = None
        self._load_timer = QTimer()
        self._load_timer.setSingleShot(True)
        self._load_timer.timeout.connect(self._flush_pending_load)
        self.loaded = []

    def _load_track(self, path, start=True):
        import time
        self._last_load_at = time.monotonic()
        self.loaded.append((path, start))


def _spin(app, ms):
    """Run the event loop for ms so the pending-load timer can fire."""
    done = []
    QTimer.singleShot(ms, lambda: done.append(True))
    while not done:
        app.processEvents()


class LoadCoalesceTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.desk = _Desk()

    def test_a_single_press_loads_at_once(self):
        """One ⏭ must not feel delayed."""
        self.desk._play_or_stop(Path("a.mp3"))
        self.assertEqual(self.desk.loaded, [(Path("a.mp3"), True)])

    def test_a_burst_reaches_the_backend_twice_not_once_per_press(self):
        """Six fast presses: the first title starts, the rest collapse into the
        one the finger stopped on."""
        for name in "abcdef":
            self.desk._play_or_stop(Path(f"{name}.mp3"))
        self.assertEqual(self.desk.loaded, [(Path("a.mp3"), True)])
        _spin(self.app, int(_LOAD_MIN_GAP_MS) + 120)
        self.assertEqual(self.desk.loaded,
                         [(Path("a.mp3"), True), (Path("f.mp3"), True)])

    def test_the_last_target_of_the_burst_wins(self):
        self.desk._play_or_stop(Path("a.mp3"))
        self.desk._play_or_stop(Path("b.mp3"))
        self.desk._play_or_stop(Path("c.mp3"))
        _spin(self.app, int(_LOAD_MIN_GAP_MS) + 120)
        self.assertEqual(self.desk.loaded[-1], (Path("c.mp3"), True))

    def test_stopping_is_never_delayed(self):
        """A stop must cut the music now, whatever the gate says."""
        self.desk._play_or_stop(Path("a.mp3"))
        self.desk._play_or_stop(None)
        self.assertEqual(self.desk.loaded[-1], (None, True))

    def test_stopping_drops_a_queued_skip(self):
        """The title the burst was heading for must not start after a stop."""
        self.desk._play_or_stop(Path("a.mp3"))
        self.desk._play_or_stop(Path("b.mp3"))     # queued
        self.desk._play_or_stop(None)              # …and cancelled
        _spin(self.app, int(_LOAD_MIN_GAP_MS) + 120)
        self.assertEqual(self.desk.loaded, [(Path("a.mp3"), True), (None, True)])

    def test_a_press_after_the_gap_goes_straight_through(self):
        """Normal operating pace is not rate-limited at all."""
        self.desk._play_or_stop(Path("a.mp3"))
        _spin(self.app, int(_LOAD_MIN_GAP_MS) + 120)
        self.desk._play_or_stop(Path("b.mp3"))
        self.assertEqual(self.desk.loaded, [(Path("a.mp3"), True),
                                            (Path("b.mp3"), True)])

    def test_a_cued_drop_keeps_its_start_flag(self):
        """Drag-drop cues with start=False — the deferred load must not play it."""
        self.desk._play_or_stop(Path("a.mp3"))
        self.desk._play_or_stop(Path("b.mp3"), start=False)
        _spin(self.app, int(_LOAD_MIN_GAP_MS) + 120)
        self.assertEqual(self.desk.loaded[-1], (Path("b.mp3"), False))

    def test_no_player_does_nothing(self):
        self.desk._player = None
        self.desk._play_or_stop(Path("a.mp3"))
        self.assertEqual(self.desk.loaded, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
