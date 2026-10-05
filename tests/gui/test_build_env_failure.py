#!/usr/bin/env python3
"""Tests for a session snapshot that cannot be built.

Run:  py -m unittest tests.gui.test_build_env_failure -v

Every edit autosaves through _build_env, and it answered any exception with a
silent None — so one deck that could not be serialized stopped the autosave for
the rest of the evening, and the first anyone heard of it was the next launch
coming up with the session of hours ago.
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_buildenv_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

import dancesport_gui as gui  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class BuildEnvFailureTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        gui.load_settings = lambda *a, **kw: {"app_mode": "both"}
        self.win = gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)

        def broken(table):
            raise KeyError("rounds")
        self.win._serialize_playlist_state = broken

    def test_it_is_logged_with_its_cause(self):
        with self.assertLogs("dancesport.gui.persist", "ERROR") as caught:
            self.assertIsNone(self.win._build_env())
        self.assertIn("rounds", "\n".join(caught.output))

    def test_the_operator_is_told_the_session_is_not_being_saved(self):
        with self.assertLogs("dancesport.gui.persist", "ERROR"):
            self.win._autosave_playlist()
        self.assertIn("not saved", self.win.statusBar().currentMessage())


if __name__ == "__main__":
    unittest.main()
