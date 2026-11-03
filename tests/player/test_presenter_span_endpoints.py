"""📺 The presenter's bar ends where playback ends: not at a cut a final's
celebration skips, and at dead air that comes before the cut (#88)."""
import unittest
from pathlib import Path
from types import SimpleNamespace

from player.window.main_presenter import PresenterMixin


def _desk(pos_ms=60_000, dur_ms=240_000, limit=120, silence_ms=None, celebrating=False):
    return SimpleNamespace(
        _player=SimpleNamespace(playbackRate=lambda: 1.0, position=lambda: pos_ms,
                                duration=lambda: dur_ms),
        _playback=SimpleNamespace(path=Path("a.mp3"), offset_ms=0),
        _pd_runs_to_its_highlight=lambda: False,
        _play_limit_secs=lambda: limit,
        _play_end_secs=lambda: float(limit),
        _celebrating=lambda: celebrating,
        _silence_stop_ms=lambda: silence_ms)


class SpanTest(unittest.TestCase):

    def left(self, **kw):
        return PresenterMixin._presenter_span(_desk(**kw))[2]

    def test_the_play_length_cut_is_the_end(self):
        self.assertAlmostEqual(self.left(), 60.0)

    def test_a_celebrating_title_runs_to_its_file_end(self):
        self.assertAlmostEqual(self.left(celebrating=True), 180.0)

    def test_dead_air_before_the_cut_is_the_end(self):
        self.assertAlmostEqual(self.left(silence_ms=90_000), 30.0)

    def test_dead_air_behind_the_cut_changes_nothing(self):
        self.assertAlmostEqual(self.left(silence_ms=200_000), 60.0)


if __name__ == "__main__":
    unittest.main()
