#!/usr/bin/env python3
"""A drop check in progress can't be acted on half-read.

Run:  py -m unittest tests.gui.test_drop_check_busy -v

The drop checks run on the GUI thread and pump events for their progress bar,
so a click can land in the middle of one. A second drop is already deferred
until the pass ends; the action buttons were not. In the Fix-paths dialog
that is "🧭 Fix (overwrite)", which rewrites the dropped playlists on disk
while the check is still reading them — lit from the previous result.
"""

import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication, QLabel

from gui.dialogs import FileDropCheckPanel
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])


class DropCheckBusyTest(unittest.TestCase):

    def setUp(self):
        d = Path(tempfile.mkdtemp(prefix="dp_dropbusy_"))
        self.m3u = d / "a.m3u"
        self.m3u.write_text("#EXTM3U\n", encoding="utf-8")
        self.seen = []
        self.panel = FileDropCheckPanel("info", run_fn=self._run,
                                        action_label="Fix", action_fn=lambda ps: None)
        self.addCleanup(reap_widget, self.panel)
        self.started = []
        self.panel.checkStarted.connect(lambda: self.started.append(1))

    def _run(self, paths, progress_cb):
        # What a click delivered by the progress bar's processEvents would find.
        self.seen.append(self.panel._action_btn.isEnabled())
        return QLabel("ok"), {"fixable": 1}

    def test_the_action_is_off_while_the_check_runs(self):
        self.panel._files.add_paths([str(self.m3u)])
        self.panel.refresh()
        self.assertEqual(self.seen, [False, False])
        self.assertTrue(self.panel._action_btn.isEnabled())

    def test_the_host_hears_that_a_check_started(self):
        # The Fix-paths dialog keeps its Fix button outside the panel; it turns
        # it off on this signal and back on from resultsReady.
        self.started.clear()
        self.panel.refresh()
        self.assertEqual(self.started, [1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
