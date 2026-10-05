#!/usr/bin/env python3
"""🏆 The event plan on the main window's player: the mini player comes up
below the cell that plays, and survives the tables it sits in.

Run:  py -m unittest tests.gui.test_event_compare_player -v

Marcel: "i want not only leertaste to start playing but also get the play
icons in it to press and stop — with the mini player coming up". The main
window side is the glue: the decks' ▶/■ go back, the overlay anchors to the
cell's row, ⏮/⏭ walk the column, and before a new result deletes the tables
the overlay moves out of them.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_event_compare_player_"))

import shiboken6  # noqa: E402
from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from gui.main_decks import DeckLayoutMixin  # noqa: E402
from gui.main_generate import GenerateMixin  # noqa: E402
from planner import event_plan  # noqa: E402
from planner.competition import parse_competition_schedule  # noqa: E402
from player.main_player import PlayerControlMixin  # noqa: E402
from player.player import PreviewOverlay  # noqa: E402
from tests.planner.test_event_variants import EventFixture  # noqa: E402


class _Main(QWidget):
    """The main window as far as the event plan's player glue reaches."""

    _show_event_compare = GenerateMixin._show_event_compare
    _on_event_prehear = GenerateMixin._on_event_prehear
    _rehome_preview = GenerateMixin._rehome_preview
    _reset_aux_play_markers = DeckLayoutMixin._reset_aux_play_markers
    _preview_skip = PlayerControlMixin._preview_skip

    def __init__(self, result, cands):
        super().__init__()
        self._event_result, self._event_cands = result, cands
        self._settings = {}
        self._preview = PreviewOverlay(QMediaPlayer(), QAudioOutput())
        self.deck = mock.Mock(_current_play_row=-1)
        self._all_tables = [self.deck]
        self._lib_browser = mock.Mock()
        self._announcer = mock.Mock()
        self._continue_event_plan = mock.Mock()
        self._apply_event_plan = mock.Mock()
        self._seek = mock.Mock()
        self.calls = []
        self.now = None

    def _play_or_stop(self, path):
        self.calls.append(path)
        self.now = path

    def deck_path(self):
        return self.now

    def _is_playing_mode(self):
        return False


class EventComparePlayerTest(EventFixture, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        super().setUp()
        self.event_list("DanceConvention 2025/HGR_S_STD.m3u", "DC")
        editions = event_plan.past_editions("danceconvention", root=self.root)
        self.cands = [event_plan.gather_candidates(self.lib, s, editions,
                                                   similar=self.similar)
                      for s in parse_competition_schedule("HGR S STD 2-1")]
        self.result = event_plan.RefineResult(
            {p: event_plan.plan_variant(self.cands, p)
             for p in ("like_last_year", "variety")})
        self.main = _Main(self.result, self.cands)
        self.addCleanup(self.main.deleteLater)
        self.main._show_event_compare()
        self.dlg = self.main._event_compare
        self.addCleanup(self.dlg.close)

    def path(self, row, col):
        comps = self.result.variants[self.dlg._profiles[col]]
        return event_plan.slot_pick(comps, (0, *self.dlg._slots[0][row])).entry.path

    def test_the_mini_player_comes_up_below_the_cell(self):
        self.dlg.prehear_cell(0, 3, 1)
        table = self.dlg._tables[0]
        self.assertEqual(self.main.calls, [self.path(3, 1)])
        self.assertIs(self.main._preview.parentWidget(), table.viewport())
        self.assertTrue(self.main._preview.isVisibleTo(table.viewport()))
        self.assertEqual(self.main._preview._full_title, self.path(3, 1).stem)
        self.main.deck.on_playback_stopped.assert_called()

    def test_the_mini_player_stays_down_when_it_is_off(self):
        self.main._settings["preview_player"] = False
        self.dlg.prehear_cell(0, 3, 1)
        self.assertIsNot(self.main._preview.parentWidget(), self.dlg._tables[0].viewport())

    def test_the_mini_player_outlives_the_tables(self):
        """A new result deletes the tables — the overlay must not go with them."""
        self.dlg.prehear_cell(0, 3, 1)
        self.dlg.set_result(self.result, self.cands)
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.assertTrue(shiboken6.isValid(self.main._preview))
        self.assertTrue(self.main._preview.isHidden())
        self.dlg.prehear_cell(0, 4, 1)
        self.assertIs(self.main._preview.parentWidget(), self.dlg._tables[0].viewport())

    def test_the_pickers_ctrl_arrows_seek_the_main_player(self):
        picker = self.dlg.slot_picker(0, 0, 1)
        self.addCleanup(picker.deleteLater)
        QTest.keyClick(picker.table(), Qt.Key.Key_Right, Qt.KeyboardModifier.ControlModifier)
        self.main._seek.assert_called_once_with(30000)

    def test_skip_walks_the_column_that_plays(self):
        self.dlg.prehear_cell(0, 3, 1)
        self.main._preview_skip(+1)
        self.assertEqual(self.main.calls[-1], self.path(4, 1))
        self.main._lib_browser.skip.assert_not_called()

    def test_skip_is_the_library_panes_when_no_cell_plays(self):
        self.main._preview_skip(+1)
        self.main._lib_browser.skip.assert_called_once_with(1)

    def test_a_deck_taking_over_clears_the_cells_mark(self):
        self.dlg.prehear_cell(0, 3, 1)
        self.main._reset_aux_play_markers()
        self.assertIsNone(self.dlg._playing)

    def test_the_event_plans_own_start_keeps_its_mark(self):
        self.dlg.prehear_cell(0, 3, 1)
        self.assertEqual(self.dlg._playing, (0, 3, 1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
