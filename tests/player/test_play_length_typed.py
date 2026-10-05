"""⏱️ The Playing-mode panel's timings: play length, fade-out, ⏸♪.

The ladder's −/+ can only land on 15 s rungs; a heat that wants 1:37 has to be
able to say so. These cover the parser, the in-place editor, the round trip
through the settings, the half-second fade steps and the availability of the
jump-to-pause button.
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_len_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from player.play_mode_panel import (  # noqa: E402
    _LEN_TYPED_MAX,
    _LEN_TYPED_MIN,
    PlayModePanel,
    parse_play_length,
)

_app = QApplication.instance() or QApplication([])


class ParsePlayLengthTest(unittest.TestCase):

    def test_the_form_the_readout_itself_shows(self):
        self.assertEqual(parse_play_length("1:37"), 97)

    def test_a_leading_zero_minute_is_fine(self):
        self.assertEqual(parse_play_length("0:45"), 45)

    def test_bare_seconds_are_taken_as_seconds(self):
        self.assertEqual(parse_play_length("97"), 97)

    def test_full_is_the_off_position_the_label_names(self):
        for text in ("full", "FULL", " full ", "voll", "0"):
            self.assertEqual(parse_play_length(text), 0, text)

    def test_surrounding_space_does_not_matter(self):
        self.assertEqual(parse_play_length("  2:00  "), 120)

    def test_nonsense_is_refused_rather_than_guessed_at(self):
        """A slip must leave the length alone, not set it to something."""
        for text in ("", "   ", "abc", "1:xx", "x:30", "1:2:3", "-30", "1,37"):
            self.assertIsNone(parse_play_length(text), text)

    def test_too_short_is_pulled_up_to_the_floor(self):
        """Below the floor the fade-out would outlast the song."""
        self.assertEqual(parse_play_length("2"), _LEN_TYPED_MIN)

    def test_too_long_is_pulled_down_to_the_ceiling(self):
        self.assertEqual(parse_play_length("99:00"), _LEN_TYPED_MAX)

    def test_seconds_past_sixty_are_still_seconds(self):
        """'90' is a length, not a malformed 1:30 — both mean the same thing."""
        self.assertEqual(parse_play_length("90"), 90)


class TypedLengthSurvivesTest(unittest.TestCase):
    """A typed length is deliberately off the ladder — nothing may snap it."""

    def test_an_off_ladder_length_is_loaded_back_exactly(self):
        secs = PlayModePanel._load_secs({"timed_enabled": True,
                                         "play_secs": 97})
        self.assertEqual(secs, 97)

    def test_an_unticked_pre_ladder_box_is_still_full(self):
        self.assertEqual(
            PlayModePanel._load_secs({"timed_enabled": False,
                                      "play_secs": 105}), 0)

    def test_a_stored_zero_is_full(self):
        self.assertEqual(
            PlayModePanel._load_secs({"timed_enabled": True, "play_secs": 0}), 0)

    def test_the_panel_shows_a_typed_length_as_it_was_typed(self):
        panel = PlayModePanel({"timed_enabled": True, "play_secs": 97})
        self.assertEqual(panel.len_lbl.text(), "1:37")
        self.assertEqual(panel.play_secs(), 97)
        panel.deleteLater()

    def test_stepping_off_a_typed_length_still_moves_by_one_rung(self):
        panel = PlayModePanel({"timed_enabled": True, "play_secs": 97})
        panel._step_len(+1)
        self.assertEqual(panel.play_secs(), 112)
        panel._step_len(-1)
        self.assertEqual(panel.play_secs(), 97)
        panel.deleteLater()


class TypeInPlaceTest(unittest.TestCase):
    """The double-click path: the readout itself turns into the edit field."""

    def setUp(self):
        self.panel = PlayModePanel({"timed_enabled": True, "play_secs": 105})

    def tearDown(self):
        self.panel.deleteLater()

    def _type(self, text):
        """Open the editor, put `text` in it and press Enter."""
        self.panel._on_len_typed()
        self.panel._len_edit.setText(text)
        self.panel._commit_len_typed()

    def test_the_editor_opens_over_the_readout_showing_what_is_set(self):
        """It has to start from the current value — the desk is nudging 1:45 to
        1:37, not entering a length from nothing."""
        self.panel._on_len_typed()
        edit = self.panel._len_edit
        self.assertEqual(edit.text(), "1:45")
        self.assertEqual(edit.parent(), self.panel.len_lbl)
        self.assertEqual(edit.geometry(), self.panel.len_lbl.rect())
        self.assertTrue(edit.hasSelectedText())

    def test_a_typed_length_lands_on_the_readout(self):
        seen = []
        self.panel.settingsChanged.connect(lambda: seen.append(1))
        self._type("1:37")
        self.assertEqual(self.panel.play_secs(), 97)
        self.assertEqual(self.panel.len_lbl.text(), "1:37")
        self.assertEqual(len(seen), 1)

    def test_committing_puts_the_readout_back(self):
        self._type("1:37")
        self.assertTrue(self.panel._len_edit.isHidden())

    def test_escape_abandons_the_edit(self):
        seen = []
        self.panel.settingsChanged.connect(lambda: seen.append(1))
        self.panel._on_len_typed()
        self.panel._len_edit.setText("0:30")
        self.panel._close_len_edit()
        self.assertEqual(self.panel.play_secs(), 105)
        self.assertEqual(seen, [])
        self.assertTrue(self.panel._len_edit.isHidden())

    def test_escape_really_reaches_the_cancel(self):
        """A QLineEdit swallows Esc, which is the whole reason for _InlineEdit —
        if that override is lost the edit becomes impossible to abandon."""
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtGui import QKeyEvent
        self.panel._on_len_typed()
        self.panel._len_edit.keyPressEvent(
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape,
                      Qt.KeyboardModifier.NoModifier))
        self.assertTrue(self.panel._len_edit.isHidden())

    def test_a_second_commit_does_not_fire_twice(self):
        """editingFinished arrives on Enter AND again on the focus-out."""
        seen = []
        self.panel.settingsChanged.connect(lambda: seen.append(1))
        self._type("1:37")
        self.panel._commit_len_typed()
        self.assertEqual(len(seen), 1)

    def test_nonsense_leaves_the_length_standing(self):
        self._type("half past three")
        self.assertEqual(self.panel.play_secs(), 105)

    def test_typing_full_switches_the_cut_off(self):
        self._type("full")
        self.assertEqual(self.panel.play_secs(), 0)
        self.assertFalse(self.panel.timed_enabled())
        self.assertEqual(self.panel.len_lbl.text(), "full")

    def test_typing_what_is_already_set_reports_no_change(self):
        seen = []
        self.panel.settingsChanged.connect(lambda: seen.append(1))
        self._type("1:45")
        self.assertEqual(seen, [])

    def test_the_editor_is_built_once_and_reused(self):
        self.panel._on_len_typed()
        first = self.panel._len_edit
        self.panel._close_len_edit()
        self.panel._on_len_typed()
        self.assertIs(self.panel._len_edit, first)

    def test_the_readout_takes_a_double_click_at_all(self):
        """The handler is hung on the label itself — if that wiring is lost the
        feature is unreachable however good the parser is."""
        self.assertEqual(self.panel.len_lbl.mouseDoubleClickEvent,
                         self.panel._on_len_typed)


class FadeStepTest(unittest.TestCase):
    """The fade-out moves in half seconds — whole ones are too coarse short."""

    def _panel(self, **over):
        return PlayModePanel(dict(over))

    def test_the_arrows_move_by_half_a_second(self):
        p = self._panel(fade_secs=3)
        p.fade_spin.stepUp()
        self.assertEqual(p.fade_secs(), 3.5)
        p.fade_spin.stepDown()
        p.fade_spin.stepDown()
        self.assertEqual(p.fade_secs(), 2.5)
        p.deleteLater()

    def test_a_half_second_fade_is_kept_as_typed(self):
        """It has to survive the panel, not be rounded back to a whole one."""
        p = self._panel(fade_secs=1.5)
        self.assertEqual(p.fade_secs(), 1.5)
        p.deleteLater()

    def test_a_whole_second_setting_from_before_still_loads(self):
        p = self._panel(fade_secs=3)
        self.assertEqual(p.fade_secs(), 3.0)
        p.deleteLater()

    def test_no_fade_is_still_reachable(self):
        p = self._panel(fade_secs=0)
        self.assertEqual(p.fade_secs(), 0.0)
        p.deleteLater()


class PauseAvailableTest(unittest.TestCase):
    """⏸♪ jumps into the between-songs pause — it needs one to exist."""

    def _panel(self, **over):
        base = {"auto_advance": True, "pause_enabled": True}
        base.update(over)
        return PlayModePanel(base)

    def test_both_switches_on_means_available(self):
        p = self._panel()
        self.assertTrue(p.pause_available())
        p.deleteLater()

    def test_unticking_the_pause_takes_it_away(self):
        p = self._panel(pause_enabled=False)
        self.assertFalse(p.pause_available())
        p.deleteLater()

    def test_without_auto_advance_there_is_no_gap_to_fill(self):
        """The tick box stays checked but disabled in that state, so asking it
        alone would call a pause available that can never run."""
        p = self._panel(auto_advance=False)
        self.assertTrue(p.pause_enabled())
        self.assertFalse(p.pause_available())
        p.deleteLater()

    def test_it_follows_a_live_toggle(self):
        p = self._panel()
        p.pause_check.setChecked(False)
        self.assertFalse(p.pause_available())
        p.pause_check.setChecked(True)
        self.assertTrue(p.pause_available())
        p.deleteLater()


if __name__ == "__main__":
    unittest.main()
