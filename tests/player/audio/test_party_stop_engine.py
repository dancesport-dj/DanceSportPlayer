#!/usr/bin/env python3
"""⏹ The planned stop on the ▶ Playing panel and in the advance engine.

Run:  py -m unittest tests.player.audio.test_party_stop_engine -v

The stop row sits under 🔁 and, like it, needs ⏭ auto-advance. When the rule
is due, a title end arms no pause and starts nothing: the next title is cued
for ⏯ instead. Nothing of it is saved.
"""
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from PySide6.QtMultimedia import QMediaPlayer

from player.audio.between_dances import BetweenDances
from player.audio.fade_now import FadeNow
from player.audio.playback_state import PlaybackState
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
        self.assertFalse(p.stop_time_combo.isVisible())
        self.assertEqual(p.stop_text(), "")

    def test_it_leaves_the_panel_without_auto_advance(self):
        p = self.panel(auto_advance=False)
        self.assertFalse(p.stop_row_box.isVisible())
        p.advance_check.setChecked(True)
        self.assertTrue(p.stop_row_box.isVisible())

    def test_a_count_shows_its_spinner_and_counts_down(self):
        """F14: the spinner keeps the number set, the counter beside it —
        in the length hint's amber and bold — runs down."""
        p = self.panel(auto_advance=True)
        p.stop_count_spin.setValue(3)
        self.assertFalse(p.stop_count_lbl.isVisible())
        self.choose(p, "count")
        self.assertTrue(p.stop_count_spin.isVisible())
        self.assertTrue(p.stop_count_lbl.isVisible())
        self.assertEqual(p.stop_count_lbl.text(), "3 left")
        self.assertIn("#b8860b", p.stop_count_lbl.styleSheet())
        self.assertIn("bold", p.stop_count_lbl.styleSheet())
        self.assertFalse(p.stop_title_ended(datetime.now()))
        self.assertEqual(p.stop_count_spin.value(), 3)
        self.assertEqual(p.stop_count_lbl.text(), "2 left")
        self.assertFalse(p.stop_title_ended(datetime.now()))
        self.assertEqual(p.stop_combo.currentData(), "this")
        self.assertFalse(p.stop_count_lbl.isVisible())
        self.assertTrue(p.stop_title_ended(datetime.now()))
        self.assertEqual(p.stop_combo.currentData(), "never")

    def _offers(self, *times):
        """The list the clock would give, the way `stop_time_choices` does."""
        slots = [datetime(2026, 10, 24, *map(int, t.split(":"))) for t in times]
        patcher = mock.patch("player.widgets.play_mode_panel.stop_time_choices",
                             return_value=slots)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def _pick(self, p, text):
        """What a click on a line of the open list does."""
        at = p.stop_time_combo.findText(text)
        p.stop_time_combo.setCurrentIndex(at)
        p.stop_time_combo.activated.emit(at)

    def _times(self, p):
        return [p.stop_time_combo.itemText(i) for i in range(p.stop_time_combo.count())]

    def test_a_time_shows_its_list_on_23_00(self):
        self._offers("22:30", "23:00", "23:30")
        p = self.panel(auto_advance=True)
        self.choose(p, "time")
        self.assertTrue(p.stop_time_combo.isVisible())
        self.assertEqual(self._times(p), ["22:30", "23:00", "23:30"])
        self.assertEqual(p.stop_text(), "⏹  Stops at 23:00")

    def test_past_23_00_it_opens_on_the_first_time_left(self):
        self._offers("23:25", "23:30")
        p = self.panel(auto_advance=True)
        self.choose(p, "time")
        self.assertEqual(p.stop_text(), "⏹  Stops at 23:25")

    def test_picking_a_time_arms_it(self):
        self._offers("22:30", "23:00", "23:30")
        p = self.panel(auto_advance=True)
        self.choose(p, "time")
        self._pick(p, "23:30")
        self.assertEqual(p.stop_text(), "⏹  Stops at 23:30")

    def _type(self, p, text):
        """What a double click, typing and Enter do."""
        combo = p.stop_time_combo
        combo.beginTyping()
        combo.lineEdit().setText(text)
        combo.lineEdit().editingFinished.emit()

    def test_a_double_click_opens_the_field_for_typing(self):
        self._offers("22:30", "23:00")
        p = self.panel(auto_advance=True)
        self.choose(p, "time")
        self.assertTrue(p.stop_time_combo.lineEdit().isReadOnly())
        p.stop_time_combo.beginTyping()
        self.assertFalse(p.stop_time_combo.lineEdit().isReadOnly())

    def test_a_typed_time_arms_even_off_the_list(self):
        self._offers("22:30", "23:00")
        p = self.panel(auto_advance=True)
        self.choose(p, "time")
        self._type(p, "23:17")
        self.assertEqual(p.stop_text(), "⏹  Stops at 23:17")
        self.assertEqual(p.stop_time_combo.currentText(), "23:17")
        self.assertTrue(p.stop_time_combo.lineEdit().isReadOnly())
        self.assertEqual(self._times(p), ["22:30", "23:00"])

    def test_a_typed_time_survives_the_list_opening(self):
        self._offers("22:30", "23:00")
        p = self.panel(auto_advance=True)
        self.choose(p, "time")
        self._type(p, "23:17")
        p.stop_time_combo.showPopup()
        p.stop_time_combo.hidePopup()
        self.assertEqual(p.stop_time_combo.currentText(), "23:17")
        self.assertEqual(p.stop_text(), "⏹  Stops at 23:17")

    def test_nonsense_typed_keeps_the_time_there_was(self):
        self._offers("22:30", "23:00")
        p = self.panel(auto_advance=True)
        self.choose(p, "time")
        self._type(p, "soon")
        self.assertEqual(p.stop_time_combo.currentText(), "23:00")
        self.assertEqual(p.stop_text(), "⏹  Stops at 23:00")

    def test_the_first_time_left_can_replace_one_gone_by(self):
        """Armed for 23:00, opened at 23:02: the list stands on 23:05 already,
        and clicking the line it stands on still has to arm it."""
        offer = self._offers("22:30", "23:00")
        p = self.panel(auto_advance=True)
        self.choose(p, "time")
        offer.return_value = [datetime(2026, 10, 24, 23, 5),
                              datetime(2026, 10, 24, 23, 10)]
        p.stop_time_combo.showPopup()
        p.stop_time_combo.hidePopup()
        self._pick(p, "23:05")
        self.assertEqual(p.stop_text(), "⏹  Stops at 23:05")

    def test_the_list_follows_the_clock_when_it_opens(self):
        """A panel set up at six still offers the truth at eleven."""
        offer = self._offers("22:30", "23:00", "23:30")
        p = self.panel(auto_advance=True)
        self.choose(p, "time")
        offer.return_value = [datetime(2026, 10, 24, 23, 0),
                              datetime(2026, 10, 24, 23, 5)]
        p.stop_time_combo.showPopup()
        p.stop_time_combo.hidePopup()
        self.assertEqual(self._times(p), ["23:00", "23:05"])

    def test_opening_the_list_does_not_arm_anything(self):
        offer = self._offers("22:30", "23:00", "23:30")
        p = self.panel(auto_advance=True)
        self.choose(p, "time")
        self._pick(p, "23:30")
        armed = p._party_stop.at
        offer.return_value = [datetime(2026, 10, 24, 23, 30),
                              datetime(2026, 10, 24, 23, 35)]
        changes = []
        p.stopRuleChanged.connect(lambda: changes.append(1))
        p.stop_time_combo.showPopup()
        p.stop_time_combo.hidePopup()
        self.assertEqual(changes, [])
        self.assertEqual(p._party_stop.at, armed)
        self.assertEqual(p.stop_time_combo.currentText(), "23:30")

    def test_the_real_list_is_there_at_any_hour(self):
        p = self.panel(auto_advance=True)
        self.choose(p, "time")
        self.assertGreater(p.stop_time_combo.count(), 0)
        self.assertTrue(p.stop_text().startswith("⏹  Stops at "))

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

    def test_the_at_mode_shows_only_beside_a_time(self):
        p = self.panel(auto_advance=True)
        self.assertFalse(p.stop_at_mode_combo.isVisible())
        self.choose(p, "time")
        self.assertTrue(p.stop_at_mode_combo.isVisible())
        self.choose(p, "count")
        self.assertFalse(p.stop_at_mode_combo.isVisible())

    def test_the_at_mode_plays_to_the_end_unless_told_otherwise(self):
        self.assertEqual(self.panel(auto_advance=True).stop_at_mode(), "end")
        p = self.panel(auto_advance=True, stop_at_mode="hybrid")
        self.assertEqual(p.stop_at_mode(), "hybrid")

    def test_the_at_mode_is_saved(self):
        p = self.panel(auto_advance=True)
        saved = []
        p.settingsChanged.connect(lambda: saved.append(1))
        p.stop_at_mode_combo.setCurrentIndex(
            p.stop_at_mode_combo.findData("fade"))
        self.assertEqual(saved, [1])


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

    def test_a_title_ending_just_before_the_time_starts_the_next(self):
        """The music runs at least until the time: a title ending 30 s short
        of it is followed by the next one, which then plays out (or fades,
        when "At …" is set so — not this one, it started after the time)."""
        desk = self.deck()
        self.table._current_play_row = self.song_rows()[0]
        p = desk._play_panel
        p.stop_combo.setCurrentIndex(p.stop_combo.findData("time"))
        p._party_stop.at = datetime.now() + timedelta(seconds=30)
        desk._queue_auto_advance()
        self.assertIsNotNone(desk._between.pending)
        self.assertIsNone(desk._between.cue_next)
        self.assertEqual(p.stop_combo.currentData(), "time")

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


class _TickPlayer:
    """Just enough media player for the play tick."""

    def __init__(self, pos_ms):
        self.pos_ms = pos_ms

    def playbackState(self):
        return QMediaPlayer.PlaybackState.PlayingState

    def position(self):
        return self.pos_ms

    def playbackRate(self):
        return 1.0


class StopFadeTickTest(_Fixture):
    """⏹ "At …" set to fade: the play tick fades the title on air out once
    the time has come. Its end is then the planned stop (StopEngineTest)."""

    def desk(self, mode, played_secs, past_secs=5, advance=True):
        from player.window.main_player import PlayerControlMixin

        class Desk(PlayerControlMixin):
            def __init__(self, panel):
                self._play_panel = panel
                self._player = _TickPlayer(int(played_secs * 1000))
                self._playback = PlaybackState(path=Path(r"C:\music\ww.mp3"),
                                               dance="WW")
                self._between = BetweenDances()
                self._fade_now = FadeNow()
                self._played_marked = True
                self._mix = SimpleNamespace(fade=1.0)
                self.faded = []

            def _maybe_skip_silence(self):
                return False

            def _watch_stall(self):
                return False

            def _step_fade_in(self):
                pass

            def _is_playing_mode(self):
                return True

            def _note_on_air(self):
                pass

            def _fade_out_now(self):
                self.faded.append(True)

            def _maybe_crossfade(self):
                pass

            def _pd_runs_to_its_highlight(self):
                return False

            def _play_limit_secs(self):
                return 0

            def _set_countdown(self, text):
                pass

        p = PlayModePanel({"auto_advance": advance, "stop_at_mode": mode})
        self.addCleanup(reap_widget, p)
        p.stop_combo.setCurrentIndex(p.stop_combo.findData("time"))
        p._party_stop.at = datetime.now() - timedelta(seconds=past_secs)
        return Desk(p)

    def tick(self, desk) -> bool:
        desk._on_play_tick()
        return bool(desk.faded)

    def test_play_to_the_end_lets_it_run(self):
        self.assertFalse(self.tick(self.desk("end", played_secs=120)))

    def test_fade_mode_fades_the_title_on_air(self):
        self.assertTrue(self.tick(self.desk("fade", played_secs=120)))

    def test_fade_mode_spares_a_title_started_after_the_time(self):
        self.assertFalse(self.tick(self.desk("fade", played_secs=3)))

    def test_hybrid_fades_only_a_title_that_had_played_1_30(self):
        self.assertTrue(self.tick(self.desk("hybrid", played_secs=120)))
        self.assertFalse(self.tick(self.desk("hybrid", played_secs=60)))

    def test_a_running_crossfade_is_not_faded(self):
        desk = self.desk("fade", played_secs=120)
        desk._between.xfade.state = "fading"
        self.assertFalse(self.tick(desk))

    def test_without_auto_advance_nothing_fades(self):
        self.assertFalse(self.tick(self.desk("fade", played_secs=120,
                                             advance=False)))


if __name__ == "__main__":
    unittest.main()
