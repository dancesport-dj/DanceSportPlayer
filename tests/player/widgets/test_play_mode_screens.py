"""🖥 The ▶ Playing panel's screen list follows plugged-in screens only while it lives (#30)."""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_screens_"))

import shiboken6
from PySide6.QtWidgets import QApplication

from player.widgets.play_mode_panel import PlayModePanel

_ADDED = "2screenAdded(QScreen*)"
_REMOVED = "2screenRemoved(QScreen*)"


class ScreenListTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _listeners(self):
        return (self.app.receivers(_ADDED), self.app.receivers(_REMOVED))

    def test_a_gone_panel_leaves_nothing_connected_to_the_application(self):
        before = self._listeners()
        panel = PlayModePanel({})
        self.assertEqual(self._listeners(), (before[0] + 1, before[1] + 1))
        shiboken6.delete(panel)
        self.assertEqual(self._listeners(), before)

    def test_a_plugged_in_screen_refills_a_living_panel(self):
        panel = PlayModePanel({})
        self.addCleanup(shiboken6.delete, panel)
        calls = []
        panel._fill_screens = lambda *a: calls.append(a)
        self.app.screenAdded.emit(self.app.primaryScreen())
        self.assertEqual(calls, [()])


if __name__ == "__main__":
    unittest.main()
