#!/usr/bin/env python3
"""Click-through, chapter 15: Tags.

Run:  py -m unittest tests.gui.test_click_15_tags -v

The operator's paths through the manual, clicked in order on a real
MainWindow (see tests/gui/monkey_support.py):

    docs/manual-planner/15-tags.md
"""

import os
import unittest
from pathlib import Path
from unittest import mock

# First: it points the app's state files at a temp folder before any app
# module is imported.
from tests.gui.monkey_support import ClickThrough, printable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QMessageBox
from shared.columns import _COL_CUSTOM, _COL_RATING, _COL_TITLE

_RAW_DESC, _RAW_VALUE = 1, 2      # the Extended tab's columns (gui.tag_edit_dialog)


class TagsClickTest(ClickThrough):
    """15 Tags."""

    def keep_file(self, path: Path):
        """The library is shared by the class: a scenario that writes into one
        of its MP3s puts the bytes back afterwards. The library cache goes by
        whole-second mtimes: written back in the second of the edit, the next
        window would still read the edited tags."""
        data = path.read_bytes()

        def put_back():
            path.write_bytes(data)
            st = path.stat()
            os.utime(path, (st.st_atime, st.st_mtime + 2))
        self.addCleanup(put_back)

    def tag_file(self, path: Path, title: str, **txxx):
        """A title and custom text frames written into one MP3 of the library
        as an ID3v2.3 tag, the way UltraMixer leaves them (put back after)."""
        from mutagen.id3 import ID3, TIT2, TXXX
        self.keep_file(path)
        tags = ID3()
        tags.add(TIT2(encoding=3, text=[title]))
        for desc, value in txxx.items():
            tags.add(TXXX(encoding=3, desc=desc, text=[value]))
        tags.save(path, v2_version=3)

    def show_column(self, op, name: str, table=None):
        """Header right-click ▸ tick the column `name`."""
        table = table or self.win._deckset.table
        op.pick(name)
        op._context_menu(table.horizontalHeader(), QPoint(30, 5), "")
        QTest.qWait(5)
        self.assertTrue(self.wait_until(lambda: not op.script), op.script)

    def click_star(self, table, row: int, star: int, double=False):
        from gui.star_rating import star_rects
        idx = table.model().index(row, _COL_RATING)
        table.scrollTo(idx)
        at = star_rects(table.visualRect(idx), table.fontMetrics())[star - 1].center()
        click = QTest.mouseDClick if double else QTest.mouseClick
        click(table.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, at)
        QTest.qWait(5)

    def edit_tags(self, op, row: int, act):
        """Right-click ▸ 🏷 Edit tags…, `act` works the editor."""
        from gui.tag_edit_dialog import TagEditDialog
        op.pick("🏷  Edit tags")
        op.answer(lambda w: isinstance(w, TagEditDialog), act)
        self.right_click(op, self.win._deckset.table, row)
        self.assertTrue(self.wait_until(lambda: not op.script), op.script)

    def save(self, dlg):
        self.click(dlg.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save))

    def raw_row(self, dlg, desc: str) -> int:
        raw = dlg._raw
        return next(r for r in range(raw.rowCount())
                    if raw.item(r, _RAW_DESC).text() == desc)

    def type_cell(self, table, row: int, col: int, text: str):
        """Open the cell's editor, type, Return. QTest's double-click alone
        opens none: the view edits only when a press on the same cell came
        before it."""
        table.editItem(table.item(row, col))
        QTest.qWait(5)
        self.type_into(QApplication.focusWidget(), text)

    def test_edited_tags_are_written_into_the_mp3_and_read_back(self):
        from planner import id3_frames

        def edit(dlg):
            dlg._form["title"].setEditText("Retitled")
            dlg._stars.setCurrentIndex(dlg._stars.findData(4))
            self.save(dlg)

        def write_too(box):
            self.click(box.button(QMessageBox.StandardButton.Yes))

        with self.clicking() as op:
            self.generate(rounds="1")
            row = self.song_rows()[0]
            entry = self.entry_at(row)
            self.keep_file(Path(entry.path))
            op.answer(self.titled("🏷  Write into the MP3?"), write_too)
            self.edit_tags(op, row, edit)

            form = id3_frames.read_form(entry.path)
            self.assertEqual(form["title"].value, "Retitled")
            self.assertTrue(any(f.frame == "POPM" for f in id3_frames.read_fields(entry.path)),
                            "the stars stayed out of the file")
            self.assertEqual((entry.title, entry.rating), ("Retitled", 4))

            # 🏷 Re-read MP3 tags: what the row shows comes from the file again.
            entry.title, entry.rating = "stale", 0
            op.pick("🏷  Re-read MP3 tags")
            self.right_click(op, self.win._deckset.table, row)
            self.assertTrue(self.wait_until(lambda: entry.title == "Retitled"),
                            f"re-read gave {printable(entry.title)!r}")
            self.assertEqual(entry.rating, 4)
            self.assertIn("Retitled", self.win._deckset.table.item(row, _COL_TITLE).text())

    def test_the_extended_tab_edits_adds_and_removes_frames_in_the_file(self):
        from planner import id3_frames
        seen = {}

        def edit(dlg):
            raw = dlg._raw
            dlg._tabs.setCurrentIndex(1)
            # The form's frame can't be typed here; it follows the form.
            title = next(r for r in range(raw.rowCount())
                         if raw.item(r, 0).data(Qt.ItemDataRole.UserRole) == "TIT2")
            seen["title locked"] = not (raw.item(title, _RAW_VALUE).flags()
                                        & Qt.ItemFlag.ItemIsEditable)
            dlg._form["title"].setEditText("New title")
            seen["title mirrored"] = raw.item(title, _RAW_VALUE).text()
            # 📋 Copy: a description is copied, not edited.
            op.pick("📋  Copy")
            r = self.raw_row(dlg, "ultramixer_last_played")
            op._context_menu(raw, self.cell_pos(raw, r, _RAW_DESC), "")
            QTest.qWait(5)
            seen["copied"] = QApplication.clipboard().text()
            self.type_cell(raw, r, _RAW_VALUE, "2026-10-11")
            raw.selectRow(self.raw_row(dlg, "junk"))
            self.click(dlg._raw_remove_btn)
            self.click(dlg._raw_add_btn)
            new = raw.rowCount() - 1
            combo = raw.cellWidget(new, 0)
            combo.setCurrentIndex(combo.findData("TXXX"))
            self.type_cell(raw, new, _RAW_DESC, "mood")
            self.type_cell(raw, new, _RAW_VALUE, "calm")
            self.save(dlg)

        with self.clicking() as op:
            self.generate(rounds="1")
            row = self.song_rows()[0]
            path = Path(self.entry_at(row).path)
            self.tag_file(path, "Old title", ultramixer_last_played="2025-01-01", junk="x")
            self.edit_tags(op, row, edit)

        self.assertTrue(seen["title locked"], "the form's frame was typeable on the Extended tab")
        self.assertEqual(seen["title mirrored"], "New title")
        self.assertEqual(seen["copied"], "ultramixer_last_played")
        frames = {(f.frame, f.desc): f.value for f in id3_frames.read_fields(path)}
        self.assertEqual(frames, {("TIT2", ""): "New title",
                                  ("TXXX", "ultramixer_last_played"): "2026-10-11",
                                  ("TXXX", "mood"): "calm"})
        self.assertEqual(id3_frames.tag_version(path), 3, "the ID3v2.3 tag became v2.4")

    def test_a_star_click_rates_in_the_app_and_survives_a_restart(self):
        with self.clicking() as op:
            self.generate(rounds="1")
            table = self.win._deckset.table
            self.assertTrue(table.isColumnHidden(_COL_RATING), "★ shown before it was asked for")
            self.show_column(op, "★  Rating")
            self.assertFalse(table.isColumnHidden(_COL_RATING))
            row = self.song_rows()[0]
            entry = self.entry_at(row)
            path = Path(entry.path)
            before = path.read_bytes()
            opened = len(op.opened)

            self.click_star(table, row, 3)
            self.assertEqual(entry.rating, 3)
            self.click_star(table, row, 3)
            self.assertFalse(entry.rating, "the star the rating ends on didn't clear it")
            self.click_star(table, row, 3)
            started, opened_files = [], []
            table.playRequested.connect(started.append)
            with mock.patch("gui.playlist_table._open_in_default_player",
                            lambda path, _parent: opened_files.append(path)):
                self.click_star(table, row, 3, double=True)
            self.assertEqual(started, [], "a double-click on ★ played the title")
            self.assertEqual(opened_files, [], "a double-click on ★ opened the file")
            self.assertEqual(len(op.opened), opened, f"a star click asked: {op.opened[opened:]}")
            self.assertEqual(path.read_bytes(), before, "a star click wrote into the MP3")
            stars = entry.rating or 0

            self.key(Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier
                     | Qt.KeyboardModifier.ShiftModifier)
            self.restart()
            table = self.win._deckset.table
            self.assertEqual(self.entry_at(row).rating or 0, stars, "the rating was lost on restart")
            # The sandbox's load_settings forgets the saved column ticks.
            self.show_column(op, "★  Rating")
            if stars:                     # leave the shared DB as it was
                self.click_star(table, row, stars)
            self.assertFalse(self.entry_at(row).rating)

    def test_custom_typed_in_the_editor_shows_in_its_column_until_reset(self):
        def type_custom(dlg):
            self.type_into(dlg._custom, "warm-up")
            if dlg.isVisible():
                self.save(dlg)

        def reset(dlg):
            self.click(dlg._reset_btn)

        with self.clicking() as op:
            self.generate(rounds="1")
            table = self.win._deckset.table
            self.assertTrue(table.isColumnHidden(_COL_CUSTOM), "Custom shown before it was asked for")
            self.show_column(op, "Custom")
            row = self.song_rows()[0]
            path = Path(self.entry_at(row).path)
            before = path.read_bytes()
            self.edit_tags(op, row, type_custom)
            self.assertEqual(table.item(row, _COL_CUSTOM).text(), "warm-up")
            self.assertEqual(path.read_bytes(), before, "an unmapped Custom wrote into the MP3")

            # ↺ Back to the file's tags forgets it again.
            self.edit_tags(op, row, reset)
            self.assertEqual(table.item(row, _COL_CUSTOM).text(), "")
            self.assertIsNone(self.entry_at(row).custom or None)

    def test_fill_custom_from_an_extended_tag_maps_the_column(self):
        from planner import custom_field
        self.addCleanup(custom_field.set_source, None)
        seen = {}

        def fill(dlg):
            dlg._tabs.setCurrentIndex(1)
            op.pick("🏷  Fill Custom from this tag")
            op._context_menu(dlg._raw, self.cell_pos(
                dlg._raw, self.raw_row(dlg, "ultramixer_last_played"), _RAW_VALUE), "")
            QTest.qWait(5)
            seen["custom"] = dlg._custom.text()
            dlg.reject()

        with self.clicking() as op:
            self.generate(rounds="1")
            table = self.win._deckset.table
            self.show_column(op, "Custom")
            row, other = self.song_rows()[:2]
            self.tag_file(Path(self.entry_at(row).path), "Tagged",
                          ultramixer_last_played="2026-05-01")
            self.edit_tags(op, row, fill)
            self.assertEqual(seen["custom"], "2026-05-01", "the editor's Custom stayed empty")
            self.assertEqual(custom_field.source(), ("TXXX", "ultramixer_last_played"))
            self.assertTrue(self.wait_until(
                lambda: table.item(row, _COL_CUSTOM).text() == "2026-05-01"),
                f"the column reads {table.item(row, _COL_CUSTOM).text()!r}")
            self.assertEqual(table.item(other, _COL_CUSTOM).text(), "")

    def test_map_custom_from_the_header_reads_the_tag_and_back(self):
        from planner import custom_field
        from gui.tag_edit_dialog import CustomSourceDialog
        self.addCleanup(custom_field.set_source, None)
        seen = {}

        def map_to(dlg):
            dlg._frame.setCurrentIndex(dlg._frame.findData("TXXX"))
            seen["offered"] = [dlg._desc.itemText(i) for i in range(dlg._desc.count())]
            dlg._desc.setEditText("ultramixer_last_played")
            seen["sampled"] = dlg._seen.text()
            self.click(dlg._ok)

        def app_only(dlg):
            dlg._frame.setCurrentIndex(dlg._frame.findData(None))
            self.click(dlg._ok)

        def map_custom(op, act):
            op.pick("Map Custom to an MP3 tag")
            op.answer(lambda w: isinstance(w, CustomSourceDialog), act)
            op._context_menu(table.horizontalHeader(), QPoint(30, 5), "")
            QTest.qWait(5)
            self.assertTrue(self.wait_until(lambda: not op.script), op.script)

        with self.clicking() as op:
            self.generate(rounds="1")
            table = self.win._deckset.table
            self.show_column(op, "Custom")
            row = self.song_rows()[0]
            self.tag_file(Path(self.entry_at(row).path), "Tagged",
                          ultramixer_last_played="2026-05-01")
            map_custom(op, map_to)
            self.assertIn("ultramixer_last_played", seen["offered"])
            self.assertIn("2026-05-01", seen["sampled"])
            self.assertTrue(self.wait_until(
                lambda: table.item(row, _COL_CUSTOM).text() == "2026-05-01"),
                f"the column reads {table.item(row, _COL_CUSTOM).text()!r}")

            map_custom(op, app_only)
            self.assertIsNone(custom_field.source())
            self.assertTrue(self.wait_until(lambda: table.item(row, _COL_CUSTOM).text() == ""),
                            "the column kept the tag's value")


if __name__ == "__main__":
    unittest.main()
