#!/usr/bin/env python3
"""The play length's explanation pops up at tooltip size, not at 34 px.

Run:  .venv\\Scripts\\python.exe -m unittest tests.player.test_play_len_tooltip -v

A style sheet without a selector styles the widget's tooltip too: Qt shows
the tip in a QLabel that takes the style of the widget it explains. The big
mm:ss play length was styled that way, so hovering it put its six-line
explanation on the screen in 34 px bold — over a thousand pixels wide. The
−/+ beside it did the same at 22 px.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_lentip_"))

from PySide6.QtCore import QPoint  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QToolTip  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from player.play_mode_panel import PlayModePanel  # noqa: E402


class PlayLengthTooltipTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.panel = PlayModePanel({})
        self.addCleanup(reap_widget, self.panel)
        self.addCleanup(QToolTip.hideText)
        self.panel.show()
        plain = QLabel("x", self.panel)
        plain.setToolTip("plain")
        self.normal = self.tip_font(plain)

    def tip_font(self, widget):
        QToolTip.hideText()
        QToolTip.showText(widget.mapToGlobal(QPoint(2, 2)), widget.toolTip(),
                          widget)
        tips = [w for w in QApplication.topLevelWidgets()
                if w.objectName() == "qtooltip_label" and w.isVisible()]
        self.assertEqual(len(tips), 1)
        return tips[0].font()

    def assert_normal_tips(self):
        for name in ("len_lbl", "len_minus", "len_plus"):
            with self.subTest(widget=name):
                self.assertEqual(self.tip_font(getattr(self.panel, name)),
                                 self.normal)

    def test_the_side_panel_explains_at_tooltip_size(self):
        self.assert_normal_tips()

    def test_the_strip_explains_at_tooltip_size(self):
        self.panel._wide = True
        self.panel._apply_skin()
        self.assert_normal_tips()

    def test_the_readout_itself_is_still_big(self):
        self.assertEqual(self.panel.len_lbl.font().pixelSize(), 34)
        self.assertTrue(self.panel.len_lbl.font().bold())


if __name__ == "__main__":
    unittest.main(verbosity=2)
