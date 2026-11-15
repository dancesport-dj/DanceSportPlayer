#!/usr/bin/env python3
"""The spin boxes under the main player take the wheel only after a click.

Run:  py -m unittest tests.player.widgets.test_spin_wheel -v

"when i scroll with a touchpad i often change the configured value with the
scroll down gesture despite wanting to change it, make sure it only work after
i click into the field. happend by start after and fade out spin boxes"
(Marcel, 2026-11-15).

A two-finger scroll over the playing column that happens to pass over a spin
box used to step it (Qt hands the wheel to a spin box without focus). Now an
unfocused spin box ignores the wheel, so the scroll area behind it takes the
scroll; once the field has been clicked into, the wheel steps it as usual.
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDoubleSpinBox, QSpinBox

from player.widgets.panel_parts import ClickWheelDoubleSpinBox, ClickWheelSpinBox
from player.widgets.play_mode_panel import PlayModePanel
from tests.qt_test_support import reap_widget


def _wheel(widget, delta=-120):
    """One notch of the wheel at the centre of `widget`; returns the event."""
    pos = QPointF(widget.rect().center())
    ev = QWheelEvent(pos, widget.mapToGlobal(pos), QPoint(0, 0), QPoint(0, delta),
                     Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                     Qt.ScrollPhase.NoScrollPhase, False)
    ev.setAccepted(True)
    QApplication.sendEvent(widget, ev)
    return ev


class WheelNeedsFocusTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _shown(self, widget):
        widget.show()
        self.addCleanup(reap_widget, widget)
        return widget

    def test_an_unfocused_spin_box_ignores_the_wheel(self):
        for cls, value in ((ClickWheelSpinBox, 5), (ClickWheelDoubleSpinBox, 5.0)):
            with self.subTest(cls=cls.__name__):
                spin = self._shown(cls())
                spin.setRange(0, 10)
                spin.setValue(value)
                ev = _wheel(spin)
                self.assertEqual(spin.value(), value)
                self.assertFalse(ev.isAccepted())   # the scroll area gets it

    def test_a_focused_spin_box_takes_the_wheel(self):
        for cls, value in ((ClickWheelSpinBox, 5), (ClickWheelDoubleSpinBox, 5.0)):
            with self.subTest(cls=cls.__name__):
                spin = self._shown(cls())
                spin.setRange(0, 10)
                spin.setValue(value)
                spin.activateWindow()
                QTest.qWaitForWindowActive(spin)
                spin.setFocus()
                self.assertTrue(spin.hasFocus())
                _wheel(spin, -120)
                self.assertLess(spin.value(), value)

    def test_the_wheel_alone_does_not_give_it_focus(self):
        spin = self._shown(ClickWheelSpinBox())
        self.assertEqual(spin.focusPolicy(), Qt.FocusPolicy.StrongFocus)

    def test_the_spin_boxes_of_the_panel_are_the_click_to_use_kind(self):
        panel = self._shown(PlayModePanel({}))
        for name in ("fade_spin", "pd_delay_spin", "pd_spin", "pause_spin",
                     "stop_count_spin", "xfade_spin"):
            with self.subTest(spin=name):
                spin = getattr(panel, name)
                self.assertIsInstance(spin, (ClickWheelSpinBox,
                                             ClickWheelDoubleSpinBox))
                self.assertIsInstance(spin, (QSpinBox, QDoubleSpinBox))


if __name__ == "__main__":
    unittest.main(verbosity=2)
