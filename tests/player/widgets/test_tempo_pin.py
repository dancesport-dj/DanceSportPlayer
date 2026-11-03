#!/usr/bin/env python3
"""📌 The tempo pin on the player card and the TSO button beside it.

Run:  py -m unittest tests.player.widgets.test_tempo_pin -v
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tempo_pin_"))

from PySide6.QtGui import QColor
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

from player.widgets.player import BigPlayerWidget
from tests.qt_test_support import reap_widget


def brightest(widget) -> float:
    """The lightness of the brightest pixel: the icon, on the dark card."""
    image = widget.grab().toImage()
    return max(QColor(image.pixel(x, y)).lightnessF()
               for y in range(image.height()) for x in range(image.width()))


class TsoGreysThePinTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.card = BigPlayerWidget(QMediaPlayer())
        self.addCleanup(reap_widget, self.card)
        self.card.resize(900, 420)

    def test_the_pin_can_be_pressed_without_tso(self):
        self.assertTrue(self.card._tempo_pin.isEnabled())

    def test_tso_takes_the_pin_off_and_disables_it(self):
        self.card._tempo_pin.setChecked(True)
        self.card._tso_btn.click()
        self.assertFalse(self.card._tempo_pin.isChecked())
        self.assertFalse(self.card._tempo_pin.isEnabled())

    def test_the_disabled_pin_really_looks_grey(self):
        """Qt's own disabled icon came out lighter on the dark card, not dimmer."""
        lit = brightest(self.card._tempo_pin)
        self.card.set_tso_mode(True)
        self.assertLess(brightest(self.card._tempo_pin), lit * 0.7)

    def test_tso_off_brings_the_pin_back(self):
        lit = brightest(self.card._tempo_pin)
        self.card.set_tso_mode(True)
        self.card.set_tso_mode(False)
        self.assertTrue(self.card._tempo_pin.isEnabled())
        self.assertEqual(brightest(self.card._tempo_pin), lit)


class PinFitsItsRowTest(unittest.TestCase):
    """The pin stands as tall as the buttons beside it, on the same line."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_it_lines_up_with_the_tap_button(self):
        card = BigPlayerWidget(QMediaPlayer())
        self.addCleanup(reap_widget, card)
        card.resize(900, 420)
        card.show()
        self.app.processEvents()
        pin = card._tempo_pin.geometry()
        tap = card._takt_btn.geometry()
        self.assertEqual((pin.top(), pin.height()), (tap.top(), tap.height()))


if __name__ == "__main__":
    unittest.main()
