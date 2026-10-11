#!/usr/bin/env python3
"""🚦 Ready? — the event pre-flight dialog.

Run:  py -m unittest tests.gui.test_readiness_dialog -v

The 🚦 Check menu's first entry grades what will be played (every deck that
holds titles and the Eintanzen list) and shows one traffic light per check.
Each yellow or red line has a button that runs the existing fix — 🧭 Fix paths,
the 📊 / 🔇 / 🐂 library passes, 🔁 Check duplicates, 🎵 the music report — and
↻ grades again afterwards. The files / duplicates / music headings open their
full tool even when the line is green.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_ready_"))

from dancesport_planner import MusicEntry, MusicLibrary, PlaylistSuggester, RoundConfig
from planner.readiness import FAIL, OK, WARN
from tests.qt_test_support import reap_widget, stub_window_startup


class ReadinessDialogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        cls._settings_dir = tempfile.mkdtemp(prefix="dp_ready_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._settings_dir)
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.dir = Path(tempfile.mkdtemp(prefix="dp_ready_music_"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.win._library.cache = None   # no measurements known: only files + duplicates

    def entry(self, name, dance="LW", exists=True) -> MusicEntry:
        path = self.dir / f"{name}.mp3"
        if exists:
            path.write_bytes(b"ID3")
        return MusicEntry(path=path, title=name, dance=dance, popularity=3)

    def load(self, *entries):
        lib = MusicLibrary()
        lib.entries.extend(entries)
        self.win._library.lib = lib
        self.win._deckset.tableB.load(
            {"Finale": [[e] for e in entries]}, ["LW"],
            [RoundConfig(name="Finale", heats=len(entries), tier="final")], "S",
            play_cb=self.win._play_or_stop, suggester=PlaylistSuggester(lib),
            use_timbre=False, style="Standard")

    def open_dialog(self):
        self.win._check_readiness()
        dlg = self.win._ready_dlg
        self.assertIsNotNone(dlg)
        return dlg

    def test_a_missing_file_turns_the_light_red(self):
        self.load(self.entry("Valse"), self.entry("Gone", exists=False))
        dlg = self.open_dialog()
        self.assertEqual(dlg.level, FAIL)
        self.assertIn("paths", dlg.fix_buttons)

    def test_the_fix_button_runs_the_path_fixer(self):
        self.load(self.entry("Gone", exists=False))
        dlg = self.open_dialog()
        with mock.patch.object(self.win, "_fix_deck_paths") as fix:
            dlg.fix_buttons["paths"].click()
        fix.assert_called_once()

    def test_a_clean_evening_is_green_without_fix_buttons(self):
        self.load(self.entry("Valse"), self.entry("Quickstep"))
        dlg = self.open_dialog()
        self.assertEqual((dlg.level, dlg.fix_buttons), (OK, {}))

    def test_an_empty_desk_is_yellow(self):
        self.assertEqual(self.open_dialog().level, WARN)

    def test_check_again_grades_anew(self):
        gone = self.entry("Gone", exists=False)
        self.load(gone)
        dlg = self.open_dialog()
        gone.path.write_bytes(b"ID3")
        dlg.recheck_btn.click()
        self.assertEqual(dlg.level, OK)

    def test_a_second_click_reuses_the_open_dialog(self):
        self.load(self.entry("Valse"))
        first = self.open_dialog()
        self.assertIs(self.open_dialog(), first)

    def test_a_green_heading_still_opens_its_tool(self):
        self.load(self.entry("Valse"))
        dlg = self.open_dialog()
        self.assertEqual(set(dlg.tool_links), {"files", "duplicates", "music"})
        with mock.patch.object(self.win, "_fix_deck_paths") as fix, \
                mock.patch.object(self.win, "_check_music") as music:
            dlg.tool_links["files"].linkActivated.emit("#")
            dlg.tool_links["music"].linkActivated.emit("#")
        fix.assert_called_once()
        music.assert_called_once()

    def test_fix_paths_stands_in_the_button_column_even_when_green(self):
        """Marcel: "align fix button also right" - with the other fix buttons."""
        self.load(self.entry("Valse"))
        dlg = self.open_dialog()
        btn = dlg.paths_btn
        _row, column, _rs, _cs = dlg._grid.getItemPosition(dlg._grid.indexOf(btn))
        self.assertEqual(column, 2)
        with mock.patch.object(self.win, "_fix_deck_paths") as fix:
            btn.click()
        fix.assert_called_once()

    def test_a_red_files_line_has_one_fix_paths_button(self):
        self.load(self.entry("Gone", exists=False))
        dlg = self.open_dialog()
        self.assertIs(dlg.fix_buttons["paths"], dlg.paths_btn)
        from PySide6.QtWidgets import QPushButton
        caption = dlg.paths_btn.text()
        self.assertEqual(
            [b for b in dlg.findChildren(QPushButton) if b.text() == caption],
            [dlg.paths_btn])

    def test_a_music_suspect_is_yellow_with_the_report_one_click_away(self):
        valse = self.entry("Valse")
        self.load(valse)
        found = ([(valse, 3, 0.0, 60, ["⏱ too short"], ["Finale"])], 1, 0, [], True)
        with mock.patch.object(self.win, "_compute_music_suspects", return_value=found):
            dlg = self.open_dialog()
        self.assertEqual(dlg.level, WARN)
        self.assertIn("music", dlg.fix_buttons)
        with mock.patch.object(self.win, "_check_music") as music:
            dlg.fix_buttons["music"].click()
        music.assert_called_once()

    def test_a_cancelled_music_check_leaves_its_line_out(self):
        self.load(self.entry("Valse"))
        with mock.patch.object(self.win, "_music_suspects_with_progress",
                               return_value=None):
            dlg = self.open_dialog()
        self.assertNotIn("music", dlg.tool_links)
        self.assertEqual(dlg.level, OK)


if __name__ == "__main__":
    unittest.main(verbosity=2)
