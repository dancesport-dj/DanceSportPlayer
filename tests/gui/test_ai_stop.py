#!/usr/bin/env python3
"""The conversation window has a Stop for the AI run.

Run:  py -m unittest tests.gui.test_ai_stop -v

A run can take minutes, and the 🤖 button stayed greyed out until the thread
gave up on its own. ⏹ Stop in the transcript window asks the worker to cancel;
the worker reports it as `cancelled`, not as an error, and the window says the
run was stopped and nothing changed.
"""

import os
import tempfile
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_aistop_"))

from planner import llm  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class AiStopTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self):
        from gui.ai_dialogs import AiTranscriptDialog
        dlg = AiTranscriptDialog()
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_stop_asks_once_and_says_so(self):
        dlg = self._dialog()
        asked = []
        dlg.stopRequested.connect(lambda: asked.append(True))
        dlg._stop_btn.click()
        dlg._stop_btn.click()
        self.assertEqual(asked, [True])
        self.assertFalse(dlg._stop_btn.isEnabled())
        self.assertIn("Stopping", dlg._status.text())

    def test_a_finished_run_has_nothing_to_stop(self):
        dlg = self._dialog()
        dlg.show()
        self.assertTrue(dlg._stop_btn.isVisible())
        dlg.finish("Done.")
        self.assertFalse(dlg._stop_btn.isVisible())

    def _run_worker(self, ask):
        from gui.workers import AiPlaylistWorker
        w = AiPlaylistWorker("rules", "task", [], "opus", "")
        got = {"cancelled": 0, "error": [], "done": []}
        w.cancelled.connect(lambda: got.__setitem__("cancelled", got["cancelled"] + 1))
        w.error.connect(got["error"].append)
        w.done.connect(lambda *a: got["done"].append(a))
        with mock.patch.object(llm, "ask_playlist", ask):
            w.cancel()
            w.run()                       # on this thread: direct signal delivery
        return got, ask

    def test_the_worker_reports_a_stop_as_cancelled_not_as_an_error(self):
        got, ask = self._run_worker(mock.Mock(side_effect=llm.Cancelled()))
        self.assertEqual(got, {"cancelled": 1, "error": [], "done": []})
        self.assertTrue(ask.call_args.kwargs["cancel"].is_set(),
                        "the worker's stop flag reaches the planner")

    def test_a_stopped_run_ends_quietly_in_the_window(self):
        from gui.main_generate import GenerateMixin
        log_dlg = mock.Mock()
        shown = []
        fake = types.SimpleNamespace(
            _ai_log=log_dlg,
            statusBar=lambda: types.SimpleNamespace(showMessage=shown.append))
        with mock.patch("gui.main_generate.QMessageBox") as box:
            GenerateMixin._on_ai_playlist_cancelled(fake)
        log_dlg.finish.assert_called_once()
        self.assertIn("Stopped", log_dlg.finish.call_args.args[0])
        self.assertEqual(shown, ["AI playlist stopped."])
        self.assertEqual(box.mock_calls, [], "a stop is not an error box")


if __name__ == "__main__":
    unittest.main(verbosity=2)
