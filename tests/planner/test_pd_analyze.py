"""Tests for which Paso Dobles the 🐂 batch analysis actually decodes
(gui.workers.PdHighlightAnalyzer.select_todo)."""
import os
import tempfile
import unittest
from pathlib import Path


def _analyzer():
    # Lazy import, same reason as test_pd_stop: gui.workers pulls in modules
    # that resolve the GUI state files at import time.
    os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                          tempfile.mkdtemp(prefix="dp_pda_"))
    from gui.workers import PdHighlightAnalyzer
    return PdHighlightAnalyzer


class _FakeCache:
    """Three tracks: one never analyzed, one auto-detected, one hand-marked."""

    NEW = Path(r"C:\music\new.mp3")
    AUTO = Path(r"C:\music\auto.mp3")
    MANUAL = Path(r"C:\music\manual.mp3")
    ALL = [NEW, AUTO, MANUAL]

    def get_pd_highlights(self, path):
        return None if path == self.NEW else [45.0, 78.0, 121.0]

    def is_pd_manual(self, path):
        return path == self.MANUAL


class PdAnalyzeSelectionTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.select = staticmethod(_analyzer().select_todo)
        cls.cache = _FakeCache()

    def test_normal_run_only_fills_the_gaps(self):
        self.assertEqual(self.select(self.cache, _FakeCache.ALL, False),
                         [_FakeCache.NEW])

    def test_forced_run_redoes_the_auto_detected_ones(self):
        self.assertEqual(self.select(self.cache, _FakeCache.ALL, True),
                         [_FakeCache.NEW, _FakeCache.AUTO])

    def test_hand_marked_tracks_survive_a_forced_run(self):
        # The operator's ear beats the detector — 🎯 marks are never redone.
        self.assertNotIn(_FakeCache.MANUAL,
                         self.select(self.cache, _FakeCache.ALL, True))


if __name__ == "__main__":
    unittest.main()
