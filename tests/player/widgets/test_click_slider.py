#!/usr/bin/env python3
"""Tests for ClickSlider: a click on the track jumps, a press on the handle grabs.

Run:  py -m unittest tests.player.widgets.test_click_slider -v

The jump mapped the press over the full widget width while Qt travels the handle
between half a handle in and half a handle short of the end, so a press that
landed on the handle computed another value and moved it — aiming at the handle
gave a jump instead of a grab.
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionSlider

from player.widgets.player_parts import ClickSlider, TempoSlider
from tests.qt_test_support import reap_widget


def _handle_rect(slider):
    opt = QStyleOptionSlider()
    slider.initStyleOption(opt)
    return slider.style().subControlRect(
        QStyle.ComplexControl.CC_Slider, opt,
        QStyle.SubControl.SC_SliderHandle, slider)


class ClickSliderTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _slider(self, cls=ClickSlider, lo=0, hi=100000, value=0):
        s = cls(Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        s.setValue(value)
        s.resize(200, 24)
        s.show()
        self.addCleanup(reap_widget, s)
        self.jumps = []
        s.clickJumped.connect(self.jumps.append)
        return s

    def _press(self, s, pos):
        QTest.mousePress(s, Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier, pos)
        QTest.mouseRelease(s, Qt.MouseButton.LeftButton,
                           Qt.KeyboardModifier.NoModifier, pos)

    def test_a_press_on_the_handle_leaves_the_value_alone(self):
        s = self._slider()
        self._press(s, _handle_rect(s).center())
        self.assertEqual(s.value(), 0)
        self.assertEqual(self.jumps, [])

    def test_a_press_on_the_handle_mid_track_leaves_it_alone_too(self):
        s = self._slider(value=50000)
        self._press(s, _handle_rect(s).center())
        self.assertEqual(s.value(), 50000)
        self.assertEqual(self.jumps, [])

    def test_a_tempo_fader_handle_press_does_not_nudge_it(self):
        s = self._slider(TempoSlider, lo=-16, hi=16, value=24 - 32)
        self._press(s, _handle_rect(s).center())
        self.assertEqual(s.value(), -8)

    def test_a_press_on_the_track_still_jumps_there(self):
        s = self._slider()
        self._press(s, QPoint(150, 12))
        self.assertEqual(len(self.jumps), 1)
        self.assertGreater(self.jumps[0], 60000)
        self.assertEqual(s.value(), self.jumps[0])


if __name__ == "__main__":
    unittest.main()
