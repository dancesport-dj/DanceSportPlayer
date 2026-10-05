#!/usr/bin/env python3
"""📌 Snapping the floating cartwall back into the main window.

Run:  py -m unittest tests.player.test_cartwall_dock -v

The 🎛 wall is a dock: it can be dragged out onto a second screen, which is
what a two-monitor desk wants. Getting it back was the problem — Qt offers
only the drag itself and a double-click on the title bar, and neither is
anything the operator finds mid-tournament. So the wall carries a 📌 button.

It is up ONLY while the wall floats: docked, there is nothing to snap back,
and a dead button on the one toolbar that has to stay readable during a heat
is worse than no button.
"""

import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_cartdock_"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QDockWidget, QMainWindow)
from tests.qt_test_support import reap_widget  # noqa: E402

from player import cartwall as gc  # noqa: E402
from player.main_cartwall import CART_DOCK, CartwallMixin  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)


class _Desk(CartwallMixin, QMainWindow):
    """A window with the real dock and the real wall, and nothing else.

    `_build_cartwall` also builds the audio pool and reads cartwall.json, so
    the two lines that matter here are done by hand — the mixin methods under
    test only ever touch the dock and the status bar."""

    def __init__(self):
        super().__init__()
        self._cartwall = gc.CartwallWidget()
        self._cart_dock = QDockWidget("🎛  Cartwall", self)
        self._cart_dock.setObjectName(CART_DOCK)
        self._cart_dock.setWidget(self._cartwall)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._cart_dock)
        self._wire_cart_dock()


class DockButtonTest(unittest.TestCase):
    """The button on the wall itself."""

    def setUp(self):
        self.w = gc.CartwallWidget()
        self.addCleanup(reap_widget, self.w)
        self.w.show()

    def test_a_docked_wall_does_not_show_it(self):
        """Nothing to snap back — the button is not there at all."""
        self.assertFalse(self.w._dock_btn.isVisible())

    def test_floating_brings_it_up(self):
        self.w.set_floating(True)
        self.assertTrue(self.w._dock_btn.isVisible())

    def test_docking_again_takes_it_away(self):
        self.w.set_floating(True)
        self.w.set_floating(False)
        self.assertFalse(self.w._dock_btn.isVisible())

    def test_pressing_it_asks_for_the_dock(self):
        """The wall knows nothing about docks — it only says what it wants."""
        seen = []
        self.w.dockRequested.connect(lambda: seen.append(1))
        self.w._dock_btn.click()
        self.assertEqual(seen, [1])


class DockWiringTest(unittest.TestCase):
    """The mixin: what the button actually does to the dock."""

    def setUp(self):
        self.desk = _Desk()
        self.addCleanup(reap_widget, self.desk)

    def test_the_button_puts_a_floating_wall_back(self):
        self.desk._cart_dock.setFloating(True)
        self.assertTrue(self.desk._cart_dock.isFloating())
        self.desk._cartwall._dock_btn.click()
        self.assertFalse(self.desk._cart_dock.isFloating())

    def test_a_wall_that_is_already_docked_is_left_alone(self):
        self.desk._on_cart_dock_back()
        self.assertFalse(self.desk._cart_dock.isFloating())

    def test_floating_the_dock_shows_the_button_by_itself(self):
        """Dragged out by hand, not through the button — the wall still has to
        offer the way back."""
        self.desk._cart_dock.setFloating(True)
        self.assertTrue(self.desk._cartwall._dock_btn.isVisible())

    def test_snapping_back_hides_it_again(self):
        self.desk._cart_dock.setFloating(True)
        self.desk._cart_dock.setFloating(False)
        self.assertFalse(self.desk._cartwall._dock_btn.isVisible())

    def test_a_re_docked_wall_stands_up_again(self):
        """A side dock is tall and narrow, so the wall turns portrait — the
        same rule a drag back would apply."""
        self.desk._cart_dock.setFloating(True)
        self.desk._cartwall._dock_btn.click()
        self.assertFalse(self.desk._cart_dock.isFloating())
        self.assertIn(self.desk.dockWidgetArea(self.desk._cart_dock),
                      (Qt.DockWidgetArea.LeftDockWidgetArea,
                       Qt.DockWidgetArea.RightDockWidgetArea))


if __name__ == "__main__":
    unittest.main(verbosity=2)
