"""shared.widgets.guard_wheel: an input under a scrolled page takes the wheel
only once it has been clicked into; until then the page scrolls.

Run:  .venv/Scripts/python.exe -m unittest tests.shared.test_guard_wheel -v
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from shared.widgets import guard_wheel
from tests.qt_test_support import reap_widget


def wheel(widget, notches=-1):
    centre = QPointF(widget.rect().center())
    event = QWheelEvent(centre, QPointF(widget.mapToGlobal(centre.toPoint())),
                        QPoint(), QPoint(0, 120 * notches), Qt.MouseButton.NoButton,
                        Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase,
                        False)
    QApplication.sendEvent(widget, event)


class GuardWheelTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        page = QWidget()
        lyt = QVBoxLayout(page)
        self.spin = QSpinBox()
        self.spin.setRange(0, 100)
        self.spin.setValue(50)
        self.combo = QComboBox()
        self.combo.addItems(["a", "b", "c"])
        lyt.addWidget(self.spin)
        lyt.addWidget(self.combo)
        lyt.addSpacing(2000)
        self.scroll.setWidget(page)
        self.scroll.resize(300, 200)
        guard_wheel(self.scroll)
        self.scroll.show()
        self.addCleanup(reap_widget, self.scroll)

    # ===== Acceptance criteria =====

    def test_an_unclicked_input_keeps_its_value_and_the_page_scrolls(self):
        bar = self.scroll.verticalScrollBar()
        wheel(self.spin)
        self.assertEqual(self.spin.value(), 50)
        self.assertGreater(bar.value(), 0)

    def test_a_clicked_input_steps(self):
        self.scroll.activateWindow()
        QTest.qWaitForWindowActive(self.scroll)
        self.spin.setFocus()
        wheel(self.spin, notches=1)
        self.assertEqual(self.spin.value(), 51)

    # ===== Core behavior =====

    def test_combos_are_guarded_too(self):
        wheel(self.combo)
        self.assertEqual(self.combo.currentIndex(), 0)

    def test_the_wheel_no_longer_hands_out_focus(self):
        self.assertEqual(self.spin.focusPolicy(), Qt.FocusPolicy.StrongFocus)

    # ===== Coverage and null checks =====

    def test_an_input_outside_any_scroll_area_just_ignores_the_wheel(self):
        holder = QWidget()
        self.addCleanup(reap_widget, holder)
        inner = QSpinBox(holder)
        inner.setValue(5)
        guard_wheel(holder)
        wheel(inner)
        self.assertEqual(inner.value(), 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
