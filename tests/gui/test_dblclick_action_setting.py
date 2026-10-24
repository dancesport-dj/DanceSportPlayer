"""📂 What a double-click on a title does — ⚙ Settings → 🔊 Sound & player.

Run:  py -m unittest tests.gui.test_dblclick_action_setting -v

A tester on a Mac double-clicked a title and found it opened in Apple's Music
app, with nothing in ⚙ Settings to stop it. The switch then became a choice:
Nothing (the default), Open external player (the old switch on) and Edit
tags, which opens the 🏷 Tags editor from 📚 the library and the 🏆 tree; the
right-click entries keep working either way. Edit tags was once two, Edit MP3
tag and Edit DB information, until Marcel merged the two editors into one.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Offscreen BEFORE any QApplication exists, and state files into a temp dir.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_dblclick_ext_"))

from PySide6.QtWidgets import QApplication

from gui import common
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget, stub_window_startup


def _action(test, action):
    """Set the module choice for one test and put the old one back after."""
    test.addCleanup(common.set_dblclick_action, common.dblclick_action())
    common.set_dblclick_action(action)


class SoundTabTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_it_starts_on_nothing(self):
        self.assertEqual(self._dlg({}).values()["dblclick_action"], "nothing")

    def test_it_offers_the_three_choices(self):
        combo = self._dlg({})._dblclick_combo
        self.assertEqual([combo.itemData(i) for i in range(combo.count())],
                         ["nothing", "external", "tags"])
        self.assertEqual(combo.itemText(2), "Edit tags")

    def test_it_stands_last_on_the_tab_and_says_it_is_for_the_library(self):
        """Marcel: "the double click on a title … should be at the botton
        since it is only for library, make it clearer"."""
        from PySide6.QtCore import QPoint
        from PySide6.QtWidgets import QTabWidget
        from planner.i18n.lang_de import CATALOG
        dlg = self._dlg({})
        tabs = dlg.findChild(QTabWidget)
        tabs.setCurrentIndex(tabs.indexOf(
            next(tabs.widget(i) for i in range(tabs.count())
                 if tabs.widget(i).isAncestorOf(dlg._dblclick_combo))))
        dlg.show()
        self.app.processEvents()

        def y(w):
            return w.mapTo(dlg, QPoint(0, 0)).y()

        self.assertGreater(y(dlg._dblclick_combo), y(dlg._player_layout_combo))
        self.assertGreater(y(dlg._dblclick_note), y(dlg._dblclick_combo))
        for text in (dlg._dblclick_head.text(), dlg._dblclick_note.text()):
            with self.subTest(text=text):
                self.assertIn(text, CATALOG)

    def test_a_stored_choice_is_shown_and_saved(self):
        dlg = self._dlg({"dblclick_action": "tags"})
        self.assertEqual(dlg._dblclick_combo.currentData(), "tags")
        dlg._dblclick_combo.setCurrentIndex(dlg._dblclick_combo.findData("external"))
        self.assertEqual(dlg.values()["dblclick_action"], "external")

    def test_the_default_settings_have_nothing(self):
        from gui.dialogs import load_settings
        with mock.patch("gui.dialogs.SETTINGS.read", return_value=None):
            self.assertEqual(load_settings()["dblclick_action"], "nothing")

    def test_the_old_switch_on_becomes_external(self):
        from gui.dialogs import load_settings
        with mock.patch("gui.dialogs.SETTINGS.read",
                        return_value={"dblclick_external": True}):
            self.assertEqual(load_settings()["dblclick_action"], "external")

    def test_a_choice_wins_over_the_old_switch(self):
        from gui.dialogs import load_settings
        with mock.patch("gui.dialogs.SETTINGS.read", return_value={
                "dblclick_external": True, "dblclick_action": "tags"}):
            self.assertEqual(load_settings()["dblclick_action"], "tags")

    def test_the_two_old_editors_become_tags(self):
        from gui.dialogs import load_settings
        for old in ("mp3", "db"):
            with self.subTest(old=old), mock.patch(
                    "gui.dialogs.SETTINGS.read", return_value={"dblclick_action": old}):
                self.assertEqual(load_settings()["dblclick_action"], "tags")

    def test_an_unknown_choice_does_nothing(self):
        _action(self, "bogus")
        self.assertEqual(common.dblclick_action(), "nothing")


class LibraryBrowserTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from gui.library_browser import LibraryBrowser
        self.browser = LibraryBrowser()
        self.addCleanup(reap_widget, self.browser)
        self.opened, self.edited = [], []
        self.browser._open_external = self.opened.append
        self.browser._edit_tags = lambda paths, focus=None: self.edited.append((paths, focus))
        self.browser._row_path = lambda _row: Path(r"C:\music\a.mp3")

    def test_nothing_leaves_the_file_alone(self):
        _action(self, "nothing")
        self.browser._on_double_click(0, 1)
        self.assertEqual((self.opened, self.edited), ([], []))

    def test_external_opens_it(self):
        _action(self, "external")
        self.browser._on_double_click(0, 1)
        self.assertEqual(self.opened, [Path(r"C:\music\a.mp3")])

    def test_edit_tags_opens_the_editor(self):
        _action(self, "tags")
        self.browser._on_double_click(0, 1)
        self.assertEqual(self.edited, [({r"C:\music\a.mp3"}, "genre")])
        self.assertEqual(self.opened, [])

    def test_the_editor_is_told_which_column_was_double_clicked(self):
        from gui.library_browser import _LIB_COL_CUSTOM, _LIB_COL_LEN, _LIB_COL_TITLE
        _action(self, "tags")
        for col in (_LIB_COL_TITLE, 2, _LIB_COL_CUSTOM, _LIB_COL_LEN):
            self.browser._on_double_click(0, col)
        self.assertEqual([f for _p, f in self.edited], ["title", "artist", "custom", None])


class TournamentTreeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from gui import tournament_tree as gt
        from planner.store import JsonStore
        d = Path(tempfile.mkdtemp(prefix="dp_dblclick_tree_"))
        self.path = d / "a.mp3"
        self.path.write_bytes(b"")
        self.entry = MusicEntry(path=self.path, title="a", dance="LW")
        self.pane = gt.TournamentTree(JsonStore.at(str(d / "t.json")))
        self.addCleanup(reap_widget, self.pane)
        self.pane._row_path = lambda _row: str(self.path)
        self.pane._entry_for = lambda _p: self.entry
        self.edited = []
        # Without a parent the pane is its own window().
        self.pane._edit_entry_tags = lambda entries, focus=None: self.edited.append((entries, focus))
        self.opened = []
        patcher = mock.patch.object(gt, "_open_in_default_player",
                                    lambda p, _parent=None: self.opened.append(p))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_nothing_leaves_the_file_alone(self):
        _action(self, "nothing")
        self.pane._on_track_double_click(0, 1)
        self.assertEqual((self.opened, self.edited), ([], []))

    def test_external_opens_it(self):
        _action(self, "external")
        self.pane._on_track_double_click(0, 1)
        self.assertEqual(self.opened, [self.path])

    def test_edit_tags_opens_the_editor(self):
        _action(self, "tags")
        self.pane._on_track_double_click(0, 1)
        self.assertEqual(self.edited, [([self.entry], None)])

    def test_the_editor_is_told_which_column_was_double_clicked(self):
        _action(self, "tags")
        for col in (2, 3, 4, 8):
            self.pane._on_track_double_click(0, col)
        self.assertEqual([f for _e, f in self.edited], ["genre", "artist", "title", "classes"])


class WindowTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_dblclick_ext_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(
            cls, {"app_mode": "both", "dblclick_action": "tags"})

    def setUp(self):
        _action(self, "nothing")
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, self.win)

    def test_the_window_starts_as_the_setting_says(self):
        self.assertEqual(common.dblclick_action(), "tags")

    def test_a_saved_change_applies_at_once(self):
        from PySide6.QtWidgets import QDialog
        given = {**self.win._settings, "dblclick_action": "external"}

        class Dlg:
            def __init__(self, *_a, **_k):
                pass

            def exec(self):
                return QDialog.DialogCode.Accepted

            def values(self):
                return given

            def running_look_touched(self):
                return False

            def deleteLater(self):
                pass

        with mock.patch("gui.window.main_global.SettingsDialog", Dlg), \
                mock.patch("gui.window.main_global.save_settings"):
            self.win._open_settings()
        self.assertEqual(common.dblclick_action(), "external")
        self.assertTrue(common.dblclick_opens_external())


if __name__ == "__main__":
    unittest.main()
