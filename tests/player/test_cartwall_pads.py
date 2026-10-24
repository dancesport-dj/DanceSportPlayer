"""The cartwall's pads on their own: the pad widget, its dialogs and editors.

The key picker, the shortcuts dialog, the pad widget and its edit lock, the
colour swatch, the pad length, the pad dialog, the typed values and the
multi-select. The wall as a whole (grid, running pads, shape, colours, keys,
file, fade, pages) is in tests.player.test_cartwall_ui.

Text is asserted, never rendering: the offscreen QPA has no fonts.
"""
import contextlib
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_cartpads_"))

from PySide6.QtCore import QEvent, QMimeData, QPoint, QUrl, Qt
from PySide6.QtGui import QDropEvent, QKeyEvent, QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel
from tests.qt_test_support import reap_widget

from planner.playing import cartwall as pc
from player.dialogs import cart_pad_dialog as cpd
from player.widgets import cart_keys, cartwall as gc

_app = QApplication.instance() or QApplication(sys.argv)

# A file that really exists — a pad whose sample is missing is painted grey, so
# the colour tests would otherwise all be testing the "⚠ gone" style.
_SAMPLE = os.path.join(tempfile.mkdtemp(prefix="dp_cartfx_"), "tusch.mp3")
open(_SAMPLE, "wb").close()


def _hex(rgb):
    """An (r, g, b[, a]) band colour as the "#rrggbb" the stylesheets carry."""
    r, g, b = rgb[:3]
    return f"#{r:02x}{g:02x}{b:02x}"


def _drop(widget, mime):
    event = QDropEvent(QPoint(4, 4), Qt.DropAction.CopyAction, mime,
                       Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    widget.dropEvent(event)
    return event


def _url_mime(*paths):
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(p) for p in paths])
    return mime


@contextlib.contextmanager
def _accepted_dialog(pad):
    """Stand in for the pad dialog: exec() returns Ok and pad() returns `pad`.
    A modal exec() in a test run would sit there until the suite timed out."""
    class _Stub:
        previewVolume = previewFire = None

        def __init__(self, *a, **kw):
            self.previewVolume = _Sig()
            self.previewFire = _Sig()

        def exec(self):
            return gc.QDialog.DialogCode.Accepted

        def pad(self):
            return pad

    class _Sig:
        def connect(self, _slot):
            pass

    real = gc.CartPadDialog
    gc.CartPadDialog = _Stub
    try:
        yield
    finally:
        gc.CartPadDialog = real


class KeyPickerTest(unittest.TestCase):
    """Press it, learn it, or ✕ it."""

    def setUp(self):
        self.p = cart_keys._KeyPicker("Ctrl+1")

    def tearDown(self):
        self.p.deleteLater()

    def test_it_opens_on_the_key_it_was_given(self):
        self.assertEqual(self.p.sequence(), "Ctrl+1")

    def test_the_cross_clears_the_key(self):
        seen = []
        self.p.changed.connect(lambda: seen.append(True))
        self.p._on_clear()
        self.assertEqual(self.p.sequence(), "")
        self.assertEqual(len(seen), 1)

    def test_a_learned_key_is_kept_and_reported(self):
        seen = []
        self.p.changed.connect(lambda: seen.append(True))
        self.p._learn.click()
        QTest.keyClick(self.p._edit, Qt.Key.Key_F9)
        self.assertEqual(self.p.sequence(), "F9")
        self.assertEqual(self.p._learn.text(), "Learn")
        self.assertTrue(seen)


class ShortcutsDialogTest(unittest.TestCase):
    """The wall's tab of the ⌨ Keys window: two layers, and the clashes
    marked before they bite."""

    def _dialog(self, pages, slot_keys=pc.SLOT_KEYS, grid=(4, 4)):
        dlg = cart_keys.CartKeysPanel(grid, pages, slot_keys)
        self.addCleanup(dlg.deleteLater)
        return dlg

    def test_it_lists_a_row_per_slot_and_a_row_per_pad_on_every_page(self):
        pages = [pc.Page(pads={(0, 0): pc.CartPad(path="a.mp3")}),
                 pc.Page(pads={(1, 1): pc.CartPad(path="b.mp3"),
                               (2, 2): pc.CartPad(path="c.mp3")})]
        dlg = self._dialog(pages)
        self.assertEqual(len(dlg._slot_pickers), 16)     # 4 × 4
        self.assertEqual(len(dlg._pad_pickers), 3)

    def test_it_opens_on_the_keys_the_wall_is_using(self):
        pages = [pc.Page(pads={(0, 0): pc.CartPad(path="a.mp3",
                                                  shortcut="Ctrl+Shift+T")})]
        dlg = self._dialog(pages, slot_keys=("F5", "F6"))
        self.assertEqual(dlg.slot_keys(), ("F5", "F6"))
        self.assertEqual(dlg.pad_keys(), {(0, 0, 0): "Ctrl+Shift+T"})

    def test_a_wall_with_no_pads_still_opens(self):
        dlg = self._dialog([pc.blank_page()])
        self.assertEqual(dlg.pad_keys(), {})

    def test_a_slot_key_a_pad_already_took_is_marked_not_the_pad(self):
        """The order mirrors the wall: pads first, so the SLOT is the loser."""
        pages = [pc.Page(pads={(0, 3): pc.CartPad(path="a.mp3",
                                                  shortcut="Ctrl+1")})]
        dlg = self._dialog(pages)
        self.assertEqual(dlg._slot_warnings[0].text(), "⚠ already used by a (p1)")
        self.assertEqual(dlg._pad_pickers[0][2].text(), "")
        self.assertIn("1 key claimed twice", dlg._clash.text())

    def test_a_learned_key_is_checked_for_clashes_at_once(self):
        dlg = self._dialog([pc.blank_page()])
        picker = dlg._slot_pickers[4]
        picker._learn.click()
        QTest.keyClick(picker._edit, Qt.Key.Key_1,
                       Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(dlg._slot_warnings[4].text(), "⚠ already used by Slot 1")

    def test_two_slots_on_one_key_mark_the_second(self):
        dlg = self._dialog([pc.blank_page()])
        dlg._slot_pickers[4].set_sequence("Ctrl+1")
        dlg._refresh_conflicts()
        self.assertEqual(dlg._slot_warnings[0].text(), "")
        self.assertEqual(dlg._slot_warnings[4].text(), "⚠ already used by Slot 1")

    def test_a_pad_that_has_the_key_is_named_by_its_label(self):
        pages = [pc.Page(), pc.Page(pads={(0, 0): pc.CartPad(
            path="a.mp3", label="Tusch", shortcut="F13")})]
        dlg = self._dialog(pages)
        dlg._slot_pickers[2].set_sequence("F13")
        dlg._refresh_conflicts()
        self.assertEqual(dlg._slot_warnings[2].text(),
                         "⚠ already used by Tusch (p2)")

    def test_a_key_outside_the_wall_is_marked_with_what_it_does(self):
        """A desk key or a key of the app's own on a pad too is ambiguous to
        Qt: neither fires. The row says which action has it."""
        pages = [pc.Page(pads={(0, 0): pc.CartPad(path="a.mp3", shortcut="F13")})]
        dlg = cart_keys.CartKeysPanel((4, 4), pages, pc.SLOT_KEYS,
                               taken={"F13": "⏭  Next title",
                                      "Ctrl+S": "Save the focused playlist"})
        self.addCleanup(dlg.deleteLater)
        self.assertEqual(dlg._pad_pickers[0][2].text(),
                         "⚠ The app uses this key: ⏭  Next title")
        dlg._slot_pickers[1].set_sequence("Ctrl+S")
        dlg._refresh_conflicts()
        self.assertEqual(dlg._slot_warnings[1].text(),
                         "⚠ The app uses this key: Save the focused playlist")
        self.assertIn("2 keys claimed twice", dlg._clash.text())

    def test_the_rows_fit_the_window_warning_and_all(self):
        """No row wider than the window: Learn, ✕ and the warning in view."""
        pages = [pc.Page(pads={(0, 0): pc.CartPad(path="a.mp3", shortcut="F13")})]
        dlg = cart_keys.CartKeysPanel((2, 8), pages, pc.SLOT_KEYS,
                               taken={"F13": "🔉↓  Fade out now"})
        self.addCleanup(dlg.deleteLater)
        dlg.show()
        QApplication.processEvents()
        scroll = dlg.findChild(cart_keys.QScrollArea)
        self.assertLessEqual(scroll.widget().width(), scroll.viewport().width())
        self.assertEqual(scroll.horizontalScrollBar().maximum(), 0)

    def test_a_clean_wall_says_nothing(self):
        dlg = self._dialog([pc.Page(pads={(0, 0): pc.CartPad(path="a.mp3",
                                                             shortcut="F9")})])
        self.assertEqual(dlg._clash.text(), "")
        self.assertEqual(dlg._slot_warnings[0].text(), "")

    def test_blank_keys_never_clash_with_each_other(self):
        pages = [pc.Page(pads={(0, 0): pc.CartPad(path="a.mp3"),
                               (1, 1): pc.CartPad(path="b.mp3")})]
        dlg = self._dialog(pages, slot_keys=())
        self.assertEqual(dlg._clash.text(), "")

    def test_restore_defaults_leaves_the_pad_keys_alone(self):
        pages = [pc.Page(pads={(0, 0): pc.CartPad(path="a.mp3",
                                                  shortcut="Ctrl+Shift+T")})]
        dlg = self._dialog(pages, slot_keys=("F5", "F6"))
        dlg._restore_defaults()
        self.assertEqual(dlg.slot_keys(), pc.SLOT_KEYS)
        self.assertEqual(dlg.pad_keys(), {(0, 0, 0): "Ctrl+Shift+T"})

    def test_it_names_the_keys_as_set_now_for_the_desk_tab(self):
        """Who has which key — the edits not saved yet included, and in the
        wall's own order: a pad's key first, a slot never takes it twice."""
        pages = [pc.Page(pads={(0, 0): pc.CartPad(path="a.mp3", label="Tusch",
                                                  shortcut="Ctrl+1")})]
        dlg = self._dialog(pages)
        dlg._slot_pickers[1].set_sequence("F9")
        self.assertEqual(dlg.owners()["Ctrl+1"], "Tusch (p1)")
        self.assertEqual(dlg.owners()["F9"], "Slot 2")
        self.assertNotIn("Ctrl+2", dlg.owners())

    def test_an_edit_is_reported_a_new_taken_list_is_not(self):
        dlg = self._dialog([pc.blank_page()])
        seen = []
        dlg.changed.connect(lambda: seen.append(True))
        dlg.set_taken({"Ctrl+1": "⏭  Next title"})
        self.assertEqual(seen, [])
        self.assertEqual(dlg._slot_warnings[0].text(),
                         "⚠ The app uses this key: ⏭  Next title")
        dlg._slot_pickers[0]._on_clear()
        self.assertEqual(seen, [True])
        self.assertEqual(dlg._slot_warnings[0].text(), "")

    def test_a_key_cleared_in_the_dialog_comes_back_as_no_key(self):
        pages = [pc.Page(pads={(0, 0): pc.CartPad(path="a.mp3",
                                                  shortcut="Ctrl+Shift+T")})]
        dlg = self._dialog(pages)
        dlg._pad_pickers[0][1]._on_clear()
        self.assertEqual(dlg.pad_keys(), {(0, 0, 0): ""})


class CartPadWidgetTest(unittest.TestCase):
    def setUp(self):
        self.w = gc.CartwallWidget()
        self.w.set_edit(True)      # this class is about BUILDING the wall

    def tearDown(self):
        self.w.deleteLater()

    def test_dropping_audio_on_an_empty_pad_assigns_it(self):
        seen = []
        self.w.changed.connect(lambda: seen.append(True))
        _drop(self.w._buttons[(0, 0, 0)], _url_mime("C:\\samples\\tusch.mp3"))
        self.assertEqual(self.w.pad_at((0, 0, 0)).path, "C:\\samples\\tusch.mp3")
        self.assertEqual(seen, [True])

    def test_a_non_audio_drop_is_refused(self):
        _drop(self.w._buttons[(0, 0, 0)], _url_mime("C:\\notes.txt"))
        self.assertIsNone(self.w.pad_at((0, 0, 0)))

    def test_a_deck_drop_is_forced_to_copy(self):
        """TableDragDropMixin.startDrag offers Copy | Move | Link — a Move would
        make the row vanish out of the deck we borrowed it from."""
        event = _drop(self.w._buttons[(0, 0, 0)], _url_mime("C:\\s\\a.mp3"))
        self.assertEqual(event.dropAction(), Qt.DropAction.CopyAction)

    def test_dragging_a_pad_onto_another_swaps_them(self):
        self.w.set_wall(pc.DEFAULT_GRID, [pc.Page(pads={
            (0, 0): pc.CartPad(path="a.mp3"),
            (1, 1): pc.CartPad(path="b.mp3")})])
        mime = QMimeData()
        mime.setData(gc._PAD_MIME, b"0,0")
        _drop(self.w._buttons[(0, 1, 1)], mime)
        self.assertEqual(self.w.pad_at((0, 1, 1)).path, "a.mp3")
        self.assertEqual(self.w.pad_at((0, 0, 0)).path, "b.mp3")

    def test_clearing_a_pad_empties_only_that_cell(self):
        self.w.set_wall(pc.DEFAULT_GRID, [pc.Page(pads={
            (0, 0): pc.CartPad(path="a.mp3"),
            (0, 1): pc.CartPad(path="b.mp3")})])
        self.w._on_clear((0, 0, 0))
        self.assertIsNone(self.w.pad_at((0, 0, 0)))
        self.assertIsNotNone(self.w.pad_at((0, 0, 1)))

    def test_the_pad_x_clears_it(self):
        """✕ in the pad's bottom-right corner — clearing a pad without hunting
        through the right-click menu."""
        self.w.set_wall(pc.DEFAULT_GRID, [pc.Page(pads={
            (0, 0): pc.CartPad(path="a.mp3"),
            (0, 1): pc.CartPad(path="b.mp3")})])
        self.w._buttons[(0, 0, 0)]._del_btn.click()
        self.assertIsNone(self.w.pad_at((0, 0, 0)))
        self.assertIsNotNone(self.w.pad_at((0, 0, 1)))

    def test_the_pad_x_is_edit_mode_only_and_needs_a_pad(self):
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path="a.mp3")})])
        filled = self.w._buttons[(0, 0, 0)]._del_btn
        empty = self.w._buttons[(0, 0, 1)]._del_btn
        self.w.set_edit(True)
        self.assertTrue(filled.isVisibleTo(self.w))
        self.assertFalse(empty.isVisibleTo(self.w))
        self.w.set_edit(False)
        self.assertFalse(filled.isVisibleTo(self.w))

    def test_a_multi_select_drop_fills_the_free_pads_after_the_one_aimed_at(self):
        # An explicit grid, not the default: this is about the FILL ORDER, which
        # must not change meaning when the default wall shape does.
        self.w.set_wall((4, 4), [pc.blank_page()])
        _drop(self.w._buttons[(0, 0, 1)],
              _url_mime("C:\\s\\a.mp3", "C:\\s\\b.mp3", "C:\\s\\c.mp3"))
        self.assertEqual(self.w.pad_at((0, 0, 1)).path, "C:\\s\\a.mp3")
        self.assertEqual(self.w.pad_at((0, 0, 2)).path, "C:\\s\\b.mp3")
        self.assertEqual(self.w.pad_at((0, 0, 3)).path, "C:\\s\\c.mp3")
        self.assertIsNone(self.w.pad_at((0, 0, 0)))

    def test_a_drop_bigger_than_the_wall_says_how_many_landed(self):
        """The wall stops at its page cap; the tracks past it did not land,
        and a log line nobody reads is not how the operator finds that out."""
        self.w.set_wall((2, 2), [pc.blank_page()])
        paths = [f"C:\\s\\{n}.mp3" for n in range(pc.FILE_PAGE_CAP * 4 + 3)]
        told = []
        real = gc.QMessageBox.information
        gc.QMessageBox.information = staticmethod(
            lambda *a, **kw: told.append(a[2]))
        self.addCleanup(setattr, gc.QMessageBox, "information", real)
        _drop(self.w._buttons[(0, 0, 0)], _url_mime(*paths))
        self.assertEqual(len(told), 1)
        self.assertIn(f"{pc.FILE_PAGE_CAP * 4} of {len(paths)}", told[0])

    def test_a_multi_select_drop_skips_pads_that_are_already_set_up(self):
        self.w.set_wall((4, 4),
                        [pc.Page(pads={(0, 1): pc.CartPad(path="keep.mp3")})])
        _drop(self.w._buttons[(0, 0, 0)], _url_mime("C:\\s\\a.mp3", "C:\\s\\b.mp3"))
        self.assertEqual(self.w.pad_at((0, 0, 1)).path, "keep.mp3")
        self.assertEqual(self.w.pad_at((0, 0, 2)).path, "C:\\s\\b.mp3")

    def _tools_row(self):
        """The flow layout holding the grid combo, ✏ and the transport."""
        return self.w.layout().itemAt(1)

    def _one_row_width(self) -> int:
        tools = self._tools_row()
        return sum(tools.itemAt(i).sizeHint().width()
                   for i in range(tools.count()))

    def test_the_wall_can_be_dragged_narrower_than_its_tool_row(self):
        """The dock lives beside the decks, so the floor has to be the PADS —
        a tool bar that pins the wall at its natural width means the user can
        only ever make the dock bigger."""
        self.assertLess(self.w.minimumSizeHint().width(), self._one_row_width())

    def test_a_narrow_wall_wraps_its_tools_onto_a_second_row(self):
        """'if i have not enough space to show all buttons they should be get in
        2 rows' — clipping ⏹ off the edge is not an option."""
        tools = self._tools_row()
        wide = self._one_row_width()
        self.assertGreater(tools.heightForWidth(wide // 2),
                           tools.heightForWidth(wide + 40))

    def test_the_page_nav_keeps_its_own_row(self):
        """It is the one control the operator hunts for mid-heat, so it never
        wraps in among the tools."""
        nav = self.w.layout().itemAt(0)
        self.assertIs(nav.indexOf(self.w._page_lbl) >= 0, True)
        self.assertLess(self._tools_row().indexOf(self.w._page_lbl), 0)

    def test_a_pad_shows_its_loop_and_trim_at_a_glance(self):
        self.w.set_wall(pc.DEFAULT_GRID, [pc.Page(pads={
            (0, 0): pc.CartPad(path="bed.mp3", loop=True, volume=0.25)})])
        text = self.w._buttons[(0, 0, 0)]._title.text()
        self.assertIn("🔁", text)
        self.assertIn("25%", text)

    def test_a_background_pad_carries_its_own_mark(self):
        self.w.set_wall(pc.DEFAULT_GRID, [pc.Page(pads={
            (0, 0): pc.CartPad(path="bed.mp3", background=True),
            (0, 1): pc.CartPad(path="tusch.mp3")})])
        self.assertIn("♫", self.w._buttons[(0, 0, 0)]._title.text())
        self.assertNotIn("♫", self.w._buttons[(0, 0, 1)]._title.text())

    def test_the_background_mark_takes_the_pads_text_colour(self):
        """The colour emoji 🎶 is purple and drowned on a purple or green
        pad; the plain ♫ is drawn in the pad's own text colour."""
        self.w.set_wall(pc.DEFAULT_GRID, [pc.Page(pads={
            (0, 0): pc.CartPad(path="bed.mp3", background=True)})])
        self.assertNotIn("🎶", self.w._buttons[(0, 0, 0)]._title.text())


    def test_a_pad_that_ducks_the_music_shows_it(self):
        # Marcel: "the pull the music down icon should be shown on the
        # cards" - "i want to see direct how it behave".
        self.w.set_wall(pc.DEFAULT_GRID, [pc.Page(pads={
            (0, 0): pc.CartPad(path="tusch.mp3"),
            (0, 1): pc.CartPad(path="quiet.mp3", duck=False),
            (1, 0): pc.CartPad(path="bed.mp3", duck=True, background=True)})])
        self.assertIn("↓", self.w._buttons[(0, 0, 0)]._title.text())
        self.assertNotIn("↓", self.w._buttons[(0, 0, 1)]._title.text())
        # A background pad never ducks, whatever its old flag says. The mark is
        # an arrow, not the pale 🔈 emoji (Marcel's pick).
        self.assertNotIn("↓", self.w._buttons[(0, 1, 0)]._title.text())

    def test_a_pad_that_stops_the_others_carries_its_own_mark(self):
        # Marcel: "also add a logo for this to the pad".
        self.w.set_wall(pc.DEFAULT_GRID, [pc.Page(pads={
            (0, 0): pc.CartPad(path="anthem.mp3", stops_others=True),
            (0, 1): pc.CartPad(path="tusch.mp3")})])
        # Marcel: "instead of Stop Icon print a S", then "draw a rectangle
        # around it so it is not misinterpreted as title": the squared 🅂.
        self.assertIn("\U0001F142", self.w._buttons[(0, 0, 0)]._title.text())
        self.assertNotIn("\U0001F142", self.w._buttons[(0, 0, 1)]._title.text())
        self.assertNotIn("■", self.w._buttons[(0, 0, 0)]._title.text())
        # First "make the S glyph smaller so it matches size of the other
        # ones" (16 -> 13 px), then "make s glypth 14px in size".
        self.assertIn("font-size:14px", self.w._buttons[(0, 0, 0)]._title.text())

    def test_a_pad_title_is_shown_as_written_not_as_markup(self):
        # The title is rich text for the bigger 🅂, so a file name with a <
        # or an & in it must be escaped, not read as a tag.
        self.w.set_wall(pc.DEFAULT_GRID, [pc.Page(pads={
            (0, 0): pc.CartPad(path="<b>Rock & Roll.mp3")})])
        label = self.w._buttons[(0, 0, 0)]._title
        self.assertEqual(label.textFormat(), Qt.TextFormat.RichText)
        self.assertIn("&lt;b&gt;Rock &amp; Roll", label.text())

class EditLockTest(unittest.TestCase):
    """✏ off is the tournament state: pads fire, and nothing else."""

    def setUp(self):
        self.w = gc.CartwallWidget()

    def tearDown(self):
        self.w.deleteLater()

    def test_a_fresh_wall_is_locked(self):
        self.assertFalse(self.w.edit_mode())
        self.assertFalse(self.w._edit_btn.isChecked())
        self.assertFalse(self.w._buttons[(0, 0, 0)].acceptDrops())

    def test_a_locked_wall_refuses_a_drop(self):
        _drop(self.w._buttons[(0, 0, 0)], _url_mime("C:\\s\\a.mp3"))
        self.assertIsNone(self.w.pad_at((0, 0, 0)))
        self.w.set_edit(True)
        _drop(self.w._buttons[(0, 0, 0)], _url_mime("C:\\s\\a.mp3"))
        self.assertEqual(self.w.pad_at((0, 0, 0)).path, "C:\\s\\a.mp3")

    def test_a_locked_wall_still_fires(self):
        seen = []
        self.w.padClicked.connect(seen.append)
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path=_SAMPLE)})])
        self.w._buttons[(0, 0, 0)].tapped.emit((0, 0, 0))
        self.assertEqual(seen, [(0, 0, 0)])

    def test_the_phone_remote_fires_through_the_same_edit_gate(self):
        seen = []
        self.w.padClicked.connect(seen.append)
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path=_SAMPLE)})])
        self.w.play_pad((0, 0, 0))
        self.assertEqual(seen, [(0, 0, 0)])
        self.w.set_edit(True)
        self.w.play_pad((0, 0, 0))
        self.assertEqual(seen, [(0, 0, 0)])
        self.w.set_edit(False)

    def test_an_editable_wall_does_not_fire(self):
        """Building a wall must not set off every pad you touch."""
        seen = []
        self.w.padClicked.connect(seen.append)
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path=_SAMPLE)})])
        self.w.set_edit(True)
        self.w._buttons[(0, 0, 0)].tapped.emit((0, 0, 0))
        self.assertEqual(seen, [])
        self.w.set_edit(False)
        self.w._buttons[(0, 0, 0)].tapped.emit((0, 0, 0))
        self.assertEqual(seen, [(0, 0, 0)])

    def test_a_slot_key_is_silent_while_the_wall_is_being_edited(self):
        """The keys are application-wide, so they have to obey the lock too."""
        seen = []
        self.w.padClicked.connect(seen.append)
        self.w.set_wall((4, 4),
                        [pc.Page(pads={(0, 0): pc.CartPad(path=_SAMPLE)})])
        self.w.set_edit(True)
        for shortcut in self.w._shortcuts:
            if shortcut.key().toString() == "Ctrl+1":
                shortcut.activated.emit()
        self.assertEqual(seen, [])

    def test_the_grid_control_ignores_the_lock(self):
        """Reshaping the wall to the dock you just dragged is a VIEW decision and
        it never loses a pad, so it must not need ✏ unlocked first."""
        self.assertTrue(self.w._size_box.isEnabled())
        self.w.set_edit(True)
        self.assertTrue(self.w._size_box.isEnabled())

    def test_the_pen_button_is_an_icon_not_a_caption(self):
        """'edit button should be a pen' — and a pen with no text beside it, so
        it survives a dock dragged down to two pads wide."""
        self.assertFalse(self.w._edit_btn.icon().isNull())
        self.assertEqual(self.w._edit_btn.text(), "")


class ColourSwatchTest(unittest.TestCase):

    def test_every_offered_colour_paints_a_swatch(self):
        for value in cpd.PAD_COLOURS.values():
            self.assertFalse(gc._colour_icon(value or "#ffffff").isNull())

    def test_no_pad_style_ends_in_a_stray_brace(self):
        """A plain string among the f-strings left '}}' in the sheet and Qt
        logged 'Could not parse stylesheet' on every restyle."""
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        w.set_wall(pc.DEFAULT_GRID,
                   [pc.Page(pads={(0, 0): pc.CartPad(path=_SAMPLE)})])
        pad = w._buttons[(0, 0, 0)]
        for state in (lambda: None, lambda: pad.set_playing(True),
                      lambda: pad.set_pad(None)):
            state()
            sheet = pad.styleSheet()
            self.assertEqual(sheet.count("{"), sheet.count("}"), sheet)
            self.assertNotIn("}}", sheet)

    def test_white_is_the_standard_pad_colour(self):
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        w.set_wall(pc.DEFAULT_GRID,
                   [pc.Page(pads={(0, 0): pc.CartPad(path=_SAMPLE)})])
        self.assertEqual(w.default_colour(), "#ffffff")
        self.assertIn("#ffffff", w._buttons[(0, 0, 0)].styleSheet())

    def test_the_palette_offers_no_blue(self):
        """Blue is how the wall says 'running' and 'this much has played' — a pad
        painted in either would lie about its state."""
        blues = {gc._PLAY_BG.lower(), gc._PLAY_BORDER.lower(),
                 _hex(gc._PLAYED_BAND)}
        self.assertFalse(blues & {v.lower() for v in cpd.PAD_COLOURS.values()})

    def test_a_running_pad_is_light_blue_with_a_deep_blue_band(self):
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        w.set_wall(pc.DEFAULT_GRID,
                   [pc.Page(pads={(0, 0): pc.CartPad(path=_SAMPLE)})])
        w.set_playing((0, 0, 0), True)
        self.assertIn(gc._PLAY_BG, w._buttons[(0, 0, 0)].styleSheet())
        # The band has to be the darker of the two, or "how far in am I" reads
        # backwards.
        self.assertLess(gc._luma(_hex(gc._PLAYED_BAND)),
                        gc._luma(gc._PLAY_BG))

class PadLengthTest(unittest.TestCase):
    """'as in playin cartwall show length in cart' — an idle pad says how long
    its sample is, and only a running one counts down."""

    def setUp(self):
        # Seeded rather than shipping a real three-minute MP3 in the repo.
        gc._DURATIONS[_SAMPLE] = 192
        self.w = gc.CartwallWidget()

    def tearDown(self):
        gc._DURATIONS.pop(_SAMPLE, None)
        self.w.deleteLater()

    def test_an_idle_pad_shows_the_sample_length(self):
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path=_SAMPLE)})])
        self.assertEqual(self.w._buttons[(0, 0, 0)]._time.text(), "03:12")

    def test_a_pad_gets_its_length_back_when_it_stops(self):
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path=_SAMPLE)})])
        button = self.w._buttons[(0, 0, 0)]
        self.w.set_playing((0, 0, 0), True)
        self.w.set_remaining((0, 0, 0), 61_000, 0.7)
        self.assertEqual(button._time.text(), "01:01")
        self.w.set_playing((0, 0, 0), False)
        self.assertEqual(button._time.text(), "03:12")

    def test_the_length_really_gets_room_on_the_pad(self):
        """It was there and 0 px wide: the labels have an Ignored size policy,
        so a stretch item between them took the whole footer row."""
        self.w.set_wall((2, 8),
                        [pc.Page(pads={(0, 0): pc.CartPad(path=_SAMPLE)})])
        self.w.resize(400, 900)
        self.w.show()
        self.addCleanup(self.w.hide)
        QApplication.processEvents()
        button = self.w._buttons[(0, 0, 0)]
        self.assertGreater(button._time.width(), 30)
        self.assertGreater(button._key_lbl.width(), 30)

    def test_the_slot_key_is_greyer_than_the_title(self):
        """'show the short cut in light grey' — it is a hint, not something the
        operator reads mid-heat."""
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path=_SAMPLE)})])
        sheet = self.w._buttons[(0, 0, 0)].styleSheet()
        self.assertIn("QLabel#cartKey", sheet)
        key_fg = sheet.split("QLabel#cartKey { color: ")[1].split(";")[0]
        self.assertGreater(gc._luma(key_fg), gc._luma("#2b3038"))

    def test_a_length_that_cannot_be_read_stays_dashes(self):
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path="X:\\gone.mp3")})])
        self.assertEqual(self.w._buttons[(0, 0, 0)]._time.text(), "--:--")


class CartPadDialogTest(unittest.TestCase):
    def test_an_untouched_dialog_round_trips_the_pad(self):
        pad = pc.CartPad(path="a.mp3", label="Tusch", colour="#2f8f4e",
                         volume=0.25, loop=True, duck=False)
        self.assertEqual(cpd.CartPadDialog(pad).pad(), pad)

    def test_the_dialog_reads_back_what_was_edited(self):
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3"))
        dlg._label.setText("Fanfare")
        dlg._vol.setValue(25)
        out = dlg.pad()
        self.assertEqual(out.label, "Fanfare")
        self.assertAlmostEqual(out.volume, 0.25)

    def test_a_pad_can_be_given_a_key_of_its_own(self):
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3"), slot_key="Ctrl+1")
        self.assertEqual(dlg.pad().shortcut, "")
        dlg._key.setKeySequence(QKeySequence("Ctrl+Shift+T"))
        self.assertEqual(dlg.pad().shortcut, "Ctrl+Shift+T")

    def test_endless_repeat_switches_the_duck_off_with_it(self):
        """A bed holding the deck music down for a whole ceremony is never what
        anyone means by 'background music'."""
        dlg = cpd.CartPadDialog(pc.CartPad(path="bed.mp3"))
        self.assertTrue(dlg._duck.isChecked())
        dlg._loop.setChecked(True)
        self.assertFalse(dlg._duck.isChecked())
        self.assertTrue(dlg.pad().loop)

    def test_a_background_pad_round_trips(self):
        pad = pc.CartPad(path="bed.mp3", loop=True, duck=False, background=True)
        self.assertEqual(cpd.CartPadDialog(pad).pad(), pad)

    def test_background_switches_the_duck_off_and_locks_it(self):
        """A pad that dips under the music cannot also pull the music down —
        the two would hold each other at the bottom."""
        dlg = cpd.CartPadDialog(pc.CartPad(path="bed.mp3"))
        self.assertTrue(dlg._duck.isEnabled())
        dlg._background.setChecked(True)
        self.assertFalse(dlg._duck.isChecked())
        self.assertFalse(dlg._duck.isEnabled())
        self.assertTrue(dlg.pad().background)
        dlg._background.setChecked(False)
        self.assertTrue(dlg._duck.isEnabled())

    def test_a_background_pad_opens_with_the_duck_locked(self):
        dlg = cpd.CartPadDialog(pc.CartPad(path="bed.mp3", duck=False,
                                           background=True))
        self.assertFalse(dlg._duck.isEnabled())

    def test_there_is_no_dip_slider(self):
        """A background pad goes all the way down under a title; there is no
        depth left to set."""
        dlg = cpd.CartPadDialog(pc.CartPad(path="bed.mp3", background=True))
        self.assertFalse(hasattr(dlg, "_dip"))
        self.assertNotIn("Dip to", [lbl.text() for lbl in dlg.findChildren(QLabel)])

    def test_the_background_box_says_dip_while_titles_only_mute_it(self):
        dlg = cpd.CartPadDialog(pc.CartPad(path="bed.mp3"))
        self.assertIn("dip under the music", dlg._background.text())
        self.assertIn("comes back up", dlg._background.toolTip())

    def test_the_background_box_says_pause_when_titles_pause_it(self):
        """⚙ Background pads when a title starts: Pause. The pad carries on
        from where it was, so the box says that, not "dip"."""
        dlg = cpd.CartPadDialog(pc.CartPad(path="bed.mp3"), background_pauses=True)
        self.assertIn("pause while a title plays", dlg._background.text())
        self.assertNotIn("dip", dlg._background.text())
        self.assertIn("from where it was", dlg._background.toolTip())

    def test_the_wall_hands_its_background_mode_to_the_dialog(self):
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        w.set_wall(pc.DEFAULT_GRID, [pc.Page(pads={(0, 0): pc.CartPad(path="bed.mp3")})])
        w.set_background_pauses(True)
        with mock.patch.object(gc, "CartPadDialog") as dialog:
            dialog.return_value.exec.return_value = 0   # Cancel
            w._on_edit((0, 0, 0))
        self.assertTrue(dialog.call_args.kwargs["background_pauses"])

    def test_the_window_tells_the_wall(self):
        from types import SimpleNamespace
        from typing import Any, cast

        from player.audio.mix import OutputMix
        from player.window.main_cartwall import CartwallMixin
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        host = cast(Any, SimpleNamespace(_settings={"cart_bg_mode": "pause"},
                                         _mix=OutputMix(), _cartwall=w))
        CartwallMixin.apply_cart_settings(host)
        self.assertTrue(w._bg_pauses)
        host._settings = {}
        CartwallMixin.apply_cart_settings(host)
        self.assertFalse(w._bg_pauses)

    def test_stopping_the_others_round_trips(self):
        dlg = cpd.CartPadDialog(pc.CartPad(path="anthem.mp3"))
        self.assertFalse(dlg._stops_others.isChecked())
        dlg._stops_others.setChecked(True)
        self.assertTrue(dlg.pad().stops_others)
        pad = pc.CartPad(path="anthem.mp3", stops_others=True)
        self.assertEqual(cpd.CartPadDialog(pad).pad(), pad)

    def test_the_fade_time_round_trips(self):
        pad = pc.CartPad(path="a.mp3", fade_ms=2500)
        self.assertEqual(cpd.CartPadDialog(pad).pad().fade_ms, 2500)

    def test_a_zero_fade_reads_as_a_cut(self):
        """0 is legal and it clicks — the label has to say so, or it looks like
        a slider that simply failed to move."""
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3", fade_ms=400))
        dlg._fade.setValue(0)
        self.assertEqual(dlg._fade_lbl.text(), "cut")
        self.assertEqual(dlg.pad().fade_ms, 0)

    def test_a_pad_follows_the_wall_until_it_is_given_its_own_fade(self):
        """'a global option for fadeout time, which i can overwrite at each
        card' — untouched, the pad stores nothing and follows the wall."""
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3"), wall_fade_ms=2000)
        self.assertFalse(dlg._fade_own.isChecked())
        self.assertFalse(dlg._fade.isEnabled())
        self.assertEqual(dlg._fade.value(), 2000)      # shown, not stored
        self.assertIn("(wall)", dlg._fade_lbl.text())
        self.assertIsNone(dlg.pad().fade_ms)
        dlg._fade_own.setChecked(True)
        dlg._fade.setValue(1200)
        self.assertEqual(dlg.pad().fade_ms, 1200)
        self.assertNotIn("(wall)", dlg._fade_lbl.text())

    def test_dropping_the_override_goes_back_to_the_wall(self):
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3", fade_ms=100),
                               wall_fade_ms=2000)
        self.assertTrue(dlg._fade_own.isChecked())
        dlg._fade_own.setChecked(False)
        self.assertIsNone(dlg.pad().fade_ms)
        self.assertEqual(dlg._fade.value(), 2000)

    def test_the_volume_slider_is_heard_while_it_moves(self):
        """'when i am in settings and adjust volume auto apply it' — the level
        goes out on every step, not on Ok."""
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3"))
        seen = []
        dlg.previewVolume.connect(seen.append)
        dlg._vol.setValue(30)
        dlg._vol.setValue(45)
        self.assertEqual(seen, [0.30, 0.45])

    def test_the_preview_stops_when_the_dialog_closes(self):
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3"))
        seen = []
        dlg.previewFire.connect(seen.append)
        dlg._play_btn.setChecked(True)
        self.assertEqual(dlg._play_btn.text(), "⏹")
        dlg.reject()
        self.assertEqual(seen, [True, False])

    def test_a_multi_pad_edit_says_so(self):
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3"), pad_count=4)
        captions = [w.text() for w in dlg.findChildren(gc.QLabel)]
        self.assertTrue(any("4 pads selected" in c for c in captions), captions)


class TypedValueTest(unittest.TestCase):
    """'for the cardwall settings of volume and fade out allow double click to
    tip a value' — the readout beside each slider is a field as well."""

    def _type(self, label, text):
        """Double-click, type, Enter."""
        label.double_clicked.emit()
        label._edit.setText(text)
        label._edit.editingFinished.emit()

    def test_a_double_click_offers_the_bare_number(self):
        """The caption reads '25 %' and '1.5 s (wall)'; the field must open on
        what a typist would start from."""
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3", volume=0.25,
                                          fade_ms=1500))
        dlg._vol_lbl.double_clicked.emit()
        self.assertEqual(dlg._vol_lbl._edit.text(), "25")
        dlg._fade_lbl.double_clicked.emit()
        self.assertEqual(dlg._fade_lbl._edit.text(), "1.5")

    def test_a_typed_per_cent_moves_the_volume(self):
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3"))
        seen = []
        dlg.previewVolume.connect(seen.append)
        self._type(dlg._vol_lbl, "42")
        self.assertEqual(dlg._vol.value(), 42)
        self.assertEqual(dlg.pad().volume, 0.42)
        self.assertEqual(seen, [0.42])          # heard at once, as when dragged
        self.assertTrue(dlg._vol_lbl._edit.isHidden())

    def test_a_typed_fade_is_read_as_seconds(self):
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3", fade_ms=100))
        self._type(dlg._fade_lbl, "2.5")
        self.assertEqual(dlg.pad().fade_ms, 2500)

    def test_the_unit_may_be_typed_along_with_it(self):
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3", fade_ms=100))
        self._type(dlg._fade_lbl, "3 s")
        self.assertEqual(dlg.pad().fade_ms, 3000)
        self._type(dlg._vol_lbl, "60 %")
        self.assertEqual(dlg._vol.value(), 60)

    def test_a_german_comma_is_a_decimal_point(self):
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3", fade_ms=100))
        self._type(dlg._fade_lbl, "1,5")
        self.assertEqual(dlg.pad().fade_ms, 1500)

    def test_a_value_past_the_end_of_the_slider_is_clamped(self):
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3", fade_ms=100))
        self._type(dlg._fade_lbl, "999")
        self.assertEqual(dlg.pad().fade_ms, pc.MAX_FADE_MS)

    def test_nonsense_leaves_the_slider_where_it_was(self):
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3", fade_ms=800))
        self._type(dlg._fade_lbl, "later")
        self.assertEqual(dlg.pad().fade_ms, 800)

    def test_escape_abandons_what_was_typed(self):
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3", fade_ms=800))
        dlg._fade_lbl.double_clicked.emit()
        dlg._fade_lbl._edit.setText("4")
        _app.sendEvent(dlg._fade_lbl._edit,
                       QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape,
                                 Qt.KeyboardModifier.NoModifier))
        self.assertTrue(dlg._fade_lbl._edit.isHidden())
        self.assertEqual(dlg.pad().fade_ms, 800)
        # The focus-out that follows the hide must not commit it after all.
        dlg._fade_lbl._edit.editingFinished.emit()
        self.assertEqual(dlg.pad().fade_ms, 800)

    def test_a_pad_that_follows_the_wall_has_nothing_to_type(self):
        """The slider is greyed out there, and so is the number beside it."""
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3"), wall_fade_ms=2000)
        self.assertFalse(dlg._fade.isEnabled())
        dlg._fade_lbl.double_clicked.emit()
        self.assertIsNone(dlg._fade_lbl._edit)
        self.assertIsNone(dlg.pad().fade_ms)

    def test_enter_does_not_close_the_settings_window(self):
        """'enter on key close whole window' — a QLineEdit commits Return and
        then hands the key on, and the next thing in line is Ok."""
        dlg = cpd.CartPadDialog(pc.CartPad(path="a.mp3", volume=0.25))
        self.addCleanup(reap_widget, dlg)
        dlg.show()          # Ok only becomes the default button once shown
        _app.processEvents()
        dlg._vol_lbl.double_clicked.emit()
        dlg._vol_lbl._edit.setText("42")
        _app.sendEvent(dlg._vol_lbl._edit,
                       QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return,
                                 Qt.KeyboardModifier.NoModifier))
        self.assertEqual(dlg._vol.value(), 42)      # typed value kept
        self.assertTrue(dlg._vol_lbl._edit.isHidden())
        self.assertEqual(dlg.result(), 0)
        self.assertFalse(dlg.isHidden())

class MultiSelectTest(unittest.TestCase):
    """'allow multiselect of a card in edit mode to color it or activate another
    setting' — one right-click recolours six pads instead of six right-clicks."""

    def setUp(self):
        self.w = gc.CartwallWidget()
        self.w.set_wall((2, 8), [pc.Page(pads={
            (0, 0): pc.CartPad(path=_SAMPLE),
            (0, 1): pc.CartPad(path=_SAMPLE),
            (1, 0): pc.CartPad(path=_SAMPLE)})])
        self.w.set_edit(True)

    def tearDown(self):
        self.w.deleteLater()

    def test_a_plain_click_selects_one_pad(self):
        self.w._on_select((0, 0, 0), False)
        self.w._on_select((0, 0, 1), False)
        self.assertEqual(self.w.selection(), {(0, 0, 1)})

    def test_ctrl_click_adds_and_takes_away(self):
        self.w._on_select((0, 0, 0), False)
        self.w._on_select((0, 0, 1), True)
        self.assertEqual(self.w.selection(), {(0, 0, 0), (0, 0, 1)})
        self.w._on_select((0, 0, 1), True)
        self.assertEqual(self.w.selection(), {(0, 0, 0)})

    def test_a_selected_pad_is_outlined_not_filled(self):
        """The fill colours already mean 'running' and 'this much has played' —
        a selection that filled a pad would lie about its state."""
        self.w._on_select((0, 0, 0), False)
        sheet = self.w._buttons[(0, 0, 0)].styleSheet()
        self.assertIn(f"2px solid {gc._SEL_BORDER}", sheet)
        self.assertNotIn(gc._SEL_BORDER, sheet.split("background:")[1])

    def test_colouring_hits_the_whole_selection(self):
        self.w._on_select((0, 0, 0), False)
        self.w._on_select((0, 1, 0), True)
        self.w._on_colour((0, 0, 0), "#2f8f4e")
        self.assertEqual(self.w.pad_at((0, 0, 0)).colour, "#2f8f4e")
        self.assertEqual(self.w.pad_at((0, 1, 0)).colour, "#2f8f4e")
        self.assertEqual(self.w.pad_at((0, 0, 1)).colour, "")

    def test_an_edit_outside_the_selection_hits_only_that_pad(self):
        """Right-clicking a pad that is not in the selection works on THAT pad,
        the way every file manager behaves."""
        self.w._on_select((0, 0, 0), False)
        self.w._on_select((0, 0, 1), True)
        self.w._on_colour((0, 1, 0), "#b23b3b")
        self.assertEqual(self.w.pad_at((0, 1, 0)).colour, "#b23b3b")
        self.assertEqual(self.w.pad_at((0, 0, 0)).colour, "")

    def test_clearing_empties_every_selected_pad(self):
        self.w._on_select((0, 0, 0), False)
        self.w._on_select((0, 0, 1), True)
        self.w._on_clear((0, 0, 0))
        self.assertEqual(pc.pad_count(self.w.pages()), 1)
        self.assertEqual(self.w.selection(), set())

    def test_locking_the_wall_drops_the_selection(self):
        self.w._on_select((0, 0, 0), False)
        self.w.set_edit(False)
        self.assertEqual(self.w.selection(), set())
        self.assertFalse(self.w._buttons[(0, 0, 0)].selected())

    def test_a_page_turn_drops_the_selection(self):
        """A selection is a set of CELLS, and after a page turn those cells hold
        something else entirely."""
        self.w._add_page()          # the wall under test has one page
        self.w.step_page(-1)
        self.w._on_select((0, 0, 0), False)
        self.w.step_page(1)
        self.assertEqual(self.w.selection(), set())

    def test_a_settings_edit_shares_only_what_a_pad_can_share(self):
        self.w._on_select((0, 0, 0), False)
        self.w._on_select((0, 0, 1), True)
        edited = pc.CartPad(path=_SAMPLE, label="Tusch", colour="#7a3fbf",
                            volume=0.25, loop=True, duck=False, fade_ms=1500,
                            background=True, shortcut="Ctrl+Shift+T")
        with _accepted_dialog(edited):
            self.w._on_edit((0, 0, 0))
        other = self.w.pad_at((0, 0, 1))
        self.assertTrue(other.background)
        self.assertEqual(other.colour, "#7a3fbf")
        self.assertAlmostEqual(other.volume, 0.25)
        self.assertTrue(other.loop)
        self.assertEqual(other.fade_ms, 1500)
        self.assertEqual(other.label, "")        # its own, not the anchor's
        self.assertEqual(other.shortcut, "")     # six pads cannot share one key

    def test_a_settings_edit_hands_on_only_what_was_changed(self):
        # Marcel: "allow multi select setting change f.e. to configure every
        # selected pad as duck or solo". Ticking two boxes must not also copy
        # the anchor's colour and volume over pads that have their own.
        own = self.w.pad_at((0, 0, 1))
        own.colour, own.volume, own.loop = "#f4d35e", 0.5, True
        self.w._on_select((0, 0, 0), False)
        self.w._on_select((0, 0, 1), True)
        edited = pc.CartPad(path=_SAMPLE, duck=False, stops_others=True)
        with _accepted_dialog(edited):
            self.w._on_edit((0, 0, 0))
        other = self.w.pad_at((0, 0, 1))
        self.assertFalse(other.duck)
        self.assertTrue(other.stops_others)
        self.assertEqual(other.colour, "#f4d35e")
        self.assertAlmostEqual(other.volume, 0.5)
        self.assertTrue(other.loop)


if __name__ == "__main__":
    unittest.main()
