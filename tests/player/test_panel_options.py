#!/usr/bin/env python3
"""Options on the ▶ Playing panel, under the player.

  * ▶️ 'Double-click starts the title' — a play-set value, so 🏆 and 🎉 switch
    it over with everything else they switch,
  * 🐂 'Start after: x s' — how long a Paso Doble is held back after the call,
    and
  * 🎙 the advanced voice controls ('…with takt', '…with heat', 🔈 Test), which
    are hidden unless ⚙ Settings asks for them.

Run:  py -m unittest tests.player.test_panel_options -v

The desk column is the most crowded place in the app and the busiest moment to
read it is mid-round. What is set once and never touched again does not belong
there — but hiding a control must not change what it was set to.
"""

import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_panel_opt_"))

from PySide6.QtWidgets import QApplication  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from PySide6.QtCore import Qt  # noqa: E402
from player.play_mode_panel import PlayModePanel, _Toggle  # noqa: E402


class _PanelTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def panel(self, **settings) -> PlayModePanel:
        p = PlayModePanel(settings)
        self.addCleanup(reap_widget, p)
        # Only a shown widget reports its children's visibility; offscreen this
        # costs nothing.
        p.show()
        return p


class DoubleClickOptionTest(_PanelTest):
    """The ▶️ box sits with the other desk toggles, below the player."""

    def test_it_starts_out_cueing(self):
        self.assertFalse(self.panel().dblclick_plays())

    def test_a_settings_file_that_says_so_starts_it_playing(self):
        self.assertTrue(self.panel(dblclick_plays=True).dblclick_plays())

    def test_it_is_part_of_a_play_set(self):
        p = self.panel()
        self.assertIn("dblclick", p.play_set())

    def test_a_set_switches_it_over_and_says_so(self):
        p = self.panel()
        changed = p.apply_play_set(secs=0, advance=True, pause_off=True,
                                   dblclick=True)
        self.assertTrue(p.dblclick_plays())
        self.assertTrue(any("double-click" in c for c in changed))

    def test_a_set_stored_before_it_existed_leaves_it_alone(self):
        p = self.panel(dblclick_plays=True)
        p.apply_play_set(secs=0, advance=True, pause_off=True)
        self.assertTrue(p.dblclick_plays())

    def test_changing_it_is_reported_for_saving(self):
        p = self.panel()
        seen = []
        p.settingsChanged.connect(lambda: seen.append(p.dblclick_plays()))
        p.dblclick_check.setChecked(True)
        self.assertEqual(seen, [True])


class PdStartDelayTest(_PanelTest):
    """🐂 'Start after: x s', in the Paso Doble block."""

    def test_a_paso_doble_starts_at_once_by_default(self):
        self.assertEqual(self.panel().pd_start_delay(), 0)

    def test_a_settings_file_sets_the_wait(self):
        self.assertEqual(self.panel(pd_start_delay=6).pd_start_delay(), 6)

    def test_who_calls_it_is_not_a_second_switch(self):
        """🔈 Announce next dance already says whether the app speaks."""
        self.assertFalse(hasattr(self.panel(), "pd_call_check"))

    def test_changing_the_wait_is_reported_for_saving(self):
        p = self.panel(pd_start_delay=5)
        seen = []
        p.settingsChanged.connect(lambda: seen.append(p.pd_start_delay()))
        p.pd_delay_spin.setValue(8)
        self.assertEqual(seen, [8])


class VoiceControlsTest(_PanelTest):
    """'…with takt', '…with heat' and 🔈 Test are advanced — off the panel
    unless asked for."""

    def _advanced(self, p):
        return (p.announce_takt_check, p.announce_heat_check,
                p.announce_test_btn)

    def test_they_are_not_shown_by_default(self):
        p = self.panel()
        for w in self._advanced(p):
            with self.subTest(control=w.text()):
                self.assertFalse(w.isVisible())

    def test_the_setting_brings_them_out(self):
        p = self.panel(announce_next=True, announce_advanced=True)
        for w in self._advanced(p):
            with self.subTest(control=w.text()):
                self.assertTrue(w.isVisible())

    def test_they_can_be_switched_on_and_off_live(self):
        """⚙ Settings applies without a restart."""
        p = self.panel(announce_next=True)
        p.set_voice_advanced_shown(True)
        self.assertTrue(p.announce_test_btn.isVisible())
        p.set_voice_advanced_shown(False)
        self.assertFalse(p.announce_test_btn.isVisible())

    def test_hidden_is_not_off(self):
        """The announcement keeps saying what it was set to say — only the
        switches are out of the way."""
        p = self.panel(announce_next=True, announce_takt=True,
                       announce_heat=True)
        self.assertFalse(p.announce_takt_check.isVisible())
        self.assertTrue(p.announce_takt())
        self.assertTrue(p.announce_heat())

    def test_the_announce_box_itself_stays(self):
        """It is the switch of the round, not fine print."""
        p = self.panel()
        self.assertTrue(p.announce_check.isVisible())

    def test_the_voice_comes_with_the_announcement(self):
        """Nothing is announced, so there is nothing to pick a voice for."""
        p = self.panel(announce_next=False)
        self.assertFalse(p.announce_voice_combo.isVisible())
        p.announce_check.setChecked(True)
        self.assertTrue(p.announce_voice_combo.isVisible())

    def test_the_advanced_pair_stays_inside_the_announcement(self):
        """⚙ asked for them, but with 🔈 off there is nothing to append to."""
        p = self.panel(announce_next=False, announce_advanced=True)
        self.assertFalse(p.announce_test_btn.isVisible())
        p.announce_check.setChecked(True)
        self.assertTrue(p.announce_test_btn.isVisible())


class FoldingSubSettingsTest(_PanelTest):
    """A switch that is off has no settings worth a line.

    The desk column is read mid-round and scrolling it then costs a heat, so
    the fine print of 🐂, the pause and 🔈 folds away with the switch above it
    — and comes back with everything it was set to."""

    def test_the_paso_doble_block_follows_its_switch(self):
        p = self.panel(pd_highlight_stop=True)
        self.assertTrue(p.pd_sub_box.isVisible())
        p.pd_check.setChecked(False)
        self.assertFalse(p.pd_sub_box.isVisible())
        for w in (p.pd_spin, p.pd_learn_btn, p.pd_edit_btn):
            with self.subTest(control=w.objectName() or type(w).__name__):
                self.assertFalse(w.isVisible())

    def test_the_wait_after_the_call_does_not_fold_away(self):
        """It is about how a Paso Doble STARTS, not how it ends: the couples
        walk on when the dance is called whether or not a highlight stops it,
        so folding the stop must not take the only way to set the wait with
        it."""
        p = self.panel(pd_highlight_stop=True, pd_start_delay=7)
        p.pd_check.setChecked(False)
        self.assertTrue(p.pd_delay_spin.isVisible())
        self.assertEqual(p.pd_start_delay(), 7)

    def test_a_folded_paso_doble_starts_folded(self):
        p = self.panel(pd_highlight_stop=False)
        self.assertFalse(p.pd_sub_box.isVisible())
        self.assertTrue(p.pd_delay_spin.isVisible())

    def test_folding_it_away_ends_edit_mode(self):
        """Left running behind a hidden button it would keep the highlight stop
        suspended with nothing on screen saying so."""
        p = self.panel(pd_highlight_stop=True)
        p.pd_edit_btn.setChecked(True)
        p.pd_check.setChecked(False)
        self.assertFalse(p.pd_edit_btn.isChecked())
        self.assertFalse(p.pd_marks_box.isVisible())

    def test_the_settings_survive_the_fold(self):
        p = self.panel(pd_highlight_stop=True, pd_highlight_n=3,
                       pd_start_delay=7)
        p.pd_check.setChecked(False)
        p.pd_check.setChecked(True)
        self.assertTrue(p.pd_sub_box.isVisible())
        self.assertEqual(p.pd_spin.value(), 3)
        self.assertEqual(p.pd_start_delay(), 7)

    def test_the_filler_music_follows_the_pause(self):
        p = self.panel(auto_advance=True, pause_enabled=True)
        self.assertTrue(p.pause_sub_box.isVisible())
        p.pause_check.setChecked(False)
        self.assertFalse(p.pause_sub_box.isVisible())
        self.assertFalse(p.pause_music_box.isVisible())

    def test_no_auto_advance_means_no_pause_block_at_all(self):
        """Without ⏭ every song is started by hand, so there is no gap."""
        p = self.panel(auto_advance=False, pause_enabled=True)
        self.assertFalse(p.pause_sub_box.isVisible())

    def test_the_announcement_block_follows_its_switch(self):
        p = self.panel(announce_next=False)
        self.assertFalse(p.announce_sub_box.isVisible())
        p.announce_check.setChecked(True)
        self.assertTrue(p.announce_sub_box.isVisible())

    def test_folding_saves_the_scroll(self):
        """The point of the exercise: a desk with everything off is shorter."""
        wide = self.panel(pd_highlight_stop=True, auto_advance=True,
                          pause_enabled=True, announce_next=True)
        lean = self.panel(pd_highlight_stop=False, auto_advance=True,
                          pause_enabled=False, announce_next=False)
        self.assertLess(lean.sizeHint().height(),
                        wide.sizeHint().height() - 100)


class ToggleButtonTest(_PanelTest):
    """The desk's options are switches, not tick boxes — a trial run, so what
    matters is that the swap changed nothing but the look."""

    _NAMES = ("pd_check", "advance_check", "pause_check", "announce_check",
              "announce_takt_check", "announce_heat_check", "loudness_check",
              "artwork_check", "dblclick_check")

    def test_every_option_is_a_switch(self):
        p = self.panel()
        for name in self._NAMES:
            w = getattr(p, name)
            self.assertIsInstance(w, _Toggle, name)
            self.assertTrue(w.isCheckable(), name)

    def test_a_switch_still_carries_its_setting(self):
        p = self.panel(show_artwork=True, loudness_eq=False)
        self.assertTrue(p.artwork_check.isChecked())
        self.assertFalse(p.loudness_check.isChecked())

    def test_it_still_toggles_and_still_tells(self):
        p = self.panel(show_artwork=False)
        seen = []
        p.artwork_check.toggled.connect(seen.append)
        p.artwork_check.setChecked(True)
        self.assertEqual(seen, [True])

    def test_the_space_bar_belongs_to_the_transport(self):
        """A focused button would swallow it; the desk plays and pauses with it."""
        p = self.panel()
        self.assertEqual(p.dblclick_check.focusPolicy(),
                         Qt.FocusPolicy.NoFocus)

    def test_the_knob_sits_where_the_state_says(self):
        """Built already-on, the switch must not slide itself on the way in."""
        p = self.panel(show_artwork=True, dblclick_plays=False)
        self.assertEqual(p.artwork_check.slide, 1.0)
        self.assertEqual(p.dblclick_check.slide, 0.0)

    def test_flipping_it_on_screen_slides_the_knob(self):
        p = self.panel(show_artwork=False)
        p.artwork_check.setChecked(True)
        self.assertEqual(p.artwork_check._anim.endValue(), 1.0)
        p.artwork_check.settle()
        self.assertEqual(p.artwork_check.slide, 1.0)

    def test_the_pill_survives_a_narrow_column(self):
        """A squeezed desk elides the caption; the switch itself stays whole."""
        p = self.panel()
        w = p.dblclick_check
        self.assertGreater(w.minimumSizeHint().width(), w._TRACK_W)
        w.resize(w._TRACK_W + 12, w.sizeHint().height())
        w.render(w.grab())          # must paint, not divide by a negative width

    def test_the_voice_extras_still_follow_the_announcement(self):
        p = self.panel(announce_next=False)
        self.assertFalse(p.announce_takt_check.isEnabled())
        self.assertFalse(p.announce_heat_check.isEnabled())


class FreshInstallDefaultsTest(_PanelTest):
    """What the panel looks like before anyone has saved a setting.

    An install with no gui_settings.json yet is what a new user sees first, so
    these three are a decision, not an accident: songs run back to back, the
    levels are pulled together, and the player card shows a cover.
    """

    def test_the_break_between_songs_starts_off(self):
        p = self.panel()
        self.assertFalse(p.pause_check.isChecked())
        self.assertFalse(p.pause_enabled())

    def test_the_configured_break_length_is_still_there(self):
        """Off is not zero — the box keeps a time for switching back on."""
        self.assertEqual(self.panel().pause_spin.value(), 15)

    def test_the_levels_are_equalized(self):
        self.assertTrue(self.panel().loudness_check.isChecked())

    def test_the_artwork_shows(self):
        p = self.panel()
        self.assertTrue(p.artwork_check.isChecked())
        self.assertTrue(p.show_artwork())

    def test_a_saved_setting_still_wins(self):
        p = self.panel(pause_enabled=True, show_artwork=False, loudness_eq=False)
        self.assertTrue(p.pause_check.isChecked())
        self.assertFalse(p.artwork_check.isChecked())
        self.assertFalse(p.loudness_check.isChecked())


class KeepAwakeOptionTest(_PanelTest):
    """☀ 'Keep the screen awake', right below the 🖥 presenter row."""

    def test_the_screen_stays_awake_by_default(self):
        """A tournament runs for hours with nobody touching the desk — the
        screensaver blanking the beamer mid-heat is never what was wanted."""
        self.assertTrue(self.panel().keep_awake())

    def test_a_settings_file_can_switch_it_off(self):
        self.assertFalse(self.panel(keep_awake=False).keep_awake())

    def test_it_sits_below_the_presenter_row(self):
        """Next to the button whose screen it mostly protects."""
        p = self.panel()
        # Both live in the same group of the panel — the one the ─── rules cut
        # out around the day's buttons.
        lyt = p.awake_check.parentWidget().layout()
        pres = awake = None
        for i in range(lyt.count()):
            w = lyt.itemAt(i).widget()
            if w is not None and w.isAncestorOf(p.presenter_btn):
                pres = i
            if w is p.awake_check:
                awake = i
        self.assertIsNotNone(pres)
        self.assertIsNotNone(awake)
        self.assertGreater(awake, pres)

    def test_changing_it_is_reported_for_saving(self):
        p = self.panel()
        seen = []
        p.settingsChanged.connect(lambda: seen.append(p.keep_awake()))
        p.awake_check.setChecked(False)
        self.assertEqual(seen, [False])

    def test_it_is_no_part_of_a_play_set(self):
        """The screen behaves the same at a party as in a heat — a play set has
        no business turning the screensaver back on."""
        self.assertNotIn("awake", self.panel().play_set())



if __name__ == "__main__":
    unittest.main(verbosity=2)
