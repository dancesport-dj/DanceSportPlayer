"""The AI chat bubbles are drawn in their colours (review section 4).

Commit 9c39eda0 renamed `_Bubble` to `Bubble` (and `_ThinkingBubble`), but the
stylesheets still addressed the old type names, so Qt matched nothing and every
bubble came out as a bare frame.
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_bubble_"))

from PySide6.QtWidgets import QApplication

from gui.dialogs.ai_dialogs import Bubble, ThinkingBubble
from tests.qt_test_support import reap_widget


class BubbleStyleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _pixel(self, widget, x, y):
        self.addCleanup(reap_widget, widget)
        widget.resize(260, 90)
        return widget.grab().toImage().pixelColor(x, y).name()

    def test_a_sent_bubble_has_its_blue_background(self):
        bubble = Bubble("sent", "You", "Request", "hello")
        self.assertEqual(self._pixel(bubble, 5, 45), "#dce9fb")

    def test_a_received_bubble_has_its_border(self):
        bubble = Bubble("received", "Claude", "Answer", "hello")
        self.assertEqual(self._pixel(bubble, 0, 45), "#d7dbe2")

    def test_the_thinking_bubble_has_its_border(self):
        bubble = ThinkingBubble("Claude", "thinking")
        self.assertEqual(self._pixel(bubble, 0, 45), "#d7dbe2")


if __name__ == "__main__":
    unittest.main()
