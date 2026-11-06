#!/usr/bin/env python3
"""The 🧹 Clear all button asks which kinds of list to empty.

Run:  py -m unittest tests.gui.dialogs.test_clear_all_dialog -v
"""

import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_clear_all_"))

from PySide6.QtWidgets import QApplication, QDialogButtonBox

from gui.dialogs.clear_all_dialog import ClearAllDialog
from gui.window.main_persist import PersistenceMixin
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)


class ClearAllDialogTest(unittest.TestCase):

    def dialog(self, *counts):
        dlg = ClearAllDialog(None, *counts)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_only_the_playlists_are_ticked_at_the_start(self):
        self.assertEqual(self.dialog(3, 2, 5).choice(), (True, False, False))

    def test_a_kind_with_nothing_in_it_is_greyed_out_and_not_ticked(self):
        dlg = self.dialog(0, 2, 0)
        self.assertEqual(dlg.choice(), (False, False, False))
        self.assertFalse(dlg.playlists.isEnabled())
        self.assertTrue(dlg.wishlists.isEnabled())
        self.assertFalse(dlg.party.isEnabled())

    def test_ok_needs_at_least_one_tick(self):
        dlg = self.dialog(3, 2, 5)
        ok = dlg.box.button(QDialogButtonBox.StandardButton.Ok)
        self.assertTrue(ok.isEnabled())
        dlg.playlists.setChecked(False)
        self.assertFalse(ok.isEnabled())
        dlg.party.setChecked(True)
        self.assertTrue(ok.isEnabled())


class _Table:
    def __init__(self, rows):
        self.rows = rows
        self._current_play_row = -1
        self.host = SimpleNamespace(reset_wishlist_name=mock.Mock())
        self._render_flat_entries = mock.Mock(side_effect=self.empty)

    def rowCount(self):
        return self.rows

    def empty(self, _entries):
        self.rows = 0


class ClearAllActionTest(unittest.TestCase):
    """_clear_all_playlists on a stand-in window: which lists go for a choice."""

    def window(self):
        party = _Table(4)
        party._row_meta = SimpleNamespace(entries=lambda: [1] * 4, clear=mock.Mock())
        return SimpleNamespace(
            _deckset=SimpleNamespace(decks=[_Table(2), _Table(0)], day_decks=[],
                                     wishlists=[_Table(3)], warmup_table=party),
            _warmup_has_content=lambda: True,
            _blank_deck=mock.Mock(), _apply_deck_view=mock.Mock(),
            _autosave_playlist=mock.Mock(), _clear_party_list=mock.Mock(),
            _used_view=PersistenceMixin._used_view, _update_wish_area=mock.Mock(),
            _wish_state=4,
            statusBar=lambda: SimpleNamespace(showMessage=mock.Mock()))

    def run_with(self, win, choice):
        with mock.patch("gui.window.main_persist.ask_clear_all", return_value=choice):
            PersistenceMixin._clear_all_playlists(win)

    def test_the_default_choice_empties_playlists_only(self):
        win = self.window()
        self.run_with(win, (True, False, False))
        self.assertEqual(win._blank_deck.call_count, 2)
        win._deckset.wishlists[0]._render_flat_entries.assert_not_called()
        win._clear_party_list.assert_not_called()

    def test_wishlists_and_party_go_only_when_ticked(self):
        win = self.window()
        self.run_with(win, (False, True, True))
        win._blank_deck.assert_not_called()
        win._deckset.wishlists[0]._render_flat_entries.assert_called_once_with([])
        win._clear_party_list.assert_called_once()

    def test_emptied_lists_collapse_but_one_of_each_stays_open(self):
        win = self.window()
        win._deckset.deck_count = 8
        self.run_with(win, (True, True, False))
        self.assertEqual(win._deckset.deck_count, 1)
        self.assertEqual(win._wish_state, 1)

    def test_lists_that_keep_their_songs_stay_shown(self):
        win = self.window()
        win._deckset.decks = [_Table(0), _Table(0), _Table(0), _Table(2)]
        win._deckset.deck_count = 8
        win._deckset.wishlists = [_Table(0), _Table(4)]
        self.run_with(win, (False, False, True))   # nothing cleared but the party list
        self.assertEqual(win._deckset.deck_count, 8)
        self.assertEqual(win._wish_state, 4)

    def test_cancel_changes_nothing(self):
        win = self.window()
        self.run_with(win, None)
        win._blank_deck.assert_not_called()
        win._autosave_playlist.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
