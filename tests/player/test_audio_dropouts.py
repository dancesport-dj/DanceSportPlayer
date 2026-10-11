#!/usr/bin/env python3
"""Tests for the evidence a stutter leaves in session.log.

Run:  py -m unittest tests.player.test_audio_dropouts -v

A stutter nobody can point at a time for cannot be traced. Windows adds and
drops outputs under a running player (the monitors' HDMI audio flips about 100
times a day as the screens sleep and wake), and each change goes on the record.

The FFmpeg renderer's own stall messages do NOT, any more: logging them froze
the app (see NoMediaThreadLoggingTest).
"""

import ast
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_dropouts_"))

from PySide6.QtWidgets import QApplication

from tests.player.test_audio_idle import _Desk


class NoMediaThreadLoggingTest(unittest.TestCase):
    """The app must not switch on a Qt debug category to log from.

    Its message handler is Python, so every message switched on there runs
    Python on the thread that sent it. The FFmpeg renderer sends from its own
    thread, and the GUI thread waits on that thread inside QMediaPlayer.stop()
    while holding the GIL. A message in that window waited for the GIL and the
    GUI thread waited for the message, so the app froze for good. That
    happened on 2026-10-10, with the renderer's stall messages switched on."""

    def test_no_debug_category_is_switched_on(self):
        source = (Path(__file__).resolve().parents[2] / "dancesport_gui.py").read_text(
            encoding="utf-8")
        calls = [ast.get_source_segment(source, node)
                 for node in ast.walk(ast.parse(source))
                 if isinstance(node, ast.Call)
                 and getattr(node.func, "attr", None) == "setFilterRules"]
        self.assertEqual([c for c in calls if "debug=true" in c], [])


class OutputsChangedTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_a_list_change_around_the_same_default_is_logged(self):
        desk = _Desk()
        with self.assertLogs("dancesport.gui.audio", level="INFO") as logs:
            desk.device.on_outputs_changed()
        self.assertIn("outputs changed", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main(verbosity=2)
