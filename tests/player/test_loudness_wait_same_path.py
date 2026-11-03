"""📊 Playing a title whose background loudness probe is still running waits for
it, like a fresh load does (#84)."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from player.audio.pending_work import PendingWork
from player.window import main_audio
from player.window.main_audio import AudioLevelMixin


class SamePathProbeTest(unittest.TestCase):

    def fake(self, running_path):
        worker = mock.Mock()
        worker.isRunning.return_value = True
        worker.path = running_path
        return SimpleNamespace(
            _lufs_pending=None, _lufs_token=None, _pending=PendingWork(), _lufs_worker=worker, _lufs_failed=set(),
            _pv=lambda _k: True,
            _library=SimpleNamespace(cache=SimpleNamespace(get_lufs=lambda _p: None)),
            _playback=SimpleNamespace(token=7),
            _resume_after_loudness=mock.Mock())

    def run_await(self, dlg, path, start):
        with (mock.patch.object(main_audio, "find_ffmpeg", return_value="ffmpeg"),
              mock.patch.object(main_audio.QTimer, "singleShot") as single):
            return AudioLevelMixin._await_loudness(dlg, path, start), single

    def test_play_during_a_background_probe_of_the_same_title_waits(self):
        path = Path("a.mp3")
        dlg = self.fake(path)
        stand_down, single = self.run_await(dlg, path, True)
        self.assertTrue(stand_down)
        self.assertEqual(dlg._lufs_pending, path)
        self.assertEqual(dlg._lufs_token, 7)
        single.assert_called_once()

    def test_a_cue_during_the_same_probe_still_does_not_wait(self):
        path = Path("a.mp3")
        dlg = self.fake(path)
        stand_down, single = self.run_await(dlg, path, False)
        self.assertFalse(stand_down)
        self.assertIsNone(dlg._lufs_pending)
        single.assert_not_called()


    def test_the_wait_is_not_repeated_when_the_play_comes_back(self):
        """#1: the wait is capped. When it runs out, the title starts; its
        load re-enters `_await_loudness`, which must not wait a second time
        for the probe that is still running."""
        path = Path("a.mp3")
        dlg = self.fake(path)
        dlg._lufs_pending = path
        dlg._lufs_token = 7
        calls = []

        def load(p, start):
            calls.append(AudioLevelMixin._await_loudness(dlg, p, start))
        dlg._load_track = load
        with (mock.patch.object(main_audio, "find_ffmpeg", return_value="ffmpeg"),
              mock.patch.object(main_audio.QTimer, "singleShot") as single):
            AudioLevelMixin._resume_after_loudness(dlg, path)
        self.assertEqual(calls, [False])        # stands down for nobody
        single.assert_not_called()
        self.assertIsNone(dlg._lufs_pending)


if __name__ == "__main__":
    unittest.main()
