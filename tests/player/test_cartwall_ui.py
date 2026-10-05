"""CartwallWidget and its pads, on their own — no MainWindow, no audio.

Text is asserted, never rendering: the offscreen QPA has no fonts, so a
screenshot of this page is tofu. What matters here is that the grid has the
right shape, that a pad edit reaches the model, and that the wall never loses a
pad when the operator resizes it mid-tournament.
"""
import contextlib
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_cartui_"))

from PySide6.QtCore import (  # noqa: E402
    QEvent, QMimeData, QPoint, QPointF, QUrl, Qt)
from PySide6.QtGui import (  # noqa: E402
    QDropEvent, QKeyEvent, QKeySequence, QMouseEvent)
from PySide6.QtWidgets import QApplication  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from planner import cartwall as pc  # noqa: E402
from player import cartwall as gc  # noqa: E402

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


def _dbl_click():
    return QMouseEvent(QMouseEvent.Type.MouseButtonDblClick, QPointF(2, 2),
                       QPointF(2, 2), Qt.MouseButton.LeftButton,
                       Qt.MouseButton.LeftButton,
                       Qt.KeyboardModifier.NoModifier)


@contextlib.contextmanager
def _typed_text(text, ok=True):
    """Stand in for QInputDialog.getText — a modal exec() never returns here."""
    real = gc.QInputDialog.getText
    gc.QInputDialog.getText = staticmethod(lambda *a, **kw: (text, ok))
    try:
        yield
    finally:
        gc.QInputDialog.getText = real


@contextlib.contextmanager
def _fade_dialog(ms, ok=True):
    """Stand in for WallFadeDialog, for the same reason as _typed_text."""
    class _Stub:
        def __init__(self, *a, **kw):
            pass

        def exec(self):
            return (gc.QDialog.DialogCode.Accepted if ok
                    else gc.QDialog.DialogCode.Rejected)

        def fade_ms(self):
            return ms

    real = gc.WallFadeDialog
    gc.WallFadeDialog = _Stub
    try:
        yield
    finally:
        gc.WallFadeDialog = real


@contextlib.contextmanager
def _shortcuts_dialog(slot_keys=pc.SLOT_KEYS, pad_keys=None, ok=True):
    """Stand in for CartShortcutsDialog: it hands back the two layers the real
    one collects, without ever opening. `slot_keys` defaults to the standard
    ones so a test about pad keys does not silently wipe the slot keys."""
    class _Stub:
        def __init__(self, *a, **kw):
            pass

        def exec(self):
            return (gc.QDialog.DialogCode.Accepted if ok
                    else gc.QDialog.DialogCode.Rejected)

        def slot_keys(self):
            return tuple(slot_keys)

        def pad_keys(self):
            return dict(pad_keys or {})

    real = gc.CartShortcutsDialog
    gc.CartShortcutsDialog = _Stub
    try:
        yield
    finally:
        gc.CartShortcutsDialog = real


@contextlib.contextmanager
def _answer(yes: bool):
    """Stand in for QMessageBox.question — modal, so never let one really open."""
    real = gc.QMessageBox.question
    button = (gc.QMessageBox.StandardButton.Yes if yes
              else gc.QMessageBox.StandardButton.No)
    gc.QMessageBox.question = staticmethod(lambda *a, **kw: button)
    try:
        yield
    finally:
        gc.QMessageBox.question = real


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


class _WallCase(unittest.TestCase):
    """A fresh cartwall widget per test."""

    def setUp(self):
        self.w = gc.CartwallWidget()

    def tearDown(self):
        self.w.deleteLater()

    def _pad_widget(self, row, col):
        return self.w._buttons[(self.w.current_page(), row, col)]


class WallGridTest(_WallCase):
    """The grid and its pages — resizing must never lose a pad."""

    def test_a_fresh_wall_is_the_default_grid(self):
        cols, rows = pc.DEFAULT_GRID
        self.assertEqual(len(self.w._buttons), cols * rows)

    def test_every_offered_grid_size_builds(self):
        for grid in pc.GRID_SIZES:
            self.w.set_wall(grid, [pc.blank_page()])
            self.assertEqual(len(self.w._buttons), grid[0] * grid[1])

    def test_the_grid_combo_offers_two_by_seven(self):
        row = pc.GRID_SIZES.index((2, 7))
        self.assertEqual(self.w._size_box.itemText(row), "2 × 7")
        self.w._on_size_picked(row)
        self.assertEqual(self.w.grid(), (2, 7))
        self.assertEqual(len(self.w._buttons), 14)

    def test_shrinking_the_grid_keeps_every_pad(self):
        pages = [pc.Page(pads={(r, c): pc.CartPad(path=f"{r}_{c}.mp3")
                               for r in range(6) for c in range(8)})]
        self.w.set_wall((8, 6), pages)
        self.w._on_size_picked(pc.GRID_SIZES.index((4, 4)))
        self.assertEqual(self.w.grid(), (4, 4))
        self.assertEqual(pc.pad_count(self.w.pages()), 48)
        self.assertEqual(len(self.w._buttons), 16)

    def test_growing_the_grid_leaves_every_pad_where_it_was(self):
        pages = [pc.Page(pads={(3, 3): pc.CartPad(path="corner.mp3")})]
        self.w.set_wall((4, 4), pages)
        self.w._on_size_picked(pc.GRID_SIZES.index((8, 6)))
        self.assertEqual(self.w.pages()[0].pads[(3, 3)].path, "corner.mp3")

    # ── taps ─────────────────────────────────────────────────────────────────
    def test_an_assigned_pad_reports_its_key_and_an_empty_one_says_nothing(self):
        seen = []
        self.w.padClicked.connect(seen.append)
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(1, 1): pc.CartPad(path="a.mp3")})])
        self._pad_widget(1, 1).tapped.emit((0, 1, 1))
        self.assertEqual(seen, [(0, 1, 1)])
        # An empty pad opens the file chooser instead of firing; the signal it
        # would fire is simply never emitted.
        self.assertIsNone(self._pad_widget(0, 0).pad())

    # ── pages ────────────────────────────────────────────────────────────────
    def test_paging_past_the_end_does_nothing(self):
        """▶ turns pages, ➕ makes them. A nav that quietly conjures a page when
        you overshoot is how a wall collects pages nobody asked for."""
        self.w.set_wall(pc.DEFAULT_GRID, [pc.blank_page()])
        self.w._step_page(1)
        self.assertEqual(len(self.w.pages()), 1)
        self.assertEqual(self.w.current_page(), 0)
        self.w._add_page()
        self.assertEqual(self.w.current_page(), 1)
        self.w._step_page(-1)
        self.assertEqual(self.w.current_page(), 0)

    def test_a_fresh_wall_already_has_a_second_page(self):
        self.assertEqual(len(self.w.pages()), pc.DEFAULT_PAGES)

    def test_page_one_cannot_be_paged_off_the_front(self):
        self.w._step_page(-1)
        self.assertEqual(self.w.current_page(), 0)

    # ── missing files ────────────────────────────────────────────────────────
    def test_a_pad_whose_file_is_gone_is_marked_not_removed(self):
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path="X:\\gone.mp3")})])
        button = self._pad_widget(0, 0)
        self.assertTrue(button._missing)
        self.assertTrue(button._title.text().startswith("⚠"))
        self.assertIsNotNone(self.w.pad_at((0, 0, 0)))


class WallRunningTest(_WallCase):
    """What a running pad shows: the countdown, the light, the band."""

    # ── playing feedback ─────────────────────────────────────────────────────
    def test_the_countdown_text_follows_the_tick(self):
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path="a.mp3")})])
        button = self._pad_widget(0, 0)
        self.assertEqual(button._time.text(), "--:--")
        self.w.set_playing((0, 0, 0), True)
        self.w.set_remaining((0, 0, 0), 93_000, 0.5)
        self.assertEqual(button._time.text(), "01:33")

    def test_a_loop_pad_shows_infinity_rather_than_counting_down(self):
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path="bed.mp3",
                                                          loop=True)})])
        self.w.set_playing((0, 0, 0), True)
        self.w.set_remaining((0, 0, 0), 4_000, 0.1)
        self.assertEqual(self._pad_widget(0, 0)._time.text(), "∞")

    def test_a_playing_pad_stays_lit_across_a_grid_change(self):
        self.w.set_wall((8, 6),
                        [pc.Page(pads={(0, 0): pc.CartPad(path="a.mp3")})])
        self.w.set_playing((0, 0, 0), True)
        self.w._on_size_picked(pc.GRID_SIZES.index((4, 4)))
        self.assertTrue(self._pad_widget(0, 0)._playing)

    def test_the_transport_is_dead_while_nothing_plays(self):
        self.assertFalse(self.w._stop_btn.isEnabled())
        self.w.set_active(1)
        self.assertTrue(self.w._stop_btn.isEnabled())
        self.w.set_active(0)
        self.assertFalse(self.w._stop_btn.isEnabled())

    def test_the_transport_button_reports_out(self):
        stopped = []
        self.w.stopAll.connect(lambda: stopped.append(True))
        self.w.set_active(1)
        self.w._stop_btn.click()
        self.assertEqual(stopped, [True])

    # ── the playing animation ────────────────────────────────────────────────
    def test_the_played_share_is_kept_for_the_progress_band(self):
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path="a.mp3")})])
        button = self._pad_widget(0, 0)
        self.w.set_playing((0, 0, 0), True)
        self.w.set_remaining((0, 0, 0), 5_000, 0.4)
        self.assertAlmostEqual(button._frac, 0.4)
        # Stopping wipes it, or the next fire would start half-washed.
        self.w.set_playing((0, 0, 0), False)
        self.assertEqual(button._frac, 0.0)

    def test_a_fading_pad_blinks_and_stops_when_it_is_gone(self):
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path="a.mp3")})])
        button = self._pad_widget(0, 0)
        self.w.set_playing((0, 0, 0), True)
        self.w.set_fading((0, 0, 0), True)
        self.assertTrue(button._blink.isActive())
        self.w.set_playing((0, 0, 0), False)
        self.assertFalse(button._blink.isActive())


class WallColourTest(_WallCase):
    """Pad colours: picked, defaulted, and readable either way."""

    def test_the_context_menu_colour_lands_on_the_pad_and_is_persisted(self):
        seen = []
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path=_SAMPLE)})])
        self.w.changed.connect(lambda: seen.append(True))
        self.w._on_colour((0, 0, 0), "#b23b3b")
        self.assertEqual(self.w.pad_at((0, 0, 0)).colour, "#b23b3b")
        self.assertEqual(seen, [True])
        self.assertIn("#b23b3b", self._pad_widget(0, 0).styleSheet())

    def test_the_wall_default_colour_reaches_pads_that_have_none(self):
        self.w.set_wall(pc.DEFAULT_GRID, [pc.Page(pads={
            (0, 0): pc.CartPad(path=_SAMPLE),
            (0, 1): pc.CartPad(path=_SAMPLE, colour="#2f8f4e")})])
        # Not white: white is already the standard, so it would prove nothing.
        self.w._on_default_colour("#c8871a")
        self.assertEqual(self.w.default_colour(), "#c8871a")
        self.assertIn("#c8871a", self._pad_widget(0, 0).styleSheet())
        self.assertIn("#2f8f4e", self._pad_widget(0, 1).styleSheet())

    def test_a_white_pad_gets_dark_text_and_an_olive_one_light_text(self):
        self.assertEqual(gc._text_on("#ffffff"), "#2b3038")
        self.assertEqual(gc._text_on("#8a8a2b"), "#ffffff")

    def test_the_wall_default_survives_being_reloaded(self):
        self.w.set_wall((4, 4), [pc.blank_page()], 0, "#7a3fbf")
        self.assertEqual(self.w.default_colour(), "#7a3fbf")


class WallKeyTest(_WallCase):
    """Ctrl+1…9 on the slots, and a pad's own key over them."""

    def test_the_first_nine_slots_carry_ctrl_1_to_ctrl_9(self):
        keys = sorted(s.key().toString() for s in self.w._shortcuts)
        self.assertEqual(keys, sorted(pc.SLOT_KEYS))
        self.assertEqual(self._pad_widget(0, 0)._shortcut, "Ctrl+1")

    def test_a_slot_key_fires_the_pad_that_sits_there(self):
        seen = []
        self.w.padClicked.connect(seen.append)
        self.w.set_wall((4, 4),
                        [pc.Page(pads={(0, 1): pc.CartPad(path="a.mp3")})])
        for shortcut in self.w._shortcuts:
            if shortcut.key().toString() == "Ctrl+2":
                shortcut.activated.emit()
        self.assertEqual(seen, [(0, 0, 1)])

    def test_a_pad_with_its_own_key_keeps_it_and_drops_the_slot_default(self):
        self.w.set_wall((4, 4), [pc.Page(pads={
            (0, 0): pc.CartPad(path="a.mp3", shortcut="Ctrl+2")})])
        keys = sorted(s.key().toString() for s in self.w._shortcuts)
        self.assertEqual(keys.count("Ctrl+2"), 1)
        self.assertEqual(self._pad_widget(0, 0)._shortcut, "Ctrl+2")
        # Ctrl+2's own slot now has no key at all — the pad took it.
        self.assertEqual(self._pad_widget(0, 1)._shortcut, "")

    def test_a_pad_key_on_another_page_still_works(self):
        self.w.set_wall((4, 4), [pc.blank_page(), pc.Page(pads={
            (3, 3): pc.CartPad(path="far.mp3", shortcut="Ctrl+Shift+F")})])
        seen = []
        self.w.padClicked.connect(seen.append)
        for shortcut in self.w._shortcuts:
            if shortcut.key().toString() == "Ctrl+Shift+F":
                shortcut.activated.emit()
        self.assertEqual(seen, [(1, 3, 3)])


class WallOwnSlotKeyTest(_WallCase):
    """A wall whose slots were remapped away from Ctrl+1…9."""

    def test_a_walls_own_slot_keys_are_what_the_slots_answer_to(self):
        self.w.set_wall((4, 4), [pc.blank_page()], slot_keys=("F5", "F6"))
        keys = sorted(s.key().toString() for s in self.w._shortcuts)
        self.assertEqual(keys, ["F5", "F6"])
        self.assertEqual(self._pad_widget(0, 0)._shortcut, "F5")
        self.assertEqual(self._pad_widget(0, 1)._shortcut, "F6")
        self.assertEqual(self._pad_widget(0, 2)._shortcut, "")

    def test_a_remapped_slot_key_fires_the_pad_that_sits_there(self):
        seen = []
        self.w.padClicked.connect(seen.append)
        self.w.set_wall((4, 4),
                        [pc.Page(pads={(0, 1): pc.CartPad(path="a.mp3")})],
                        slot_keys=("F5", "F6"))
        for shortcut in self.w._shortcuts:
            if shortcut.key().toString() == "F6":
                shortcut.activated.emit()
        self.assertEqual(seen, [(0, 0, 1)])

    def test_a_wall_that_brings_no_keys_gets_the_standard_ones(self):
        self.w.set_wall((4, 4), [pc.blank_page()])
        self.assertEqual(self.w.slot_keys(), pc.SLOT_KEYS)

    def test_rebinding_the_slot_keys_re_labels_the_faces_and_saves(self):
        seen = []
        self.w.changed.connect(lambda: seen.append(True))
        self.w.set_slot_keys(("Num+1", "Num+2"))
        self.assertEqual(self._pad_widget(0, 0)._shortcut, "Num+1")
        self.assertEqual(self.w.slot_keys(), ("Num+1", "Num+2"))
        self.assertEqual(len(seen), 1)

    def test_rebinding_to_the_keys_already_in_use_saves_nothing(self):
        seen = []
        self.w.changed.connect(lambda: seen.append(True))
        self.w.set_slot_keys(pc.SLOT_KEYS)
        self.assertEqual(seen, [])

    def test_a_pad_key_still_wins_over_a_remapped_slot_key(self):
        self.w.set_wall((4, 4), [pc.Page(pads={
            (0, 0): pc.CartPad(path="a.mp3", shortcut="F6")})],
            slot_keys=("F5", "F6"))
        keys = sorted(s.key().toString() for s in self.w._shortcuts)
        self.assertEqual(keys.count("F6"), 1)
        self.assertEqual(self._pad_widget(0, 1)._shortcut, "")


class WallShortcutsDialogWiringTest(_WallCase):
    """What the ⌨ Shortcuts… dialog hands back, applied to the wall."""

    def _wall_with_a_pad(self):
        self.w.set_wall((4, 4), [pc.Page(pads={
            (0, 0): pc.CartPad(path=_SAMPLE, label="Tusch")})])

    def test_ok_applies_both_layers_and_saves_once(self):
        self._wall_with_a_pad()
        seen = []
        self.w.changed.connect(lambda: seen.append(True))
        with _shortcuts_dialog(slot_keys=("F5", "F6"),
                               pad_keys={(0, 0, 0): "F9"}):
            self.w._on_shortcuts()
        self.assertEqual(self.w.slot_keys(), ("F5", "F6"))
        self.assertEqual(self.w.pages()[0].pads[(0, 0)].shortcut, "F9")
        self.assertEqual(len(seen), 1)      # one rebuild, however much changed

    def test_cancel_leaves_every_key_alone(self):
        self._wall_with_a_pad()
        seen = []
        self.w.changed.connect(lambda: seen.append(True))
        with _shortcuts_dialog(slot_keys=("F5",), pad_keys={(0, 0, 0): "F9"},
                               ok=False):
            self.w._on_shortcuts()
        self.assertEqual(self.w.slot_keys(), pc.SLOT_KEYS)
        self.assertEqual(self.w.pages()[0].pads[(0, 0)].shortcut, "")
        self.assertEqual(seen, [])

    def test_changing_nothing_saves_nothing(self):
        self._wall_with_a_pad()
        seen = []
        self.w.changed.connect(lambda: seen.append(True))
        with _shortcuts_dialog(pad_keys={(0, 0, 0): ""}):
            self.w._on_shortcuts()
        self.assertEqual(seen, [])

    def test_a_new_pad_key_reaches_a_running_voice(self):
        """padRefreshed is how a live voice hears about an edit."""
        self._wall_with_a_pad()
        seen = []
        self.w.padRefreshed.connect(lambda key, pad: seen.append((key, pad)))
        with _shortcuts_dialog(pad_keys={(0, 0, 0): "F9"}):
            self.w._on_shortcuts()
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][0], (0, 0, 0))
        self.assertEqual(seen[0][1].shortcut, "F9")
        self.assertEqual(seen[0][1].label, "Tusch")   # nothing else disturbed


class KeyPickerTest(unittest.TestCase):
    """Press it, pick it, or ✕ it — the same value seen twice."""

    def setUp(self):
        self.p = gc._KeyPicker("Ctrl+1")

    def tearDown(self):
        self.p.deleteLater()

    def test_it_opens_on_the_key_it_was_given(self):
        self.assertEqual(self.p.sequence(), "Ctrl+1")

    def test_picking_from_the_list_sets_the_key_and_reports_it(self):
        seen = []
        self.p.changed.connect(lambda: seen.append(True))
        self.p._on_box(self.p._box.findData("F9"))
        self.assertEqual(self.p.sequence(), "F9")
        self.assertEqual(len(seen), 1)

    def test_a_group_caption_is_not_a_key(self):
        seen = []
        self.p.changed.connect(lambda: seen.append(True))
        caption = next(i for i in range(self.p._box.count())
                       if self.p._box.itemData(i) is None)
        self.p._on_box(caption)
        self.assertEqual(self.p.sequence(), "Ctrl+1")
        self.assertEqual(seen, [])

    def test_the_cross_clears_the_key(self):
        seen = []
        self.p.changed.connect(lambda: seen.append(True))
        self.p._on_clear()
        self.assertEqual(self.p.sequence(), "")
        self.assertEqual(len(seen), 1)

    def test_a_pressed_key_shows_up_in_the_list_too(self):
        self.p.set_sequence("F9")
        self.assertEqual(self.p._box.currentData(), "F9")

    def test_a_key_the_list_does_not_offer_is_still_kept(self):
        self.p.set_sequence("Ctrl+Shift+T")
        self.assertEqual(self.p.sequence(), "Ctrl+Shift+T")
        self.assertEqual(self.p._box.currentIndex(), 0)

    def test_every_offered_key_survives_being_parsed_back(self):
        """A key that does not round-trip is one the user picks and that then
        never fires."""
        for _group, keys in gc._KEY_CHOICES:
            for key in keys:
                self.assertEqual(QKeySequence(key).toString(), key)

    def test_a_key_already_in_use_says_so_in_the_list(self):
        self.p.annotate({"F9": "slot 3"})
        idx = self.p._box.findData("F9")
        self.assertIn("slot 3", self.p._box.itemText(idx))


class ShortcutsDialogTest(unittest.TestCase):
    """The dialog itself: two layers, and the clashes marked before they bite."""

    def _dialog(self, pages, slot_keys=pc.SLOT_KEYS, grid=(4, 4)):
        dlg = gc.CartShortcutsDialog(grid, pages, slot_keys)
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
        self.assertEqual(dlg._slot_warnings[0].text(), "⚠ already used by pad "
                                                       "p1 (0,3)")
        self.assertEqual(dlg._pad_pickers[0][2].text(), "")
        self.assertIn("1 key claimed twice", dlg._clash.text())

    def test_two_slots_on_one_key_mark_the_second(self):
        dlg = self._dialog([pc.blank_page()])
        dlg._slot_pickers[4].set_sequence("Ctrl+1")
        dlg._refresh_conflicts()
        self.assertEqual(dlg._slot_warnings[0].text(), "")
        self.assertIn("slot 1", dlg._slot_warnings[4].text())

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

    def test_a_locked_pad_has_no_context_menu(self):
        """The menu is where clearing and recolouring live — exec() would block
        a test, so the guard returning before building one is the contract."""
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path=_SAMPLE)})])
        self.w._buttons[(0, 0, 0)]._context_menu(QPoint(0, 0))   # must not block

    def test_a_locked_wall_still_fires(self):
        seen = []
        self.w.padClicked.connect(seen.append)
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path=_SAMPLE)})])
        self.w._buttons[(0, 0, 0)].tapped.emit((0, 0, 0))
        self.assertEqual(seen, [(0, 0, 0)])

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


class WallShapeTest(unittest.TestCase):
    """The wall turns to match the edge it is docked on."""

    def setUp(self):
        self.w = gc.CartwallWidget()

    def tearDown(self):
        self.w.deleteLater()

    def test_a_fresh_wall_is_tall_for_the_right_hand_dock(self):
        self.assertTrue(pc.is_portrait(self.w.grid()))

    def test_a_top_dock_turns_the_wall_and_the_pads_come_along(self):
        self.w.set_wall((2, 8), [pc.Page(pads={
            (7, 0): pc.CartPad(path="bottom-left.mp3")})])
        self.w.set_portrait(False)
        self.assertEqual(self.w.grid(), (8, 2))
        self.assertEqual(self.w.pad_at((0, 0, 7)).path, "bottom-left.mp3")
        self.w.set_portrait(True)       # back to the side dock
        self.assertEqual(self.w.grid(), (2, 8))
        self.assertEqual(self.w.pad_at((0, 7, 0)).path, "bottom-left.mp3")

    def test_a_sounding_pad_stays_lit_where_the_turn_puts_it(self):
        self.w.set_wall((2, 8), [pc.Page(pads={
            (7, 0): pc.CartPad(path="bottom-left.mp3")})])
        self.w.set_playing((0, 7, 0), True)
        moved = []
        self.w.padsMoved.connect(moved.append)
        self.w.set_portrait(False)
        self.assertEqual(self.w._live, {(0, 0, 7)})
        self.assertTrue(self.w._buttons[(0, 0, 7)]._playing)
        self.assertEqual(moved, [{(0, 7, 0): (0, 0, 7)}])

    def test_a_sounding_pad_a_smaller_grid_relocates_stays_lit(self):
        self.w.set_wall((8, 6), [pc.Page(pads={
            (5, 7): pc.CartPad(path="corner.mp3")})])
        self.w.set_playing((0, 5, 7), True)
        moved = []
        self.w.padsMoved.connect(moved.append)
        self.w._on_size_picked(pc.GRID_SIZES.index((4, 4)))
        (new,) = [k for k in self.w._buttons
                  if (p := self.w.pad_at(k)) and p.path == "corner.mp3"]
        self.assertEqual(self.w._live, {new})
        self.assertEqual(moved, [{(0, 5, 7): new}])

    def test_a_turn_with_nothing_on_the_wall_moves_nothing(self):
        moved = []
        self.w.padsMoved.connect(moved.append)
        self.w.set_wall((2, 8), [pc.blank_page()])
        self.w.set_portrait(False)
        self.assertEqual(moved, [])

    def test_a_wall_already_the_right_way_round_is_left_alone(self):
        seen = []
        self.w.changed.connect(lambda: seen.append(True))
        self.w.set_portrait(True)
        self.assertEqual(seen, [])

    def test_shrinking_the_grid_leaves_no_stretch_on_the_empty_columns(self):
        """QGridLayout never drops a column, so a stale stretch would hold open
        a gap the pads cannot fill."""
        self.w.set_wall((8, 4), [pc.blank_page()])
        self.w.set_wall((2, 8), [pc.blank_page()])
        self.assertEqual(
            [self.w._grid_lyt.columnStretch(c)
             for c in range(self.w._grid_lyt.columnCount())][:8],
            [1, 1, 0, 0, 0, 0, 0, 0])


class ColourSwatchTest(unittest.TestCase):

    def test_every_offered_colour_paints_a_swatch(self):
        for value in gc.PAD_COLOURS.values():
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
        self.assertFalse(blues & {v.lower() for v in gc.PAD_COLOURS.values()})

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

    def test_the_wall_colour_can_be_set_from_a_pad(self):
        """The 🎨 header button is gone; the wall-wide fallback lives in the pad
        menu now, so the signal behind it has to reach the wall."""
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        w.set_edit(True)
        w.set_wall(pc.DEFAULT_GRID,
                   [pc.Page(pads={(0, 0): pc.CartPad(path=_SAMPLE)})])
        w._buttons[(0, 0, 0)].wall_colour_requested.emit("#c8871a")
        self.assertEqual(w.default_colour(), "#c8871a")
        self.assertIn("#c8871a", w._buttons[(0, 0, 0)].styleSheet())


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
        self.assertEqual(gc.CartPadDialog(pad).pad(), pad)

    def test_the_dialog_reads_back_what_was_edited(self):
        dlg = gc.CartPadDialog(pc.CartPad(path="a.mp3"))
        dlg._label.setText("Fanfare")
        dlg._vol.setValue(25)
        out = dlg.pad()
        self.assertEqual(out.label, "Fanfare")
        self.assertAlmostEqual(out.volume, 0.25)

    def test_a_pad_can_be_given_a_key_of_its_own(self):
        dlg = gc.CartPadDialog(pc.CartPad(path="a.mp3"), slot_key="Ctrl+1")
        self.assertEqual(dlg.pad().shortcut, "")
        dlg._key.setKeySequence(QKeySequence("Ctrl+Shift+T"))
        self.assertEqual(dlg.pad().shortcut, "Ctrl+Shift+T")

    def test_endless_repeat_switches_the_duck_off_with_it(self):
        """A bed holding the deck music down for a whole ceremony is never what
        anyone means by 'background music'."""
        dlg = gc.CartPadDialog(pc.CartPad(path="bed.mp3"))
        self.assertTrue(dlg._duck.isChecked())
        dlg._loop.setChecked(True)
        self.assertFalse(dlg._duck.isChecked())
        self.assertTrue(dlg.pad().loop)

    def test_the_fade_time_round_trips(self):
        pad = pc.CartPad(path="a.mp3", fade_ms=2500)
        self.assertEqual(gc.CartPadDialog(pad).pad().fade_ms, 2500)

    def test_a_zero_fade_reads_as_a_cut(self):
        """0 is legal and it clicks — the label has to say so, or it looks like
        a slider that simply failed to move."""
        dlg = gc.CartPadDialog(pc.CartPad(path="a.mp3", fade_ms=400))
        dlg._fade.setValue(0)
        self.assertEqual(dlg._fade_lbl.text(), "cut")
        self.assertEqual(dlg.pad().fade_ms, 0)

    def test_a_pad_follows_the_wall_until_it_is_given_its_own_fade(self):
        """'a global option for fadeout time, which i can overwrite at each
        card' — untouched, the pad stores nothing and follows the wall."""
        dlg = gc.CartPadDialog(pc.CartPad(path="a.mp3"), wall_fade_ms=2000)
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
        dlg = gc.CartPadDialog(pc.CartPad(path="a.mp3", fade_ms=100),
                               wall_fade_ms=2000)
        self.assertTrue(dlg._fade_own.isChecked())
        dlg._fade_own.setChecked(False)
        self.assertIsNone(dlg.pad().fade_ms)
        self.assertEqual(dlg._fade.value(), 2000)

    def test_the_volume_slider_is_heard_while_it_moves(self):
        """'when i am in settings and adjust volume auto apply it' — the level
        goes out on every step, not on Ok."""
        dlg = gc.CartPadDialog(pc.CartPad(path="a.mp3"))
        seen = []
        dlg.previewVolume.connect(seen.append)
        dlg._vol.setValue(30)
        dlg._vol.setValue(45)
        self.assertEqual(seen, [0.30, 0.45])

    def test_the_preview_stops_when_the_dialog_closes(self):
        dlg = gc.CartPadDialog(pc.CartPad(path="a.mp3"))
        seen = []
        dlg.previewFire.connect(seen.append)
        dlg._play_btn.setChecked(True)
        self.assertEqual(dlg._play_btn.text(), "⏹")
        dlg.reject()
        self.assertEqual(seen, [True, False])

    def test_a_multi_pad_edit_says_so(self):
        dlg = gc.CartPadDialog(pc.CartPad(path="a.mp3"), pad_count=4)
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
        dlg = gc.CartPadDialog(pc.CartPad(path="a.mp3", volume=0.25,
                                          fade_ms=1500))
        dlg._vol_lbl.double_clicked.emit()
        self.assertEqual(dlg._vol_lbl._edit.text(), "25")
        dlg._fade_lbl.double_clicked.emit()
        self.assertEqual(dlg._fade_lbl._edit.text(), "1.5")

    def test_a_typed_per_cent_moves_the_volume(self):
        dlg = gc.CartPadDialog(pc.CartPad(path="a.mp3"))
        seen = []
        dlg.previewVolume.connect(seen.append)
        self._type(dlg._vol_lbl, "42")
        self.assertEqual(dlg._vol.value(), 42)
        self.assertEqual(dlg.pad().volume, 0.42)
        self.assertEqual(seen, [0.42])          # heard at once, as when dragged
        self.assertTrue(dlg._vol_lbl._edit.isHidden())

    def test_a_typed_fade_is_read_as_seconds(self):
        dlg = gc.CartPadDialog(pc.CartPad(path="a.mp3", fade_ms=100))
        self._type(dlg._fade_lbl, "2.5")
        self.assertEqual(dlg.pad().fade_ms, 2500)

    def test_the_unit_may_be_typed_along_with_it(self):
        dlg = gc.CartPadDialog(pc.CartPad(path="a.mp3", fade_ms=100))
        self._type(dlg._fade_lbl, "3 s")
        self.assertEqual(dlg.pad().fade_ms, 3000)
        self._type(dlg._vol_lbl, "60 %")
        self.assertEqual(dlg._vol.value(), 60)

    def test_a_german_comma_is_a_decimal_point(self):
        dlg = gc.CartPadDialog(pc.CartPad(path="a.mp3", fade_ms=100))
        self._type(dlg._fade_lbl, "1,5")
        self.assertEqual(dlg.pad().fade_ms, 1500)

    def test_a_value_past_the_end_of_the_slider_is_clamped(self):
        dlg = gc.CartPadDialog(pc.CartPad(path="a.mp3", fade_ms=100))
        self._type(dlg._fade_lbl, "999")
        self.assertEqual(dlg.pad().fade_ms, pc.MAX_FADE_MS)

    def test_nonsense_leaves_the_slider_where_it_was(self):
        dlg = gc.CartPadDialog(pc.CartPad(path="a.mp3", fade_ms=800))
        self._type(dlg._fade_lbl, "later")
        self.assertEqual(dlg.pad().fade_ms, 800)

    def test_escape_abandons_what_was_typed(self):
        dlg = gc.CartPadDialog(pc.CartPad(path="a.mp3", fade_ms=800))
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
        dlg = gc.CartPadDialog(pc.CartPad(path="a.mp3"), wall_fade_ms=2000)
        self.assertFalse(dlg._fade.isEnabled())
        dlg._fade_lbl.double_clicked.emit()
        self.assertIsNone(dlg._fade_lbl._edit)
        self.assertIsNone(dlg.pad().fade_ms)

    def test_enter_does_not_close_the_settings_window(self):
        """'enter on key close whole window' — a QLineEdit commits Return and
        then hands the key on, and the next thing in line is Ok."""
        dlg = gc.CartPadDialog(pc.CartPad(path="a.mp3", volume=0.25))
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

    def test_the_wall_fade_takes_a_typed_value_too(self):
        dlg = gc.WallFadeDialog(1500)
        self._type(dlg._lbl, "0.5")
        self.assertEqual(dlg.fade_ms(), 500)


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
        self.w._step_page(-1)
        self.w._on_select((0, 0, 0), False)
        self.w._step_page(1)
        self.assertEqual(self.w.selection(), set())

    def test_a_settings_edit_shares_only_what_a_pad_can_share(self):
        self.w._on_select((0, 0, 0), False)
        self.w._on_select((0, 0, 1), True)
        edited = pc.CartPad(path=_SAMPLE, label="Tusch", colour="#7a3fbf",
                            volume=0.25, loop=True, duck=False, fade_ms=1500,
                            shortcut="Ctrl+Shift+T")
        with _accepted_dialog(edited):
            self.w._on_edit((0, 0, 0))
        other = self.w.pad_at((0, 0, 1))
        self.assertEqual(other.colour, "#7a3fbf")
        self.assertAlmostEqual(other.volume, 0.25)
        self.assertTrue(other.loop)
        self.assertEqual(other.fade_ms, 1500)
        self.assertEqual(other.label, "")        # its own, not the anchor's
        self.assertEqual(other.shortcut, "")     # six pads cannot share one key


class WallFileTest(unittest.TestCase):
    """'add export and import option of cartwall config besides the auto save'."""

    def setUp(self):
        self.w = gc.CartwallWidget()
        self.path = os.path.join(tempfile.mkdtemp(prefix="dp_cartio_"),
                                 f"wall{pc.WALL_SUFFIX}")

    def tearDown(self):
        self.w.deleteLater()

    def test_a_wall_survives_the_round_trip(self):
        pages = [pc.Page(pads={(0, 0): pc.CartPad(path=_SAMPLE, label="Tusch",
                                                  volume=0.25, loop=True,
                                                  fade_ms=1500)})]
        pc.write_wall(self.path, pc.dump_doc((4, 4), pages, 0, "#c8871a"))
        doc = pc.read_wall(self.path)
        self.assertTrue(doc.ok)
        self.assertEqual(doc.grid, (4, 4))
        self.assertEqual(doc.colour, "#c8871a")
        self.assertEqual(doc.pages[0].pads[(0, 0)], pages[0].pads[(0, 0)])

    def test_a_file_that_is_not_a_wall_is_refused(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write('{"version": 999}')
        self.assertFalse(pc.read_wall(self.path)[4])

    def test_a_file_that_is_not_even_json_is_refused(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("#EXTM3U\n")
        self.assertFalse(pc.read_wall(self.path)[4])
        self.assertFalse(pc.read_wall(self.path + ".nope")[4])

    def test_the_wall_menu_offers_both(self):
        actions = [a.text() for a in self.w._file_btn.menu().actions()]
        self.assertTrue(any("Export" in a for a in actions), actions)
        self.assertTrue(any("Import" in a for a in actions), actions)


class WallFadeTest(unittest.TestCase):
    """'i need a global option for fadeout time, which i can overwrite at each
    card' — the wall carries one, a pad may override it."""

    def setUp(self):
        self.w = gc.CartwallWidget()

    def tearDown(self):
        self.w.deleteLater()

    def test_a_fresh_wall_has_the_standard_fade(self):
        self.assertEqual(self.w.fade_ms(), pc.DEFAULT_FADE_MS)

    def test_setting_it_reports_out_and_saves(self):
        heard, saved = [], []
        self.w.fadeChanged.connect(heard.append)
        self.w.changed.connect(lambda: saved.append(1))
        self.w.set_fade_ms(2500)
        self.assertEqual(heard, [2500])
        self.assertEqual(len(saved), 1)
        self.w.set_fade_ms(2500)            # no change, no save
        self.assertEqual(len(saved), 1)

    def test_it_is_clamped_to_the_allowed_span(self):
        self.w.set_fade_ms(99_999)
        self.assertEqual(self.w.fade_ms(), pc.MAX_FADE_MS)
        self.w.set_fade_ms(-5)
        self.assertEqual(self.w.fade_ms(), 0)

    def test_it_survives_a_round_trip(self):
        doc = pc.dump_doc((4, 4), [pc.blank_page()], 0, "#ffffff", 3000)
        self.assertEqual(pc.load_doc(doc).fade_ms, 3000)

    def test_a_wall_saved_before_it_existed_gets_the_standard_one(self):
        doc = pc.dump_doc((4, 4), [pc.blank_page()], 0)
        doc.pop("fade_ms", None)
        self.assertEqual(pc.load_doc(doc).fade_ms, pc.DEFAULT_FADE_MS)

    def test_a_pad_resolves_against_the_wall(self):
        wall = pc.CartPad(path="a.mp3")
        own = pc.CartPad(path="a.mp3", fade_ms=0)
        self.assertEqual(pc.fade_for(wall, 2500), 2500)
        self.assertEqual(pc.fade_for(own, 2500), 0)   # a real cut, not "unset"

    def test_a_pad_menu_can_set_the_wall_fade(self):
        """The real path, with the modal dialog stubbed — a live exec() in a
        test run never comes back."""
        self.w.set_wall((2, 8), [pc.Page(pads={(0, 0): pc.CartPad(path=_SAMPLE)})])
        with _fade_dialog(3200):
            self.w._buttons[(0, 0, 0)].wall_fade_requested.emit()
        self.assertEqual(self.w.fade_ms(), 3200)

    def test_cancelling_leaves_the_wall_fade_alone(self):
        with _fade_dialog(3200, ok=False):
            self.w._on_wall_fade()
        self.assertEqual(self.w.fade_ms(), pc.DEFAULT_FADE_MS)

    def test_the_dialog_reads_back_what_was_set(self):
        dlg = gc.WallFadeDialog(1500)
        self.assertEqual(dlg.fade_ms(), 1500)
        dlg._fade.setValue(0)
        self.assertEqual(dlg._lbl.text(), "cut")


class EditModeClarityTest(unittest.TestCase):
    """'in edit mode stop all playback' + 'make it more clear that i can now
    edit' — the mode in which pads do not fire has to be unmistakable."""

    def setUp(self):
        self.w = gc.CartwallWidget()
        self.w.set_wall((2, 8), [pc.Page(pads={(0, 0): pc.CartPad(path=_SAMPLE)})])

    def tearDown(self):
        self.w.deleteLater()

    def test_switching_to_edit_stops_the_wall(self):
        """A pad that keeps sounding while ✏ is on cannot be stopped by tapping
        it — the tap selects now."""
        seen = []
        self.w.stopAll.connect(lambda: seen.append(1))
        self.w.set_playing((0, 0, 0), True)
        self.w.set_edit(True)
        self.assertEqual(seen, [1])

    def test_a_silent_wall_is_not_told_to_stop(self):
        seen = []
        self.w.stopAll.connect(lambda: seen.append(1))
        self.w.set_edit(True)
        self.assertEqual(seen, [])

    def test_staying_in_edit_does_not_stop_it_again(self):
        seen = []
        self.w.set_edit(True)
        self.w.set_playing((0, 0, 0), True)
        self.w.stopAll.connect(lambda: seen.append(1))
        self.w.set_edit(True)
        self.assertEqual(seen, [])

    def test_the_banner_is_up_only_while_editing(self):
        self.w.show()
        self.addCleanup(self.w.hide)
        self.assertFalse(self.w._edit_lbl.isVisible())
        self.w.set_edit(True)
        self.assertTrue(self.w._edit_lbl.isVisible())
        self.assertIn("do not play", self.w._edit_lbl.text())
        self.w.set_edit(False)
        self.assertFalse(self.w._edit_lbl.isVisible())

    def test_the_wall_is_framed_while_editing(self):
        self.w.set_edit(True)
        self.assertIn(gc._EDIT_ACCENT, self.w._grid_host.styleSheet())
        self.w.set_edit(False)
        self.assertNotIn(gc._EDIT_ACCENT, self.w._grid_host.styleSheet())


class PageNameTest(unittest.TestCase):
    """'double click on page slider should let me change the name of the page'."""

    def setUp(self):
        self.w = gc.CartwallWidget()

    def tearDown(self):
        self.w.deleteLater()

    def test_an_unnamed_page_is_numbered(self):
        self.assertIn("Page 1", self.w._page_lbl.text())

    def test_a_named_page_shows_its_name(self):
        self.w.set_wall((4, 4), [pc.Page(name="Fanfaren")])
        self.assertIn("Fanfaren", self.w._page_lbl.text())

    def test_the_label_reports_a_real_double_click(self):
        """A bare label, deliberately: the wall's own is wired to the rename
        dialog, and a modal exec() in a test run never comes back."""
        label = gc._ClickableLabel("Page 1")
        self.addCleanup(reap_widget, label)
        seen = []
        label.double_clicked.connect(lambda: seen.append(1))
        label.mouseDoubleClickEvent(_dbl_click())
        self.assertEqual(seen, [1])

    def test_renaming_writes_the_name_and_saves(self):
        saved = []
        self.w.changed.connect(lambda: saved.append(1))
        with _typed_text("Fanfaren"):
            self.w._rename_page()
        self.assertEqual(self.w.pages()[0].name, "Fanfaren")
        self.assertIn("Fanfaren", self.w._page_lbl.text())
        self.assertEqual(len(saved), 1)

    def test_cancelling_the_rename_changes_nothing(self):
        with _typed_text("Nope", ok=False):
            self.w._rename_page()
        self.assertEqual(self.w.pages()[0].name, "")

    def test_a_name_cannot_be_longer_than_a_pad_label(self):
        with _typed_text("x" * 80):
            self.w._rename_page()
        self.assertEqual(len(self.w.pages()[0].name), pc.LABEL_MAX)

    def test_the_name_is_persisted(self):
        pages = [pc.Page(name="Siegerehrung",
                         pads={(0, 0): pc.CartPad(path="a.mp3")})]
        back = pc.load_doc(pc.dump_doc((4, 4), pages, 0)).pages
        self.assertEqual(back[0].name, "Siegerehrung")


class RegridPageTest(unittest.TestCase):
    """'if they all fit on the new layout it should be kept on the page it was
    before' — a page of ceremony samples stays one page of ceremony samples."""

    def test_a_page_that_still_fits_keeps_its_own_pads(self):
        pages = [pc.Page(pads={(0, 0): pc.CartPad(path="a.mp3"),
                               (5, 7): pc.CartPad(path="b.mp3")}),
                 pc.Page(pads={(5, 7): pc.CartPad(path="c.mp3")})]
        back, moved = pc.resize_grid(pages, (4, 4))
        self.assertEqual(moved, 2)
        self.assertEqual(len(back), 2)     # nothing spilled onto a third page
        self.assertEqual({p.path for p in back[0].pads.values()},
                         {"a.mp3", "b.mp3"})
        self.assertEqual({p.path for p in back[1].pads.values()}, {"c.mp3"})

    def test_a_page_that_cannot_hold_its_own_still_spills(self):
        """Never lose a pad beats never add a page."""
        pages = [pc.Page(pads={(r, c): pc.CartPad(path=f"{r}_{c}.mp3")
                               for r in range(6) for c in range(8)})]
        back, moved = pc.resize_grid(pages, (2, 2))
        self.assertEqual(moved, 44)
        self.assertEqual(pc.pad_count(back), 48)
        self.assertEqual(len(back), 12)

    def test_the_pads_that_still_fit_do_not_move_at_all(self):
        pages = [pc.Page(pads={(0, 0): pc.CartPad(path="stay.mp3"),
                               (7, 7): pc.CartPad(path="move.mp3")})]
        back, _moved = pc.resize_grid(pages, (4, 4))
        self.assertEqual(back[0].pads[(0, 0)].path, "stay.mp3")


class RegridFileCapTest(unittest.TestCase):
    """A shrink that needs more pages than cartwall.json is read back with would
    lose every pad past them on the next start — the layout is refused instead."""

    def setUp(self):
        self.w = gc.CartwallWidget()
        self.addCleanup(reap_widget, self.w)
        # 3 full 10 × 6 pages: 180 pads, which a 2 × 2 grid needs 45 pages for.
        self.pages = [pc.Page(pads={(r, c): pc.CartPad(path=f"{p}_{r}_{c}.mp3")
                                    for r in range(6) for c in range(10)})
                      for p in range(3)]
        self.w.set_wall((10, 6), self.pages)
        self.told = []
        real = gc.QMessageBox.information
        gc.QMessageBox.information = staticmethod(
            lambda *a, **kw: self.told.append(a[2]))
        self.addCleanup(setattr, gc.QMessageBox, "information", real)

    def test_a_shrink_past_the_file_cap_keeps_the_wall(self):
        self.w._on_size_picked(pc.GRID_SIZES.index((2, 2)))
        self.assertEqual(self.w.grid(), (10, 6))
        self.assertEqual(self.w._size_box.currentIndex(),
                         pc.GRID_SIZES.index((10, 6)))
        back = pc.load_doc(pc.dump_doc(self.w.grid(), self.w.pages(), 0))
        self.assertEqual(pc.pad_count(back.pages), 180)
        self.assertEqual(len(self.told), 1)

    def test_a_shrink_that_fits_still_happens(self):
        self.w._on_size_picked(pc.GRID_SIZES.index((8, 6)))
        self.assertEqual(self.w.grid(), (8, 6))
        self.assertEqual(pc.pad_count(self.w.pages()), 180)
        self.assertEqual(self.told, [])


class PageCapTest(unittest.TestCase):
    """Pages are made deliberately: ▶ turns them, ➕ creates them, and the ones
    nobody filled do not come back."""

    def test_the_nav_never_creates_a_page(self):
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        before = len(w.pages())
        for _ in range(6):
            w._step_page(1)
        self.assertEqual(len(w.pages()), before)
        self.assertEqual(w.current_page(), before - 1)

    def test_the_add_button_appends_a_page_and_goes_to_it(self):
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        before = len(w.pages())
        w._add_page()
        self.assertEqual(len(w.pages()), before + 1)
        self.assertEqual(w.current_page(), before)

    def test_adding_stops_at_the_cap(self):
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        for _ in range(pc.MAX_PAGES + 4):
            w._add_page()
        self.assertEqual(len(w.pages()), pc.MAX_PAGES)
        self.assertFalse(w._add_btn.isEnabled())

    def test_the_last_page_can_never_be_removed(self):
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        w.set_wall(pc.DEFAULT_GRID, [pc.blank_page()])
        for _ in range(3):
            w._remove_page()
        self.assertEqual(len(w.pages()), 1)
        self.assertFalse(w._rm_btn.isEnabled())

    def test_removing_a_page_drops_it_and_steps_back(self):
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        w.set_wall(pc.DEFAULT_GRID,
                   [pc.Page(name="Fanfaren"), pc.Page(name="Gone")], page=1)
        w._remove_page()
        self.assertEqual([p.name for p in w.pages()], ["Fanfaren"])
        self.assertEqual(w.current_page(), 0)

    def test_a_page_with_pads_asks_before_it_goes(self):
        """There is no undo on the wall, and those pads were set up for a
        tournament."""
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        for answer, left in ((False, 2), (True, 1)):
            w.set_wall(pc.DEFAULT_GRID, [
                pc.blank_page(),
                pc.Page(pads={(0, 0): pc.CartPad(path="a.mp3")})], page=1)
            with _answer(answer):
                w._remove_page()
            self.assertEqual(len(w.pages()), left)

    def test_an_empty_page_goes_without_a_question(self):
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        w.set_wall(pc.DEFAULT_GRID, [pc.blank_page(), pc.blank_page()], page=1)
        w._remove_page()        # a real question here would hang the suite
        self.assertEqual(len(w.pages()), 1)

    def test_the_add_button_is_edit_mode_only(self):
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        w.show()
        self.addCleanup(w.hide)
        w.set_edit(False)
        self.assertFalse(w._add_btn.isVisible())
        self.assertFalse(w._rm_btn.isVisible())
        w.set_edit(True)
        self.assertTrue(w._add_btn.isVisible())
        self.assertTrue(w._rm_btn.isVisible())

    def test_turning_the_page_is_saved(self):
        """dump_doc stores the current page, so the turn has to reach the file —
        or the wall reopens on whichever page the last pad edit left up."""
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        saved = []
        w.changed.connect(lambda: saved.append(w.current_page()))
        w._step_page(1)
        w._step_page(-1)
        self.assertEqual(saved, [1, 0])

    def test_a_wall_full_of_empty_pages_comes_back_as_two(self):
        """An older build's resize left a page per spill. Eleven pages, eight of
        them empty, is the wall this was found on."""
        pages = [pc.Page(name="hh", pads={(0, 0): pc.CartPad(path="a.mp3")}),
                 pc.Page(pads={(0, 0): pc.CartPad(path="b.mp3")})]
        pages += [pc.blank_page() for _ in range(9)]
        doc = pc.load_doc(pc.dump_doc((2, 6), pages, 0))
        self.assertEqual(len(doc.pages), 2)
        self.assertEqual(pc.pad_count(doc.pages), 2)
        self.assertEqual(doc.pages[0].name, "hh")

    def test_pages_the_user_filled_survive_a_reload(self):
        """The counterpart to the trim: ➕ is only worth having if the page is
        still there next time."""
        pages = [pc.Page(pads={(0, 0): pc.CartPad(path=f"{i}.mp3")})
                 for i in range(5)]
        doc = pc.load_doc(pc.dump_doc((2, 6), pages, 0))
        self.assertEqual(len(doc.pages), 5)
        self.assertEqual(pc.pad_count(doc.pages), 5)

    def test_pads_past_the_cap_move_up_when_there_is_room(self):
        pages = [pc.Page(pads={(0, 0): pc.CartPad(path=f"{i}.mp3")})
                 for i in range(pc.MAX_PAGES + 3)]
        doc = pc.load_doc(pc.dump_doc((2, 6), pages, 0))
        self.assertEqual(len(doc.pages), pc.MAX_PAGES)
        self.assertEqual(pc.pad_count(doc.pages), pc.MAX_PAGES + 3)

    def test_a_page_that_cannot_be_packed_away_is_kept(self):
        """The cap limits what the nav CREATES. It never licenses dropping a
        pad, so a wall that is genuinely full keeps its pages."""
        full = [pc.Page(pads={(r, c): pc.CartPad(path=f"{i}_{r}_{c}.mp3")
                              for r in range(2) for c in range(2)})
                for i in range(pc.MAX_PAGES + 2)]
        doc = pc.load_doc(pc.dump_doc((2, 2), full, 0))
        self.assertEqual(len(doc.pages), pc.MAX_PAGES + 2)
        self.assertEqual(pc.pad_count(doc.pages), (pc.MAX_PAGES + 2) * 4)

    def test_the_small_grids_are_offered(self):
        for grid in ((2, 2), (2, 4), (2, 6)):
            self.assertIn(grid, pc.GRID_SIZES)

    def test_packing_onto_one_page_shows_every_pad_at_once(self):
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        saved = []
        w.changed.connect(lambda: saved.append(1))
        w.set_wall((2, 8), [
            pc.Page(name="Fanfaren", pads={(0, 0): pc.CartPad(path="a.mp3")}),
            pc.Page(pads={(0, 0): pc.CartPad(path="b.mp3"),
                          (3, 1): pc.CartPad(path="c.mp3")})])
        w._pack_one_page()
        self.assertEqual(len(w.pages()), 1)
        self.assertEqual(pc.pad_count(w.pages()), 3)
        self.assertEqual(w.pages()[0].name, "Fanfaren")
        self.assertTrue(saved)          # the packed wall is written out


if __name__ == "__main__":
    unittest.main()
