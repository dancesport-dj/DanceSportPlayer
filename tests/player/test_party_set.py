#!/usr/bin/env python3
"""Tests for the 🎉 party set: its TSO handling (`PlayerControlMixin._set_party_mode`)
and its promise that a party runs WITHOUT breaks.

Run:  py -m unittest tests.player.test_party_set -v

TSO pitches every title to the mean tempo of its heat — right for a round of
Quicksteps, wrong for a party, where the next song is a different dance at
whatever tempo it was recorded at. So the party set switches it off, and
switching the party set back off puts it back where the operator had it.

The toggle lives on the player card, not on the play panel, so it cannot ride
along in `apply_play_set()`; each set carries its own answer as a sibling key
`"tso"`, read by `tso_of()`. Switching the party set off applies the 🏆
tournament set, pitch and all — see DeckComesBackToTheSetTest.
"""

import os
import tempfile
import time
import unittest
from pathlib import Path

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_party_"))

from PySide6.QtMultimedia import QMediaPlayer  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from player.main_player import PlayerControlMixin  # noqa: E402
from planner.play_sets import (  # noqa: E402
    _PARTY_SET, _TOURNAMENT_SET, play_set_of, tso_of,
)
from player.play_mode_panel import PlayModePanel  # noqa: E402
from shared.columns import _COL_TITLE  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.models import MusicEntry  # noqa: E402
from player.between_dances import BetweenDances  # noqa: E402
from player.pause_filler import PauseFiller  # noqa: E402

# What the panel happens to be standing on before anything is applied — neither
# set, the way an operator's hand leaves it.
_HAND_PICKED = {"secs": 90, "fade": 3.0, "advance": False, "pause_off": False,
                "loudness": False, "announce": True, "dblclick": False}


class _Panel:
    """The play panel reduced to the party-set contract — with the REAL
    `apply_play_set` signature, so a stray "tso" kwarg is a TypeError here just
    as it would be in the app."""

    def __init__(self):
        self._set = dict(_HAND_PICKED)
        self.party_on = False
        self.tournament_lit = False
        self.pd_stop = True

    def play_set(self) -> dict:
        return dict(self._set)

    def apply_play_set(self, secs, advance, pause_off, loudness=None,
                       announce=None, fade=None, dblclick=None) -> list:
        new = {"secs": secs, "advance": advance, "pause_off": pause_off}
        if loudness is not None:
            new["loudness"] = loudness
        if announce is not None:
            new["announce"] = announce
        if fade is not None:
            new["fade"] = fade
        if dblclick is not None:
            new["dblclick"] = dblclick
        changed = [k for k, v in new.items() if self._set.get(k) != v]
        self._set.update(new)
        return changed

    def set_pd_highlight_stop(self, on: bool) -> list:
        was, self.pd_stop = self.pd_stop, bool(on)
        return [] if was == bool(on) else ["🐂 Paso Doble highlight stop → off"]

    def set_party_on(self, on: bool):
        self.party_on = on
        if on:
            self.tournament_lit = False

    def set_tournament_on(self, on: bool):
        self.tournament_lit = on

    def tournament_on(self) -> bool:
        return self.tournament_lit


class _BigPlayer:
    def __init__(self, tso: bool = False):
        self._tso = tso

    def tso_mode(self) -> bool:
        return self._tso

    def set_tso_mode(self, on: bool):
        self._tso = bool(on)


class _Desk(PlayerControlMixin, QWidget):
    """A player desk stripped to the party set. `_save_play_settings` records
    instead of writing the real settings file."""

    def __init__(self, tso: bool = True, big_player: bool = True):
        QWidget.__init__(self)
        self._play_panel = _Panel()
        self._big_player = _BigPlayer(tso) if big_player else None
        self._settings = {}
        self.saves = 0

    def _save_play_settings(self):
        self.saves += 1


class PartySetTsoTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.desk = _Desk()
        self.addCleanup(reap_widget, self.desk)

    def test_the_party_set_equalizes_the_volume(self):
        """Party songs come off all sorts of CDs — they must not jump in level."""
        self.assertIs(_PARTY_SET["loudness"], True)

    def test_a_double_click_plays_at_a_party(self):
        """Someone asks for a song: double-click, and it runs."""
        self.assertIs(_PARTY_SET["dblclick"], True)

    def test_a_double_click_only_cues_at_a_tournament(self):
        """A heat starts on ⏯, when the couples stand — not the moment the
        operator picks the next title out of the deck."""
        self.assertIs(_TOURNAMENT_SET["dblclick"], False)

    def test_the_two_sets_switch_it_over(self):
        self.desk._set_party_mode(True)
        self.assertIs(self.desk._play_panel.play_set()["dblclick"], True)
        self.desk._apply_tournament_set()
        self.assertIs(self.desk._play_panel.play_set()["dblclick"], False)

    def test_switching_the_party_set_on_switches_tso_off(self):
        self.desk._set_party_mode(True)
        self.assertFalse(self.desk._big_player.tso_mode())
        self.assertIs(self.desk._settings["tso_equalize"], False)

    def test_switching_it_back_off_puts_tso_back(self):
        self.desk._set_party_mode(True)
        self.desk._set_party_mode(False)
        self.assertTrue(self.desk._big_player.tso_mode())
        self.assertIs(self.desk._settings["tso_equalize"], True)

    def test_the_tournament_set_owns_the_pitch_coming_back(self):
        """Not the toggle's position before the party: a deck taking over is a
        round starting, and a heat is danced to the dance's mean tempo."""
        desk = _Desk(tso=False)
        self.addCleanup(reap_widget, desk)
        desk._set_party_mode(True)
        desk._set_party_mode(False)
        self.assertTrue(desk._big_player.tso_mode())

    def test_the_operator_can_configure_that_pitch_away(self):
        """⚙ Settings → 🎛 Play sets → 🏆 → 🎚 TSO."""
        self.desk._settings["tournament_set"] = dict(_TOURNAMENT_SET, tso=False)
        self.desk._set_party_mode(True)
        self.desk._set_party_mode(False)
        self.assertFalse(self.desk._big_player.tso_mode())

    def test_tso_never_reaches_the_play_panel(self):
        """It is not one of the panel's controls — passing it would raise."""
        self.desk._set_party_mode(True)
        self.desk._set_party_mode(False)
        self.assertNotIn("tso", self.desk._play_panel.play_set())

    def test_the_two_sets_take_turns(self):
        self.desk._set_party_mode(True)
        self.assertEqual(self.desk._play_panel.play_set(), _PARTY_SET)
        self.desk._set_party_mode(False)
        self.assertEqual(self.desk._play_panel.play_set(), _TOURNAMENT_SET)

    def test_a_party_can_be_configured_to_keep_the_pitch(self):
        """⚙ Settings → 🎛 Play sets → 🎉 → 🎚 TSO: the operator's word wins."""
        self.desk._settings["party_set"] = dict(_PARTY_SET, tso=True)
        self.desk._set_party_mode(True)
        self.assertTrue(self.desk._big_player.tso_mode())

    def test_a_desk_without_a_player_card_still_switches(self):
        """Playing mode may never have been opened — no card, no TSO toggle."""
        desk = _Desk(big_player=False)
        self.addCleanup(reap_widget, desk)
        desk._set_party_mode(True)
        desk._set_party_mode(False)
        self.assertEqual(desk._play_panel.play_set(), _TOURNAMENT_SET)


class TournamentSetTest(unittest.TestCase):
    """🏆 Tournament set: the competition values in one press.

    Not a toggle — there is nothing to restore afterwards, these ARE the values
    a heat is run with. So it also switches the 🎉 party set off and drops the
    values that set was standing on."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.desk = _Desk()
        self.addCleanup(reap_widget, self.desk)

    def test_it_is_what_a_heat_is_run_with(self):
        """1:40 per song out over 3 s, started by the operator, nothing
        spoken in between."""
        self.assertEqual(_TOURNAMENT_SET["secs"], 100)
        self.assertEqual(_TOURNAMENT_SET["fade"], 3.0)
        self.assertIs(_TOURNAMENT_SET["advance"], False)
        self.assertIs(_TOURNAMENT_SET["pause_off"], True)
        self.assertIs(_TOURNAMENT_SET["announce"], False)

    def test_the_paso_doble_stop_is_not_a_configurable_value(self):
        """It is not one of the values either set carries — 🏆 switches it off
        outright (below), and nobody can configure that away."""
        for s in (_TOURNAMENT_SET, _PARTY_SET):
            self.assertNotIn("pd_highlight_stop", s)
            self.assertNotIn("pd", s)

    def test_it_switches_the_paso_doble_stop_off(self):
        """🐂 Cutting a competition Paso Doble on a detected highlight is not
        reliable enough yet, and a heat stopped in the wrong bar is danced
        twice — so pressing 🏆 puts it out."""
        panel = PlayModePanel({"pd_highlight_stop": True})
        self.addCleanup(reap_widget, panel)
        self.desk._play_panel = panel
        self.desk._apply_tournament_set()
        self.assertFalse(panel.pd_highlight_stop())

    def test_it_says_that_it_did(self):
        panel = PlayModePanel({"pd_highlight_stop": True})
        self.addCleanup(reap_widget, panel)
        said = panel.set_pd_highlight_stop(False)
        self.assertTrue([s for s in said if "Paso Doble" in s])
        self.assertEqual(panel.set_pd_highlight_stop(False), [],
                         "already off — nothing to report")

    def test_a_party_leaves_the_paso_doble_stop_alone(self):
        """Only the 🏆 set touches it: a party has no heats to cut short, and
        the operator's own setting is what a deck comes back to."""
        for on in (True, False):
            panel = PlayModePanel({"pd_highlight_stop": on})
            self.addCleanup(reap_widget, panel)
            panel.apply_play_set(**_PARTY_SET)
            self.assertIs(panel.pd_highlight_stop(), on)

    def test_pressing_it_applies_the_competition_values(self):
        self.desk._apply_tournament_set()
        self.assertEqual(self.desk._play_panel.play_set(), _TOURNAMENT_SET)

    def test_it_switches_the_party_set_off(self):
        self.desk._set_party_mode(True)
        self.desk._apply_tournament_set()
        self.assertFalse(self.desk._play_panel.party_on)

    def test_the_party_button_can_be_used_again_afterwards(self):
        """_set_party_mode returns early when it thinks it is already on."""
        self.desk._set_party_mode(True)
        self.desk._apply_tournament_set()
        self.desk._set_party_mode(True)
        self.assertEqual(self.desk._play_panel.play_set(), _PARTY_SET)

    def test_it_is_persisted_like_every_other_play_setting(self):
        self.desk._apply_tournament_set()
        self.assertTrue(self.desk.saves)

    def test_it_switches_the_tso_pitch_on(self):
        """A heat is danced to the dance's mean tempo — that is what TSO is."""
        desk = _Desk(tso=False)
        self.addCleanup(reap_widget, desk)
        desk._apply_tournament_set()
        self.assertTrue(desk._big_player.tso_mode())

    def test_the_operator_can_configure_the_pitch_away(self):
        self.desk._settings["tournament_set"] = dict(_TOURNAMENT_SET, tso=False)
        self.desk._big_player.set_tso_mode(True)
        self.desk._apply_tournament_set()
        self.assertFalse(self.desk._big_player.tso_mode())

    def test_pressing_it_lights_the_button(self):
        self.desk._apply_tournament_set()
        self.assertTrue(self.desk._play_panel.tournament_on())

    def test_a_party_puts_the_light_out(self):
        self.desk._apply_tournament_set()
        self.desk._set_party_mode(True)
        self.assertFalse(self.desk._play_panel.tournament_on())


class PartyOffIsTheTournamentSetTest(unittest.TestCase):
    """🎉 clicked off puts the 🏆 set on — not a snapshot.

    The two sets are a pair, and the way out of one is the other. It used to
    restore whatever the panel happened to hold when the party began, and that
    snapshot re-made itself on every switch — so a panel that was once on
    hand-picked values could never find its way back to the set.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.desk = _Desk()
        self.addCleanup(reap_widget, self.desk)

    def test_clicking_the_party_off_applies_the_tournament_set(self):
        self.desk._set_party_mode(True)
        self.desk._set_party_mode(False)
        self.assertEqual(self.desk._play_panel.play_set(), _TOURNAMENT_SET)

    def test_hand_picked_values_do_not_survive_the_party(self):
        """His case: secs 15 with announcements on, from some evening long ago,
        coming back onto the panel at the start of every round."""
        self.desk._play_panel._set.update(secs=15, announce=True, advance=True)
        self.desk._set_party_mode(True)
        self.desk._set_party_mode(False)
        self.assertEqual(self.desk._play_panel.play_set(), _TOURNAMENT_SET)

    def test_switching_back_and_forth_cannot_drift(self):
        """The old snapshot was a fixed point; these two are constants."""
        for _ in range(3):
            self.desk._set_party_mode(True)
            self.assertEqual(self.desk._play_panel.play_set(), _PARTY_SET)
            self.desk._set_party_mode(False)
            self.assertEqual(self.desk._play_panel.play_set(), _TOURNAMENT_SET)

    def test_a_configured_tournament_set_is_what_comes_back(self):
        """⚙ Settings → 🎛 Play sets, not the built-in default."""
        self.desk._settings["tournament_set"] = dict(_TOURNAMENT_SET, secs=105)
        self.desk._set_party_mode(True)
        self.desk._set_party_mode(False)
        self.assertEqual(self.desk._play_panel.play_set()["secs"], 105)

    def test_the_tso_pitch_comes_back_with_it(self):
        """A heat is danced to the dance's mean tempo — the tournament set's
        own answer, not whatever the toggle was before the party."""
        desk = _Desk(tso=False)
        self.addCleanup(reap_widget, desk)
        desk._set_party_mode(True)
        desk._set_party_mode(False)
        self.assertTrue(desk._big_player.tso_mode())

    def test_the_light_says_so(self):
        """🏆 reports where the panel stands, and it now always stands there."""
        self.desk._set_party_mode(True)
        self.desk._set_party_mode(False)
        self.assertTrue(self.desk._play_panel.tournament_on())


class WhichSetIsOnTest(unittest.TestCase):
    """🏆/🎉 say which set the panel is STANDING on, not which was last applied.

    Both tooltips have always promised it — "lit gold while the panel stands on
    those values" — but the lights were set when a set was applied and stayed
    lit while the controls underneath them were moved by hand. Both out means
    the panel is on the operator's own values, which is worth being able to see.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.desk = _Desk()
        self.addCleanup(reap_widget, self.desk)

    def lights(self):
        p = self.desk._play_panel
        return p.party_on, p.tournament_on()

    def test_a_control_moved_by_hand_puts_the_light_out(self):
        self.desk._apply_tournament_set()
        self.assertEqual(self.lights(), (False, True))
        self.desk._play_panel._set["secs"] = 120      # as a hand on the spin box
        self.desk._refresh_set_lights()
        self.assertEqual(self.lights(), (False, False))

    def test_putting_the_value_back_lights_it_again(self):
        self.desk._apply_tournament_set()
        self.desk._play_panel._set["secs"] = 120
        self.desk._refresh_set_lights()
        self.desk._play_panel._set["secs"] = _TOURNAMENT_SET["secs"]
        self.desk._refresh_set_lights()
        self.assertEqual(self.lights(), (False, True))

    def test_the_party_light_follows_the_same_rule(self):
        self.desk._set_party_mode(True)
        self.assertEqual(self.lights(), (True, False))
        self.desk._play_panel._set["announce"] = True
        self.desk._refresh_set_lights()
        self.assertEqual(self.lights(), (False, False))

    def test_a_configured_set_is_what_they_are_measured_against(self):
        """⚙ Settings → 🎛 Play sets moved the goalposts, so the light moves."""
        self.desk._apply_tournament_set()
        self.desk._settings["tournament_set"] = dict(_TOURNAMENT_SET, secs=105)
        self.desk._refresh_set_lights()
        self.assertEqual(self.lights(), (False, False))

    def test_pressing_the_button_applies_again_after_a_drift(self):
        """The panel drifted off the party set during a party: 🎉 is a way back,
        the way 🏆 is, so a press puts the values on again."""
        self.desk._set_party_mode(True)
        self.desk._play_panel._set["secs"] = 120
        self.desk._set_party_mode(True)
        self.assertEqual(self.desk._play_panel.play_set(), _PARTY_SET)


class PlaySetDefaultsTest(unittest.TestCase):
    """Both sets are only defaults — ⚙ Settings → 🎛 Play sets overrides them."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_an_empty_settings_file_yields_the_built_in_sets(self):
        self.assertEqual(play_set_of({}, "party"), _PARTY_SET)
        self.assertEqual(play_set_of({}, "tournament"), _TOURNAMENT_SET)

    def test_a_configured_set_wins(self):
        got = play_set_of({"tournament_set": {"secs": 105, "announce": True}},
                          "tournament")
        self.assertEqual(got["secs"], 105)
        self.assertIs(got["announce"], True)

    def test_fields_are_filled_in_one_by_one(self):
        """A file written before a field joined the set must not lose the rest."""
        got = play_set_of({"party_set": {"secs": 30}}, "party")
        self.assertEqual(got["secs"], 30)
        self.assertIs(got["advance"], _PARTY_SET["advance"])
        self.assertIs(got["loudness"], _PARTY_SET["loudness"])

    def test_a_broken_value_falls_back_instead_of_raising(self):
        got = play_set_of({"party_set": {"secs": "hilfe"}}, "party")
        self.assertEqual(got["secs"], _PARTY_SET["secs"])

    def test_a_set_that_is_not_a_dict_is_ignored(self):
        self.assertEqual(play_set_of({"party_set": "on"}, "party"), _PARTY_SET)

    def test_the_tso_pitch_belongs_to_the_set(self):
        self.assertIs(tso_of({}, "tournament"), True)
        self.assertIs(tso_of({}, "party"), False)

    def test_a_configured_pitch_wins(self):
        self.assertIs(tso_of({"party_set": {"tso": True}}, "party"), True)
        self.assertIs(tso_of({"tournament_set": {"tso": False}}, "tournament"),
                      False)

    def test_a_set_stored_before_the_pitch_joined_it_keeps_the_default(self):
        self.assertIs(tso_of({"tournament_set": {"secs": 90}}, "tournament"),
                      True)

    def test_the_pitch_is_stored_in_the_set_but_never_handed_to_the_panel(self):
        """One set in the settings file, two readers — `apply_play_set` has no
        place for a toggle that lives on the player card."""
        self.assertNotIn("tso", play_set_of({"party_set": {"tso": True}},
                                            "party"))

    def test_the_desk_reads_the_configured_party_set(self):
        desk = _Desk()
        self.addCleanup(reap_widget, desk)
        desk._settings["party_set"] = dict(_PARTY_SET, secs=45)
        desk._set_party_mode(True)
        self.assertEqual(desk._play_panel.play_set()["secs"], 45)


class PartyPanelNoBreakTest(unittest.TestCase):
    """The panel side of "no breaks": what the REAL controls read out once the
    🎉 button has put the party set on them."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.panel = PlayModePanel({"pause_secs": 15, "pause_enabled": True,
                                    "auto_advance": False, "timed_enabled": True,
                                    "play_secs": 90})
        self.addCleanup(reap_widget, self.panel)
        self.panel.apply_play_set(**_PARTY_SET)

    def test_the_engine_sees_no_pause_at_all(self):
        self.assertEqual(self.panel.pause_secs(), 0)
        self.assertFalse(self.panel.pause_enabled())

    def test_every_title_plays_to_its_own_end(self):
        """A timed cut would fade each song out early — a break of its own."""
        self.assertFalse(self.panel.timed_enabled())
        self.assertEqual(self.panel.play_secs(), 0)

    def test_the_next_title_needs_no_operator(self):
        self.assertTrue(self.panel.auto_advance())

    def test_the_tournament_pause_is_only_switched_off_not_forgotten(self):
        """The spin box keeps the configured seconds so the way back is one click."""
        self.assertEqual(self.panel.pause_setting_secs(), 15)
        self.panel.apply_play_set(secs=90, advance=False, pause_off=False,
                                  loudness=False)
        self.assertEqual(self.panel.pause_secs(), 15)

    def test_the_button_itself_drives_the_switch(self):
        """🎉 Party set → partySetToggled → MainWindow._set_party_mode."""
        seen = []
        self.panel.partySetToggled.connect(seen.append)
        self.panel.party_btn.click()
        self.assertEqual(seen, [True])
        self.panel.party_btn.click()
        self.assertEqual(seen, [True, False])

    def test_reflecting_the_state_does_not_re_fire_it(self):
        """`set_party_on` follows the engine; it must not switch anything back."""
        seen = []
        self.panel.partySetToggled.connect(seen.append)
        self.panel.set_party_on(True)
        self.assertEqual(seen, [])
        self.assertTrue(self.panel.party_btn.isChecked())

    def test_the_tournament_button_asks_for_its_set(self):
        """🏆 asks on every press — the check state is a light, not a switch."""
        seen = []
        self.panel.tournamentSetRequested.connect(lambda: seen.append(1))
        self.panel.tournament_btn.click()
        self.panel.tournament_btn.click()
        self.assertEqual(seen, [1, 1])

    def test_the_tournament_button_lights_up_like_the_party_one(self):
        """Both sets say where the panel stands, in their own colour."""
        self.assertTrue(self.panel.tournament_btn.isCheckable())
        self.assertIn(":checked", self.panel.tournament_btn.styleSheet())
        self.assertNotEqual(self.panel.tournament_btn.styleSheet(),
                            self.panel.party_btn.styleSheet())

    def test_the_two_lights_are_never_on_together(self):
        self.panel.set_tournament_on(True)
        self.panel.set_party_on(True)
        self.assertFalse(self.panel.tournament_on())

    def test_lighting_the_tournament_button_does_not_ask_for_the_set(self):
        """`set_tournament_on` follows the engine; it must not re-apply anything."""
        seen = []
        self.panel.tournamentSetRequested.connect(lambda: seen.append(1))
        self.panel.set_tournament_on(True)
        self.assertEqual(seen, [])
        self.assertTrue(self.panel.tournament_on())

    def test_the_tournament_button_sits_above_the_party_one(self):
        # Both stand in the same group of the panel — the one the ─── rules
        # cut out around the day's buttons.
        lyt = self.panel.tournament_btn.parentWidget().layout()
        order = [lyt.indexOf(self.panel.tournament_btn),
                 lyt.indexOf(self.panel.party_btn)]
        self.assertNotIn(-1, order)
        self.assertLess(*order)

    def test_a_party_says_nothing_out_loud(self):
        """No pause to speak into — the voice would land on top of the music."""
        self.assertFalse(self.panel.announce_next())


class PauseRowTest(unittest.TestCase):
    """The pause between songs is switched by the checkbox in front of its own
    seconds — and everything that cannot happen is greyed out: the whole block
    without ⏭ auto-advance (every song is started by hand then, so there is no
    gap to fill), the seconds and the filler music while the pause itself is
    off. Nothing is forgotten; the values come back with the checkbox."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _panel(self, **over):
        s = {"pause_secs": 15, "pause_enabled": True, "auto_advance": True}
        s.update(over)
        panel = PlayModePanel(s)
        self.addCleanup(reap_widget, panel)
        return panel

    def test_the_pause_is_switched_by_its_own_caption(self):
        panel = self._panel()
        self.assertTrue(panel.pause_check.isChecked())
        panel.pause_check.setChecked(False)
        self.assertEqual(panel.pause_secs(), 0)
        self.assertFalse(panel.pause_enabled())

    def test_switching_it_off_keeps_the_seconds(self):
        panel = self._panel()
        panel.pause_check.setChecked(False)
        self.assertEqual(panel.pause_setting_secs(), 15)
        panel.pause_check.setChecked(True)
        self.assertEqual(panel.pause_secs(), 15)

    def test_a_pause_switched_off_greys_its_seconds_and_music_out(self):
        panel = self._panel()
        panel.pause_check.setChecked(False)
        self.assertFalse(panel.pause_spin.isEnabled())
        self.assertFalse(panel.pause_music_box.isEnabled())
        self.assertFalse(panel.pause_vol_box.isEnabled())

    def test_without_auto_advance_the_whole_block_leaves_the_panel(self):
        """Not greyed out — gone. Every song is started by hand there, so a
        pause between two of them is not a dead option but no option at all,
        and a row nobody can ever use is only in the way."""
        panel = self._panel(auto_advance=False)
        self.assertFalse(panel.pause_row_box.isVisibleTo(panel))
        self.assertFalse(panel.pause_check.isVisibleTo(panel))
        self.assertFalse(panel.pause_spin.isVisibleTo(panel))
        self.assertFalse(panel.pause_music_box.isVisibleTo(panel))
        self.assertFalse(panel.pause_vol_box.isVisibleTo(panel))

    def test_switching_auto_advance_back_on_brings_it_back(self):
        panel = self._panel(auto_advance=False)
        panel.advance_check.setChecked(True)
        self.assertTrue(panel.pause_row_box.isVisibleTo(panel))
        self.assertTrue(panel.pause_check.isVisibleTo(panel))
        self.assertTrue(panel.pause_spin.isVisibleTo(panel))
        self.assertTrue(panel.pause_music_box.isVisibleTo(panel))

    def test_a_hidden_pause_is_still_the_configured_one(self):
        """Auto-advance off does not silently switch the pause off — it only
        takes the row away, so the way back is one click and the seconds are
        still there."""
        panel = self._panel(auto_advance=False)
        self.assertTrue(panel.pause_enabled())
        self.assertEqual(panel.pause_secs(), 15)

    def test_the_checkbox_reports_a_change_like_every_other_control(self):
        panel = self._panel()
        seen = []
        panel.settingsChanged.connect(lambda: seen.append(1))
        panel.pause_check.setChecked(False)
        self.assertEqual(seen, [1])

    def test_a_play_set_moves_the_checkbox_and_says_so(self):
        panel = self._panel()
        said = panel.apply_play_set(secs=0, advance=True, pause_off=True)
        self.assertFalse(panel.pause_check.isChecked())
        self.assertTrue([s for s in said if "pause" in s])
        self.assertEqual(panel.apply_play_set(secs=0, advance=True,
                                              pause_off=True), [],
                         "already there — nothing to report")


class _MediaStub:
    """A QMediaPlayer / audio output as much as the advance path touches one."""

    def __init__(self):
        self._src = None
        self.played = 0

    def setSource(self, url):
        self._src = url

    def source(self):
        return self._src

    def playbackState(self):
        return QMediaPlayer.PlaybackState.StoppedState

    def setVolume(self, v):
        pass

    def play(self):
        self.played += 1

    def pause(self):
        pass


class _TimerStub:
    def __init__(self):
        self.running = False

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def isActive(self) -> bool:
        return self.running


class _Announcer:
    def __init__(self):
        self.spoken = []
        self.speaking = False   # the music is held while this is True

    def speak(self, code, takt=None, now=False):
        self.spoken.append(code)
        return True

    def stop(self):
        pass


class _AdvanceDesk(PlayerControlMixin, QWidget):
    """The advance engine reduced to what a party list touches: the REAL play
    panel and the REAL `_queue_auto_advance` / `_on_play_tick`, with the media
    backend, the fade timer and the loudness cache stubbed out."""

    def __init__(self, table, pause_music=()):
        QWidget.__init__(self)
        self._play_panel = PlayModePanel({
            "pause_secs": 15, "pause_enabled": True, "auto_advance": False,
            "timed_enabled": True, "play_secs": 90,
            "pause_music": list(pause_music)})
        self._all_tables = [table]
        self._big_player = None
        self._player = _MediaStub()
        self._pause_player = _MediaStub()
        self._pause_out = _MediaStub()
        self._cache = None          # → _await_loudness has nothing to measure
        self._filler = PauseFiller()
        self._between = BetweenDances()
        self._between.pending = None
        self._between.round_start = None
        self._between.advance_at = 0.0
        self._between.announced = False
        self._between.quiet_until = 0.0
        self._between.held = False
        self._between.fade_end = None
        self._fade_now_end = None
        self._announcer = _Announcer()
        self._fade_timer = _TimerStub()
        self._party_on = False
        self._settings = {}
        self.countdowns = []

    def _is_playing_mode(self) -> bool:
        return True

    def _set_countdown(self, text: str):
        self.countdowns.append(text)

    def _save_play_settings(self):
        pass


def _warmup_entry(dance: str, i: int) -> MusicEntry:
    return MusicEntry(path=Path(rf"C:\music\tanzcds\{dance}{i}.mp3"),
                      title=f"{dance} {i}", dance=dance, duration=180)


class PartyAdvanceNoBreakTest(unittest.TestCase):
    """The engine side: with the party set on, one title follows the next with
    nothing in between — no waiting pause, no filler music, and no 🏁 stop at
    the party list's own ─── section headers."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _desk(self, pause_music=()):
        """A party list of two sections (so it carries a ─── header in the
        middle) on a desk with the party set applied."""
        self.played = []
        self.table = PlaylistTable()
        self.addCleanup(reap_widget, self.table)
        self.table.load_warmup(
            [_warmup_entry("LW", 1), _warmup_entry("TG", 1),
             _warmup_entry("SA", 1), _warmup_entry("CC", 1)],
            "🤸 Eintanzen", "both", "S", False, self.played.append, None)
        desk = _AdvanceDesk(self.table, pause_music)
        self.addCleanup(reap_widget, desk)
        desk._set_party_mode(True)      # what the 🎉 button does
        return desk

    def _song_rows(self) -> list:
        return [r for r, m in enumerate(self.table._row_meta)
                if m and m.entry is not None]

    def test_the_party_list_carries_a_section_header(self):
        """Guards the fixture: without a header row the next two tests would
        pass for the wrong reason."""
        self._desk()
        self.assertEqual(len(self._song_rows()), 4)
        self.assertGreater(len(self.table._row_meta), 4)

    def test_the_advance_is_armed_with_nothing_left_to_wait_for(self):
        desk = self._desk()
        rows = self._song_rows()
        self.table._current_play_row = rows[0]
        desk._queue_auto_advance()
        self.assertIsNotNone(desk._between.pending)
        self.assertIsNone(desk._between.round_start)
        self.assertLessEqual(desk._between.advance_at, time.monotonic())

    def test_no_filler_music_starts_even_when_one_is_configured(self):
        """The ⏭ off switch means no break, so there is no break to fill."""
        desk = self._desk(pause_music=[__file__])
        self.table._current_play_row = self._song_rows()[0]
        desk._queue_auto_advance()
        self.assertFalse(desk._filler.active)
        self.assertEqual(desk._pause_player.played, 0)

    def test_the_very_first_tick_starts_the_next_title(self):
        desk = self._desk()
        rows = self._song_rows()
        self.table._current_play_row = rows[0]
        desk._queue_auto_advance()
        desk._on_play_tick()
        self.assertIsNone(desk._between.pending)
        self.assertEqual(self.played[-1],
                         self.table._row_meta[rows[1]].entry.path)

    def test_a_section_header_does_not_end_the_party(self):
        """A tournament deck stops at 🏁 when the round changes. A party list
        has no rounds — its ─── headers are skipped and the music runs on."""
        desk = self._desk()
        rows = self._song_rows()
        self.table._current_play_row = rows[1]   # last title before the header
        desk._queue_auto_advance()
        self.assertIsNotNone(desk._between.pending)
        self.assertIsNone(desk._between.round_start)
        desk._on_play_tick()
        self.assertEqual(self.played[-1],
                         self.table._row_meta[rows[2]].entry.path)

    def test_the_operator_never_sees_a_countdown(self):
        """⏸ on the panel would mean a pause is running — none ever is."""
        desk = self._desk()
        self.table._current_play_row = self._song_rows()[0]
        desk._queue_auto_advance()
        desk._on_play_tick()
        self.assertEqual([c for c in desk.countdowns if "⏸" in c], [])


class FocusNextWithoutAdvanceTest(unittest.TestCase):
    """⏭ auto-advance off — a heat: nothing starts by itself. When a title ends,
    the row that comes next is put under the cursor all the same, so the
    operator, who is watching the floor and not the screen, only has to press
    play. The selection is all that moves."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.played = []
        self.table = PlaylistTable()
        self.addCleanup(reap_widget, self.table)
        self.table.load_warmup(
            [_warmup_entry("LW", 1), _warmup_entry("TG", 1),
             _warmup_entry("SA", 1), _warmup_entry("CC", 1)],
            "🤸 Eintanzen", "both", "S", False, self.played.append, None)
        self.desk = _AdvanceDesk(self.table)
        self.addCleanup(reap_widget, self.desk)
        self.rows = [r for r, m in enumerate(self.table._row_meta)
                     if m and m.entry is not None]

    def test_the_fixture_really_has_the_advance_switched_off(self):
        self.assertFalse(self.desk._play_panel.auto_advance())

    def test_the_next_song_lands_under_the_cursor(self):
        self.table._current_play_row = self.rows[0]
        self.desk._queue_auto_advance()
        self.assertEqual(self.table.currentRow(), self.rows[1])

    def test_nothing_is_armed_and_nothing_is_played(self):
        self.table._current_play_row = self.rows[0]
        self.desk._queue_auto_advance()
        self.assertIsNone(self.desk._between.pending)
        self.assertEqual(self.played, [])
        self.assertEqual(self.desk._player.played, 0)

    def test_a_section_header_is_stepped_over(self):
        self.table._current_play_row = self.rows[1]
        self.desk._queue_auto_advance()
        self.assertEqual(self.table.currentRow(), self.rows[2])

    def test_the_last_title_leaves_the_cursor_where_it_is(self):
        self.table.setCurrentCell(self.rows[-1], _COL_TITLE)
        self.table._current_play_row = self.rows[-1]
        self.desk._queue_auto_advance()
        self.assertEqual(self.table.currentRow(), self.rows[-1])

    def test_nothing_playing_moves_nothing(self):
        """No active row — an end nobody started (a stop, say)."""
        self.table.setCurrentCell(self.rows[0], _COL_TITLE)
        self.table._current_play_row = -1
        self.desk._queue_auto_advance()
        self.assertEqual(self.table.currentRow(), self.rows[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
