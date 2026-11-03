"""Settings dialog: unreadable and out-of-range stored values (#37, #78)."""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_settings_stored_"))

from PySide6.QtWidgets import QApplication

from gui.dialogs.settings_dialog import SettingsDialog
from tests.qt_test_support import reap_widget


class StoredValuesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def dlg(self, settings):
        d = SettingsDialog(settings)
        self.addCleanup(reap_widget, d)
        return d

    def test_unreadable_check_values_do_not_stop_the_dialog_opening(self):
        """#37: int("abc") raised out of the constructor."""
        d = self.dlg({"check_min_play_secs": "abc", "check_max_play_secs": None,
                      "check_tempo_dev_pct": "x", "check_noise_floor_db": [1]})
        vals = d.values()
        self.assertEqual(vals["check_tempo_dev_pct"], 10)
        self.assertEqual(vals["check_noise_floor_db"], -50)

    def test_an_untouched_out_of_range_value_is_not_written_back_clamped(self):
        """#78: OK rewrote what was stored with the clamped spin value."""
        d = self.dlg({"duck_pct": 500, "duck_up_ms": 99999, "pre_roll_secs": 9999})
        vals = d.values()
        self.assertEqual((vals["duck_pct"], vals["duck_up_ms"], vals["pre_roll_secs"]),
                         (500, 99999, 9999))

    def test_an_edited_value_is_saved(self):
        d = self.dlg({"duck_pct": 500})
        d._duck_spin.setValue(30)
        self.assertEqual(d.values()["duck_pct"], 30)


if __name__ == "__main__":
    unittest.main()
