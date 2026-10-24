#!/usr/bin/env python3
"""⚙ A play set edited in Settings reaches the lists already standing on it.

Run:  py -m unittest tests.gui.test_play_sets_follow -v

Every list keeps its own copy of the play values (`_list_vals`), seeded once
from the set of its kind and saved with the session. Marcel: "if a title was
played before i change the play time in the settings … it still applies the
old logic" — the copy kept the old 1:45, fell off the 🏆 set and with it
off the per-dance lengths. A value still equal to the set's old one is the
set's, so it moves with it; one changed by hand stays the operator's.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_setsfollow_"))

from PySide6.QtWidgets import QApplication, QDialog

from planner.playing.play_sets import play_set_of
from tests.qt_test_support import reap_widget, stub_window_startup


class FollowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_setsfollow_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)
        self.panel = self.win._play_panel
        self.b = self.win._deckset.tableB
        self.win._on_table_focused(self.b)   # first use: the 🏆 set
        self.assertEqual(self.win._list_vals(self.b)["secs"],
                         play_set_of(self.win._settings, "tournament")["secs"])

    def _save_set(self, which, **change):
        """⚙ Settings opened, the `which` set's values changed, Save pressed."""
        given = dict(self.win._settings)
        key = f"{which}_set"
        new_set = {**(given.get(key) or {}), **change}

        class Dlg:
            def __init__(self, *_a, **_k):
                pass

            def exec(self):
                return QDialog.DialogCode.Accepted

            def values(self):
                return {**given, key: new_set}

            def running_look_touched(self):
                return False

            def deleteLater(self):
                pass

        with mock.patch("gui.window.main_global.SettingsDialog", Dlg), \
                mock.patch("gui.window.main_global.save_settings"):
            self.win._open_settings()

    def test_a_deck_on_the_set_takes_its_new_length(self):
        self._save_set("tournament", secs=120)
        self.assertEqual(self.win._list_vals(self.b)["secs"], 120)
        self.assertTrue(self.win._on_tournament_length(self.b))

    def test_the_panel_shows_the_new_length_of_its_list(self):
        self._save_set("tournament", secs=120)
        self.assertEqual(self.panel.play_set()["secs"], 120)

    def test_a_deck_not_on_the_panel_follows_too(self):
        a = self.win._deckset.tableA
        self.win._list_vals(a)
        self._save_set("tournament", secs=120, fade=4.0)
        self.assertEqual(self.win._list_vals(a)["secs"], 120)
        self.assertEqual(self.win._list_vals(a)["fade"], 4.0)

    def test_a_length_set_by_hand_stays(self):
        self.win._list_vals(self.b)["secs"] = 75
        self._save_set("tournament", secs=120, fade=4.0)
        self.assertEqual(self.win._list_vals(self.b)["secs"], 75)
        self.assertEqual(self.win._list_vals(self.b)["fade"], 4.0)

    def test_the_warm_up_follows_the_party_set_not_the_tournament(self):
        warm = self.win._deckset.warmup_table
        party_fade = self.win._list_vals(warm)["fade"]
        self._save_set("tournament", fade=party_fade + 1)
        self.assertEqual(self.win._list_vals(warm)["fade"], party_fade)
        self._save_set("party", fade=party_fade + 2)
        self.assertEqual(self.win._list_vals(warm)["fade"], party_fade + 2)

    def test_the_panels_paso_doble_follows_the_set(self):
        self.win._put_set_on("tournament")
        self._save_set("tournament", pd_stop=True, pd_n=1)
        self.assertTrue(self.panel.pd_highlight_stop())
        self.assertEqual(self.panel.pd_highlight_n(), 1)


if __name__ == "__main__":
    unittest.main()
