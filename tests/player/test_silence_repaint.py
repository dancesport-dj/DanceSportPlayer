#!/usr/bin/env python3
"""A probe that lands has to reach the ⏱ column.

Run:  py -m unittest tests.player.test_silence_repaint -v

The red ⏱ cell is painted from the cached silence spans, and rows are filled
once — when the list is loaded. So a track probed afterwards (played, or swept
up by ⚙ Settings → 🔇 Probe silences) kept its black cell until the whole list
was loaded again, and the flag the cell exists to raise never appeared. Both
paths now repaint the rows that show the probed file.
"""

import os
import tempfile
import unittest
from pathlib import Path
from player.playback_state import PlaybackState

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_sil_paint_"))

_TRACK = r"F:\my music\tanzcds\hochzeit\hochzeit_aktuellv9.mp3"


class _Table:
    def __init__(self):
        self.asked = []

    def refresh_paths(self, paths):
        self.asked.append([str(p) for p in paths])
        return len(paths)


class ProbeWhilePlayingTest(unittest.TestCase):
    """The background probe of the track that is playing."""

    def _win(self):
        from player.main_audio import AudioLevelMixin

        class Win(AudioLevelMixin):
            pass

        w = Win()
        w._silences = {}
        w._cache = None
        w._playback = PlaybackState()
        w._playback.path = None
        w._big_player = None
        w.table = _Table()
        w._all_tables = [w.table]
        return w

    def test_the_rows_showing_that_file_are_repainted(self):
        w = self._win()
        w._on_silences(_TRACK, [[131.7, 225.9]])
        self.assertEqual(w.table.asked, [[_TRACK]])

    def test_a_probe_that_found_nothing_repaints_too(self):
        # "No silence here" is an answer, and the cell may be red from an
        # earlier threshold — it has to go back to black.
        w = self._win()
        w._on_silences(_TRACK, [])
        self.assertEqual(w.table.asked, [[_TRACK]])


class BulkProbeTest(unittest.TestCase):
    """The ⚙ Settings pass over the whole library."""

    def _win(self):
        from gui.main_analyze import AnalysisMixin

        class Win(AnalysisMixin):
            pass

        w = Win()
        w.table = _Table()
        w._all_tables = [w.table]
        return w

    def test_every_probed_path_is_repainted_when_the_pass_ends(self):
        w = self._win()
        w._repaint_silence_flags([Path(_TRACK)])
        self.assertEqual(w.table.asked, [[_TRACK]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
