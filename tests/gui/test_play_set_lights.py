#!/usr/bin/env python3
"""The 🏆/🎉 lights say which play set the panel is STANDING on.

Run:  py -m unittest tests.gui.test_play_set_lights -v

Both tooltips promise it — "lit gold while the panel stands on those values" —
and for a while they did not keep it: a light went on when its set was applied
and stayed on while the controls underneath it were moved by hand.

The window here is real and the control is moved the way a hand moves it, so
the test covers the wiring (`settingsChanged` reaching the refresh) and not
just the rule; a refresh that is written but never connected fails this file.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_setlights_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui import dialogs  # noqa: E402
from planner.play_sets import _TOURNAMENT_SET  # noqa: E402
from gui.main_persist import layout_settings  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)


class PlaySetLightsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        layout_settings().clear()
        dialogs.AUTOSAVE.remove()
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.panel = self.win._play_panel

    def lights(self):
        return (self.panel.party_btn.isChecked(),
                self.panel.tournament_btn.isChecked())

    def test_a_spin_box_moved_by_hand_puts_the_gold_light_out(self):
        self.win._apply_tournament_set()
        self.assertEqual(self.lights(), (False, True))
        self.panel.fade_spin.setValue(_TOURNAMENT_SET["fade"] + 1.0)
        self.app.processEvents()
        self.assertEqual(self.lights(), (False, False),
                         "the panel no longer stands on the tournament set")

    def test_putting_the_value_back_lights_it_again(self):
        self.win._apply_tournament_set()
        self.panel.fade_spin.setValue(_TOURNAMENT_SET["fade"] + 1.0)
        self.panel.fade_spin.setValue(_TOURNAMENT_SET["fade"])
        self.app.processEvents()
        self.assertEqual(self.lights(), (False, True))

    def test_the_party_light_goes_out_the_same_way(self):
        self.win._set_party_mode(True)
        self.assertEqual(self.lights(), (True, False))
        self.panel.fade_spin.setValue(self.panel.fade_secs() + 1.0)
        self.app.processEvents()
        self.assertEqual(self.lights(), (False, False))

    def test_a_light_going_out_does_not_switch_anything(self):
        """`set_party_on` blocks the button’s signals, so the refresh cannot
        loop back into the switch it is reporting on."""
        self.win._apply_tournament_set()
        secs = self.panel.play_set()["secs"]
        self.panel.fade_spin.setValue(_TOURNAMENT_SET["fade"] + 1.0)
        self.app.processEvents()
        self.assertEqual(self.panel.play_set()["secs"], secs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
