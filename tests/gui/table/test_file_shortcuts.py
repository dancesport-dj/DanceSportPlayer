"""Keys for the file entries of the title menu, and the keys shown in it.

Run:  py -m unittest tests.gui.table.test_file_shortcuts -v

Ctrl+E shows the title in Explorer, Ctrl+T edits its tags, Ctrl+Shift+C copies
its path. The menu entries carry their key, and so do the removals that Del
already did.
"""
import unittest
from unittest import mock

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractItemView, QApplication

from gui.table import table_menu
from planner import i18n
from tests.gui.table.test_remove_with_slot import _Base

CTRL = Qt.KeyboardModifier.ControlModifier
CTRL_SHIFT = CTRL | Qt.KeyboardModifier.ShiftModifier


class FileKeysTest(_Base):

    def test_ctrl_e_shows_the_title_in_explorer(self):
        t = self.party("A", "B")
        t.selectRow(self.row_of(t, "B"))
        with mock.patch.object(table_menu, "reveal_in_explorer") as reveal:
            QTest.keyClick(t, Qt.Key.Key_E, CTRL)
        reveal.assert_called_once()
        self.assertEqual(reveal.call_args.args[0].stem, "B")

    def test_ctrl_t_edits_the_tags_of_the_selection(self):
        t = self.party("A", "B", "C")
        t.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        t.selectRow(self.row_of(t, "A"))
        t.selectRow(self.row_of(t, "B"))
        with mock.patch.object(t, "_edit_tags_of") as tags:
            QTest.keyClick(t, Qt.Key.Key_T, CTRL)
        edited = [t._row_meta[r].entry for r in tags.call_args.args[0]]
        self.assertEqual({e.title for e in edited}, {"A", "B"})

    def test_ctrl_shift_c_copies_the_path(self):
        t = self.party("A", "B")
        t.selectRow(self.row_of(t, "A"))
        QTest.keyClick(t, Qt.Key.Key_C, CTRL_SHIFT)
        self.assertTrue(QApplication.clipboard().text().endswith("A.mp3"))

    def test_nothing_selected_does_nothing(self):
        t = self.party("A")
        t.clearSelection()
        t.setCurrentCell(-1, -1)
        with mock.patch.object(table_menu, "reveal_in_explorer") as reveal:
            QTest.keyClick(t, Qt.Key.Key_E, CTRL)
        reveal.assert_not_called()


class MenuShowsKeysTest(_Base):

    def texts(self, t, title):
        return self.menu(t, self.row_of(t, title))

    def test_the_file_entries_name_their_keys(self):
        texts = self.texts(self.party("A", "B"), "A")
        for caption, key in (("📂  Show in Explorer", "Ctrl+E"),
                             ("🏷  Edit tags…", "Ctrl+T"),
                             ("📋  Copy file path", "Ctrl+Shift+C")):
            self.assertIn(f"{caption}\t{key}", texts)

    def test_the_removals_name_del(self):
        texts = self.texts(self.party("A", "B"), "A")
        self.assertIn("🗑  Remove this title (keep slot)\tDel", texts)

    def test_a_title_with_a_time_marker_can_reset_it(self):
        t = self.party("A", "B")
        row = self.row_of(t, "A")
        self.assertNotIn("↩  Reset time marker", self.texts(t, "A"))
        t._resume_marks = {str(t._row_meta[row].entry.path): 61000}
        self.assertIn("↩  Reset time marker", self.texts(t, "A"))
        self.assertNotIn("↩  Reset time marker", self.texts(t, "B"))

    def test_picking_it_forgets_the_marker(self):
        t = self.party("A", "B")
        entry = t._row_meta[self.row_of(t, "A")].entry
        t._resume_marks = {str(entry.path): 61000}
        with mock.patch.object(type(t.host), "clear_resume") as clear:
            self.menu(t, self.row_of(t, "A"), pick="↩  Reset time marker")
        clear.assert_called_once_with(entry.path)

    def test_the_key_speaks_german_too(self):
        self.addCleanup(i18n._restore_text_hook)
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)
        i18n.set_active("de")
        texts = self.texts(self.party("A", "B"), "A")
        self.assertIn("🗑  Diesen Titel entfernen (Platz bleibt frei)\tEntf", texts)
        self.assertTrue(any(x.endswith("\tStrg+E") for x in texts), texts)


if __name__ == "__main__":
    unittest.main()
