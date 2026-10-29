"""⚙ ▸ Advanced on the 🔊 Sound & player tab: the duck and the fade times
fold away.

Run:  py -m unittest tests.gui.test_sound_advanced_fold -v

Most evenings run on the defaults (Marcel, feedback on items 1-31), so the
duck level, the duck ramps, the fade-in, the hand fade, the pause-music fade
and the pre-roll sit in a section that starts folded. Folded or not, every
value is still read back and saved.
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_soundadv_"))

from PySide6.QtWidgets import QApplication

from tests.qt_test_support import reap_widget


class AdvancedFoldTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self, settings, **kw):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(settings, **kw)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_the_rows_live_in_the_folded_box(self):
        dlg = self._dlg({})
        for spin in (dlg._duck_spin, dlg._duck_down_spin, dlg._duck_up_spin,
                     dlg._fade_in_spin, dlg._hand_fade_spin,
                     dlg._pre_roll_spin):
            self.assertTrue(dlg._advanced_box.isAncestorOf(spin))
        self.assertFalse(dlg._advanced_btn.isChecked())
        self.assertTrue(dlg._advanced_box.isHidden())
        self.assertTrue(dlg._advanced_btn.text().startswith("▸"))

    def test_it_looks_like_a_button_without_hovering(self):
        """Marcel: it read as a plain label until the mouse was over it.
        The frame it shows on hover is there all the time."""
        self.assertFalse(self._dlg({})._advanced_btn.autoRaise())

    def test_a_click_unfolds_it(self):
        dlg = self._dlg({})
        dlg._advanced_btn.click()
        self.assertFalse(dlg._advanced_box.isHidden())
        self.assertTrue(dlg._advanced_btn.text().startswith("▾"))

    def test_folded_values_are_still_saved(self):
        dlg = self._dlg({"duck_pct": 25, "hand_fade_secs": 4.0})
        vals = dlg.values()
        self.assertEqual(vals["duck_pct"], 25)
        self.assertEqual(vals["hand_fade_secs"], 4.0)

    def test_it_sits_right_above_the_player_position(self):
        """Marcel: the fold belongs above ▶ Player position, under the
        voice rows, not at the foot of the tab below 📚 Library."""
        from PySide6.QtCore import QPoint
        dlg = self._dlg({}, open_sound=True)
        dlg.show()
        self.app.processEvents()

        def y(w):
            return w.mapTo(dlg, QPoint(0, 0)).y()

        self.assertLess(y(dlg._voice_combo), y(dlg._advanced_btn))
        self.assertLess(y(dlg._advanced_btn), y(dlg._player_layout_combo))
        self.assertLess(y(dlg._player_layout_combo), y(dlg._dblclick_combo))

    def test_everyday_rows_stay_outside(self):
        dlg = self._dlg({})
        for w in (dlg._vol_buttons_chk, dlg._voice_combo, dlg._preview_chk):
            self.assertFalse(dlg._advanced_box.isAncestorOf(w))


if __name__ == "__main__":
    unittest.main()
