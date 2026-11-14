"""⌨️ A number clicked into on the player panel can be typed over.

Run:  py -m unittest tests.player.test_panel_spin_typing -v

Marcel: the pause, start-after, stop-after and fade-out boxes "only accept the
arrow clicks — a typed value should work like in the settings menu". A box with
the " s" suffix puts the cursor after the suffix on a click, and a digit typed
there is refused, so nothing seemed to happen. A click now marks the whole value.
"""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_spin_typing_"))

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from player.widgets.play_mode_panel import PlayModePanel
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)

_BOXES = ("pause_spin", "pd_delay_spin", "fade_spin", "stop_count_spin", "pd_spin")


class SpinTypingTest(unittest.TestCase):

    def setUp(self):
        self.panel = PlayModePanel({"timed_enabled": True, "play_secs": 105,
                                    "pause_enabled": True})
        self.addCleanup(reap_widget, self.panel)
        self.panel.resize(500, 900)
        self.panel.show()
        _app.processEvents()

    def show_box(self, box):
        if box is self.panel.stop_count_spin:   # only there while "after N titles" is picked
            self.panel.stop_combo.setCurrentIndex(
                self.panel.stop_combo.findData("count"))
        box.setEnabled(True)
        _app.processEvents()
        self.assertTrue(box.isVisible())

    def click_in(self, box):
        edit = box.lineEdit()
        QTest.mouseClick(edit, Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier,
                         QPoint(edit.width() - 4, edit.height() // 2))
        _app.processEvents()   # the marking lands on the next tick
        return edit

    def test_a_click_marks_the_whole_value(self):
        for name in _BOXES:
            box = getattr(self.panel, name)
            self.show_box(box)
            box.setValue(box.minimum() + 1)
            edit = self.click_in(box)
            # the number is marked, the " s" after it stays out of the way
            self.assertEqual(edit.selectedText(),
                             edit.text().removesuffix(box.suffix()), name)

    def test_a_value_typed_after_a_click_lands(self):
        for name, want in (("pause_spin", 30), ("pd_delay_spin", 20),
                           ("fade_spin", 4), ("stop_count_spin", 6)):
            box = getattr(self.panel, name)
            self.show_box(box)
            box.setValue(box.minimum() + 1)
            edit = self.click_in(box)
            QTest.keyClicks(edit, str(want))
            QTest.keyClick(edit, Qt.Key.Key_Return)
            self.assertEqual(box.value(), want, name)


if __name__ == "__main__":
    unittest.main()
