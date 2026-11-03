#!/usr/bin/env python3
"""🎛 The cartwall dock can be dragged narrow.

Run:  py -m unittest tests.player.test_cartwall_narrow -v

Marcel's list, 8.1: "The cartwall width cannot be made smaller; the minimum is the
default size. Allow narrower widths." The floor was the 🔊 fader box, 296 px on
every wall, and on a wide wall the pads' 44 px each: 488 px at 10 × 6, which is
what a quarter of a Full HD window opens at.
"""

import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_cartnarrow_"))

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtWidgets import QApplication, QDockWidget, QMainWindow, QTextEdit

from planner.playing import cartwall as pc
from player.widgets import cartwall as gc
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)


def pad(name: str) -> pc.CartPad:
    return pc.CartPad(path=f"C:/x/{name}.mp3")


class FloorTest(unittest.TestCase):
    """What the wall asks of its dock."""

    def wall(self, grid, pages=1):
        wall = gc.CartwallWidget()
        self.addCleanup(reap_widget, wall)
        wall.set_wall(grid, [pc.Page(pads={(0, 0): pad("a")}) for _ in range(pages)])
        wall.show()
        _app.processEvents()
        return wall

    def floor(self, grid, pages=1):
        wall = self.wall(grid, pages)
        # Dragged down step by step, as the mouse does: the wall's floor may
        # drop on the way, once the tools have made room.
        for _ in range(4):
            wall.resize(wall.minimumSizeHint().width(), 700)
            _app.processEvents()
        return wall.minimumSizeHint().width()

    def test_the_default_wall_goes_well_under_the_old_floor(self):
        self.assertLess(self.floor(pc.DEFAULT_GRID), 150)

    def test_several_pages_do_not_pin_it_either(self):
        self.assertLess(self.floor(pc.DEFAULT_GRID, pages=3), 150)

    def test_a_four_wide_wall(self):
        self.assertLess(self.floor((4, 4)), 170)

    def test_an_eight_wide_wall(self):
        self.assertLess(self.floor((8, 4)), 300)

    def test_a_ten_wide_wall(self):
        self.assertLess(self.floor((10, 6)), 380)


class NarrowLookTest(unittest.TestCase):
    """Narrow, the wall sheds words and extras, never the controls that matter."""

    def setUp(self):
        self.w = gc.CartwallWidget()
        self.addCleanup(reap_widget, self.w)
        self.w.set_wall(pc.DEFAULT_GRID, [pc.Page(pads={(0, 0): pad("a")})])
        self.w.show()
        _app.processEvents()

    def to_width(self, width):
        self.w.resize(width, 700)
        _app.processEvents()

    def test_wide_nothing_changes(self):
        self.to_width(500)
        self.assertEqual(self.w._stop_btn.text(), "⏹  Stop all")
        self.assertTrue(self.w._level_lbl.isVisible())
        self.assertTrue(self.w._level_down_btn.isVisible())
        self.assertTrue(self.w._level_up_btn.isVisible())

    def test_narrow_the_fader_keeps_only_itself_and_the_speaker(self):
        self.to_width(130)
        self.assertTrue(self.w._mute_btn.isVisible())
        self.assertTrue(self.w._level.isVisible())
        self.assertFalse(self.w._level_lbl.isVisible())
        self.assertFalse(self.w._level_down_btn.isVisible())
        self.assertFalse(self.w._level_up_btn.isVisible())

    def test_narrow_stop_all_is_still_there_without_its_words(self):
        self.to_width(130)
        self.assertEqual(self.w._stop_btn.text(), "⏹")
        self.assertTrue(self.w._stop_btn.isVisible())
        self.assertEqual(self.w._stop_btn.toolTip(), "Fade every running pad out (Esc)")

    def test_wider_again_brings_it_all_back(self):
        self.to_width(130)
        self.to_width(500)
        self.assertEqual(self.w._stop_btn.text(), "⏹  Stop all")
        self.assertTrue(self.w._level_lbl.isVisible())
        self.assertTrue(self.w._level_up_btn.isVisible())

    def test_the_setting_that_took_the_steps_away_still_holds(self):
        self.w.set_vol_buttons_shown(False)
        self.to_width(130)
        self.to_width(500)
        self.assertFalse(self.w._level_down_btn.isVisible())
        self.assertFalse(self.w._level_up_btn.isVisible())
        self.assertTrue(self.w._level_lbl.isVisible())

    def test_the_setting_coming_back_while_narrow_waits_for_the_room(self):
        self.w.set_vol_buttons_shown(False)
        self.to_width(130)
        self.w.set_vol_buttons_shown(True)
        self.assertFalse(self.w._level_up_btn.isVisible())
        self.to_width(500)
        self.assertTrue(self.w._level_up_btn.isVisible())

    def test_no_control_is_cut_off_at_the_floor(self):
        self.to_width(self.w.minimumSizeHint().width())
        self.to_width(self.w.minimumSizeHint().width())
        edge = self.w.rect()
        for name in ("_size_box", "_edit_btn", "_stop_btn", "_mute_btn", "_level", "_file_btn"):
            box = getattr(self.w, name)
            at = box.mapTo(self.w, QPoint(0, 0))
            self.assertTrue(edge.contains(QRect(at, box.size())),
                            f"{name} at {at} {box.size()} outside {edge}")

    def test_the_pads_keep_a_width_of_their_own_at_the_floor(self):
        self.to_width(self.w.minimumSizeHint().width())
        self.to_width(self.w.minimumSizeHint().width())
        for button in self.w._buttons.values():
            self.assertGreaterEqual(button.width(), gc._PAD_MIN_W)


class DockTest(unittest.TestCase):
    """The drag itself: Qt's splitter stops at what the dock asks for."""

    def test_the_dock_follows_the_wall_down(self):
        win = QMainWindow()
        self.addCleanup(reap_widget, win)
        win.setCentralWidget(QTextEdit())
        wall = gc.CartwallWidget()
        wall.set_wall(pc.DEFAULT_GRID, [pc.Page(pads={(0, 0): pad("a")})])
        dock = QDockWidget("🎛  Cartwall", win)
        dock.setWidget(wall)
        win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        win.resize(1600, 900)
        win.show()
        _app.processEvents()
        for _ in range(4):
            win.resizeDocks([dock], [60], Qt.Orientation.Horizontal)
            _app.processEvents()
        self.assertLess(dock.width(), 150)


if __name__ == "__main__":
    unittest.main(verbosity=2)
