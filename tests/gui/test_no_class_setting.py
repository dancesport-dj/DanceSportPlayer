#!/usr/bin/env python3
"""⚙ Settings → 🏷 leave titles without a class out of generation.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_no_class_setting -v

The "🏷 No class" category is for finding the untagged titles in the library
pane. Whether they also stay out of the generated playlists is the user's
call: off by default, a checkbox switches it on, and saving it applies at
once — as does the saved choice when the window starts.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_no_class_setting_"))

from PySide6.QtWidgets import QApplication, QDialog, QTabWidget

import dancesport_gui as gui
from gui.library_browser import LibraryBrowser
from gui.window import main_global
from planner.models import (
    MusicEntry,
    is_non_turnier,
    note_class_tag_use,
    set_no_class_exclusion,
)
from tests.qt_test_support import reap_widget

_COL_TITLE = 3


def _entry(title, classes_ok=None):
    return MusicEntry(path=Path(rf"C:\music\tanzcds\{title}.mp3"), title=title,
                      dance="LW", bpm=29, classes_ok=classes_ok)


_TAGGED = _entry("tagged", classes_ok=["B", "A", "S"])
_UNTAGGED = _entry("untagged")


class _ClassTagsInUse(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        note_class_tag_use([_TAGGED])
        self.addCleanup(note_class_tag_use, ())
        self.addCleanup(set_no_class_exclusion, False)


class SettingsCheckboxTest(_ClassTagsInUse):

    def _dialog(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_it_is_off_until_ticked(self):
        dlg = self._dialog({})
        self.assertFalse(dlg._exclude_no_class_chk.isChecked())
        self.assertFalse(dlg.values()["exclude_no_class"])
        dlg._exclude_no_class_chk.setChecked(True)
        self.assertTrue(dlg.values()["exclude_no_class"])

    def test_a_saved_choice_is_shown(self):
        dlg = self._dialog({"exclude_no_class": True})
        self.assertTrue(dlg._exclude_no_class_chk.isChecked())

    def test_it_sits_on_the_general_tab(self):
        dlg = self._dialog({})
        tabs = dlg.findChild(QTabWidget)
        captions = [tabs.tabText(i) for i in range(tabs.count())]
        page = tabs.widget(captions.index("⚙ General"))
        self.assertTrue(page.isAncestorOf(dlg._exclude_no_class_chk))


class _Dialog:
    """⚙ Settings with the operator ticking 🏷."""

    def __init__(self, settings, parent, **_kw):
        self._given = dict(settings)

    def exec(self):
        return QDialog.DialogCode.Accepted

    def values(self):
        return {**self._given, "exclude_no_class": True}

    def running_look_touched(self):
        return False

    def deleteLater(self):
        pass


class WindowAppliesTest(_ClassTagsInUse):

    def _window(self, settings):
        patch = mock.patch.object(gui, "load_settings",
                                  lambda *a, **kw: dict(settings))
        patch.start()
        self.addCleanup(patch.stop)
        win = gui.MainWindow()
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        return win

    def test_the_window_starts_with_the_saved_choice(self):
        self._window({"app_mode": "both", "exclude_no_class": True})
        self.assertTrue(is_non_turnier(_UNTAGGED))

    def test_by_default_the_untagged_title_is_generated_from(self):
        self._window({"app_mode": "both"})
        self.assertFalse(is_non_turnier(_UNTAGGED))

    def test_saving_applies_it_at_once(self):
        win = self._window({"app_mode": "both"})
        for name, value in (("SettingsDialog", _Dialog),
                            ("save_settings", lambda s: None)):
            patch = mock.patch.object(main_global, name, value)
            patch.start()
            self.addCleanup(patch.stop)
        win._open_settings()
        self.assertTrue(is_non_turnier(_UNTAGGED))


class TournamentFilterTest(_ClassTagsInUse):
    """The pane's 🏆 category shows what generation draws from."""

    def setUp(self):
        super().setUp()
        self.pane = LibraryBrowser()
        self.addCleanup(reap_widget, self.pane)

    def _shown_as_tournament(self) -> set:
        self.pane.set_entries([_TAGGED, _UNTAGGED])
        combo = self.pane._cat_combo
        combo.setCurrentIndex(combo.findData("turnier"))
        t = self.pane._table
        return {t.item(r, _COL_TITLE).text() for r in range(t.rowCount())}

    def test_the_untagged_title_counts_as_tournament_music(self):
        self.assertEqual(self._shown_as_tournament(), {"tagged", "untagged"})

    def test_unless_it_is_left_out_of_generation(self):
        set_no_class_exclusion(True)
        self.assertEqual(self._shown_as_tournament(), {"tagged"})


if __name__ == "__main__":
    unittest.main()
