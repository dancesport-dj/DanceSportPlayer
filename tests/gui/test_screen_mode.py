#!/usr/bin/env python3
"""📐 Screen: Auto / Normal / Compact, from ⚙ Settings → 🎨 Look.

Run:  py -m unittest tests.gui.test_screen_mode -v

Compact folds the hints to one line, starts an empty wishlist folded and
tightens the rows, for a 13″ laptop. Auto picks Compact when the screen's
free height is short. Read once when the app starts, like the theme.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_screenmode_"))

from PySide6.QtWidgets import QApplication

from gui import screen_mode
from gui.dialogs.settings_dialog import SettingsDialog
from gui.screen_mode import COMPACT_BELOW, is_compact, screen_mode_of
from tests.qt_test_support import reap_widget


class ScreenModeTest(unittest.TestCase):

    # ===== Acceptance criteria =====
    def test_auto_is_compact_on_a_short_screen_only(self):
        self.assertTrue(is_compact({}, 728))            # 1366×768 minus the taskbar
        self.assertTrue(is_compact({}, COMPACT_BELOW - 1))
        self.assertFalse(is_compact({}, COMPACT_BELOW))
        self.assertFalse(is_compact({}, 1040))

    def test_a_chosen_mode_wins_over_the_screen(self):
        self.assertFalse(is_compact({"screen_mode": "normal"}, 600))
        self.assertTrue(is_compact({"screen_mode": "compact"}, 1400))

    # ===== Core behavior =====
    def test_the_shape_is_fixed_once_for_the_run(self):
        self.addCleanup(screen_mode.apply_settings, {}, 1080)
        screen_mode.apply_settings({}, 728)
        self.assertTrue(screen_mode.compact())
        screen_mode.apply_settings({"screen_mode": "normal"}, 728)
        self.assertFalse(screen_mode.compact())

    # ===== Coverage and null checks =====
    def test_auto_is_the_default_and_junk_falls_back_to_it(self):
        self.assertEqual(screen_mode_of({}), "auto")
        for junk in (None, "tiny", 3, [1]):
            self.assertEqual(screen_mode_of({"screen_mode": junk}), "auto", junk)


class SettingsLookTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def dialog(self, settings):
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    # ===== Acceptance criteria =====
    def test_the_look_tab_offers_the_three_modes_and_saves_the_pick(self):
        dlg = self.dialog({"screen_mode": "compact"})
        combo = dlg._screen_mode_combo
        self.assertEqual([combo.itemData(i) for i in range(combo.count())],
                         ["auto", "normal", "compact"])
        self.assertEqual(dlg.values()["screen_mode"], "compact")
        combo.setCurrentIndex(combo.findData("normal"))
        self.assertEqual(dlg.values()["screen_mode"], "normal")


if __name__ == "__main__":
    unittest.main(verbosity=2)
