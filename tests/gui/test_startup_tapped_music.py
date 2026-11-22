#!/usr/bin/env python3
"""The window builds when the music is tapped from the start.

Run:  py -m unittest tests.gui.test_startup_tapped_music -v

With ⏩ Tempo on Signalsmith or Rubber Band (or the 🎚 EQ on), the music's
route is set up while the outputs are, before the crossfade's spare deck
exists. Asking for that deck then crashed the start: "'MainWindow' object has
no attribute '_between'".
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_startup_tapped_"))

from PySide6.QtWidgets import QApplication

from player.audio import eq, pair_route, stretch_engines
from tests.qt_test_support import reap_widget, stub_window_startup


class StartupTappedMusicTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.dg = stub_window_startup(cls)

    # ===== Acceptance criteria =====

    def test_the_window_builds_with_the_tempo_engine_tapping_the_music(self):
        with mock.patch.object(stretch_engines, "taps_music", return_value=True), \
                mock.patch.object(eq, "available", return_value=True):
            win = self.dg.MainWindow()
        self.addCleanup(reap_widget, win)
        # The tapped route started the audio thread: a QThread still running
        # when the interpreter exits aborts the process (0xC0000409).
        self.addCleanup(pair_route.stop_audio_thread)
        self.assertEqual(win._audio_device._music_eq, ())


if __name__ == "__main__":
    unittest.main()
