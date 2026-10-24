#!/usr/bin/env python3
"""⏹ The planned stop on the ▶ Playing panel and in the advance engine.

Run:  py -m unittest tests.player.audio.test_party_stop_engine -v

The stop row sits under 🔁 and, like it, needs ⏭ auto-advance. When the rule
is due, a title end arms no pause and starts nothing: the next title is cued
for ⏯ instead. Nothing of it is saved.
"""
import unittest
from datetime import datetime
from types import SimpleNamespace

from PySide6.QtCore import QTime

from player.widgets.play_mode_panel import PlayModePanel
from tests.player.audio.test_repeat_list import _Fixture
from tests.qt_test_support import reap_widget


class StopRowTest(_Fixture):
    """The row itself."""

    def panel(self, **settings) -> PlayModePanel:
        p = PlayModePanel(settings)
        self.addCleanup(reap_widget, p)
        p.show()
        return p

    def choose(self, p, mode):
        p.stop_combo.setCurrentIndex(p.stop_combo.findData(mode))

    def test_it_starts_on_never_with_nothing_beside_it(self):
        p = self.panel(auto_advance=True)
        self.assertEqual(p.stop_combo.currentData(), "never")
        self.assertFalse(p.stop_count_spin.isVisible())
        self.assertFalse(p.stop_time_edit.isVisible())
        self.assertEqual(p.stop_text(), "")

    def test_it_leaves_the_panel_without_auto_advance(self):
        p = self.panel(auto_advance=False)
        self.assertFalse(p.stop_row_box.isVisible())
        p.advance_check.setChecked(True)
        self.assertTrue(p.stop_row_box.isVisible())

    def test_a_count_shows_its_spinner_and_counts_down(self):
        p = self.panel(auto_advance=True)
        p.stop_count_spin.setValue(3)
        self.choose(p, "count")
        self.assertTrue(p.stop_count_spin.isVisible())
        self.assertFalse(p.stop_title_ended(datetime.now()))
        self.assertEqual(p.stop_count_spin.value(), 2)
        self.assertFalse(p.stop_title_ended(datetime.now()))
        self.assertEqual(p.stop_combo.currentData(), "this")
        self.assertTrue(p.stop_title_ended(datetime.now()))
        self.assertEqual(p.stop_combo.currentData(), "never")

    def test_a_time_shows_its_clock(self):
        p = self.panel(auto_advance=True)
        p.stop_time_edit.setTime(QTime(23, 30))
        self.choose(p, "time")
        self.assertTrue(p.stop_time_edit.isVisible())
        self.assertEqual(p.stop_text(), "⏹  Stops at 23:30")

    def test_without_auto_advance_the_rule_is_asleep(self):
        p = self.panel(auto_advance=True)
        self.choose(p, "this")
        p.advance_check.setChecked(False)
        self.assertFalse(p.stop_due(datetime.now()))
        self.assertFalse(p.stop_title_ended(datetime.now()))
        self.assertEqual(p.stop_text(), "")

    def test_changing_it_saves_nothing(self):
        p = self.panel(auto_advance=True)
        saved = []
        p.settingsChanged.connect(lambda: saved.append(1))
        self.choose(p, "count")
        self.assertEqual(saved, [])


class StopEngineTest(_Fixture):
    """What a title end does with the rule armed."""

    def test_a_due_stop_arms_no_pause_and_cues_the_next_title(self):
        desk = self.deck()
        rows = self.song_rows()
        self.table._current_play_row = rows[0]
        p = desk._play_panel
        p.stop_combo.setCurrentIndex(p.stop_combo.findData("this"))
        desk._queue_auto_advance()
        self.assertIsNone(desk._between.pending)
        self.assertIsNone(desk._between.round_start)
        self.assertIsNotNone(desk._between.cue_next)
        cued = desk._between.cue_next
        self.assertIsNotNone(cued)
        assert cued is not None
        self.assertEqual(cued[1], rows[1])
        self.assertIn("⏹  Stopped as planned", desk.countdowns)
        self.assertEqual(p.stop_combo.currentData(), "never")

    def test_a_count_lets_the_titles_before_it_run_on(self):
        desk = self.deck()
        self.table._current_play_row = self.song_rows()[0]
        p = desk._play_panel
        p.stop_count_spin.setValue(2)
        p.stop_combo.setCurrentIndex(p.stop_combo.findData("count"))
        desk._queue_auto_advance()
        self.assertIsNotNone(desk._between.pending)
        self.assertEqual(p.stop_combo.currentData(), "this")

    def card(self, desk):
        shown = []
        desk._big_player = SimpleNamespace(set_next_up=shown.append,
                                           loop_mode=lambda: False)
        desk._music_left = lambda: 60.0
        return shown

    def test_the_card_says_when_this_title_is_the_last(self):
        desk = self.deck()
        self.table._current_play_row = self.song_rows()[0]
        shown = self.card(desk)
        p = desk._play_panel
        p.stop_combo.setCurrentIndex(p.stop_combo.findData("this"))
        desk._refresh_next_up()
        self.assertEqual(shown[-1], "⏹  Stops after this title")

    def test_the_card_adds_a_rule_still_to_come(self):
        desk = self.deck()
        self.table._current_play_row = self.song_rows()[0]
        shown = self.card(desk)
        p = desk._play_panel
        p.stop_count_spin.setValue(3)
        p.stop_combo.setCurrentIndex(p.stop_combo.findData("count"))
        desk._refresh_next_up()
        self.assertTrue(shown[-1].startswith("⏭"))
        self.assertTrue(shown[-1].endswith("  ·  ⏹  Stops after 3 titles"))

    def test_a_crossfaded_end_cannot_stop(self):
        """The next title is already sounding: the stop waits for its end."""
        desk = self.deck()
        self.table._current_play_row = self.song_rows()[0]
        p = desk._play_panel
        p.stop_combo.setCurrentIndex(p.stop_combo.findData("this"))
        desk._between.xfade.state = "fading"
        desk._queue_auto_advance()
        self.assertIsNotNone(desk._between.pending)
        self.assertEqual(p.stop_combo.currentData(), "this")


if __name__ == "__main__":
    unittest.main()
