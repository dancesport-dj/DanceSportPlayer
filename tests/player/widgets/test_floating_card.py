"""The floating card under ♪ Takt and 🎚 EQ (player.widgets.floating_card).

Run:  .venv/Scripts/python.exe -m unittest tests.player.widgets.test_floating_card -v
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_floating_card_"))

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QVBoxLayout, QWidget

from player.widgets.floating_card import FloatingCard
from tests.qt_test_support import reap_widget


class ClickAwayTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        container = QWidget()
        container.resize(900, 500)
        self.anchor = QWidget(container)
        self.anchor.setGeometry(50, 50, 30, 20)
        self.outside = QWidget(container)
        self.outside.setGeometry(50, 400, 200, 60)
        container.show()
        self.addCleanup(reap_widget, container)
        self.card = FloatingCard()
        QVBoxLayout(self.card).addWidget(QComboBox())
        self.card.show_near(self.anchor)
        self.closed = []
        self.card.closeRequested.connect(lambda: self.closed.append(1))

    # ===== Acceptance criteria =====

    def test_a_press_in_an_open_combo_list_keeps_it_open(self):
        """The list is a window of its own, often reaching past the card."""
        with mock.patch.object(QApplication, "activePopupWidget", return_value=QWidget()):
            QTest.mousePress(self.outside, Qt.MouseButton.LeftButton)
        self.assertEqual(self.closed, [])

    def test_a_press_in_its_own_question_keeps_it_open(self):
        with mock.patch.object(QApplication, "activeModalWidget", return_value=QWidget()):
            QTest.mousePress(self.outside, Qt.MouseButton.LeftButton)
        self.assertEqual(self.closed, [])

    # ===== Core behavior =====

    def test_a_press_outside_asks_it_to_close(self):
        QTest.mousePress(self.outside, Qt.MouseButton.LeftButton)
        self.assertEqual(self.closed, [1])

    def test_it_opens_right_of_its_anchor(self):
        self.assertEqual(self.card.anchor(), self.anchor)
        self.assertGreater(self.card.x(), self.anchor.geometry().right())

    # ===== Coverage and null checks =====

    def test_a_card_without_a_title_does_not_drag(self):
        QTest.mousePress(self.card, Qt.MouseButton.LeftButton)
        self.assertIsNone(self.card._drag_off)


if __name__ == "__main__":
    unittest.main(verbosity=2)
