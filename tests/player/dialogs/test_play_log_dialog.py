"""📜 Played titles: the evenings from the play log, one saved as CSV or deleted."""
import datetime as dt
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton

from planner import i18n
from planner.playing import play_log
from player.dialogs import play_log_dialog
from player.dialogs.play_log_dialog import PlayLogDialog
from tests.db_support import use_scratch_db


def at(day, hh, mm):
    return dt.datetime(2026, 10, day, hh, mm)


class PlayLogDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_play_dlg_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")

    def fill(self):
        for when, title in ((at(3, 20, 0), "a"), (at(3, 20, 3), "b"), (at(5, 19, 0), "c")):
            play_log.record(when, rf"C:\m\{title}.mp3", "Artist", title, "LW", "Deck A", 180,
                            composer="Composer " + title)

    def dialog(self):
        dlg = PlayLogDialog()
        self.addCleanup(dlg.deleteLater)
        return dlg

    def test_evenings_newest_first_with_their_titles(self):
        self.fill()
        dlg = self.dialog()
        self.assertEqual(dlg.evening_list.count(), 2)
        self.assertIn("05.10.2026", dlg.evening_list.item(0).text())
        dlg.evening_list.setCurrentRow(1)
        titles = [dlg.plays_table.item(r, 2).text() for r in range(dlg.plays_table.rowCount())]
        self.assertEqual(titles, ["a", "b"])
        self.assertEqual(dlg.plays_table.item(0, 3).text(), "Composer a")
        self.assertEqual(dlg.plays_table.item(0, 6).text(), "3:00")

    def test_save_as_csv_writes_the_selected_evening(self):
        self.fill()
        dlg = self.dialog()
        dlg.evening_list.setCurrentRow(1)
        out = self.dir / "out.csv"
        with mock.patch.object(play_log_dialog.QFileDialog, "getSaveFileName",
                               return_value=(str(out), "")) as ask:
            dlg.save_btn.click()
        self.assertIn("2026-10-03", ask.call_args.args[2])
        lines = out.read_text(encoding="utf-8-sig").splitlines()
        self.assertEqual(len(lines), 3)

    def test_delete_asks_first(self):
        self.fill()
        dlg = self.dialog()
        dlg.evening_list.setCurrentRow(0)
        with mock.patch.object(play_log_dialog.QMessageBox, "question",
                               return_value=QMessageBox.StandardButton.No):
            dlg.delete_btn.click()
        self.assertEqual(len(play_log.evenings()), 2)
        with mock.patch.object(play_log_dialog.QMessageBox, "question",
                               return_value=QMessageBox.StandardButton.Yes):
            dlg.delete_btn.click()
        self.assertEqual([e.count for e in play_log.evenings()], [2])
        self.assertEqual(dlg.evening_list.count(), 1)

    def test_the_columns_can_be_dragged_and_keep_their_width(self):
        from PySide6.QtWidgets import QHeaderView
        self.fill()
        dlg = self.dialog()
        head = dlg.plays_table.horizontalHeader()
        for c in range(dlg.plays_table.columnCount()):
            self.assertEqual(head.sectionResizeMode(c), QHeaderView.ResizeMode.Interactive)
        head.resizeSection(1, 333)                      # as a drag on the header does
        dlg.evening_list.setCurrentRow(1)               # another evening keeps it
        self.assertEqual(head.sectionSize(1), 333)

    def test_an_empty_log_says_how_it_fills(self):
        dlg = self.dialog()
        self.assertEqual(dlg.evening_list.count(), 0)
        self.assertFalse(dlg.save_btn.isEnabled())
        self.assertFalse(dlg.delete_btn.isEnabled())
        self.assertFalse(dlg.empty_hint.isHidden())


class PlayLogDialogI18nTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def test_the_buttons_and_title_speak_german(self):
        i18n.set_active("de")
        i18n.install_text_hook()
        with mock.patch.object(play_log, "evenings", return_value=[]):
            dlg = PlayLogDialog()
        self.addCleanup(dlg.deleteLater)
        texts = {b.text() for b in dlg.findChildren(QPushButton)}
        self.assertTrue({"💾  Als CSV speichern…", "🗑  Abend löschen"} <= texts, texts)
        self.assertEqual(dlg.windowTitle(), "📜 Gespielte Titel")
        self.assertIn("Titel", [dlg.plays_table.horizontalHeaderItem(c).text()
                                for c in range(dlg.plays_table.columnCount())])
        self.assertNotEqual(dlg.empty_hint.text(), play_log_dialog.EMPTY_HINT)


if __name__ == "__main__":
    unittest.main()
