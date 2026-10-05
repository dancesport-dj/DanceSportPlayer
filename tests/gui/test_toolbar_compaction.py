#!/usr/bin/env python3
"""The toolbar follows its OWN width, not just the window's.

Run:  py -m unittest tests.gui.test_toolbar_compaction -v

"the buttons on top are again collapsed even on big screen."

The row is responsive, but it is driven from `MainWindow.resizeEvent`, and the
bar does not live in the window — it lives in the right pane of the main
splitter (`rl = QVBoxLayout(right)`). So the two widths come apart the moment
anything but the window changes: folding the config panel away, or dragging the
splitter, hands the bar a few hundred px more and no resize event is ever sent
to the window. The level it was last given stays, and an operator sees eighteen
bare squares with a gap wide enough for every label sitting next to them.

Measured off the real window rather than a px budget: `_toolbar_full_width` is
what the production code measured for this font, so the test sizes everything
from it and says the same thing under any font the test host happens to have.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_toolbar_compact_"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QSplitter  # noqa: E402

from gui import dialogs  # noqa: E402
from gui.main_persist import layout_settings  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)


class ToolbarCompactionTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        layout_settings().clear()
        dialogs.AUTOSAVE.remove()

    def window(self):
        """A shown window wide enough that the row starts with full labels."""
        win = self.gui.MainWindow()
        win._loading_dlg.accept()          # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, win)
        win.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        win.show()
        self.settle()
        # The production measurement, taken for whatever font this host has.
        # Everything below is sized from it, never from a px budget.
        win.resize(win._toolbar_full_width * 2, 900)
        self.settle()
        self.splitter(win).setSizes([0, win.width()])
        self.settle()
        return win

    def settle(self):
        for _ in range(5):
            self.app.processEvents()

    @staticmethod
    def splitter(win):
        return win.findChild(QSplitter)

    def test_the_row_expands_again_when_the_config_panel_is_folded(self):
        """The bug, in the shape the operator hits it: a window that never
        changes size, and a bar that grows because the panel beside it went
        away."""
        win = self.window()
        bar = win._toolbar_widget
        self.assertEqual(0, win._toolbar_compact,
                         "a bar of %d px should carry every label (needs %d)"
                         % (bar.width(), win._toolbar_full_width))

        fixed = win.width()
        # Hand most of the width to the config panel: the bar is squeezed to
        # a fraction of what the labels need and has to compact.
        self.splitter(win).setSizes([fixed - 200, 200])
        self.settle()
        self.assertEqual(2, win._toolbar_compact,
                         "the bar is down to %d px, far under the %d every "
                         "label needs, and the row is still at level %d"
                         % (bar.width(), win._toolbar_full_width,
                            win._toolbar_compact))

        # …and fold the panel away again. The window still has not changed
        # size, so nothing tells resizeEvent anything — but the bar is wide.
        self.splitter(win).setSizes([0, fixed])
        self.settle()
        self.assertEqual(fixed, win.width(), "the window was not to be resized")
        self.assertGreaterEqual(
            bar.width(), win._toolbar_full_width,
            "the bar is not actually wide again, so the test proves nothing")
        self.assertEqual(
            0, win._toolbar_compact,
            "the bar is %d px wide and every label fits in %d, but the row is "
            "still at compaction level %d — it only ever listens to the "
            "window, and the window did not move"
            % (bar.width(), win._toolbar_full_width, win._toolbar_compact))


if __name__ == "__main__":
    unittest.main()
