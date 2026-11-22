#!/usr/bin/env python3
"""💡 The generate hints under the decks, and their one-line 📐 Compact form.

Run:  py -m unittest tests.gui.test_hints_label -v

A generate with gaps leaves eight or ten notes; wrapped, they took three
lines of a 13″ laptop's decks. Compact shows the first and how many more,
the rest on hover or a click.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_hints_"))

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from gui.hints_label import HintsLabel
from tests.qt_test_support import reap_widget

_HINTS = ["⚠ Samba: only 0 proven song(s)", "♪ Jive: no track near the ideal 43 bpm",
          "✦ 24/24 songs are fresh"]


class HintsLabelTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def label(self, compact):
        lbl = HintsLabel(compact=compact)
        self.addCleanup(reap_widget, lbl)
        lbl.resize(900, 40)
        lbl.show()
        return lbl

    def click(self, lbl):
        pos = QPointF(5, 5)
        lbl.mousePressEvent(QMouseEvent(
            QMouseEvent.Type.MouseButtonPress, pos, lbl.mapToGlobal(pos),
            Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier))

    # ===== Acceptance criteria =====
    def test_compact_shows_the_first_hint_and_how_many_more(self):
        lbl = self.label(compact=True)
        lbl.set_hints(_HINTS)
        self.assertIn("Samba", lbl.text())
        self.assertNotIn("Jive", lbl.text())
        self.assertIn("+2", lbl.text())
        self.assertFalse(lbl.wordWrap())
        for hint in _HINTS:
            self.assertIn(hint, lbl.toolTip())

    def test_a_click_unfolds_the_whole_list_and_folds_it_again(self):
        lbl = self.label(compact=True)
        lbl.set_hints(_HINTS)
        self.click(lbl)
        for hint in _HINTS:
            self.assertIn(hint, lbl.text())
        self.click(lbl)
        self.assertNotIn("Jive", lbl.text())

    def test_normal_shows_them_all_wrapped_as_before(self):
        lbl = self.label(compact=False)
        lbl.set_hints(_HINTS)
        self.assertEqual(lbl.text(), "   ".join(_HINTS))
        self.assertTrue(lbl.wordWrap())

    # ===== Core behavior =====
    def test_no_hints_hides_it(self):
        lbl = self.label(compact=True)
        lbl.set_hints(_HINTS)
        self.assertTrue(lbl.isVisible())
        lbl.set_hints([])
        self.assertFalse(lbl.isVisible())
        self.assertEqual(lbl.text(), "")

    def test_a_single_hint_needs_no_count(self):
        lbl = self.label(compact=True)
        lbl.set_hints(_HINTS[:1])
        self.assertNotIn("+", lbl.text())
        self.assertIn("Samba", lbl.text())

    def test_a_long_first_hint_does_not_widen_the_window(self):
        """One line that cannot wrap must give way, not push back."""
        lbl = self.label(compact=True)
        lbl.set_hints(["W" * 400, "x"])
        self.assertLess(lbl.minimumSizeHint().width(), 200)

    def test_a_new_generate_starts_folded_again(self):
        lbl = self.label(compact=True)
        lbl.set_hints(_HINTS)
        self.click(lbl)
        lbl.set_hints(_HINTS)
        self.assertNotIn("Jive", lbl.text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
