#!/usr/bin/env python3
"""💾 Save a playlist or a whole tournament day and file it in 🏆 Tournaments.

Run:  py -m unittest tests.gui.test_save_to_tournaments -v

Marcel: "ich möchte playlisten oder ganze comp tage per context menu nicht nur
abspeichern wie bisher sondern auch die möglichkeit haben diese im Tournament
tab hinzuzufügen". Beside each save entry of a right-click menu sits one that
saves the same way and then files what was written in the tournament tree —
a day as a folder named after it.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_save_tree_"))

from PySide6.QtCore import QPoint  # noqa: E402
from PySide6.QtGui import QContextMenuEvent  # noqa: E402
from PySide6.QtWidgets import QMenu, QMessageBox  # noqa: E402

from dancesport_planner import MusicEntry, MusicLibrary  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)

_DIR = Path(tempfile.mkdtemp(prefix="dp_save_tree_files_"))


def _entry(name, dance="CC"):
    path = _DIR / f"{name}.mp3"
    path.touch()
    return MusicEntry(path=path, title=name, dance=dance, duration=180)


class SaveToTournamentsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_save_tree_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.win._lib = MusicLibrary()
        self.table = self.win._tableB
        self.table.load_player_list([_entry("c1"), _entry("r1", "RB")],
                                    "Party", play_cb=None)
        filed = mock.patch.object(self.win._tourney_tree, "file_saved",
                                  return_value=1)
        self.filed = filed.start()
        self.addCleanup(filed.stop)

    def save_as(self, name, **kwargs):
        from gui import main_export
        out = _DIR / name
        with mock.patch.object(main_export.QFileDialog, "getSaveFileName",
                               return_value=(str(out), "")), \
                mock.patch.object(main_export, "save_settings"):
            self.win._on_table_save_requested(self.table, **kwargs)
        return out

    def menu_texts(self, pick=None):
        from gui import table_actions
        seen = []

        class _Menu(QMenu):
            def exec(self, *_args):
                seen.extend(a.text() for a in self.actions())
                return next((a for a in self.actions()
                             if pick and a.text().startswith(pick)), None)

        pos = QPoint(5, self.table.rowViewportPosition(0) + 2)
        with mock.patch.object(table_actions, "QMenu", _Menu):
            self.table.contextMenuEvent(QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, pos, self.table.mapToGlobal(pos)))
        return seen

    def test_a_plain_save_files_nothing(self):
        out = self.save_as("Plain.m3u")
        self.assertTrue(out.exists())
        self.filed.assert_not_called()

    def test_save_and_add_files_the_written_playlist(self):
        out = self.save_as("Filed.m3u", file_in_tree=True)
        self.assertTrue(out.exists())
        self.filed.assert_called_once_with([out], None)

    def test_the_tournaments_tab_comes_to_the_front_unfolded(self):
        """Marcel said yes to showing the Tournaments tab after filing."""
        tabs = self.win._lib_tabs
        tabs.setCurrentIndex(0)
        self.win._toggle_lib_pane_fold(True, save=False)
        with mock.patch("gui.main_fold.save_settings"):
            self.save_as("Front.m3u", file_in_tree=True)
        self.assertIs(tabs.currentWidget(), self.win._tourney_tree)
        self.assertFalse(self.win._lib_pane_folded)

    def test_a_plain_save_leaves_the_tabs_alone(self):
        tabs = self.win._lib_tabs
        tabs.setCurrentIndex(0)
        self.save_as("Stay.m3u")
        self.assertEqual(tabs.currentIndex(), 0)

    def test_the_playlist_menu_offers_it_beside_the_save(self):
        texts = self.menu_texts()
        save = texts.index("💾  Save as M3U…")
        self.assertEqual(texts[save + 1], "🏆  Save and add to Tournaments…")

    def test_picking_it_saves_and_files(self):
        with mock.patch.object(self.win, "_on_table_save_requested") as save:
            self.menu_texts(pick="🏆  Save and add")
        save.assert_called_once_with(self.table, file_in_tree=True)

    def test_a_cancelled_save_files_nothing(self):
        from gui import main_export
        with mock.patch.object(main_export.QFileDialog, "getSaveFileName",
                               return_value=("", "")):
            self.win._on_table_save_requested(self.table, file_in_tree=True)
        self.filed.assert_not_called()

    def test_a_saved_day_is_filed_as_its_own_folder(self):
        from gui import main_export
        day = self.win._day_decks[0]
        day.load_player_list([_entry("s1")], "Day", play_cb=None)
        self.win._day_tab_title = "Samstag"
        written = []

        def export(_pl, _dances, base, _cls, out_path, path_for):
            out_path.write_text("#EXTM3U\n", encoding="utf-8")
            written.append(out_path)
            return str(out_path)

        root = Path(tempfile.mkdtemp(prefix="dp_save_tree_day_"))
        with mock.patch.object(main_export.QFileDialog, "getExistingDirectory",
                               return_value=str(root)), \
                mock.patch.object(self.win, "_serialize_playlist_state",
                                  return_value={"rounds": []}), \
                mock.patch.object(self.win, "_deck_export_jobs",
                                  return_value=[("HGR S STD", {}, [], "S"),
                                                ("SEN I S STD", {}, [], "S")]), \
                mock.patch.object(main_export, "export_m3u", export), \
                mock.patch.object(QMessageBox, "exec", return_value=0):
            self.win._save_day_plan_m3us(file_in_tree=True)
        self.assertEqual(len(written), 2)
        self.filed.assert_called_once_with(written, "Samstag")

    def test_the_day_tab_menu_offers_it_beside_the_save(self):
        from gui import main_decks
        seen = []

        class _Menu(QMenu):
            def exec(self, *_args):
                seen.extend(a.text() for a in self.actions())
                return None

        with mock.patch.object(main_decks, "QMenu", _Menu):
            self.win._day_tab_menu(QPoint(0, 0))
        save = seen.index("💾  Save all competition M3Us")
        self.assertEqual(seen[save + 1], "🏆  Save all and add to Tournaments")


if __name__ == "__main__":
    unittest.main(verbosity=2)
