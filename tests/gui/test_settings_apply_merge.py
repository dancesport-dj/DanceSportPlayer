#!/usr/bin/env python3
"""Tests for ⚙ Settings → OK not undoing what changed while it was open.

Run:  py -m unittest tests.gui.test_settings_apply_merge -v

The dialog is modal, but the evening goes on behind it: the 🔕 guard records
the devices it muted, the master fader is saved. The dialog handed back the
whole dict as it was when it opened, and OK saved that — so the record of the
muted devices was gone, and after the next start nothing unmuted them.
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_settings_merge_"))

from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

import dancesport_gui as gui  # noqa: E402
from gui import main_global  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

MUTED = ["{0.0.0.00000000}.{00aae184-test}"]


class _Dialog:
    """⚙ Settings, with the operator changing one value while the evening
    changes two others behind it."""

    def __init__(self, settings, parent, **_kw):
        self._given = dict(settings)
        self._win = parent

    def exec(self):
        self._win._settings["system_sounds_muted"] = MUTED
        self._win._settings["master_volume"] = 0.42
        return QDialog.DialogCode.Accepted

    def values(self):
        vals = dict(self._given)
        vals["check_tempo_dev_pct"] = 7
        return vals


class SettingsApplyMergeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        gui.load_settings = lambda *a, **kw: {"app_mode": "both",
                                               "master_volume": 0.8}
        self.win = gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        for name, value in (("SettingsDialog", _Dialog),
                            ("save_settings", lambda s: None)):
            patch = mock.patch.object(main_global, name, value)
            patch.start()
            self.addCleanup(patch.stop)

    def test_what_changed_behind_the_dialog_survives_its_ok(self):
        self.win._open_settings()
        self.assertEqual(self.win._settings.get("system_sounds_muted"), MUTED)
        self.assertEqual(self.win._settings.get("master_volume"), 0.42)

    def test_what_the_operator_changed_in_it_is_applied(self):
        self.win._open_settings()
        self.assertEqual(self.win._settings.get("check_tempo_dev_pct"), 7)


if __name__ == "__main__":
    unittest.main()
