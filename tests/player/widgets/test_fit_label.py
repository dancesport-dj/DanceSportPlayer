"""FitLabel: a caption that shrinks to one row instead of wrapping."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QApplication

from player.widgets.panel_parts import FitLabel

_app = QApplication.instance() or QApplication([])
TEXT = "Mixed voices · heat only · over the music"
MARGIN = 40


def _need(text):
    """Width the bold text takes at the normal size (offscreen fonts are wide,
    so widths are derived rather than hard-coded)."""
    f = QFont(FitLabel("").font())
    f.setBold(True)
    return QFontMetrics(f).horizontalAdvance(text)


class FitLabelTest(unittest.TestCase):

    def _label(self, text, width):
        lbl = FitLabel("")
        lbl.setStyleSheet("font-weight:bold;")
        lbl.setIndent(MARGIN)
        lbl.resize(width, 20)
        lbl.setText(text)
        return lbl

    def _base(self):
        return FitLabel("").font().pointSizeF()

    def test_fits_indented_at_the_normal_size(self):
        lbl = self._label(TEXT, MARGIN + _need(TEXT) + 10)
        self.assertEqual(lbl.contentsMargins().left(), MARGIN)
        self.assertEqual(lbl.font().pointSizeF(), self._base())

    def test_too_long_for_the_indent_takes_the_whole_width_centred(self):
        lbl = self._label(TEXT, _need(TEXT) + 10)   # fits only without the indent
        self.assertEqual(lbl.contentsMargins().left(), 0)
        self.assertTrue(lbl.alignment() & Qt.AlignmentFlag.AlignHCenter)
        self.assertEqual(lbl.font().pointSizeF(), self._base())

    def test_still_too_long_shrinks_in_half_point_steps(self):
        width = int(_need(TEXT) * 0.8)
        lbl = self._label(TEXT, width)
        pt = lbl.font().pointSizeF()
        self.assertLess(pt, self._base())
        self.assertEqual((self._base() - pt) % 0.5, 0)
        self.assertEqual(lbl.contentsMargins().left(), 0)
        f = QFont(lbl.font())
        f.setBold(True)
        self.assertLessEqual(QFontMetrics(f).horizontalAdvance(TEXT), width)
        self.assertFalse(lbl.wordWrap())

    def test_widening_goes_back_up_the_steps(self):
        lbl = self._label(TEXT, int(_need(TEXT) * 0.8))
        small = lbl.font().pointSizeF()
        lbl.show()
        lbl.resize(MARGIN + _need(TEXT) + 20, 20)
        _app.processEvents()
        self.assertGreater(lbl.font().pointSizeF(), small)
        self.assertEqual(lbl.contentsMargins().left(), MARGIN)


if __name__ == "__main__":
    unittest.main()
