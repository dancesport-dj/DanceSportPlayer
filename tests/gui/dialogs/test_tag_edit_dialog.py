"""🏷 The tag editor dialog: what each track becomes.

Run:  py -m unittest tests.gui.dialogs.test_tag_edit_dialog -v

The dialog edits one track or a whole selection. With several, a field they
disagree on is kept per track until it is changed, and a change reaches each
track on its own terms: ticking B adds B to every track's own classes.
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tagdlg_"))

from unittest import mock

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from gui.dialogs.tag_edit_dialog import (
    CLASSES,
    TagEditDialog,
    marker_suggestions,
    parse_markers,
    with_filename_title,
)
from gui.table import table_menu
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget

_C = Qt.CheckState


def _e(name="x", **kw) -> MusicEntry:
    return MusicEntry(path=Path(rf"C:\m\{name}.mp3"), title=name, dance="LW", **kw)


class _DlgTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def dialog(self, *entries, suggestions=()):
        dlg = TagEditDialog(list(entries), suggestions)
        self.addCleanup(reap_widget, dlg)
        return dlg


class OneTrackTest(_DlgTest):

    def test_it_opens_on_the_tracks_own_tags(self):
        dlg = self.dialog(_e(rating=3, classes_ok=["B", "A", "S"],
                             is_instrumental=True, comment_tags=["classic", "remix"]))
        self.assertEqual(dlg._stars.currentData(), 3)
        self.assertEqual([c for c, b in dlg._cls.items() if b.checkState() == _C.Checked],
                         ["B", "A", "S"])
        self.assertEqual(dlg._instr.checkState(), _C.Checked)
        self.assertEqual(dlg._markers.text(), "classic, remix")

    def test_nothing_changed_changes_nothing(self):
        e = _e(rating=3, classes_ok=["S"], comment_tags=["classic"])
        self.assertEqual(self.dialog(e).changes_for(e), {})

    def test_only_what_was_changed_is_returned(self):
        e = _e(rating=3, classes_ok=["S"])
        dlg = self.dialog(e)
        dlg._stars.setCurrentIndex(dlg._stars.findData(5))
        self.assertEqual(dlg.changes_for(e), {"rating": 5})

    def test_classes_are_written_in_class_order(self):
        e = _e(classes_ok=["S"])
        dlg = self.dialog(e)
        dlg._cls["B"].setCheckState(_C.Checked)
        dlg._cls["A"].setCheckState(_C.Checked)
        self.assertEqual(dlg.changes_for(e), {"classes_ok": ["B", "A", "S"]})

    def test_unticking_every_class_means_every_class(self):
        e = _e(classes_ok=["S"])
        dlg = self.dialog(e)
        dlg._cls["S"].setCheckState(_C.Unchecked)
        self.assertEqual(dlg.changes_for(e), {"classes_ok": []})

    def test_the_instrumental_flag(self):
        e = _e()
        dlg = self.dialog(e)
        dlg._instr.setCheckState(_C.Checked)
        self.assertEqual(dlg.changes_for(e), {"is_instrumental": True})

    def test_a_suggestion_click_adds_the_marker_and_a_second_takes_it_out(self):
        e = _e(comment_tags=["classic"])
        dlg = self.dialog(e, suggestions=["remix"])
        dlg.toggle_marker("remix")
        self.assertEqual(dlg.changes_for(e), {"comment_tags": ["classic", "remix"]})
        dlg.toggle_marker("remix")
        self.assertEqual(dlg.changes_for(e), {})

    def test_a_suggestion_shows_whether_the_marker_is_set(self):
        dlg = self.dialog(_e(comment_tags=["classic"]), suggestions=["classic", "remix"])
        self.assertEqual({m: b.isChecked() for m, b in dlg._chips.items()},
                         {"classic": True, "remix": False})
        dlg._markers.setText("remix")
        self.assertEqual({m: b.isChecked() for m, b in dlg._chips.items()},
                         {"classic": False, "remix": True})

    def test_typed_markers_are_read_like_the_files(self):
        self.assertEqual(parse_markers("Classic, vocal_f;  remix,classic,"),
                         ["classic", "vocal_f", "remix"])

    def test_reset_is_offered_only_when_there_is_an_edit(self):
        plain = _e()
        self.assertFalse(self.dialog(plain)._reset_btn.isEnabled())
        edited = _e(tag_edits={"rating": None})
        dlg = self.dialog(edited)
        self.assertTrue(dlg._reset_btn.isEnabled())
        dlg._reset_btn.click()
        self.assertTrue(dlg.reset_requested)
        self.assertEqual(dlg.result(), dlg.DialogCode.Accepted)


class SeveralTracksTest(_DlgTest):

    def setUp(self):
        self.a = _e("a", rating=2, classes_ok=["C", "B"], comment_tags=["classic"])
        self.b = _e("b", rating=4, classes_ok=["B", "A"], is_instrumental=True)
        self.dlg = self.dialog(self.a, self.b)

    def test_fields_they_differ_in_start_as_keep(self):
        self.assertEqual(self.dlg._stars.currentData(), -1)
        self.assertEqual(self.dlg._cls["B"].checkState(), _C.Checked)
        self.assertEqual(self.dlg._cls["C"].checkState(), _C.PartiallyChecked)
        self.assertEqual(self.dlg._cls["S"].checkState(), _C.Unchecked)
        self.assertEqual(self.dlg._instr.checkState(), _C.PartiallyChecked)
        self.assertEqual(self.dlg._markers.text(), "")

    def test_untouched_keeps_every_track_as_it_is(self):
        self.assertEqual(self.dlg.changes_for(self.a), {})
        self.assertEqual(self.dlg.changes_for(self.b), {})

    def test_a_ticked_class_joins_each_tracks_own(self):
        self.dlg._cls["S"].setCheckState(_C.Checked)
        self.assertEqual(self.dlg.changes_for(self.a), {"classes_ok": ["C", "B", "S"]})
        self.assertEqual(self.dlg.changes_for(self.b), {"classes_ok": ["B", "A", "S"]})

    def test_a_class_they_all_had_can_go(self):
        self.dlg._cls["B"].setCheckState(_C.Unchecked)
        self.assertEqual(self.dlg.changes_for(self.a), {"classes_ok": ["C"]})
        self.assertEqual(self.dlg.changes_for(self.b), {"classes_ok": ["A"]})

    def test_one_rating_for_all(self):
        self.dlg._stars.setCurrentIndex(self.dlg._stars.findData(5))
        self.assertEqual(self.dlg.changes_for(self.a), {"rating": 5})
        self.assertEqual(self.dlg.changes_for(self.b), {"rating": 5})

    def test_typed_markers_replace_them_all(self):
        self.dlg._markers.setText("remix")
        self.assertEqual(self.dlg.changes_for(self.a), {"comment_tags": ["remix"]})
        self.assertEqual(self.dlg.changes_for(self.b), {"comment_tags": ["remix"]})


class RawTabTest(_DlgTest):
    """The second tab: every ID3 frame of one MP3, written into the file."""

    def setUp(self):
        from mutagen.id3 import APIC, COMM, ID3, TIT2, TXXX
        d = Path(tempfile.mkdtemp(prefix="dp_tagdlg_raw_"))
        self.path = d / "Cha (CC 30).mp3"
        self.path.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 2000)
        tags = ID3()
        for f in (TIT2(encoding=1, text="Cha"),
                  TXXX(encoding=1, desc="ultramixer_meter", text="4/4"),
                  COMM(encoding=1, lang="eng", desc="", text="classic"),
                  APIC(encoding=0, mime="image/jpeg", type=3, desc="cover", data=b"x" * 10)):
            tags.add(f)
        tags.update_to_v23()
        tags.save(self.path, v2_version=3)
        self.entry = MusicEntry(path=self.path, title="Cha", dance="CC")

    def row(self, dlg, key) -> int:
        return next(r for r in range(dlg._raw.rowCount())
                    if dlg._raw.item(r, 0).data(Qt.ItemDataRole.UserRole) == key)

    def test_one_mp3_gets_the_tab_with_every_frame(self):
        dlg = self.dialog(self.entry)
        self.assertTrue(dlg._tabs.isTabEnabled(1))
        self.assertEqual(dlg._raw.rowCount(), 4)
        r = self.row(dlg, "TXXX:ultramixer_meter")
        self.assertEqual(dlg._raw.item(r, 1).text(), "ultramixer_meter")
        self.assertEqual(dlg._raw.item(r, 2).text(), "4/4")

    def test_only_the_value_of_a_text_frame_is_editable(self):
        dlg = self.dialog(self.entry)
        editable = Qt.ItemFlag.ItemIsEditable
        r = self.row(dlg, "TXXX:ultramixer_meter")
        self.assertTrue(dlg._raw.item(r, 2).flags() & editable)
        self.assertFalse(dlg._raw.item(r, 0).flags() & editable)
        self.assertFalse(dlg._raw.item(self.row(dlg, "APIC:cover"), 2).flags() & editable)
        # The description opens as text to copy, but takes nothing typed.
        editor = self.open_editor(dlg, r, 1)
        self.assertTrue(editor.isReadOnly())
        editor.setText("changed")
        dlg._raw.itemDelegateForColumn(1).setModelData(
            editor, dlg._raw.model(), dlg._raw.model().index(r, 1))
        self.assertEqual(dlg._raw.item(r, 1).text(), "ultramixer_meter")

    def open_editor(self, dlg, r, c):
        from PySide6.QtWidgets import QLineEdit
        dlg._raw.editItem(dlg._raw.item(r, c))
        editor = dlg._raw.viewport().findChild(QLineEdit)
        self.assertIsNotNone(editor, "a double-click opened no text field")
        return editor

    def test_a_description_can_be_marked_and_copied(self):
        dlg = self.dialog(self.entry)
        editor = self.open_editor(dlg, self.row(dlg, "TXXX:ultramixer_meter"), 1)
        self.assertEqual(editor.text(), "ultramixer_meter")

    def test_the_right_click_menu_copies_the_cell(self):
        dlg = self.dialog(self.entry)
        menu = dlg._raw_menu(self.row(dlg, "TXXX:ultramixer_meter"), 1)
        self.addCleanup(menu.deleteLater)
        copy = next(a for a in menu.actions() if a.text() == "📋  Copy")
        copy.trigger()
        self.assertEqual(QApplication.clipboard().text(), "ultramixer_meter")

    def test_a_new_rows_description_is_still_typed(self):
        dlg = self.dialog(self.entry)
        dlg._raw_add_btn.click()
        r = dlg._raw.rowCount() - 1
        self.assertFalse(self.open_editor(dlg, r, 1).isReadOnly())

    def test_no_file_has_it_switched_off(self):
        for entries in ([_e("gone")], [_e("gone"), _e("lost")]):
            dlg = self.dialog(*entries)
            self.assertFalse(dlg._tabs.isTabEnabled(1))
            self.assertTrue(dlg._tabs.tabToolTip(1))
            self.assertIsNone(dlg.raw_edits(entries[0]))

    def test_untouched_writes_nothing(self):
        self.assertIsNone(self.dialog(self.entry).raw_edits())

    def test_an_edited_value(self):
        dlg = self.dialog(self.entry)
        dlg._raw.item(self.row(dlg, "TXXX:ultramixer_meter"), 2).setText("3/4")
        self.assertEqual(dlg.raw_edits(), {"sets": {"TXXX:ultramixer_meter": "3/4"},
                                           "deletes": [], "adds": []})

    def test_remove_selected(self):
        dlg = self.dialog(self.entry)
        dlg._raw.selectRow(self.row(dlg, "APIC:cover"))
        dlg._raw_remove_btn.click()
        self.assertEqual(dlg._raw.rowCount(), 3)
        self.assertEqual(dlg.raw_edits(), {"sets": {}, "deletes": ["APIC:cover"], "adds": []})

    def test_add_a_custom_field(self):
        dlg = self.dialog(self.entry)
        dlg._raw_add_btn.click()
        r = dlg._raw.rowCount() - 1
        combo = dlg._raw.cellWidget(r, 0)
        self.assertEqual(combo.currentData(), "TXXX")
        self.assertEqual(combo.findData("TIT2"), -1, "TIT2 is already there")
        dlg._raw.item(r, 1).setText("my_note")
        dlg._raw.item(r, 2).setText("slow intro")
        self.assertEqual(dlg.raw_edits(), {"sets": {}, "deletes": [],
                                           "adds": [("TXXX", "my_note", "slow intro")]})

    def test_a_standard_frame_has_no_description(self):
        dlg = self.dialog(self.entry)
        dlg._raw_add_btn.click()
        r = dlg._raw.rowCount() - 1
        dlg._raw.item(r, 1).setText("typed first")
        combo = dlg._raw.cellWidget(r, 0)
        combo.setCurrentIndex(combo.findData("TBPM"))
        self.assertFalse(dlg._raw.item(r, 1).flags() & Qt.ItemFlag.ItemIsEditable)
        dlg._raw.item(r, 2).setText("30")
        self.assertEqual(dlg.raw_edits()["adds"], [("TBPM", "", "30")])

    def test_the_forms_fields_are_left_to_the_form(self):
        """Title and the plain comment are the form's: shown here, read-only,
        as the form has them; not offered by ➕, not removed by ➖."""
        dlg = self.dialog(self.entry)
        editable = Qt.ItemFlag.ItemIsEditable
        for key in ("TIT2", "COMM::eng"):
            self.assertFalse(dlg._raw.item(self.row(dlg, key), 2).flags() & editable)
        dlg._form["title"].setEditText("Cha Cha")
        self.assertEqual(dlg._raw.item(self.row(dlg, "TIT2"), 2).text(), "Cha Cha")
        self.assertIsNone(dlg.raw_edits())
        dlg._raw.selectRow(self.row(dlg, "TIT2"))
        dlg._raw_remove_btn.click()
        self.assertEqual(dlg._raw.rowCount(), 4)
        dlg._raw_add_btn.click()
        combo = dlg._raw.cellWidget(dlg._raw.rowCount() - 1, 0)
        for fid in ("TALB", "TYER", "TPOS", "TCON"):
            self.assertEqual(combo.findData(fid), -1, fid)


    def test_an_added_row_left_empty_or_removed_again_is_dropped(self):
        dlg = self.dialog(self.entry)
        dlg._raw_add_btn.click()
        self.assertIsNone(dlg.raw_edits())
        dlg._raw_add_btn.click()
        r = dlg._raw.rowCount() - 1
        dlg._raw.item(r, 2).setText("x")
        dlg._raw.selectRow(r)
        dlg._raw_remove_btn.click()
        self.assertIsNone(dlg.raw_edits())


class SeveralRawTest(_DlgTest):
    """Marcel: the Extended tab for a whole selection. It lists every frame
    any of the MP3s has; a value they share shows, one they differ in (or
    that some lack) is "< keep >". Only what is changed reaches the files,
    each on its own terms."""

    def setUp(self):
        from mutagen.id3 import COMM, ID3, TIT2, TXXX
        d = Path(tempfile.mkdtemp(prefix="dp_tagdlg_raws_"))
        frames = {
            "a": (TIT2(encoding=1, text="Cha"),
                  TXXX(encoding=1, desc="ultramixer_meter", text="4/4"),
                  TXXX(encoding=1, desc="um_dance", text="CC"),
                  COMM(encoding=1, lang="eng", desc="", text="classic")),
            "b": (TIT2(encoding=1, text="Rumba"),
                  TXXX(encoding=1, desc="ultramixer_meter", text="4/4"),
                  TXXX(encoding=1, desc="um_dance", text="RB"),
                  TXXX(encoding=1, desc="only_b", text="x")),
        }
        self.entries = []
        for name, fs in frames.items():
            path = d / f"{name}.mp3"
            path.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 2000)
            tags = ID3()
            for f in fs:
                tags.add(f)
            tags.update_to_v23()
            tags.save(path, v2_version=3)
            self.entries.append(MusicEntry(path=path, title=name, dance="CC"))
        self.a, self.b = self.entries

    def row(self, dlg, key) -> int:
        return next(r for r in range(dlg._raw.rowCount())
                    if dlg._raw.item(r, 0).data(Qt.ItemDataRole.UserRole) == key)

    def value(self, dlg, key) -> str:
        return dlg._raw.item(self.row(dlg, key), 2).text()

    def test_every_frame_of_the_selection_is_listed(self):
        dlg = self.dialog(self.a, self.b)
        self.assertTrue(dlg._tabs.isTabEnabled(1))
        keys = {dlg._raw.item(r, 0).data(Qt.ItemDataRole.UserRole)
                for r in range(dlg._raw.rowCount())}
        self.assertEqual(keys, {"TIT2", "TXXX:ultramixer_meter", "TXXX:um_dance",
                                "TXXX:only_b", "COMM::eng"})
        self.assertEqual(self.value(dlg, "TXXX:ultramixer_meter"), "4/4")
        self.assertEqual(self.value(dlg, "TXXX:um_dance"), "< keep >")
        self.assertEqual(self.value(dlg, "TXXX:only_b"), "< keep >")

    def test_untouched_writes_nothing(self):
        dlg = self.dialog(self.a, self.b)
        self.assertIsNone(dlg.raw_edits(self.a))
        self.assertIsNone(dlg.raw_edits(self.b))

    def test_a_typed_value_reaches_each_file(self):
        dlg = self.dialog(self.a, self.b)
        dlg._raw.item(self.row(dlg, "TXXX:um_dance"), 2).setText("CC")
        dlg._raw.item(self.row(dlg, "TXXX:only_b"), 2).setText("y")
        # a has um_dance "CC" already: nothing to write there; it lacks only_b.
        self.assertEqual(dlg.raw_edits(self.a), {
            "sets": {}, "deletes": [], "adds": [("TXXX", "only_b", "y")]})
        self.assertEqual(dlg.raw_edits(self.b), {
            "sets": {"TXXX:um_dance": "CC", "TXXX:only_b": "y"},
            "deletes": [], "adds": []})

    def test_remove_drops_it_where_it_is(self):
        dlg = self.dialog(self.a, self.b)
        dlg._raw.selectRow(self.row(dlg, "TXXX:only_b"))
        dlg._raw_remove_btn.click()
        self.assertIsNone(dlg.raw_edits(self.a))
        self.assertEqual(dlg.raw_edits(self.b),
                         {"sets": {}, "deletes": ["TXXX:only_b"], "adds": []})

    def test_an_added_field_goes_into_each(self):
        dlg = self.dialog(self.a, self.b)
        dlg._raw_add_btn.click()
        r = dlg._raw.rowCount() - 1
        dlg._raw.item(r, 1).setText("only_b")
        dlg._raw.item(r, 2).setText("z")
        # b has that frame already: it gets the value instead of a second one.
        self.assertEqual(dlg.raw_edits(self.a), {
            "sets": {}, "deletes": [], "adds": [("TXXX", "only_b", "z")]})
        self.assertEqual(dlg.raw_edits(self.b), {
            "sets": {"TXXX:only_b": "z"}, "deletes": [], "adds": []})

    def test_the_forms_frames_are_left_to_the_form(self):
        dlg = self.dialog(self.a, self.b)
        editable = Qt.ItemFlag.ItemIsEditable
        for key in ("TIT2", "COMM::eng"):
            self.assertFalse(dlg._raw.item(self.row(dlg, key), 2).flags() & editable)
        dlg._form["title"].setEditText("Same")
        self.assertIsNone(dlg.raw_edits(self.a))

    def test_a_track_without_an_mp3_gets_nothing(self):
        gone = _e("gone")
        dlg = self.dialog(self.a, gone)
        self.assertTrue(dlg._tabs.isTabEnabled(1))
        dlg._raw.item(self.row(dlg, "TXXX:um_dance"), 2).setText("SA")
        self.assertIsNone(dlg.raw_edits(gone))
        self.assertEqual(dlg.raw_edits(self.a)["sets"], {"TXXX:um_dance": "SA"})


def _png() -> bytes:
    from PySide6.QtCore import QBuffer, QIODevice
    from PySide6.QtGui import QColor, QImage
    img = QImage(4, 4, QImage.Format.Format_RGB32)
    img.fill(QColor("red"))
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


class FormTest(_DlgTest):
    """The Mp3tag-style form: the MP3's own fields, for one track or many."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_tagdlg_form_"))

    def mp3(self, name, *frames) -> MusicEntry:
        from mutagen.id3 import ID3
        path = self.dir / f"{name}.mp3"
        path.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 2000)
        tags = ID3()
        for f in frames:
            tags.add(f)
        tags.update_to_v23()
        tags.save(path, v2_version=3)
        return MusicEntry(path=path, title=name, dance="CC")

    def two(self):
        from mutagen.id3 import TIT2, TPE1
        return (self.mp3("a", TIT2(encoding=1, text="Cha A"), TPE1(encoding=1, text="Band")),
                self.mp3("b", TIT2(encoding=1, text="Cha B"), TPE1(encoding=1, text="Band")))

    def test_one_track_shows_its_fields_and_cover(self):
        from mutagen.id3 import APIC, COMM, TIT2, TYER
        e = self.mp3("a", TIT2(encoding=1, text="Cha"), TYER(encoding=0, text="2019"),
                     COMM(encoding=1, lang="eng", desc="", text="classic"),
                     APIC(encoding=0, mime="image/png", type=3, desc="", data=_png()))
        dlg = self.dialog(e)
        self.assertEqual(dlg._form["title"].currentText(), "Cha")
        self.assertEqual(dlg._form["year"].currentText(), "2019")
        self.assertEqual(dlg._form["comment"].currentText(), "classic")
        self.assertEqual(dlg._form["album"].currentText(), "")
        self.assertFalse(dlg._cover.pixmap().isNull())
        self.assertEqual(dlg.form_changes(), {})

    def test_typed_and_blanked(self):
        from mutagen.id3 import COMM, TIT2
        e = self.mp3("a", TIT2(encoding=1, text="Cha"),
                     COMM(encoding=1, lang="eng", desc="", text="classic"))
        dlg = self.dialog(e)
        dlg._form["title"].setEditText("Cha Cha")
        dlg._form["album"].setEditText("Latin")
        combo = dlg._form["comment"]
        combo.setCurrentIndex(combo.findText("< blank >"))
        self.assertEqual(dlg.form_changes(),
                         {"title": "Cha Cha", "album": "Latin", "comment": ""})

    def test_several_tracks_keep_what_they_differ_in(self):
        a, b = self.two()
        dlg = self.dialog(a, b)
        self.assertEqual(dlg._form["title"].currentText(), "< keep >")
        self.assertEqual(dlg._form["artist"].currentText(), "Band")
        self.assertEqual(dlg.form_changes(), {})
        dlg._form["title"].setEditText("Cha")
        dlg._form["artist"].setEditText("Other")
        self.assertEqual(dlg.form_changes(), {"title": "Cha", "artist": "Other"})

    def test_the_title_arrow_offers_the_file_name(self):
        """F12: beside blank and keep, "< filename >" — each track's own."""
        a, b = self.two()
        dlg = self.dialog(a, b)
        combo = dlg._form["title"]
        combo.setCurrentIndex(combo.findText("< filename >"))
        changes = dlg.form_changes()
        self.assertEqual(with_filename_title(changes, a.path), {"title": "a"})
        self.assertEqual(with_filename_title(changes, b.path), {"title": "b"})
        self.assertLess(dlg._form["artist"].findText("< filename >"), 0)
        self.assertEqual(combo.currentText(), "< filename >")   # one each

    def test_for_one_track_the_file_name_itself_is_shown(self):
        """Marcel: picking "< filename >" for one track shows its name."""
        a, _b = self.two()
        dlg = self.dialog(a)
        combo = dlg._form["title"]
        combo.setCurrentIndex(combo.findText("< filename >"))
        self.assertEqual(combo.currentText(), "a")
        self.assertEqual(dlg.form_changes(), {"title": "a"})

    def test_a_differing_field_offers_its_values(self):
        a, b = self.two()
        combo = self.dialog(a, b)._form["title"]
        self.assertGreaterEqual(combo.findText("Cha A"), 0)
        combo.setCurrentIndex(combo.findText("Cha B"))
        self.assertEqual(combo.currentText(), "Cha B")

    def test_unreadable_tags_have_the_form_switched_off(self):
        a, _b = self.two()
        with mock.patch("gui.dialogs.tag_edit_dialog.id3_frames.read_form",
                        side_effect=OSError("locked")):
            dlg = self.dialog(a)
        self.assertFalse(dlg._file_box.isEnabled())
        self.assertIn("locked", dlg._file_box.toolTip())
        self.assertEqual(dlg.form_changes(), {})

    def test_only_the_mp3s_of_a_mixed_selection(self):
        a, _b = self.two()
        dlg = self.dialog(a, _e("gone"))
        self.assertTrue(dlg._file_box.isEnabled())
        self.assertEqual(dlg._form["title"].currentText(), "Cha A")
        self.assertEqual(dlg.form_mp3s(), [a])


class NoMp3Test(_DlgTest):
    """Marcel: "for the non mp3 one show the db part in the dialog". A FLAC,
    an M4A … has no MP3 form to write into, so the app's own title, artist …
    stand in its place, kept in the DB like the stars."""

    def flac(self, name="x", **kw) -> MusicEntry:
        return MusicEntry(path=Path(rf"C:\m\{name}.flac"), title=name, dance="LW", **kw)

    def test_it_shows_the_apps_values_instead_of_the_mp3_form(self):
        dlg = self.dialog(self.flac(tag_artist="Band", year=2001))
        self.assertEqual(dlg._db["title"].currentText(), "x")
        self.assertEqual(dlg._db["tag_artist"].currentText(), "Band")
        self.assertEqual(dlg._db["year"].currentText(), "2001")
        self.assertEqual(dlg._db["genre"].currentText(), "LW")
        self.assertFalse(hasattr(dlg, "_file_box"))
        self.assertEqual(dlg.form_changes(), {})
        self.assertFalse(dlg._write_app.isEnabled())

    def test_untouched_changes_nothing(self):
        e = self.flac(tag_artist="Band")
        self.assertEqual(self.dialog(e).changes_for(e), {})

    def test_the_file_name_as_title(self):
        a, b = self.flac("a"), self.flac("b")
        dlg = self.dialog(a, b)
        combo = dlg._db["title"]
        combo.setCurrentIndex(combo.findText("< filename >"))
        self.assertEqual(dlg.changes_for(a), {"title": "a"})
        self.assertEqual(dlg.changes_for(b), {"title": "b"})
        self.assertEqual(combo.currentText(), "< filename >")

    def test_for_one_track_the_db_title_shows_the_file_name(self):
        e = MusicEntry(path=Path(r"C:\m\Tango 31 (LT).flac"), title="Old", dance="LW")
        dlg = self.dialog(e)
        combo = dlg._db["title"]
        combo.setCurrentIndex(combo.findText("< filename >"))
        self.assertEqual(combo.currentText(), "Tango 31 (LT)")
        self.assertEqual(dlg.changes_for(e), {"title": "Tango 31 (LT)"})

    def test_typed_values_are_returned(self):
        e = self.flac(tag_artist="Band", year=2001)
        dlg = self.dialog(e)
        dlg._db["title"].setEditText("New Title")
        dlg._db["tag_artist"].setEditText("New Band")
        dlg._db["genre"].setEditText("Slowfox")
        dlg._db["year"].setEditText(dlg._blank)
        dlg._stars.setCurrentIndex(dlg._stars.findData(4))
        self.assertEqual(dlg.changes_for(e),
                         {"title": "New Title", "tag_artist": "New Band",
                          "genre": "Slowfox", "year": 0, "rating": 4})

    def test_several_tracks_differing_start_as_keep(self):
        a, b = self.flac("a", tag_artist="A"), self.flac("b", tag_artist="B")
        dlg = self.dialog(a, b)
        self.assertEqual(dlg._db["tag_artist"].currentText(), dlg._keep)
        self.assertEqual(dlg._db["genre"].currentText(), "LW")
        self.assertEqual(dlg.changes_for(a), {})

    mp3 = FormTest.mp3
    two = FormTest.two

    def test_an_mp3_on_disk_keeps_the_form(self):
        FormTest.setUp(self)
        a, _b = self.two()
        dlg = self.dialog(a)
        self.assertEqual(dlg._db, {})
        self.assertTrue(dlg._file_box.isEnabled())

    def test_a_double_click_lands_on_the_columns_field(self):
        dlg = TagEditDialog([self.flac(tag_artist="Band")], focus="artist")
        self.addCleanup(reap_widget, dlg)
        combo = dlg._db["tag_artist"]
        self.assertIs(dlg._focused, combo)
        self.assertIn(dlg.focusWidget(), (combo, combo.lineEdit()))

    def test_its_text_is_translated(self):
        from planner.i18n.lang_de import CATALOG
        dlg = self.dialog(self.flac())
        for text in (dlg._db_box.title(), dlg._db_box.toolTip()):
            with self.subTest(text=text):
                self.assertIn(text, CATALOG)


class CustomFieldTest(_DlgTest):
    """The free Custom field in the "In the app" box, and the frame it is
    mapped to on the Extended tab."""

    UM = ("TXXX", "ultramixer_last_played")
    setUp = FormTest.setUp
    mp3 = FormTest.mp3

    def custom_dialog(self, *entries, source=None):
        dlg = TagEditDialog(list(entries), custom_source=source)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_it_shows_the_tracks_value(self):
        e = _e(custom="-1")
        self.assertEqual(self.custom_dialog(e)._custom.text(), "-1")

    def test_typing_changes_it(self):
        e = _e(custom="-1")
        dlg = self.custom_dialog(e)
        dlg._custom.setText("Gala")
        self.assertEqual(dlg.changes_for(e), {"custom": "Gala"})

    def test_emptying_it_is_a_change(self):
        e = _e(custom="-1")
        dlg = self.custom_dialog(e)
        dlg._custom.setText("")
        self.assertEqual(dlg.changes_for(e), {"custom": ""})

    def test_tracks_that_differ_keep_theirs_until_typed(self):
        a, b = _e("a", custom="1"), _e("b", custom="2")
        dlg = self.custom_dialog(a, b)
        self.assertEqual(dlg._custom.text(), "")
        self.assertIn("differs", dlg._custom.placeholderText())
        self.assertEqual(dlg.changes_for(a), {})
        dlg._custom.setText("Gala")
        self.assertEqual(dlg.changes_for(b), {"custom": "Gala"})

    def test_the_tooltip_names_the_mapped_tag(self):
        self.assertIn("ultramixer_last_played",
                      self.custom_dialog(_e(), source=self.UM)._custom.toolTip())
        self.assertIn("app only", self.custom_dialog(_e())._custom.toolTip())

    def _with_um(self):
        from mutagen.id3 import TIT2, TXXX
        return self.mp3("u", TIT2(encoding=1, text="Cha"),
                        TXXX(encoding=1, desc="ultramixer_last_played", text="-1"),
                        TXXX(encoding=1, desc="ultramixer_meter", text="4/4"))

    def _raw_row(self, dlg, key) -> int:
        return next(r for r in range(dlg._raw.rowCount())
                    if dlg._raw.item(r, 0).data(Qt.ItemDataRole.UserRole) == key)

    def test_the_mapped_frame_is_read_only_on_the_extended_tab(self):
        dlg = self.custom_dialog(self._with_um(), source=("TXXX", "ULTRAMIXER_last_played"))
        r = self._raw_row(dlg, "TXXX:ultramixer_last_played")
        self.assertFalse(dlg._raw.item(r, 2).flags() & Qt.ItemFlag.ItemIsEditable)
        self.assertIn("Custom", dlg._raw.item(r, 2).toolTip())
        other = self._raw_row(dlg, "TXXX:ultramixer_meter")
        self.assertTrue(dlg._raw.item(other, 2).flags() & Qt.ItemFlag.ItemIsEditable)

    def test_the_mapped_frame_cannot_be_removed_there(self):
        dlg = self.custom_dialog(self._with_um(), source=self.UM)
        dlg._raw.selectRow(self._raw_row(dlg, "TXXX:ultramixer_last_played"))
        dlg._raw_remove()
        self.assertIsNone(dlg.raw_edits())

    def test_without_a_mapping_it_is_an_ordinary_frame(self):
        dlg = self.custom_dialog(self._with_um())
        r = self._raw_row(dlg, "TXXX:ultramixer_last_played")
        self.assertTrue(dlg._raw.item(r, 2).flags() & Qt.ItemFlag.ItemIsEditable)

    # ----- 🏷 Fill Custom from this tag (a right-click on the Extended tab) ---

    def mapping_dialog(self, entry, source=None, answer=True):
        self.mapped = []
        dlg = TagEditDialog([entry], custom_source=source,
                            map_custom=lambda f, d: self.mapped.append((f, d)) or answer)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def fill_action(self, dlg, key):
        menu = dlg._raw_menu(self._raw_row(dlg, key), 2)
        self.addCleanup(menu.deleteLater)
        return next((a for a in menu.actions() if "Fill Custom" in a.text()), None)

    def test_a_row_maps_custom_to_its_frame(self):
        dlg = self.mapping_dialog(self._with_um())
        self.fill_action(dlg, "TXXX:ultramixer_meter").trigger()
        self.assertEqual(self.mapped, [("TXXX", "ultramixer_meter")])
        r = self._raw_row(dlg, "TXXX:ultramixer_meter")
        self.assertFalse(dlg._raw.item(r, 2).flags() & Qt.ItemFlag.ItemIsEditable)
        self.assertEqual(dlg._custom.text(), "4/4")
        self.assertIn("ultramixer_meter", dlg._custom.toolTip())

    def test_a_value_typed_into_the_row_goes_back_to_the_files(self):
        dlg = self.mapping_dialog(self._with_um())
        r = self._raw_row(dlg, "TXXX:ultramixer_meter")
        dlg._raw.item(r, 2).setText("3/4")
        self.fill_action(dlg, "TXXX:ultramixer_meter").trigger()
        self.assertEqual(dlg._raw.item(r, 2).text(), "4/4")
        self.assertEqual(dlg._custom.text(), "4/4")

    def test_the_row_mapped_before_is_editable_again(self):
        dlg = self.mapping_dialog(self._with_um(), source=self.UM)
        self.fill_action(dlg, "TXXX:ultramixer_meter").trigger()
        old = self._raw_row(dlg, "TXXX:ultramixer_last_played")
        self.assertTrue(dlg._raw.item(old, 2).flags() & Qt.ItemFlag.ItemIsEditable)

    def test_a_value_typed_in_the_app_stays(self):
        e = self._with_um()
        e.custom, e.tag_edits = "Gala", {"custom": "Gala"}
        dlg = self.mapping_dialog(e)
        self.fill_action(dlg, "TXXX:ultramixer_meter").trigger()
        self.assertEqual(dlg._custom.text(), "Gala")

    def test_a_refused_mapping_changes_nothing(self):
        dlg = self.mapping_dialog(self._with_um(), answer=False)
        self.fill_action(dlg, "TXXX:ultramixer_meter").trigger()
        r = self._raw_row(dlg, "TXXX:ultramixer_meter")
        self.assertTrue(dlg._raw.item(r, 2).flags() & Qt.ItemFlag.ItemIsEditable)
        self.assertIn("app only", dlg._custom.toolTip())

    def test_frames_that_cannot_fill_it_are_not_offered(self):
        from mutagen.id3 import COMM, TIT2
        e = self.mp3("c", TIT2(encoding=1, text="Cha"),
                     COMM(encoding=1, lang="eng", desc="", text="classic"))
        dlg = self.mapping_dialog(e)
        self.assertFalse(self.fill_action(dlg, "TIT2").isEnabled())
        comm = next(dlg._raw.item(r, 0).data(Qt.ItemDataRole.UserRole)
                    for r in range(dlg._raw.rowCount())
                    if dlg._raw.item(r, 0).data(Qt.ItemDataRole.UserRole).startswith("COMM"))
        self.assertFalse(self.fill_action(dlg, comm).isEnabled())

    def test_without_the_window_it_is_not_offered(self):
        dlg = self.custom_dialog(self._with_um())
        self.assertIsNone(self.fill_action(dlg, "TXXX:ultramixer_meter"))


class CustomSourceDialogTest(_DlgTest):
    """Header right-click → Map Custom to an MP3 tag…"""

    SAMPLES = (40, {("TXXX", "ultramixer_meter"): (12, "4/4"),
                    ("TXXX", "ultramixer_last_played"): (31, "-1"),
                    ("COMM", "Songs-DB_Custom1"): (5, "classic")})

    def source_dialog(self, current=None, samples=(0, {})):
        from gui.dialogs.tag_edit_dialog import CustomSourceDialog
        dlg = CustomSourceDialog(current, samples=samples)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_it_opens_on_app_only(self):
        dlg = self.source_dialog()
        self.assertEqual(dlg.source(), (None, ""))
        self.assertFalse(dlg._desc.isEnabled())

    def test_it_opens_on_the_current_mapping(self):
        dlg = self.source_dialog(("TXXX", "ultramixer_last_played"))
        self.assertEqual(dlg.source(), ("TXXX", "ultramixer_last_played"))
        self.assertIn("(TXXX)", dlg._frame.currentText())

    def test_a_custom_text_needs_a_description(self):
        dlg = self.source_dialog()
        dlg._frame.setCurrentIndex(dlg._frame.findData("TXXX"))
        ok = dlg._ok
        self.assertTrue(dlg._desc.isEnabled())
        self.assertFalse(ok.isEnabled())
        dlg._desc.setEditText("  ultramixer_meter ")
        self.assertTrue(ok.isEnabled())
        self.assertEqual(dlg.source(), ("TXXX", "ultramixer_meter"))

    def test_a_standard_frame_has_no_description(self):
        dlg = self.source_dialog(("TXXX", "x"))
        dlg._frame.setCurrentIndex(dlg._frame.findData("TIT1"))
        self.assertFalse(dlg._desc.isEnabled())
        self.assertEqual(dlg.source(), ("TIT1", ""))

    def test_the_forms_own_frames_are_not_offered(self):
        dlg = self.source_dialog()
        offered = [dlg._frame.itemData(i) for i in range(dlg._frame.count())]
        self.assertNotIn("TIT2", offered)
        self.assertIn("COMM", offered)

    def offered(self, dlg):
        return [dlg._desc.itemText(i) for i in range(dlg._desc.count())]

    def test_the_sampled_descriptions_are_offered_most_common_first(self):
        dlg = self.source_dialog(samples=self.SAMPLES)
        dlg._frame.setCurrentIndex(dlg._frame.findData("TXXX"))
        self.assertEqual(self.offered(dlg), ["ultramixer_last_played", "ultramixer_meter"])
        self.assertEqual(dlg._desc.currentText(), "")
        dlg._frame.setCurrentIndex(dlg._frame.findData("COMM"))
        self.assertEqual(self.offered(dlg), ["Songs-DB_Custom1"])

    def test_the_old_tags_comment_needs_no_description_and_is_read_only(self):
        from planner.music.custom_field import V1
        dlg = self.source_dialog(samples=(40, {(V1, ""): (9, "vocal AS")}))
        dlg._frame.setCurrentIndex(dlg._frame.findData(V1))
        self.assertFalse(dlg._desc.isEnabled())
        self.assertTrue(dlg._ok.isEnabled())
        self.assertEqual(dlg.source(), (V1, ""))
        self.assertIn("9 of 40", dlg._seen.text())
        self.assertIn("read only", dlg._seen.text())

    def test_picking_one_shows_how_often_and_a_value(self):
        dlg = self.source_dialog(samples=self.SAMPLES)
        dlg._frame.setCurrentIndex(dlg._frame.findData("TXXX"))
        dlg._desc.setCurrentIndex(dlg._desc.findText("ultramixer_meter"))
        self.assertEqual(dlg.source(), ("TXXX", "ultramixer_meter"))
        self.assertIn("12 of 40", dlg._seen.text())
        self.assertIn("4/4", dlg._seen.text())

    def test_a_typed_description_is_matched_in_any_case(self):
        dlg = self.source_dialog(samples=self.SAMPLES)
        dlg._frame.setCurrentIndex(dlg._frame.findData("TXXX"))
        dlg._desc.setEditText("UltraMixer_Meter")
        self.assertIn("12 of 40", dlg._seen.text())
        dlg._desc.setEditText("nowhere")
        self.assertIn("none of the 40", dlg._seen.text())

    def test_the_current_mapping_stays_chosen(self):
        dlg = self.source_dialog(("TXXX", "ultramixer_meter"), samples=self.SAMPLES)
        self.assertEqual(dlg.source(), ("TXXX", "ultramixer_meter"))
        self.assertIn("12 of 40", dlg._seen.text())

    def test_without_samples_or_for_the_app_nothing_is_said(self):
        self.assertEqual(self.source_dialog(("TXXX", "x"))._seen.text(), "")
        self.assertEqual(self.source_dialog(samples=self.SAMPLES)._seen.text(), "")


SONGS =[MusicEntry(path=Path(rf"C:\music\tanzcds\LW{i}.mp3"),
                    title=f"LW {i}", dance="LW", duration=180)
         for i in (1, 2, 3)]


class DeckMenuTest(_DlgTest):
    """🏷 Edit tags… in a deck row's right-click menu, for the row or the
    selection it was opened in."""

    def _table(self):
        from gui.table.playlist_table import PlaylistTable
        win = QWidget()
        win._settings = {"app_mode": "both"}
        win.edited = []
        win._edit_entry_tags = win.edited.append
        self.addCleanup(reap_widget, win)
        t = PlaylistTable()
        t.setParent(win)
        t.load_warmup(SONGS, "🤸 Party", "both", "S", False, lambda *a: None, None)
        return t, win

    def _menu(self, t, row, choose=None):
        """Action texts of the menu opened on `row`; `choose` picks one."""
        opened = []

        class _Menu(QMenu):
            def exec(self, *_args):
                opened.append([a.text() for a in self.actions()])
                return next((a for a in self.actions() if a.text() == choose), None)

        pos = QPoint(5, t.rowViewportPosition(row) + 2)
        with mock.patch.object(table_menu, "QMenu", _Menu):
            t.contextMenuEvent(QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, pos, t.mapToGlobal(pos)))
        self.assertTrue(opened, "the context menu never opened")
        return opened[0]

    def test_a_row_offers_it_and_edits_that_track(self):
        t, win = self._table()
        row = t._row_meta.song_rows()[1]
        self.assertIn("🏷  Edit tags…", self._menu(t, row))
        self._menu(t, row, choose="🏷  Edit tags…")
        self.assertEqual(win.edited, [[t._row_meta.entry_at(row)]])

    def test_inside_a_selection_it_edits_the_selection(self):
        t, win = self._table()
        rows = t._row_meta.song_rows()
        t.setSelectionMode(t.SelectionMode.MultiSelection)
        for r in rows:
            t.selectRow(r)
        caption = f"🏷  Edit tags of {len(rows)} tracks…"
        self.assertIn(caption, self._menu(t, rows[0]))
        self._menu(t, rows[0], choose=caption)
        self.assertEqual(win.edited, [[t._row_meta.entry_at(r) for r in rows]])


class SuggestionsTest(unittest.TestCase):

    def test_the_most_used_markers_first_and_no_one_off_notes(self):
        entries = ([_e(comment_tags=["classic", "vocal_f"])] * 5
                   + [_e(comment_tags=["vocal_f"])] * 2
                   + [_e(comment_tags=["amazon.com song id: 219253690"])] * 3
                   + [_e(comment_tags=["album\r\ncredit"])] * 3
                   + [_e(comment_tags=["once"])])
        self.assertEqual(marker_suggestions(entries), ["vocal_f", "classic"])


class TagsDialogTest(_DlgTest):
    """Marcel: "merge both dialogs and remove the app only option, rname the
    other to tags. so the user can choose in this new dialog what he wants to
    overwrite". One 🏷 Tags dialog: the MP3's form, the app's fields and the
    Extended tab, and a tick that says whether the app's fields go into the
    MP3 too — once a question after Save."""

    setUp = FormTest.setUp
    mp3 = FormTest.mp3

    def test_it_is_called_tags(self):
        self.assertEqual(self.dialog(_e()).windowTitle(), "🏷  Tags")
        self.assertEqual(self.dialog(_e("a"), _e("b")).windowTitle(),
                         "🏷  Tags of 2 tracks")

    def test_there_is_no_database_mode_any_more(self):
        with self.assertRaises(TypeError):
            TagEditDialog([_e()], mode="db")
        dlg = self.dialog(_e())
        self.assertFalse(hasattr(dlg, "mode"))

    def test_it_holds_the_file_the_app_and_the_extended_tab(self):
        dlg = self.dialog(self.mp3("a"))
        self.assertTrue(dlg._file_box.isEnabled())
        self.assertEqual(dlg._tabs.count(), 2)

    def test_the_app_fields_stay_in_the_app_unless_ticked(self):
        dlg = self.dialog(self.mp3("a"))
        self.assertTrue(dlg._write_app.isEnabled())
        self.assertFalse(dlg.write_app_to_mp3())
        dlg._write_app.setChecked(True)
        self.assertTrue(dlg.write_app_to_mp3())

    def test_the_tick_sits_in_the_app_box(self):
        dlg = self.dialog(self.mp3("a"))
        self.assertTrue(dlg._app_box.isAncestorOf(dlg._write_app))

    def test_without_an_mp3_on_disk_there_is_nothing_to_tick(self):
        dlg = self.dialog(_e("gone"))
        self.assertFalse(dlg._write_app.isEnabled())
        dlg._write_app.setChecked(True)
        self.assertFalse(dlg.write_app_to_mp3())

    def test_the_tick_says_where_custom_goes_only_while_mapped(self):
        tip = self.dialog(self.mp3("a"))._write_app.toolTip()
        self.assertIn("Windows rating", tip)
        self.assertNotIn("Custom", tip)
        dlg = TagEditDialog([self.mp3("b")], custom_source=("TXXX", "x"))
        self.addCleanup(reap_widget, dlg)
        self.assertIn("Custom", dlg._write_app.toolTip())

    def test_its_text_is_translated(self):
        from planner.i18n.lang_de import CATALOG
        dlg = self.dialog(self.mp3("a"))
        # "🏷  Tags" reads the same in German, so it has no entry.
        for text in (dlg._write_app.text(), dlg._write_app.toolTip(),
                     "🏷  Tags of %d tracks"):
            with self.subTest(text=text):
                self.assertIn(text, CATALOG)


class FocusTest(_DlgTest):
    """Marcel: "for the double click in library which opens edit tag: it
    should focus the column where the user double clicked" + "and highlight it
    with an indicator". The list names the field; the dialog gives it the
    focus and frames it."""

    setUp = FormTest.setUp
    mp3 = FormTest.mp3

    def focused(self, entry, field):
        dlg = TagEditDialog([entry], focus=field)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_the_double_clicked_field_has_the_focus(self):
        dlg = self.focused(self.mp3("a"), "artist")
        combo = dlg._form["artist"]
        self.assertIn(dlg.focusWidget(), (combo, combo.lineEdit()))

    def test_it_is_framed_and_nothing_else_is(self):
        dlg = self.focused(self.mp3("a"), "artist")
        self.assertIs(dlg._focused, dlg._form["artist"])
        self.assertIn("highlight", dlg._form["artist"].styleSheet())
        self.assertEqual(dlg._form["title"].styleSheet(), "")

    def test_an_app_field_too(self):
        dlg = self.focused(self.mp3("a"), "custom")
        self.assertIs(dlg.focusWidget(), dlg._custom)
        self.assertIn("highlight", dlg._custom.styleSheet())

    def test_the_classes_row_is_framed_and_its_first_box_focused(self):
        dlg = self.focused(self.mp3("a"), "classes")
        self.assertIs(dlg._focused, dlg._cls_row)
        self.assertIs(dlg.focusWidget(), dlg._cls[CLASSES[0]])

    def test_a_disabled_field_is_framed_but_not_focused(self):
        with mock.patch("gui.dialogs.tag_edit_dialog.id3_frames.read_form",
                        side_effect=OSError("locked")):
            dlg = self.focused(self.mp3("a"), "title")
        self.assertIs(dlg._focused, dlg._form["title"])
        self.assertNotIn(dlg.focusWidget(), (dlg._form["title"], dlg._form["title"].lineEdit()))

    def test_without_a_field_nothing_is_framed(self):
        for field in (None, "bpm"):
            with self.subTest(field=field):
                self.assertIsNone(self.focused(self.mp3("a"), field)._focused)


if __name__ == "__main__":
    unittest.main(verbosity=2)
