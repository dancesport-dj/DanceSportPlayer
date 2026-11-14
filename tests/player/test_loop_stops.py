"""What still ends a looping title while 🔁 plays the full length.

Marcel: with "Full length" chosen, a 🐂 PD-highlight stop or a 🔇 dead-air stop
might still end the title early. Both do - they are musical ends, not the play
length - and the loop then starts the same title again (`_queue_auto_advance`
keeps the row while `_looping()`). These tests pin that down on the real tick
and the real silence skip.
"""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_loopstops_"))

from player.window.main_audio import AudioLevelMixin
from tests.player.audio.test_pd_stop import _player_mixin, _TickDesk

LOOP_FULL = SimpleNamespace(loop_mode=lambda: True, loop_cut=lambda: False)


class PdHighlightStopTest(unittest.TestCase):

    def setUp(self):
        class Desk(_TickDesk, _player_mixin()):
            pass
        self.d = Desk(on=True, pos_ms=79_000)
        self.d._pd_stop_at = 78.0
        self.d._pd_verify_stop = False
        self.d._big_player = LOOP_FULL

    def test_the_highlight_stop_still_ends_a_looping_paso_doble(self):
        self.d._on_play_tick()
        self.assertEqual(self.d._ended, ["PD highlight stop"])

    def test_before_the_highlight_it_plays_on(self):
        self.d._player._pos = 70_000
        self.d._on_play_tick()
        self.assertEqual(self.d._ended, [])


class _SilentDesk(AudioLevelMixin):
    """A title whose last 5 s are dead air, 3 s into them."""

    def __init__(self):
        self._playback = SimpleNamespace(path=Path("song.mp3"), offset_ms=0,
                                         fade_in_from=None)
        self._silences = {"song.mp3": [(95.0, 100.0)]}
        self._player = SimpleNamespace(position=lambda: 98_000)
        self.ended = []

    def _track_duration(self, _path):
        return 100.0

    def statusBar(self):
        return SimpleNamespace(showMessage=lambda *a: None)

    def _on_timed_end(self, why):
        self.ended.append(why)


class DeadAirStopTest(unittest.TestCase):

    def test_the_dead_air_stop_ends_a_looping_title_too(self):
        d = _SilentDesk()
        d._big_player = LOOP_FULL
        self.assertTrue(d._maybe_skip_silence())
        self.assertEqual(d.ended, ["trailing silence"])


if __name__ == "__main__":
    unittest.main()
