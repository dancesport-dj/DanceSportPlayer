"""⚙ Settings: one tab per kind of setting, not one "Paths & search" for all.

Run:  py -m unittest tests.gui.test_settings_tabs -v
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_settings_tabs_"))

from PySide6.QtWidgets import QApplication, QLabel, QScrollArea, QTabWidget

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

    def test_every_page_scrolls(self):
        for i in range(self.tabs.count()):
            self.assertIsInstance(self.tabs.widget(i), QScrollArea, self.tabs.tabText(i))

    def test_the_buttons_stay_on_a_small_screen(self):
        """A laptop screen shorter than the tallest page: the page scrolls,
        and OK / Cancel below it stay where they can be pressed."""
        avail = self.dlg.screen().availableGeometry()
        for hint in (self.dlg.minimumSizeHint(), self.dlg.size()):
            self.assertLessEqual(hint.height(), avail.height())
            self.assertLessEqual(hint.width(), avail.width())

    def test_the_per_dance_lengths_keep_their_own_size(self):
        """Marcel: "the per dance input fields are now too long make them as
        before but make sure in the height they are visible on small
        screens" — as wide as a length needs, however wide the dialog is,
        and full height on a laptop screen: the page scrolls instead."""
        self.tabs.setCurrentWidget(self.page("🎛 Play sets"))
        for size in ((1600, 1000), (700, 450)):
            self.dlg.resize(*size)
            self.dlg.show()
            QApplication.processEvents()
            for dance, (combo, _secs) in self.dlg._dance_len_combos.items():
                self.assertEqual(combo.width(), combo.sizeHint().width(), (size, dance))
                self.assertGreaterEqual(combo.height(), combo.sizeHint().height(),
                                        (size, dance))

    def test_the_tso_pitch_targets_keep_their_own_size(self):
        """Marcel: "tso pitch target also need not to be so wide" — and then
        "a little bit wider ... I miss the last border edge of the combobox":
        on a Mac the popup button's frame reaches past its size hint, so a
        few pixels of room on top, not the dialog's whole width."""
        combos = self.dlg._band_combos
        self.tabs.setCurrentWidget(
            next(self.tabs.widget(i) for i in range(self.tabs.count())
                 if self.tabs.widget(i).isAncestorOf(combos["LW"])))
        for size in ((1600, 1000), (700, 450)):
            self.dlg.resize(*size)
            self.dlg.show()
            QApplication.processEvents()
            for dance, combo in combos.items():
                extra = combo.width() - combo.sizeHint().width()
                self.assertTrue(6 <= extra <= 20, (size, dance, extra))
                self.assertGreaterEqual(combo.height(), combo.sizeHint().height(),
                                        (size, dance))


if __name__ == "__main__":
    unittest.main(verbosity=2)
