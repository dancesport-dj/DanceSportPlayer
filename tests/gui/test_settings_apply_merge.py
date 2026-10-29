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

from PySide6.QtWidgets import QApplication, QDialog

import dancesport_gui as gui
from gui.window import main_global
from tests.qt_test_support import reap_widget

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

    def running_look_touched(self):
        return False

    def deleteLater(self):
        pass


class _SettingsCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        patcher = mock.patch.object(gui, "load_settings",
                                    lambda *a, **kw: {"app_mode": "both",
                                                      "master_volume": 0.8})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.win = gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        for name, value in (("SettingsDialog", _Dialog),
                            ("save_settings", lambda s: None)):
            patch = mock.patch.object(main_global, name, value)
            patch.start()
            self.addCleanup(patch.stop)


class SettingsApplyMergeTest(_SettingsCase):

    def test_what_changed_behind_the_dialog_survives_its_ok(self):
        self.win._open_settings()
        self.assertEqual(self.win._settings.get("system_sounds_muted"), MUTED)
        self.assertEqual(self.win._settings.get("master_volume"), 0.42)

    def test_what_the_operator_changed_in_it_is_applied(self):
        self.win._open_settings()
        self.assertEqual(self.win._settings.get("check_tempo_dev_pct"), 7)


class _ButtonDialog(_Dialog):
    """…and then a button that closes the dialog to run something: like the
    real one, it calls back from inside exec(), the dialog's values in hand."""

    EDIT: dict = {}
    BUTTON = ""

    def __init__(self, settings, parent, **kw):
        super().__init__(settings, parent)
        self._kw = kw

    def exec(self):
        super().exec()
        cb = self._kw[self.BUTTON]
        cb(self.values()) if self.BUTTON in ("rescan_cb", "all_cb", "build_cb") else cb()
        return QDialog.DialogCode.Accepted

    def values(self):
        return {**super().values(), **self.EDIT}


class SettingsButtonTest(_SettingsCase):
    """BUG_REVIEW B3.1 / B4.6: what such a button runs, it runs on the
    settings as OK leaves them, and it leaves OK's follow-ups intact."""

    def press(self, button, **edit):
        dlg = type("Dlg", (_ButtonDialog,), {"EDIT": edit, "BUTTON": button})
        with mock.patch.object(main_global, "SettingsDialog", dlg):
            self.win._open_settings()

    def test_a_rescan_leaves_the_mode_change_to_ok(self):
        with mock.patch.object(self.win, "_library_still_loading", return_value=True), \
                mock.patch.object(self.win, "_apply_app_mode") as apply_mode:
            self.press("rescan_cb", app_mode="player")
        apply_mode.assert_called_once()
        self.assertEqual(self.win._settings["app_mode"], "player")
        self.assertEqual(self.win._settings.get("master_volume"), 0.42)
        self.assertFalse(set(main_global.CART_WALL_KEYS) & set(self.win._settings))

    def test_relearn_runs_once_on_the_new_folder(self):
        order = mock.Mock()
        with mock.patch("planner.config.set_playlist_dir", order.set_dir), \
                mock.patch.object(self.win, "_relearn_playlists", order.relearn):
            self.press("relearn_cb", playlist_dir="D:/new lists")
        self.assertEqual([c[0] for c in order.mock_calls], ["set_dir", "relearn"])

    def test_the_venue_pack_holds_the_edited_values(self):
        seen = []
        with mock.patch.object(self.win, "_export_venue_pack",
                               lambda: seen.append(self.win._settings.get("check_tempo_dev_pct"))):
            self.press("venue_export_cb")
        self.assertEqual(seen, [7])


if __name__ == "__main__":
    unittest.main()
