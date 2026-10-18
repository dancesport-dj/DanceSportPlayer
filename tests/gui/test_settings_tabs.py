"""⚙ Settings: one tab per kind of setting, not one "Paths & search" for all.

Run:  py -m unittest tests.gui.test_settings_tabs -v
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_settings_tabs_"))

from PySide6.QtWidgets import QApplication, QLabel, QTabWidget

from gui.dialogs.settings_dialog import SettingsDialog


class SettingsTabsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dlg = SettingsDialog({}, None)
        self.addCleanup(self.dlg.deleteLater)
        self.tabs = self.dlg.findChild(QTabWidget)

    def page(self, caption):
        captions = [self.tabs.tabText(i) for i in range(self.tabs.count())]
        return self.tabs.widget(captions.index(caption))

    def assertOn(self, caption, *widgets):
        page = self.page(caption)
        for w in widgets:
            self.assertTrue(page.isAncestorOf(w), (caption, w))

    def test_the_tabs_and_their_order(self):
        captions = [self.tabs.tabText(i) for i in range(self.tabs.count())]
        self.assertEqual(captions[:4], ["⚙ General", "📁 Paths",
                                        "🎨 Look", "🔊 Sound && player"])
        # One checkbox made a tab of its own too small to be worth a click.
        self.assertNotIn("🔎 Search", captions)

    def test_general(self):
        self.assertOn("⚙ General", self.dlg._app_mode_combo, self.dlg._remote_box,
                      self.dlg._global_chk)

    def test_paths(self):
        self.assertOn("📁 Paths", self.dlg._lib_edit, self.dlg._glob_edit,
                      self.dlg._save_edit, self.dlg._m3u_format_combo,
                      self.dlg._pl_edit, self.dlg._relearn_btn,
                      self.dlg._ref_edit, self.dlg._remap_edit)

    def test_sound_and_player(self):
        self.assertOn("🔊 Sound && player", self.dlg._backend_combo,
                      self.dlg._release_audio_chk, self.dlg._mute_sys_chk)

    def test_the_player_rows_sit_with_the_sound(self):
        self.assertOn("🔊 Sound && player", self.dlg._preview_chk,
                      self.dlg._player_layout_combo, self.dlg._voice_combo,
                      self.dlg._heat_chk, self.dlg._voice_test_btn)

    def test_the_venue_intro_wraps_to_the_tab_width(self):
        # A hard line break inside a word-wrapped label pins it to a narrow
        # column however wide the dialog is.
        intro = [lbl.text() for lbl in self.page("📦 Venue pack").findChildren(QLabel)
                 if "PC" in lbl.text()]
        self.assertTrue(intro)
        self.assertNotIn("\n", intro[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
