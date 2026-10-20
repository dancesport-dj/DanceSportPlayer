"""CartwallWidget as a whole, on its own — no MainWindow, no audio.

Text is asserted, never rendering: the offscreen QPA has no fonts, so a
screenshot of this page is tofu. What matters here is that the grid has the
right shape, that a pad edit reaches the model, and that the wall never loses a
pad when the operator resizes it mid-tournament. The pads on their own (the
pad widget, its dialogs and editors) are in tests.player.test_cartwall_pads.
"""
import contextlib
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_cartui_"))

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (QApplication, QStyleOptionToolButton, QToolButton,
    QWidgetItem)
from tests.qt_test_support import reap_widget

from planner.playing import cartwall as pc
from player.dialogs import cart_pad_dialog as cpd
from player.widgets import cartwall as gc

_app = QApplication.instance() or QApplication(sys.argv)

# A file that really exists — a pad whose sample is missing is painted grey, so
# the colour tests would otherwise all be testing the "⚠ gone" style.
_SAMPLE = os.path.join(tempfile.mkdtemp(prefix="dp_cartfx_"), "tusch.mp3")
open(_SAMPLE, "wb").close()


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
        self.w.step_page(1)
        self.assertEqual(len(self.w.pages()), 1)
        self.assertEqual(self.w.current_page(), 0)
        self.w._add_page()
        self.assertEqual(self.w.current_page(), 1)
        self.w.step_page(-1)
        self.assertEqual(self.w.current_page(), 0)

    def test_a_fresh_wall_already_has_a_second_page(self):
        self.assertEqual(len(self.w.pages()), pc.DEFAULT_PAGES)

    def test_page_one_cannot_be_paged_off_the_front(self):
        self.w.step_page(-1)
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
    """What the ⌨ Keys window hands back, applied to the wall. The window
    itself belongs to MainWindow — it holds the desk keys too."""

    def _wall_with_a_pad(self):
        self.w.set_wall((4, 4), [pc.Page(pads={
            (0, 0): pc.CartPad(path=_SAMPLE, label="Tusch")})])

    def test_ok_applies_both_layers_and_saves_once(self):
        self._wall_with_a_pad()
        seen = []
        self.w.changed.connect(lambda: seen.append(True))
        self.w.apply_keys({(0, 0, 0): "F9"}, ("F5", "F6"))
        self.assertEqual(self.w.slot_keys(), ("F5", "F6"))
        self.assertEqual(self.w.pages()[0].pads[(0, 0)].shortcut, "F9")
        self.assertEqual(len(seen), 1)      # one rebuild, however much changed

    def test_changing_nothing_saves_nothing(self):
        self._wall_with_a_pad()
        seen = []
        self.w.changed.connect(lambda: seen.append(True))
        self.w.apply_keys({(0, 0, 0): ""}, pc.SLOT_KEYS)
        self.assertEqual(seen, [])

    def test_the_pad_menu_asks_for_the_keys_window(self):
        seen = []
        self.w.keysRequested.connect(lambda: seen.append(True))
        self._pad_widget(0, 0).shortcuts_requested.emit()
        self.assertEqual(seen, [True])

    def test_a_keys_button_only_while_editing(self):
        """Next to ✏: setting keys is building the wall, not playing it."""
        seen = []
        self.w.keysRequested.connect(lambda: seen.append(True))
        self.assertTrue(self.w._keys_btn.isHidden())
        self.w.set_edit(True)
        self.assertFalse(self.w._keys_btn.isHidden())
        self.w._keys_btn.click()
        self.assertEqual(seen, [True])
        self.w.set_edit(False)
        self.assertTrue(self.w._keys_btn.isHidden())

    def test_a_new_pad_key_reaches_a_running_voice(self):
        """padRefreshed is how a live voice hears about an edit."""
        self._wall_with_a_pad()
        seen = []
        self.w.padRefreshed.connect(lambda key, pad: seen.append((key, pad)))
        self.w.apply_keys({(0, 0, 0): "F9"}, pc.SLOT_KEYS)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][0], (0, 0, 0))
        self.assertEqual(seen[0][1].shortcut, "F9")
        self.assertEqual(seen[0][1].label, "Tusch")   # nothing else disturbed


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
        actions = [a.text() for a in self.w._file_menu.actions()]
        self.assertTrue(any("Export" in a for a in actions), actions)
        self.assertTrue(any("Import" in a for a in actions), actions)

    def test_the_folder_button_keeps_no_room_for_a_menu_arrow(self):
        """A button with its menu attached draws a ⌄ on its right and keeps
        room for it even when the ⌄ is styled away — the 🗂 sat left of the
        middle of a button that itself lined up with the rest."""
        opt = QStyleOptionToolButton()
        self.w._file_btn.initStyleOption(opt)
        self.assertFalse(opt.features & QStyleOptionToolButton.ToolButtonFeature.HasMenu)

    def test_the_folder_button_shows_its_menu_arrow_on_the_right(self):
        """'add the down arrow right side in the middle': a ▾ after the 🗂,
        in the text, so it sits on the glyph's line and not in Qt's corner."""
        self.assertEqual(self.w._file_btn.text(), "🗂▾")

    def test_the_menu_arrow_costs_the_tool_row_no_width(self):
        """Marcel: 'with the new dir icon with the arrow in the cartwall it is
        broken in a new line'. The tool row flows, so every pixel the ▾ adds
        can push the button onto a second row. It keeps a bare 🗂's width."""
        bare = QToolButton()
        bare.setText("🗂")
        bare.setAutoRaise(True)
        # What the flow layout sizes the button by, fixed width included.
        self.assertLessEqual(QWidgetItem(self.w._file_btn).sizeHint().width(),
                             bare.sizeHint().width())

    def test_a_click_on_the_folder_button_opens_the_menu(self):
        self.w.show()
        self.addCleanup(self.w._file_menu.hide)
        self.w._file_btn.click()
        self.assertTrue(self.w._file_menu.isVisible())


class WallFadeTest(unittest.TestCase):
    """'i need a global option for fadeout time, which i can overwrite at each
    card' — the wall carries one, a pad may override it."""

    def setUp(self):
        self.w = gc.CartwallWidget()

    def tearDown(self):
        self.w.deleteLater()

    def test_a_fresh_wall_has_the_standard_fade(self):
        self.assertEqual(self.w.fade_ms(), pc.DEFAULT_FADE_MS)
        # "make cartwall default fade out 1s"
        self.assertEqual(self.w.fade_ms(), 1000)

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
        dlg = cpd.WallFadeDialog(1500)
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
        label = cpd._ClickableLabel("Page 1")
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
            w.step_page(1)
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

    def test_one_page_shows_no_arrows(self):
        """'if we have only one page you should not show the arrow left and
        right from Main, only if we have more than one page'."""
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        w.set_wall(pc.DEFAULT_GRID, [pc.Page(name="Main")])
        self.assertTrue(w._prev_btn.isHidden())
        self.assertTrue(w._next_btn.isHidden())

    def test_a_second_page_brings_the_arrows_back(self):
        w = gc.CartwallWidget()
        self.addCleanup(reap_widget, w)
        w.set_wall(pc.DEFAULT_GRID, [pc.Page(name="Main")])
        w._add_page()
        self.assertFalse(w._prev_btn.isHidden())
        self.assertFalse(w._next_btn.isHidden())
        w._remove_page()
        self.assertTrue(w._prev_btn.isHidden())
        self.assertTrue(w._next_btn.isHidden())

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
        w.step_page(1)
        w.step_page(-1)
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
