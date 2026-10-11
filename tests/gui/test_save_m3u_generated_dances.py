#!/usr/bin/env python3
"""💾 Save M3U writes the dances the playlist was generated with.

Run:  py -m unittest tests.gui.test_save_m3u_generated_dances -v

Found by the GUI monkey (tests/gui/test_monkey.py): Generate, then tick one
more dance checkbox, then 💾 Save M3U crashed with IndexError in
`export_m3u` — it read the dances off the live checkboxes, while every heat
of the playlist holds one song per dance it was generated with.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_save_m3u_dances_"))

from tests.gui.test_deck_file_reveal import _entry
from tests.qt_test_support import reap_widget, stub_window_startup


class SaveM3uGeneratedDancesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_save_m3u_dances_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)

    def test_a_dance_ticked_after_generate_is_not_saved(self):
        win = self.win
        checks = win._cfg.dance_checks
        extra = list(checks)[-1]
        checks[extra].setChecked(False)
        _, age, cls, dances, _, _ = win._cfg.get_config()
        self.assertTrue(dances)
        self.assertNotIn(extra, dances)
        win._age, win._dance_class, win._dances = age, cls, dances
        win._playlist = {"Final": [[_entry(f"song_{d}", d) for d in dances]]}

        checks[extra].setChecked(True)
        out_dir = Path(tempfile.mkdtemp(prefix="dp_save_m3u_dances_out_"))
        with mock.patch("planner.m3u.OUTPUT_DIR", out_dir):
            win._save_m3u()

        [saved] = out_dir.glob("*.m3u*")
        text = saved.read_text(encoding="utf-8-sig", errors="replace")
        for d in dances:
            self.assertIn(f"song_{d}", text)
        self.assertEqual(text.count("# ── "), len(dances),
                         "one section per generated dance, none for the ticked one")


if __name__ == "__main__":
    unittest.main(verbosity=2)
