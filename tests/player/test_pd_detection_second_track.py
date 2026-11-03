"""🐂 A Paso Doble loaded while another one is being detected still gets its own
detection (#83)."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from player.audio.pending_work import PendingWork
from player.window import main_pd
from player.window.main_pd import PdStopMixin


class SecondTrackTest(unittest.TestCase):

    def fake(self, *running_paths):
        workers = {}
        for running_path in running_paths:
            worker = mock.Mock()
            worker.isRunning.return_value = True
            worker.path = running_path
            workers[str(running_path)] = worker
        return SimpleNamespace(_pd_highlights={}, _library=SimpleNamespace(cache=None),
                               _arm_pd_stop=mock.Mock(), _pending=PendingWork(pd_workers=workers),
                               _on_pd_highlights=mock.Mock(), _on_pd_error=mock.Mock())

    def test_a_different_track_starts_its_own_worker(self):
        dlg = self.fake(Path("first.pd.mp3"))
        with mock.patch.object(main_pd, "PdHighlightWorker") as cls:
            PdStopMixin._ensure_pd_highlights(dlg, Path("second.mp3"))
        cls.assert_called_once()
        cls.return_value.start.assert_called_once()
        self.assertIs(dlg._pending.pd_workers[str(Path("second.mp3"))], cls.return_value)

    def test_the_same_track_is_not_detected_twice(self):
        dlg = self.fake(Path("first.mp3"))
        with mock.patch.object(main_pd, "PdHighlightWorker") as cls:
            PdStopMixin._ensure_pd_highlights(dlg, Path("first.mp3"))
        cls.assert_not_called()

    def test_a_replay_of_the_first_track_does_not_start_a_second_analysis(self):
        """#81: the one worker slot held only the latest track, so the replay of
        the earlier one, still running, was analysed a second time."""
        dlg = self.fake(Path("first.mp3"), Path("second.mp3"))
        with mock.patch.object(main_pd, "PdHighlightWorker") as cls:
            PdStopMixin._ensure_pd_highlights(dlg, Path("first.mp3"))
        cls.assert_not_called()

    def test_finished_workers_are_dropped_from_the_map(self):
        dlg = self.fake(Path("first.mp3"))
        dlg._pending.pd_workers[str(Path("first.mp3"))].isRunning.return_value = False
        with mock.patch.object(main_pd, "PdHighlightWorker"):
            PdStopMixin._ensure_pd_highlights(dlg, Path("second.mp3"))
        self.assertEqual(list(dlg._pending.pd_workers), [str(Path("second.mp3"))])


if __name__ == "__main__":
    unittest.main()
