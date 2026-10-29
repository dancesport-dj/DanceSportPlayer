"""🎯 ✖ ✏️ look switched off when no Paso Doble is on the deck.

Run:  py -m unittest tests.player.widgets.test_pd_tools_greyed -v

The tools were disabled with anything but a Paso Doble on the deck, but in
the player strip they looked just the same: its dark skin gave every button
one colour and background, enabled or not. Marcel saw them lit with a Rumba
loaded and took it that nothing had changed.
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from player.widgets.panel_parts import Toggle
from player.widgets.play_mode_panel import PlayModePanel
from tests.qt_test_support import reap_widget


class PdToolsGreyedTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def look(self, wide, on):
        panel = PlayModePanel({"pd_highlight_stop": True, "pd_highlight_n": 2})
        self.addCleanup(reap_widget, panel)
        panel.set_wide(wide)
        panel.set_pd_loaded(on)
        btn = panel.pd_learn_btn
        btn.resize(200, 26)
        btn.ensurePolished()
        return btn.grab().toImage()

    def test_in_the_strip_off_looks_off(self):
        self.assertNotEqual(self.look(True, True), self.look(True, False))

    def test_in_the_strip_off_sinks_back(self):
        """Marcel: off was a lighter grey than the live navy buttons, so the
        tools that do nothing stood out most. Off is darker, and grey."""
        on = self.look(True, True).pixelColor(100, 13)
        off = self.look(True, False).pixelColor(100, 13)
        self.assertLess(off.lightness(), on.lightness())
        self.assertLess(off.hslSaturation(), 40)

    def test_down_the_side_off_looks_off(self):
        self.assertNotEqual(self.look(False, True), self.look(False, False))

    def test_down_the_side_off_is_a_darker_grey(self):
        """Marcel: down the side 🎯 looked the same enabled or not — the
        system's disabled grey is barely off its live white. Off is a grey
        clearly darker than live, text and all."""
        on = self.look(False, True).pixelColor(100, 13)
        off = self.look(False, False).pixelColor(100, 13)
        self.assertGreater(on.lightness() - off.lightness(), 25)
        self.assertLess(off.hslSaturation(), 40)

    def test_down_the_side_off_is_the_switches_grey(self):
        """…and the very grey of a switched-off ⏻ switch beside them, so off
        reads the same across the panel."""
        off = self.look(False, False).pixelColor(100, 13)
        self.assertEqual(off.name(), Toggle._OFF_TRACK.name())


if __name__ == "__main__":
    unittest.main(verbosity=2)
