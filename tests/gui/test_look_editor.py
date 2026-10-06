#!/usr/bin/env python3
"""🎨 The look editor and the own looks in ⚙ Settings › Look.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_look_editor -v
"""

import dataclasses
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_look_editor_"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402

from gui import dialogs, look_editor  # noqa: E402
from gui.dialogs import SettingsDialog  # noqa: E402
from gui.look_editor import LookEditor, LookPreview, contrast_warnings  # noqa: E402
from planner import i18n  # noqa: E402
from shared import looks, theme, user_looks  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class _Clean(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self._state = tempfile.mkdtemp(prefix="dp_look_editor_")
        self._env = os.environ.get("DANCEPLAYLIST_STATE_DIR")
        os.environ["DANCEPLAYLIST_STATE_DIR"] = self._state
        user_looks.load()
        self.addCleanup(self._restore)

    def _restore(self):
        os.environ["DANCEPLAYLIST_STATE_DIR"] = self._env
        user_looks.load()
        theme.set_active("light")

    def made(self, source="midnight", name="Hall at night"):
        look = user_looks.copy_of(looks.LOOKS[source], name)
        user_looks.put(look)
        return look

    def keep(self, widget):
        self.addCleanup(reap_widget, widget)
        return widget


# ── The editor ──────────────────────────────────────────────────────────────

class ContrastWarningTest(unittest.TestCase):

    def test_text_as_dark_as_its_ground_is_named(self):
        look = looks.LOOKS["paper"]
        bad = dataclasses.replace(look, tokens=dataclasses.replace(
            look.tokens, text=look.tokens.base))
        warnings = contrast_warnings(bad)
        self.assertTrue(any(w.startswith("Text on lists: 1.0 : 1") for w in warnings),
                        warnings)

    def test_the_high_contrast_looks_raise_none(self):
        for key in ("contrast_dark", "contrast_light"):
            with self.subTest(key=key):
                self.assertEqual(contrast_warnings(looks.LOOKS[key]), [])


class LookPreviewTest(_Clean):

    def test_it_takes_every_built_in_look(self):
        preview = self.keep(LookPreview())
        for look in looks.LOOKS.values():
            with self.subTest(look=look.key):
                preview.set_look(look)
                self.assertIn(look.tokens.window, preview.styleSheet())

    def test_every_row_of_the_table_is_shown(self):
        """A look's row padding must not push the last song under a scrollbar."""
        preview = self.keep(LookPreview())
        preview.set_look(looks.LOOKS["console"])
        table = preview._table
        rows = sum(table.rowHeight(r) for r in range(table.rowCount()))
        self.assertGreaterEqual(table.height(),
                                table.horizontalHeader().sizeHint().height() + rows)


class LookEditorTest(_Clean):

    def editor(self, source="paper"):
        return self.keep(LookEditor(user_looks.copy_of(looks.LOOKS[source], "Mine")))

    def test_untouched_it_gives_back_the_look_it_was_handed(self):
        look = user_looks.copy_of(looks.LOOKS["studio"], "Mine")
        self.assertEqual(self.keep(LookEditor(look)).look(), look)

    def test_no_name_no_save(self):
        ed = self.editor()
        ed._name.setText("  ")
        self.assertFalse(ed._save.isEnabled())
        ed._name.setText("Gala")
        self.assertTrue(ed._save.isEnabled())
        self.assertEqual(ed.look().caption, "Gala")

    def test_a_picked_colour_is_kept_and_previewed(self):
        ed = self.editor()
        with mock.patch.object(look_editor.QColorDialog, "getColor",
                               return_value=QColor("#123456")):
            ed._pick("accent")
        self.assertEqual(ed.look().tokens.accent, "#123456")
        self.assertIn("#123456", ed._preview.styleSheet())
        self.assertEqual(ed._swatches["accent"].text(), "#123456")

    def test_a_cancelled_picker_changes_nothing(self):
        ed = self.editor()
        before = ed.look()
        with mock.patch.object(look_editor.QColorDialog, "getColor",
                               return_value=QColor()):
            ed._pick("accent")
        self.assertEqual(ed.look(), before)

    def test_the_fade_switches_a_gradient_on_and_off(self):
        ed = self.editor("paper")
        self.assertEqual(ed.look().tokens.surface_top, "")
        ed._gradients["surface_top"].setChecked(True)
        self.assertTrue(ed.look().tokens.surface_top.startswith("#"))
        ed._gradients["surface_top"].setChecked(False)
        self.assertEqual(ed.look().tokens.surface_top, "")
        self.assertEqual(ed._swatches["surface_top"].text(), "off")

    def test_picking_a_gradient_colour_ticks_its_fade(self):
        ed = self.editor("paper")
        with mock.patch.object(look_editor.QColorDialog, "getColor",
                               return_value=QColor("#eeeeee")):
            ed._pick("header_top")
        self.assertTrue(ed._gradients["header_top"].isChecked())
        self.assertEqual(ed.look().tokens.header_top, "#eeeeee")

    def test_shape_choices_reach_the_look(self):
        ed = self.editor()
        ed._radius.setValue(12)
        ed._buttons.setCurrentIndex(ed._buttons.findData("pill"))
        ed._tabs.setCurrentIndex(ed._tabs.findData("segment"))
        ed._focus.setCurrentIndex(ed._focus.findData("underline"))
        look = ed.look()
        self.assertEqual((look.tokens.radius, look.buttons, look.tabs, look.focus),
                         (12, "pill", "segment", "underline"))

    def test_a_dark_window_makes_a_dark_look(self):
        ed = self.editor("paper")
        with mock.patch.object(look_editor.QColorDialog, "getColor",
                               return_value=QColor("#101418")):
            ed._pick("window")
        self.assertTrue(ed.look().dark)

    def test_a_faint_pair_is_warned_about_but_still_saved(self):
        ed = self.editor("paper")
        with mock.patch.object(look_editor.QColorDialog, "getColor",
                               return_value=QColor("#fafafa")):
            ed._pick("text")
        self.assertIn("Hard to read", ed._warnings.text())
        self.assertTrue(ed._save.isEnabled())


class LookEditorGermanTest(_Clean):
    """QTabBar and QTableWidgetItem are not hooked: their texts ask for German."""

    def setUp(self):
        super().setUp()
        i18n.set_active("de")
        i18n.install_text_hook()
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)
        self.addCleanup(i18n._restore_text_hook)

    def test_the_preview_speaks_german(self):
        preview = self.keep(LookPreview())
        tabs = preview.findChild(look_editor.QTabBar)
        self.assertEqual([tabs.tabText(i) for i in range(tabs.count())],
                         ["Planung", "Wiedergabe"])
        self.assertEqual(preview._table.item(2, 0).text(), "Gruppe 1")
        self.assertIn("VORRUNDE", preview._table.item(0, 0).text())

    def test_the_editor_speaks_german(self):
        ed = self.keep(LookEditor(user_looks.copy_of(looks.LOOKS["console"], "x")))
        self.assertIn("Familie: Pult-Looks", " ".join(
            label.text() for label in ed.findChildren(look_editor.QLabel)))
        self.assertEqual(ed._buttons.itemText(0), "Umrandet")


# ── ⚙ Settings › Look ───────────────────────────────────────────────────────

class _FakeEditor:
    """LookEditor, accepted at once with the name changed to `name`."""
    name = "Edited"
    accepted = True

    def __init__(self, look, parent=None):
        self._look = look

    def exec(self):
        return (QDialog.DialogCode.Accepted if self.accepted
                else QDialog.DialogCode.Rejected)

    def look(self):
        return dataclasses.replace(self._look, caption=self.name)


class SettingsOwnLooksTest(_Clean):

    def dlg(self, settings=None):
        return self.keep(SettingsDialog(settings or {}))

    def editor(self, **kw):
        fake = type("Editor", (_FakeEditor,), kw)
        patch = mock.patch.object(dialogs, "LookEditor", fake)
        patch.start()
        self.addCleanup(patch.stop)

    def keys(self, dlg):
        lst = dlg._theme_list
        return [lst.item(i).data(Qt.ItemDataRole.UserRole) for i in range(lst.count())]

    def test_own_looks_are_listed_last_under_their_own_head(self):
        mine = self.made()
        dlg = self.dlg()
        lst = dlg._theme_list
        self.assertEqual(lst.item(lst.count() - 2).text(), "Own looks")
        self.assertEqual(self.keys(dlg)[-1], mine.key)
        self.assertEqual(lst.item(lst.count() - 1).text().strip(), mine.caption)

    def test_a_built_in_look_cannot_be_edited_deleted_or_exported(self):
        dlg = self.dlg({"theme": "midnight"})
        for button in (dlg._look_edit, dlg._look_delete, dlg._look_export):
            self.assertFalse(button.isEnabled())
        self.assertTrue(dlg._look_new.isEnabled())
        self.assertTrue(dlg._look_import.isEnabled())

    def test_picking_an_own_look_shows_its_live_preview(self):
        mine = self.made()
        dlg = self.dlg({"theme": mine.key})
        self.assertFalse(dlg._look_preview.isHidden())
        self.assertTrue(dlg._theme_preview.isHidden())
        self.assertIn(mine.tokens.window, dlg._look_preview.styleSheet())
        self.assertTrue(dlg._look_edit.isEnabled())
        self.assertIn("of your own", dlg._theme_blurb.text())
        dlg._select_theme("midnight")
        self.assertTrue(dlg._look_preview.isHidden())
        self.assertFalse(dlg._theme_preview.isHidden())

    def test_new_copies_the_selected_look_and_picks_the_copy(self):
        self.editor(name="Gala")
        dlg = self.dlg({"theme": "console"})
        dlg._new_look()
        [mine] = user_looks.mine()
        self.assertEqual(mine.caption, "Gala")
        self.assertEqual(looks.family(mine), "desk")
        self.assertEqual(dlg.values()["theme"], mine.key)
        user_looks.load()
        self.assertIsNotNone(looks.get(mine.key), "saved at once, not on OK")

    def test_new_from_light_starts_from_paper(self):
        seen = []

        class Editor(_FakeEditor):
            def __init__(self, look, parent=None):
                seen.append(look)
                super().__init__(look, parent)

        mock.patch.object(dialogs, "LookEditor", Editor).start()
        self.addCleanup(mock.patch.stopall)
        self.dlg({"theme": "light"})._new_look()
        self.assertEqual(seen[0].tokens, looks.LOOKS["paper"].tokens)
        self.assertEqual(seen[0].caption, "Paper (own)")

    def test_a_cancelled_editor_makes_nothing(self):
        self.editor(accepted=False)
        dlg = self.dlg({"theme": "console"})
        dlg._new_look()
        self.assertEqual(user_looks.mine(), [])
        self.assertEqual(dlg.selected_theme(), "console")

    def test_edit_saves_under_the_same_key(self):
        mine = self.made()
        self.editor(name="Renamed")
        dlg = self.dlg({"theme": mine.key})
        dlg._edit_look()
        self.assertEqual(looks.get(mine.key).caption, "Renamed")
        self.assertEqual(dlg.selected_theme(), mine.key)

    def test_delete_asks_first(self):
        mine = self.made()
        dlg = self.dlg({"theme": mine.key})
        with mock.patch.object(dialogs.QMessageBox, "question",
                               return_value=QMessageBox.StandardButton.No):
            dlg._delete_look()
        self.assertIsNotNone(looks.get(mine.key))
        with mock.patch.object(dialogs.QMessageBox, "question",
                               return_value=QMessageBox.StandardButton.Yes):
            dlg._delete_look()
        self.assertIsNone(looks.get(mine.key))
        self.assertEqual(dlg.selected_theme(), "light")
        self.assertNotIn(mine.key, self.keys(dlg))

    def test_export_then_import_through_the_buttons(self):
        mine = self.made(name="Gala")
        dlg = self.dlg({"theme": mine.key})
        path = str(Path(self._state) / "gala.json")
        with mock.patch.object(dialogs.QFileDialog, "getSaveFileName",
                               return_value=(path, "")):
            dlg._export_look()
        with mock.patch.object(dialogs.QFileDialog, "getOpenFileName",
                               return_value=(path, "")):
            dlg._import_look()
        copy = looks.get(dlg.selected_theme())
        self.assertEqual(copy.caption, "Gala (2)")
        self.assertEqual(copy.tokens, mine.tokens)

    def test_a_broken_file_is_refused_with_a_message(self):
        path = Path(self._state) / "broken.json"
        path.write_text("{", encoding="utf-8")
        dlg = self.dlg()
        with mock.patch.object(dialogs.QFileDialog, "getOpenFileName",
                               return_value=(str(path), "")), \
                mock.patch.object(dialogs.QMessageBox, "warning") as warned:
            dlg._import_look()
        warned.assert_called_once()
        self.assertEqual(user_looks.mine(), [])


class RestartOfferTest(_Clean):
    """Edits are saved at once, so the pick can stay the same while the look
    the app runs in changed: that alone has to offer the restart."""

    def test_editing_the_running_look_asks_for_a_restart(self):
        mine = self.made()
        theme.set_active(mine.key)
        mock.patch.object(dialogs, "LookEditor", _FakeEditor).start()
        self.addCleanup(mock.patch.stopall)
        dlg = self.keep(SettingsDialog({"theme": mine.key}))
        self.assertFalse(dlg.running_look_touched())
        dlg._edit_look()
        self.assertTrue(dlg.running_look_touched())

    def test_editing_another_look_does_not(self):
        running, other = self.made(name="A"), self.made(name="B")
        theme.set_active(running.key)
        mock.patch.object(dialogs, "LookEditor", _FakeEditor).start()
        self.addCleanup(mock.patch.stopall)
        dlg = self.keep(SettingsDialog({"theme": other.key}))
        dlg._edit_look()
        self.assertFalse(dlg.running_look_touched())


if __name__ == "__main__":
    unittest.main()
