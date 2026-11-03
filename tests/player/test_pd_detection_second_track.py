"""🐂 A Paso Doble loaded while another one is being detected still gets its own
detection (#83)."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from player.window import main_pd
from player.window.main_pd import PdStopMixin


class SecondTrackTest(unittest.TestCase):

    def fake(self, running_path):
        worker = mock.Mock()
        worker.isRunning.return_value = True
        worker.path = running_path
        return SimpleNamespace(_pd_highlights={}, _library=SimpleNamespace(cache=None),
                               _arm_pd_stop=mock.Mock(), _pd_worker=worker,
                               _on_pd_highlights=mock.Mock(), _on_pd_error=mock.Mock())

    def test_a_different_track_starts_its_own_worker(self):
        dlg = self.fake(Path("first.pd.mp3"))
        with mock.patch.object(main_pd, "PdHighlightWorker") as cls:
            PdStopMixin._ensure_pd_highlights(dlg, Path("second.mp3"))
        cls.assert_called_once()
        cls.return_value.start.assert_called_once()
        self.assertIs(dlg._pd_worker, cls.return_value)

    def test_the_same_track_is_not_detected_twice(self):
        dlg = self.fake(Path("first.mp3"))
        with mock.patch.object(main_pd, "PdHighlightWorker") as cls:
            PdStopMixin._ensure_pd_highlights(dlg, Path("first.mp3"))
        cls.assert_not_called()


if __name__ == "__main__":
    unittest.main()
