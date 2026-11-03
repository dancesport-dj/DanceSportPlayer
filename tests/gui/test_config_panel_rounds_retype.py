"""Retyping the same rounds text after a bad one still rebuilds (#76)."""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_rounds_retype_"))

from PySide6.QtWidgets import QApplication


class RoundsRetypeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_a_bad_text_is_not_remembered_as_parsed(self):
        from gui.config_panel import ConfigPanel
        panel = ConfigPanel()
        self.addCleanup(panel.deleteLater)
        panel.rounds_edit.setText("3")
        panel._parse_rounds()
        good = list(panel._round_cfgs)
        panel.rounds_edit.setText("x-nonsense")
        panel._parse_rounds()
        self.assertEqual(panel._round_cfgs, good)       # kept, nothing to rebuild from
        self.assertEqual(panel._last_parsed_rounds, "3")   # the last GOOD text

    def test_a_bad_text_is_flagged_and_a_good_one_clears_it(self):
        from gui.config_panel import ConfigPanel
        panel = ConfigPanel()
        self.addCleanup(panel.deleteLater)
        panel.rounds_edit.setText("3")
        panel._parse_rounds()
        self.assertTrue(panel.rounds_valid)
        panel.rounds_edit.setText("x-nonsense")
        panel._parse_rounds()
        self.assertFalse(panel.rounds_valid)           # generate must not use the old rounds
        self.assertTrue(panel.rounds_edit.toolTip())   # and the field says why
        self.assertTrue(panel.rounds_edit.styleSheet())
        panel.rounds_edit.setText("3")
        panel._parse_rounds()
        self.assertTrue(panel.rounds_valid)
        self.assertEqual(panel.rounds_edit.styleSheet(), "")


if __name__ == "__main__":
    unittest.main()
