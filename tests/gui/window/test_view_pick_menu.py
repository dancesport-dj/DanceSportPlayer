#!/usr/bin/env python3
"""⧉ ⭐ 🗜 — a click opens a pick list, the mouse wheel steps.

Run:  py -m unittest tests.gui.window.test_view_pick_menu -v

"when i want a specific playlist, whishlist count or nothing i must click
multiple times till i get it from the multibutton". A left click stepped the
ring one view on, so from 2 playlists to none took three clicks. Now the click
opens a menu listing every view with the current one ticked, and one pick
lands there. The wheel over a button still steps through the ring (up =
forward), and the right click still steps back.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_viewpick_"))

from PySide6.QtCore import QPoint, QPointF, QSettings, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QMenu

from gui.window import main_decks


class _MenuSpy:
    """Stands in for the menu's exec: records what the menu offered and picks
    the entry whose text is `pick` (None = the menu was dismissed).

    Patching QMenu.exec doesn't take (the Shiboken slot ignores an attribute
    set on the type, and the real modal exec blocks the run), so the test
    swaps the module's QMenu for a subclass whose exec lands here."""

    def __init__(self, pick=None):
        self.pick = pick
        self.entries = []   # (text, checked), "-" for a separator
        spy = self

        class _Menu(QMenu):
            def exec(self, *_args):
                return spy.offered(self)

        self.menu_class = _Menu

    def offered(self, menu):
        self.entries = [("-" if a.isSeparator() else (a.text(), a.isChecked()))
                        for a in menu.actions()]
        return next((a for a in menu.actions() if a.text() == self.pick), None)


def _wheel(widget, up: bool):
    """One notch of the mouse wheel over `widget`."""
    centre = QPointF(widget.rect().center())
    event = QWheelEvent(centre, QPointF(widget.mapToGlobal(centre.toPoint())),
                        QPoint(0, 0), QPoint(0, 120 if up else -120),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                        Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(widget, event)


class ViewPickMenuTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._settings_dir = tempfile.mkdtemp(prefix="dp_viewpick_qs_")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, cls._settings_dir)
        cls.app = QApplication.instance() or QApplication([])
        from tests.qt_test_support import stub_window_startup
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        from tests.qt_test_support import reap_widget
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)

    def _click(self, btn, pick=None) -> _MenuSpy:
        spy = _MenuSpy(pick)
        with mock.patch.object(main_decks, "QMenu", spy.menu_class):
            btn.click()
        return spy

    def _deck_view(self, n):
        self.win._deckset.deck_count = n
        self.win._apply_deck_view()

    def test_the_captions_show_that_a_list_opens(self):
        # The ▾ is the one visible cue that a click no longer just steps.
        for btn in (self.win._dual_btn, self.win._dual_wish_btn, self.win._compact_btn):
            self.assertTrue(btn.text().endswith("  ▾"), btn.text())
        self._deck_view(2)
        self.win._set_wish_state(3)
        self.win._set_compact_state(3)
        self.assertEqual(self.win._dual_btn.text(), "2 playlists  ▾")
        self.assertEqual(self.win._dual_wish_btn.text(), "3 wishlists  ▾")
        self.assertEqual(self.win._compact_btn.text(), "🔢  Numbers  ▾")

    # ── ⧉ playlists ──────────────────────────────────────────────────────────

    def test_the_playlist_button_lists_every_view_with_the_current_ticked(self):
        self._deck_view(2)
        spy = self._click(self.win._dual_btn)
        self.assertEqual(spy.entries, [
            ("1 playlist", False), ("2 playlists", True), ("4 playlists", False),
            ("8 playlists", False), "-", ("No playlist", False)])

    def test_one_pick_lands_on_that_view(self):
        self._deck_view(2)
        self._click(self.win._dual_btn, pick="No playlist")
        self.assertEqual(self.win._deckset.deck_count, 0)

    def test_a_dismissed_menu_changes_nothing(self):
        self._deck_view(4)
        self._click(self.win._dual_btn)
        self.assertEqual(self.win._deckset.deck_count, 4)

    def test_a_player_build_offers_no_eight(self):
        self._deck_view(1)
        with mock.patch.object(type(self.win), "_max_decks", lambda _self: 4):
            spy = self._click(self.win._dual_btn)
        self.assertNotIn(("8 playlists", False), spy.entries)
        self.assertEqual(len(spy.entries), 5)

    def test_the_wheel_steps_the_playlist_ring(self):
        self._deck_view(2)
        _wheel(self.win._dual_btn, up=True)
        self.assertEqual(self.win._deckset.deck_count, 4)
        _wheel(self.win._dual_btn, up=False)
        _wheel(self.win._dual_btn, up=False)
        self.assertEqual(self.win._deckset.deck_count, 1)

    # ── ⭐ wishlists ─────────────────────────────────────────────────────────

    def test_the_wishlist_button_lists_every_state_with_the_current_ticked(self):
        self.win._set_wish_state(1)
        spy = self._click(self.win._dual_wish_btn)
        self.assertEqual(spy.entries, [
            ("No wishlist", False), "-", ("1 wishlist", True),
            ("2 wishlists", False), ("3 wishlists", False),
            ("4 wishlists", False), ("4 wishlists (2×2)", False)])

    def test_picking_the_grid_stacks_four(self):
        self.win._set_wish_state(1)
        self._click(self.win._dual_wish_btn, pick="4 wishlists (2×2)")
        self.assertEqual((self.win._wish_state, self.win._wish_grid), (4, True))

    def test_the_grid_is_ticked_and_plain_four_is_not(self):
        self.win._set_wish_state(4, grid=True)
        spy = self._click(self.win._dual_wish_btn)
        self.assertIn(("4 wishlists", False), spy.entries)
        self.assertIn(("4 wishlists (2×2)", True), spy.entries)

    def test_the_wheel_steps_the_wishlist_ring(self):
        self.win._set_wish_state(3)
        _wheel(self.win._dual_wish_btn, up=True)
        self.assertEqual((self.win._wish_state, self.win._wish_grid), (4, False))
        _wheel(self.win._dual_wish_btn, up=False)
        self.assertEqual(self.win._wish_state, 3)

    # ── 🗜 header view ───────────────────────────────────────────────────────

    def test_the_header_button_lists_the_four_views(self):
        self.win._set_compact_state(2)
        spy = self._click(self.win._compact_btn)
        self.assertEqual(spy.entries, [
            ("Full headers", False), ("🗜  Compact", False),
            ("🚫  No groups", True), ("🔢  Numbers", False)])

    def test_picking_a_header_view_applies_it(self):
        self.win._set_compact_state(0)
        self._click(self.win._compact_btn, pick="🔢  Numbers")
        self.assertEqual(self.win._compact_state, 3)
        self.assertTrue(self.win._compact_btn.isChecked())

    def test_a_dismissed_menu_leaves_the_button_pressed_as_it_was(self):
        # 🗜 is checkable: the click itself toggles it before the menu opens.
        for state in (0, 1):
            self.win._set_compact_state(state)
            self._click(self.win._compact_btn)
            self.assertEqual(self.win._compact_state, state)
            self.assertEqual(self.win._compact_btn.isChecked(), state > 0)

    def test_the_wheel_steps_the_header_views_both_ways(self):
        self.win._set_compact_state(0)
        _wheel(self.win._compact_btn, up=True)
        self.assertEqual(self.win._compact_state, 1)
        _wheel(self.win._compact_btn, up=False)
        _wheel(self.win._compact_btn, up=False)
        self.assertEqual(self.win._compact_state, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
