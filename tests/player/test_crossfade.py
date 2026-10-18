#!/usr/bin/env python3
"""🔀 The crossfade: its play-set value, its curves, its levels and its rules.

Run:  py -m unittest tests.player.test_crossfade -v

Near the end of a title the list walks straight on from, the player it plays
on becomes the tail and takes its last seconds out, while the second player
becomes the deck and brings the next one in from silence. These pin when that
happens (only where the list would have walked on with no gap anyway), what
the two levels are along the way, that ⏯, 🔉↓ and 🛑 reach both titles, and
that any other load — ⏹, ⏭, a click — ends it.
"""

import math
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_xfade_"))

from PySide6.QtCore import QObject
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QApplication
from tests.qt_test_support import reap_widget
from tests.player.test_fade_blip import PLAYING, _LoggedDesk, _LoggedMedia
from tests.player.audio.test_fade_indicator import _TimerStub

from planner.playing.play_sets import (
    _PARTY_SET,
    _TOURNAMENT_SET,
    XFADE_CURVES,
    crossfade_curve,
    crossfade_secs,
    play_set_of,
    same_play_values,
    upgrade_xfade,
)
from player.audio.between_dances import BetweenDances
from player.window.main_player import PlayerControlMixin
from player.window.main_xfade import CrossfadeMixin
from player.audio.mix import OutputMix
from shared.audio.playback import crossfade_levels
from player.widgets.play_mode_panel import PlayModePanel
from shared.xfade_view import CrossfadeCurveButton, CrossfadeView, lead_secs


class PlaySetTest(unittest.TestCase):

    def test_neither_set_crossfades_by_default(self):
        """Marcel: "for party set … crossfade not ticked"."""
        party, heat = play_set_of({}, "party"), play_set_of({}, "tournament")
        # Off, but over a length worth hearing when it is switched on.
        self.assertEqual((party["xfade_on"], party["xfade"]), (False, 4.0))
        self.assertEqual((heat["xfade_on"], heat["xfade"]), (False, 4.0))
        self.assertEqual(crossfade_secs(party), 0.0)
        self.assertEqual(crossfade_secs(heat), 0.0)
        for s in (_PARTY_SET, _TOURNAMENT_SET):
            self.assertIn("xfade", s)
            self.assertIn("xfade_on", s)

    def test_a_set_saved_before_the_crossfade_gets_the_default(self):
        old = {"party_set": {"secs": 0, "fade": 3.0, "advance": True}}
        got = play_set_of(old, "party")
        self.assertEqual((got["xfade_on"], got["xfade"]), (False, 4.0))

    def test_a_set_saved_before_the_switch_keeps_what_it_did(self):
        """Back then 0 s was off and anything else on."""
        got = play_set_of({"party_set": {"xfade": 0.0}}, "party")
        self.assertEqual((got["xfade_on"], got["xfade"]), (False, 4.0))
        got = play_set_of({"tournament_set": {"xfade": 2.5}}, "tournament")
        self.assertEqual((got["xfade_on"], got["xfade"]), (True, 2.5))

    def test_a_hand_edited_value_is_clamped_or_dropped(self):
        def secs(v):
            return play_set_of({"party_set": {"xfade": v, "xfade_on": True}},
                               "party")["xfade"]
        self.assertEqual(secs(99), 10.0)
        self.assertEqual(secs(-3), 0.5)
        self.assertEqual(secs("x"), 4.0)

    def test_both_sets_start_on_equal_power_and_keep_a_curve_picked(self):
        for which in ("party", "tournament"):
            self.assertEqual(play_set_of({}, which)["xfade_curve"], "equal")
        got = play_set_of({"party_set": {"xfade_curve": "scurve"}}, "party")
        self.assertEqual(got["xfade_curve"], "scurve")
        got = play_set_of({"party_set": {"xfade_curve": "wobble"}}, "party")
        self.assertEqual(got["xfade_curve"], "equal")

    def test_values_without_a_curve_are_equal_power(self):
        self.assertEqual(crossfade_curve({}), "equal")
        self.assertEqual(crossfade_curve({"xfade_curve": 3}), "equal")
        self.assertEqual(crossfade_curve({"xfade_curve": "linear"}), "linear")


class SwitchTest(unittest.TestCase):

    def test_upgrade_leaves_new_values_and_the_argument_alone(self):
        new = {"xfade": 0.5, "xfade_on": False}
        self.assertEqual(upgrade_xfade(new), new)
        self.assertEqual(upgrade_xfade({"secs": 90}), {"secs": 90})
        old = {"xfade": 0.0}
        self.assertEqual(upgrade_xfade(old), {"xfade": 4.0, "xfade_on": False})
        self.assertEqual(old, {"xfade": 0.0})

    def test_off_is_off_whatever_the_seconds(self):
        self.assertEqual(crossfade_secs({"xfade": 6.0, "xfade_on": False}), 0.0)
        self.assertEqual(crossfade_secs({"xfade": 6.0}), 0.0)
        self.assertEqual(crossfade_secs({"xfade": 6.0, "xfade_on": True}), 6.0)

    def test_the_seconds_of_a_switched_off_crossfade_do_not_tell_sets_apart(self):
        a = {"secs": 0, "xfade": 6.0, "xfade_on": False}
        self.assertTrue(same_play_values(a, dict(a, xfade=4.0)))
        self.assertFalse(same_play_values(dict(a, xfade_on=True),
                                          dict(a, xfade_on=True, xfade=4.0)))
        self.assertFalse(same_play_values(a, dict(a, xfade_on=True)))
        # Nor does its curve.
        self.assertTrue(same_play_values(dict(a, xfade_curve="linear"),
                                         dict(a, xfade_curve="scurve")))
        on = dict(a, xfade_on=True)
        self.assertFalse(same_play_values(dict(on, xfade_curve="linear"),
                                          dict(on, xfade_curve="scurve")))


class CurveTest(unittest.TestCase):

    def test_the_old_title_goes_from_full_to_nothing_and_the_new_one_back(self):
        self.assertEqual(crossfade_levels(0.0), (1.0, 0.0))
        out, inc = crossfade_levels(1.0)
        self.assertAlmostEqual(out, 0.0)
        self.assertAlmostEqual(inc, 1.0)

    def test_equal_power_all_the_way(self):
        """Two unrelated songs add in power: no dip in the middle."""
        for t in (0.1, 0.25, 0.5, 0.8):
            out, inc = crossfade_levels(t)
            self.assertAlmostEqual(out * out + inc * inc, 1.0)
        out, inc = crossfade_levels(0.5)
        self.assertAlmostEqual(out, math.sqrt(0.5))
        self.assertAlmostEqual(inc, math.sqrt(0.5))

    def test_outside_the_ramp_it_holds_its_ends(self):
        self.assertEqual(crossfade_levels(-1), (1.0, 0.0))
        self.assertEqual(crossfade_levels(2), crossfade_levels(1.0))

    def test_every_curve_goes_from_one_title_to_the_other(self):
        for curve in XFADE_CURVES:
            self.assertEqual(crossfade_levels(0.0, curve), (1.0, 0.0), curve)
            out, inc = crossfade_levels(1.0, curve)
            self.assertAlmostEqual(out, 0.0, msg=curve)
            self.assertAlmostEqual(inc, 1.0, msg=curve)

    def test_linear_is_two_straight_lines_with_a_dip(self):
        self.assertEqual(crossfade_levels(0.25, "linear"), (0.75, 0.25))
        out, inc = crossfade_levels(0.5, "linear")
        self.assertAlmostEqual(out * out + inc * inc, 0.5)   # −3 dB

    def test_the_s_curve_is_steady_but_slow_off_both_ends(self):
        for t in (0.1, 0.5, 0.9):
            out, inc = crossfade_levels(t, "scurve")
            self.assertAlmostEqual(out * out + inc * inc, 1.0)
        self.assertLess(crossfade_levels(0.1, "scurve")[1],
                        crossfade_levels(0.1, "equal")[1])
        self.assertGreater(crossfade_levels(0.9, "scurve")[1],
                           crossfade_levels(0.9, "equal")[1])
        self.assertAlmostEqual(crossfade_levels(0.5, "scurve")[1], math.sqrt(0.5))

    def test_an_unknown_curve_is_equal_power(self):
        self.assertEqual(crossfade_levels(0.3, "wobble"), crossfade_levels(0.3))


class MixTest(unittest.TestCase):

    def test_the_incoming_title_is_held_down_by_its_ramp(self):
        mix = OutputMix(0.8)
        mix.fade_in = 0.5
        self.assertAlmostEqual(mix.deck(), 0.4)

    def test_the_tail_keeps_its_own_gain_and_follows_the_desk(self):
        mix = OutputMix(1.0)
        mix.gain = 0.2                 # the NEW title's loudness gain…
        mix.tail_gain = 0.6            # …is not the old one's
        self.assertAlmostEqual(mix.tail(0.5), 0.3)
        mix.set_desk_duck(True)
        self.assertAlmostEqual(mix.tail(1.0), 0.6 * 0.2)


class _Meta(SimpleNamespace):
    pass


class _Table:
    def __init__(self, rounds):
        self._rounds = rounds
        self._current_play_row = 0

    def next_song_row(self, row, step):
        nrow = row + step
        if 0 <= nrow < len(self._rounds):
            return nrow, Path(f"{nrow}.mp3")
        return -1, None

    @property
    def _row_meta(self):
        rounds = self._rounds
        return SimpleNamespace(
            at=lambda r: _Meta(round_name=rounds[r]) if 0 <= r < len(rounds) else None)


class _Player:
    def __init__(self, pos=0, dur=200_000, rate=1.0):
        self.pos, self.dur, self.rate = pos, dur, rate
        self.state = QMediaPlayer.PlaybackState.PlayingState

    def playbackState(self):
        return self.state

    def position(self):
        return self.pos

    def duration(self):
        return self.dur

    def playbackRate(self):
        return self.rate

    def source(self):
        return "song-a"


class _Desk(CrossfadeMixin):
    """The window around the crossfade, reduced to what it asks."""

    def __init__(self, xfade=4.0, limit=0):
        self._mix = OutputMix(1.0)
        self._between = BetweenDances()
        self._player = _Player()
        self._playback = SimpleNamespace(path=Path("a.mp3"), offset_ms=0)
        self.marks = []
        self._play_panel = SimpleNamespace(
            pd_editing=lambda: False,
            play_set=lambda: {"xfade": xfade, "xfade_on": xfade > 0},
            xfade_view=SimpleNamespace(set_progress=self.marks.append))
        self._fade_now = SimpleNamespace(running=False)
        self.table = _Table(["R1", "R1", "R2"])
        self._deckset = SimpleNamespace(all_tables=[self.table])
        self.vals = {"xfade": xfade, "xfade_on": xfade > 0}
        self.limit = limit
        self.advance, self.pause, self.loop, self.pd = True, 0, False, False
        self.playing_mode = True
        self.stop_ms = None
        self.announce = False
        self.pd_hold = 0.0
        self.calls = []

    # What the mixin reads of its host.
    def _engine_list(self):
        return self.table

    def _list_vals(self, _t):
        return self.vals

    def _is_playing_mode(self):
        return self.playing_mode

    def _playing_advance(self):
        return self.advance

    def _engine_pause_secs(self):
        return self.pause

    def _looping(self):
        return self.loop

    def _pd_runs_to_its_highlight(self):
        return self.pd

    def _play_limit_secs(self):
        return self.limit

    def _play_end_secs(self):
        return self.limit

    def _silence_stop_ms(self):
        return self.stop_ms

    def _next_song_to_advance(self):
        row = self.table._current_play_row + 1
        return (self.table, row, Path("b.mp3")) if row < 3 else None

    def _apply_volume(self):
        self.calls.append(("volume", self._mix.deck()))

    def _on_timed_end(self, reason="play length"):
        self.calls.append(("end", reason))

    def _fire_pending_advance(self):
        self.calls.append(("advance",))

    def _preview_skip(self, step):
        self.calls.append(("skip", step))

    def _remember_stop_point(self):
        self.calls.append(("mark",))

    def _wants_start_call(self):
        return self.announce

    def _pd_start_hold(self):
        return self.pd_hold

    def _speak_start_call(self):
        self.calls.append(("call",))
        return True


class WhenTest(unittest.TestCase):
    """A crossfade only where the list would have walked on with no gap."""

    def due(self, desk, pos_ms):
        desk._player.pos = pos_ms
        return desk._crossfade_due(desk._music_left())

    def test_due_in_the_last_seconds_of_a_full_length_title(self):
        desk = _Desk()
        self.assertFalse(self.due(desk, 195_000))   # 5 s left
        self.assertTrue(self.due(desk, 196_500))    # 3.5 s left

    def test_the_tempo_fader_is_counted(self):
        desk = _Desk()
        desk._player.rate = 0.5                     # 3.5 s of file = 7 s
        self.assertFalse(self.due(desk, 196_500))

    def test_dead_air_after_the_last_note_ends_the_title_earlier(self):
        desk = _Desk()
        desk.stop_ms = 180_000
        self.assertTrue(self.due(desk, 177_000))

    def test_a_timed_cut_ends_it_earlier_too(self):
        desk = _Desk(limit=90)
        self.assertTrue(self.due(desk, 87_000))
        self.assertFalse(self.due(desk, 80_000))

    def test_off_never(self):
        self.assertFalse(self.due(_Desk(xfade=0), 199_000))
        desk = _Desk()
        desk.vals["xfade_on"] = False
        self.assertFalse(self.due(desk, 199_000))

    def test_a_list_saved_without_the_value_does_not_crossfade(self):
        desk = _Desk()
        desk.vals = {"secs": 0}
        self.assertFalse(self.due(desk, 199_000))

    def test_no_crossfade_where_the_list_would_not_walk_straight_on(self):
        for attr, value in (("advance", False), ("pause", 15), ("loop", True),
                            ("pd", True), ("playing_mode", False)):
            desk = _Desk()
            setattr(desk, attr, value)
            self.assertFalse(self.due(desk, 199_000), attr)

    def test_not_over_a_fade_by_hand(self):
        desk = _Desk()
        desk._fade_now.running = True
        self.assertFalse(self.due(desk, 199_000))

    def test_not_into_the_next_round(self):
        desk = _Desk()
        desk.table._current_play_row = 1            # R1 → R2 next
        self.assertFalse(self.due(desk, 199_000))

    def test_not_after_the_last_title(self):
        desk = _Desk()
        desk.table._current_play_row = 2
        self.assertFalse(self.due(desk, 199_000))

    def test_not_twice(self):
        desk = _Desk()
        desk._between.xfade.state = "fading"
        self.assertFalse(self.due(desk, 199_000))

    def test_an_unknown_length_waits(self):
        desk = _Desk()
        desk._player.dur = 0
        self.assertFalse(self.due(desk, 0))


class RampTest(unittest.TestCase):
    """The handover and the two ramps after it."""

    def desk(self):
        desk = _Desk()
        desk._between.xfade.incoming = Path("b.mp3")
        desk._between.xfade.length = 4.0
        return desk

    def test_the_handover_ends_the_old_title_and_starts_the_next(self):
        desk = self.desk()
        desk._mix.gain, desk._mix.fade = 0.8, 0.5
        desk._swap_decks = lambda: desk.calls.append(("swap",))
        desk._hand_over()
        self.assertEqual(desk._between.xfade.state, "fading")
        self.assertEqual(desk.calls[:3],
                         [("swap",), ("end", "crossfade"), ("advance",)])
        self.assertAlmostEqual(desk._mix.tail_gain, 0.4)

    def test_its_own_incoming_title_starts_from_silence(self):
        desk = self.desk()
        desk._between.xfade.state, desk._between.xfade.t0 = "fading", time.monotonic()
        desk._crossfade_takes(Path("b.mp3"))
        self.assertLess(desk._mix.fade_in, 0.05)
        self.assertEqual(desk._between.xfade.state, "fading")

    def test_a_late_start_joins_the_ramp_where_it_stands(self):
        """Its loudness held it back half the crossfade: it does not start
        from silence then, it starts where the in-ramp has got to."""
        desk = self.desk()
        desk._between.xfade.state, desk._between.xfade.t0 = "fading", time.monotonic() - 2.0
        desk._crossfade_takes(Path("b.mp3"))
        self.assertAlmostEqual(desk._mix.fade_in, math.sqrt(0.5), places=2)

    def test_any_other_load_ends_it_at_full_level(self):
        for path in (Path("c.mp3"), None):
            desk = self.desk()
            desk._between.xfade.state, desk._between.xfade.t0 = "fading", time.monotonic()
            desk._mix.fade_in = 0.3
            desk._crossfade_takes(path)
            self.assertIsNone(desk._between.xfade.state)
            self.assertEqual(desk._mix.fade_in, 1.0)

    def test_the_ramp_brings_the_new_title_up_and_then_ends(self):
        desk = self.desk()
        desk._between.xfade.state = "fading"
        with mock.patch("player.window.main_xfade.time.monotonic", return_value=102.0):
            desk._between.xfade.t0 = 100.0
            desk._step_crossfade()
            self.assertAlmostEqual(desk._mix.fade_in, math.sqrt(0.5))
            self.assertEqual(desk._between.xfade.state, "fading")
        with mock.patch("player.window.main_xfade.time.monotonic", return_value=104.5):
            desk._step_crossfade()
        self.assertIsNone(desk._between.xfade.state)
        self.assertEqual(desk._mix.fade_in, 1.0)

    def test_the_picture_follows_the_ramp_and_lets_go_at_the_end(self):
        desk = self.desk()
        desk._between.xfade.state = "fading"
        with mock.patch("player.window.main_xfade.time.monotonic", return_value=101.0):
            desk._between.xfade.t0 = 100.0
            desk._step_crossfade()
        self.assertAlmostEqual(desk.marks[-1], 0.25)
        desk._end_crossfade()
        self.assertIsNone(desk.marks[-1])

    def test_the_ramp_runs_on_the_curve_it_was_started_on(self):
        desk = self.desk()
        desk._between.xfade.state = "fading"
        desk._between.xfade.curve = "linear"
        with mock.patch("player.window.main_xfade.time.monotonic", return_value=101.0):
            desk._between.xfade.t0 = 100.0
            desk._step_crossfade()
        self.assertAlmostEqual(desk._mix.fade_in, 0.25)

    def test_the_dance_is_named_once_the_crossover_is_through(self):
        """🔈 Not over two titles mixing: the incoming one is named the moment
        it plays alone."""
        desk = self.desk()
        desk.announce = True
        desk._between.xfade.state = "fading"
        with mock.patch("player.window.main_xfade.time.monotonic", return_value=102.0):
            desk._between.xfade.t0 = 100.0
            desk._step_crossfade()
        self.assertNotIn(("call",), desk.calls)
        with mock.patch("player.window.main_xfade.time.monotonic", return_value=104.5):
            desk._step_crossfade()
        self.assertIsNone(desk._between.xfade.state)
        self.assertEqual(desk.calls[-1], ("call",))

    def test_a_held_paso_doble_is_not_named_twice(self):
        """🐂 Marcel: "the crossover for paso doble with announce next dance
        calls paso 2x one male one female voice". The Paso Doble's start
        wait has called it already, at its head — the end of the ramp must
        not say it again (a mixed evening hears the other voice)."""
        desk = self.desk()
        desk.announce = True
        desk.pd_hold = 5.0
        desk._between.xfade.state = "fading"
        with mock.patch("player.window.main_xfade.time.monotonic", return_value=104.5):
            desk._between.xfade.t0 = 100.0
            desk._step_crossfade()
        self.assertIsNone(desk._between.xfade.state)
        self.assertNotIn(("call",), desk.calls)

    def test_no_call_after_it_when_the_call_is_off(self):
        desk = self.desk()
        desk._between.xfade.state = "fading"
        with mock.patch("player.window.main_xfade.time.monotonic", return_value=104.5):
            desk._between.xfade.t0 = 100.0
            desk._step_crossfade()
        self.assertNotIn(("call",), desk.calls)

    def test_a_crossfade_cut_short_names_nothing(self):
        """⏹, ⏭ or a click took over: the new title makes its own call."""
        desk = self.desk()
        desk.announce = True
        desk._between.xfade.state, desk._between.xfade.t0 = "fading", time.monotonic()
        desk._crossfade_takes(Path("c.mp3"))
        self.assertNotIn(("call",), desk.calls)

    def test_the_curve_comes_from_the_playing_list(self):
        desk = _Desk()
        desk.vals["xfade_curve"] = "scurve"
        self.assertEqual(crossfade_curve(desk._xfade_vals()), "scurve")


def at(desk, pos_ms):
    """Stand the fake deck `pos_ms` into its title."""
    player = desk._player
    assert isinstance(player, _Player)
    player.pos = pos_ms


def shown(desk):
    """Where the picture's marker was last put; None = never shown."""
    return desk.marks[-1] if desk.marks else None


class MarkerTest(unittest.TestCase):
    """The picture's marker walks the whole box: in from the left edge before
    the crossfade, over the ramp while it runs, out to the right edge after."""

    def test_it_comes_in_from_the_left_before_the_crossfade(self):
        desk = _Desk()                              # 4 s ramp: 3 s either side
        at(desk, 194_000)                  # 6 s left
        desk._maybe_crossfade()
        self.assertAlmostEqual(desk.marks[-1], -0.5)
        at(desk, 192_000)                  # 8 s left: not yet
        desk._maybe_crossfade()
        self.assertIsNone(shown(desk))

    def test_a_stop_before_the_crossfade_takes_the_marker_away(self):
        """⏹ ends the ticks, so nothing else would."""
        desk = _Desk()
        at(desk, 194_000)
        desk._maybe_crossfade()
        desk._end_crossfade()
        self.assertIsNone(shown(desk))

    def test_no_marker_where_no_crossfade_is_coming(self):
        desk = _Desk()
        desk.pause = 15
        at(desk, 194_000)
        desk._maybe_crossfade()
        self.assertIsNone(shown(desk))
        desk.table._current_play_row = 1            # R1 -> R2 next
        desk.pause = 0
        desk._maybe_crossfade()
        self.assertIsNone(shown(desk))

    def after(self):
        desk = _Desk()
        xf = desk._between.xfade
        xf.incoming, xf.length, xf.state, xf.t0 = Path("b.mp3"), 4.0, "fading", 100.0
        with mock.patch("player.window.main_xfade.time.monotonic", return_value=104.5):
            desk._step_crossfade()
        return desk

    def test_it_walks_out_to_the_right_after_the_crossfade(self):
        desk = self.after()
        self.assertIsNone(desk._between.xfade.state)
        self.assertAlmostEqual(desk.marks[-1], 1.125)
        with mock.patch("player.window.main_xfade.time.monotonic", return_value=106.0):
            desk._maybe_crossfade()
        self.assertAlmostEqual(desk.marks[-1], 1.5)
        with mock.patch("player.window.main_xfade.time.monotonic", return_value=107.5):
            desk._maybe_crossfade()
        self.assertIsNone(shown(desk))

    def test_another_load_takes_the_marker_away_at_once(self):
        desk = self.after()
        desk._crossfade_takes(Path("c.mp3"))
        self.assertIsNone(shown(desk))
        with mock.patch("player.window.main_xfade.time.monotonic", return_value=106.0):
            desk._maybe_crossfade()
        self.assertIsNone(shown(desk))

class _Device(QObject):
    """The output device: says which player it heard, and who it follows."""

    def __init__(self, log):
        super().__init__()
        self.log = log
        self.followed = []

    def on_playback_state(self, *_):
        self.log.append(("device", self.sender()))

    def swap_deck(self, player, out):
        self.followed.append((player, out))


class _Follower:
    """The card and the overlay: who they follow."""

    def __init__(self):
        self.followed = []

    def set_deck(self, player):
        self.followed.append(player)

    set_player = set_deck


class _QtDesk(QObject, _Desk):
    """The desk on real players, wired the way MainWindow wires its deck."""

    def __init__(self):
        QObject.__init__(self)
        _Desk.__init__(self)
        self.heard = []
        self._audio_device = _Device(self.heard)
        self._big_player, self._preview = _Follower(), _Follower()
        self._taskbar = object()
        self._player, self._audio_out = QMediaPlayer(), QAudioOutput()
        self._player.setAudioOutput(self._audio_out)
        for name, slot in self._deck_slots():
            getattr(self._player, name).connect(slot)

    def _on_media_status(self, *_):
        self.heard.append(("status", self.sender()))

    def _on_player_error(self, *_):
        self.heard.append(("error", self.sender()))

    def _on_playback_state(self, *_):
        self.heard.append(("state", self.sender()))

    def _on_taskbar_state(self, *_):
        self.heard.append(("taskbar", self.sender()))


class SwapTest(unittest.TestCase):
    """🔀 The outgoing title stays on its player; the deck changes player."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def desk(self):
        desk = _QtDesk()
        desk._player.pos = 0
        return desk

    def test_the_outgoing_title_is_not_touched(self):
        """No reopen, no seek, no stop: what the hall hears plays on."""
        desk = self.desk()
        deck = desk._player
        with mock.patch.object(QMediaPlayer, "setSource") as src, \
                mock.patch.object(QMediaPlayer, "setPosition") as seek, \
                mock.patch.object(QMediaPlayer, "stop") as stop:
            desk._start_crossfade(4.0)
        self.assertEqual(desk._between.xfade.state, "fading")
        self.assertIs(desk._between.xfade.player, deck)
        self.assertIsNot(desk._player, deck)
        for call in (src, seek, stop):
            self.assertFalse(call.called, call)
        self.assertEqual(desk.calls[:2], [("end", "crossfade"), ("advance",)])

    def test_the_tail_keeps_its_output_and_the_deck_takes_the_spare_one(self):
        desk = self.desk()
        deck, out = desk._player, desk._audio_out
        desk._start_crossfade(4.0)
        self.assertIs(desk._between.xfade.out, out)
        self.assertIs(deck.audioOutput(), out)
        self.assertIsNot(desk._audio_out, out)
        self.assertIs(desk._player.audioOutput(), desk._audio_out)

    def test_the_window_now_hears_the_new_deck_only(self):
        desk = self.desk()
        old = desk._player
        desk._start_crossfade(4.0)
        new = desk._player
        stopped = QMediaPlayer.PlaybackState.StoppedState
        old.playbackStateChanged.emit(stopped)
        old.mediaStatusChanged.emit(QMediaPlayer.MediaStatus.EndOfMedia)
        self.assertEqual(desk.heard, [])
        new.playbackStateChanged.emit(stopped)
        new.mediaStatusChanged.emit(QMediaPlayer.MediaStatus.LoadedMedia)
        new.errorOccurred.emit(QMediaPlayer.Error.ResourceError, "x")
        self.assertEqual([who for who, _ in desk.heard],
                         ["device", "state", "taskbar", "status", "error"])
        self.assertTrue(all(p is new for _, p in desk.heard))

    def test_the_card_the_overlay_and_the_device_follow(self):
        desk = self.desk()
        desk._start_crossfade(4.0)
        self.assertEqual(desk._big_player.followed, [desk._player])
        self.assertEqual(desk._preview.followed, [desk._player])
        self.assertEqual(desk._audio_device.followed,
                         [(desk._player, desk._audio_out)])

    def test_the_next_crossfade_swaps_back(self):
        desk = self.desk()
        first = desk._player
        desk._start_crossfade(4.0)
        desk._end_crossfade()
        self.assertIsNone(desk._between.xfade.state)
        desk._start_crossfade(4.0)
        self.assertIs(desk._player, first)
        desk.heard.clear()
        first.playbackStateChanged.emit(QMediaPlayer.PlaybackState.PlayingState)
        self.assertEqual([who for who, _ in desk.heard],
                         ["device", "state", "taskbar"])

    def test_without_a_taskbar_there_is_nothing_of_it_to_move(self):
        desk = _Desk()
        desk._audio_device = SimpleNamespace(on_playback_state=print)
        desk._taskbar = None
        desk._on_media_status = desk._on_player_error = print
        desk._on_playback_state = desk._on_taskbar_state = print
        self.assertEqual([name for name, _ in desk._deck_slots()],
                         ["mediaStatusChanged", "errorOccurred",
                          "playbackStateChanged", "playbackStateChanged"])


PAUSED = QMediaPlayer.PlaybackState.PausedState


class _Tail:
    """The fading player: what was done to it, in order."""

    def __init__(self):
        self.log = []

    def pause(self):
        self.log.append("pause")

    def play(self):
        self.log.append("play")

    def stop(self):
        self.log.append("stop")

    def setSource(self, _url):
        self.log.append("release")


class _Out:
    def __init__(self):
        self.volume = None

    def setVolume(self, v):
        self.volume = v


class _HallMedia(_LoggedMedia):
    """The deck, as far as a timed end reads and releases it."""

    def position(self):
        return 0

    def duration(self):
        return 0

    def setSource(self, _url):
        self.log.append("release")


class _HallDesk(_LoggedDesk):
    """The real playing-mode engine and its real timed end, mid crossfade."""

    def __init__(self):
        super().__init__()
        self._player = _HallMedia(self.log)
        self._play_panel.xfade_view = SimpleNamespace(set_progress=lambda p: None)
        self._preview = None
        self._deckset.all_tables = ()
        self._now_playing = SimpleNamespace(setText=lambda t: None)
        self._big_player = mock.MagicMock()
        xf = self._between.xfade
        xf.player, xf.out, xf.timer = _Tail(), _Out(), _TimerStub()
        xf.state, xf.length, xf.incoming = "fading", 4.0, Path("b.mp3")
        xf.t0 = time.monotonic() - 1.0
        xf.timer.start()
        self._mix.tail_gain = 1.0

    def _on_timed_end(self, why="play length"):
        PlayerControlMixin._on_timed_end(self, why)

    def _queue_auto_advance(self):
        pass

    def _reset_aux_play_markers(self):
        pass


class StopBothTest(unittest.TestCase):
    """⏯, 🔉↓ and 🛑 during a crossfade reach the fading title too."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.desk = _HallDesk()
        self.addCleanup(reap_widget, self.desk)
        self.xf = self.desk._between.xfade

    def test_pausing_the_deck_holds_the_tail_and_its_ramp(self):
        self.desk._on_playback_state(PAUSED)
        self.assertEqual(self.xf.player.log, ["pause"])
        self.assertFalse(self.xf.timer.isActive())
        self.assertEqual(self.xf.state, "fading")

    def test_resuming_picks_both_up_where_they_were(self):
        t0 = self.xf.t0
        self.desk._on_playback_state(PAUSED)
        self.xf.paused_at -= 2.0                     # held for two seconds
        self.desk._on_playback_state(PLAYING)
        self.assertEqual(self.xf.player.log, ["pause", "play"])
        self.assertTrue(self.xf.timer.isActive())
        self.assertAlmostEqual(self.xf.t0, t0 + 2.0, delta=0.05)
        self.assertIsNone(self.xf.paused_at)

    def test_the_deck_starting_its_title_does_not_touch_the_tail(self):
        self.desk._on_playback_state(PLAYING)
        self.assertEqual(self.xf.player.log, [])

    def test_a_pause_with_no_crossfade_leaves_the_spare_alone(self):
        self.xf.state = None
        self.desk._on_playback_state(PAUSED)
        self.assertEqual(self.xf.player.log, [])

    def test_the_tail_follows_a_fade_by_hand(self):
        mix = OutputMix(1.0)
        mix.tail_gain = 0.8
        mix.fade = 0.5
        self.assertAlmostEqual(mix.tail(1.0), 0.4)

    def test_a_fade_by_hand_that_ends_the_title_ends_the_tail(self):
        self.desk._fade_out_now()
        self.desk._fade_now.end = time.monotonic() - 0.1
        self.desk._on_play_tick()
        self.assertIsNone(self.xf.state)
        self.assertIn("stop", self.xf.player.log)

    def test_the_handover_itself_keeps_it(self):
        self.desk._on_timed_end("crossfade")
        self.assertEqual(self.xf.state, "fading")
        self.assertEqual(self.xf.player.log, [])

    def test_a_panic_hold_pauses_the_tail_at_silence(self):
        self.desk._fade_and_hold()
        self.desk._fade_now.end = time.monotonic() - 0.1
        self.desk._on_play_tick()
        self.assertIn("pause", self.desk.log)
        # Held with the deck, before its level goes back to whole: a pause
        # lands late, and the next ramp step would play the tail loud.
        self.assertEqual(self.xf.player.log, ["pause"])
        self.assertFalse(self.xf.timer.isActive())
        self.desk._on_playback_state(PAUSED)         # the deck's pause lands
        self.assertEqual(self.xf.player.log, ["pause"])


class SkipTest(unittest.TestCase):
    """⏭ with the crossfade on fades into the next title instead of cutting."""

    def desk(self, **kw):
        desk = _Desk(**kw)
        xf = desk._between.xfade
        xf.player, xf.out, xf.timer = _Tail(), _Out(), _TimerStub()
        desk._swap_decks = lambda: desk.calls.append(("swap",))
        return desk

    def test_skip_crossfades_into_the_next_row(self):
        desk = self.desk()
        self.assertTrue(desk._crossfade_skip())
        xf = desk._between.xfade
        self.assertEqual(xf.state, "fading")
        self.assertEqual(xf.incoming, Path("1.mp3"))
        self.assertEqual(xf.length, 4.0)
        # The place in the title being left is kept first, as a plain ⏭ does.
        self.assertEqual(desk.calls, [("mark",), ("swap",), ("skip", 1)])

    def test_even_into_the_next_round_the_operator_asked_for_it(self):
        desk = self.desk()
        desk.table._current_play_row = 1            # R1 -> R2
        self.assertTrue(desk._crossfade_skip())
        self.assertEqual(desk._between.xfade.incoming, Path("2.mp3"))

    def test_a_plain_skip_where_it_cannot(self):
        cases = {
            "off": lambda d: d.vals.update(xfade_on=False),
            "planning": lambda d: setattr(d, "playing_mode", False),
            "pause on": lambda d: setattr(d, "pause", 15),
            "not playing": lambda d: setattr(
                d._player, "state", QMediaPlayer.PlaybackState.PausedState),
            "fade by hand": lambda d: setattr(d._fade_now, "running", True),
            "fading": lambda d: setattr(d._between.xfade, "state", "fading"),
            "last title": lambda d: setattr(d.table, "_current_play_row", 2),
        }
        for name, spoil in cases.items():
            desk = self.desk()
            spoil(desk)
            self.assertFalse(desk._crossfade_skip(), name)
            self.assertEqual(desk.calls, [], name)

    def test_the_ramp_takes_the_new_title_when_it_loads(self):
        desk = self.desk()
        desk._crossfade_skip()
        desk._crossfade_takes(Path("1.mp3"))
        self.assertEqual(desk._between.xfade.state, "fading")


class JumpTest(unittest.TestCase):
    """📱 A next title tapped on the phone: the playing one fades out while
    the tapped one comes in at once, wherever it sits in the list."""

    def desk(self, **kw):
        desk = SkipTest.desk(self, **kw)
        desk._pv = lambda key: {"fade": 2.5}[key]
        desk.table._on_play_click = lambda r, p: desk.calls.append(("click", r, p))
        desk.table.scroll_row_into_play_view = lambda r: None
        return desk

    def test_it_crossfades_into_the_tapped_row(self):
        desk = self.desk()
        self.assertTrue(desk._crossfade_jump(desk.table, 2, Path("2.mp3")))
        xf = desk._between.xfade
        self.assertEqual((xf.state, xf.incoming, xf.length),
                         ("fading", Path("2.mp3"), 4.0))
        self.assertEqual(desk.calls,
                         [("mark",), ("swap",), ("click", 2, Path("2.mp3"))])

    def test_crossfade_off_the_fade_out_time_is_the_ramp(self):
        desk = self.desk()
        desk.vals.update(xfade_on=False)
        self.assertTrue(desk._crossfade_jump(desk.table, 2, Path("2.mp3")))
        self.assertEqual(desk._between.xfade.length, 2.5)

    def test_a_pause_between_dances_does_not_stop_it(self):
        """⏭ waits for the pause; a tapped title was asked for now."""
        desk = self.desk()
        desk.pause = 15
        self.assertTrue(desk._crossfade_jump(desk.table, 2, Path("2.mp3")))

    def test_where_nothing_can_fade_it_says_so(self):
        cases = {
            "planning": lambda d: setattr(d, "playing_mode", False),
            "not playing": lambda d: setattr(
                d._player, "state", QMediaPlayer.PlaybackState.PausedState),
            "fade by hand": lambda d: setattr(d._fade_now, "running", True),
            "fading": lambda d: setattr(d._between.xfade, "state", "fading"),
        }
        for name, spoil in cases.items():
            desk = self.desk()
            spoil(desk)
            self.assertFalse(desk._crossfade_jump(desk.table, 2, Path("2.mp3")), name)
            self.assertEqual(desk.calls, [], name)


class SkipButtonTest(unittest.TestCase):
    """The ⏭ button asks the crossfade first."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def press(self, fades):
        desk = _HallDesk()
        self.addCleanup(reap_widget, desk)
        desk._announcer = mock.MagicMock()
        with mock.patch.object(_HallDesk, "_crossfade_skip", return_value=fades), \
                mock.patch.object(_HallDesk, "_preview_skip", create=True) as skip:
            desk._on_player_next()
        return skip

    def test_a_crossfade_replaces_the_cut(self):
        self.assertFalse(self.press(True).called)

    def test_otherwise_the_plain_skip(self):
        self.press(False).assert_called_once_with(+1)


class PanelTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.panel = PlayModePanel({"auto_advance": True, "pause_enabled": False})
        self.addCleanup(reap_widget, self.panel)

    def test_the_set_carries_the_crossfade(self):
        self.panel.xfade_check.setChecked(True)
        self.panel.xfade_spin.setValue(2.5)
        self.assertEqual(self.panel.play_set()["xfade"], 2.5)
        self.assertIs(self.panel.play_set()["xfade_on"], True)

    def test_off_by_default_over_a_length_worth_hearing(self):
        self.assertFalse(self.panel.xfade_on())
        self.assertEqual(self.panel.xfade_secs(), 0.0)
        self.assertFalse(self.panel.xfade_spin.isEnabled())
        self.panel.xfade_check.setChecked(True)
        self.assertEqual(self.panel.xfade_secs(), 4.0)
        self.assertTrue(self.panel.xfade_spin.isEnabled())

    def test_switching_off_keeps_the_seconds(self):
        self.panel.xfade_check.setChecked(True)
        self.panel.xfade_spin.setValue(7.0)
        self.panel.xfade_check.setChecked(False)
        self.assertEqual(self.panel.xfade_secs(), 0.0)
        self.assertEqual(self.panel.xfade_setting_secs(), 7.0)
        self.panel.xfade_check.setChecked(True)
        self.assertEqual(self.panel.xfade_secs(), 7.0)

    def test_the_stored_settings_come_back(self):
        for stored, want in (({"xfade_secs": 6.0, "xfade_on": True}, (True, 6.0)),
                             ({"xfade_secs": 6.0, "xfade_on": False}, (False, 6.0)),
                             ({"xfade_secs": 0.0}, (False, 4.0)),
                             ({"xfade_secs": 3.0}, (True, 3.0))):
            panel = PlayModePanel(stored)
            self.addCleanup(reap_widget, panel)
            self.assertEqual((panel.xfade_on(), panel.xfade_setting_secs()),
                             want, stored)

    def test_applying_a_set_moves_it_and_says_so(self):
        changed = self.panel.apply_play_set(secs=0, advance=True, pause_off=True,
                                            xfade=4.0, xfade_on=True)
        self.assertEqual(self.panel.xfade_secs(), 4.0)
        self.assertIn("crossfade → 4 s", changed)
        changed = self.panel.apply_play_set(secs=0, advance=True, pause_off=True,
                                            xfade=4.0, xfade_on=False)
        self.assertIn("crossfade → off", changed)

    def test_seconds_that_stay_off_are_not_reported(self):
        changed = self.panel.apply_play_set(secs=self.panel.play_secs(),
                                            advance=True, pause_off=True,
                                            xfade=8.0, xfade_on=False)
        self.assertEqual(changed, [])
        self.assertEqual(self.panel.xfade_setting_secs(), 8.0)

    def test_a_list_without_the_value_leaves_it_alone(self):
        self.panel.xfade_check.setChecked(True)
        self.panel.xfade_spin.setValue(3.0)
        self.panel.apply_play_set(secs=0, advance=True, pause_off=True)
        self.assertEqual(self.panel.xfade_secs(), 3.0)

    def test_the_picture_follows_the_value(self):
        self.panel.xfade_check.setChecked(True)
        self.panel.xfade_spin.setValue(6.0)
        self.assertEqual(self.panel.xfade_view.secs(), 6.0)
        self.panel.xfade_check.setChecked(False)
        self.assertEqual(self.panel.xfade_view.secs(), 0.0)

    def test_the_curve_rides_in_the_set_and_greys_out_with_the_switch(self):
        self.assertEqual(self.panel.play_set()["xfade_curve"], "equal")
        self.assertFalse(self.panel.xfade_curves.isEnabled())
        self.panel.xfade_check.setChecked(True)
        self.assertTrue(self.panel.xfade_curves.isEnabled())
        self.panel.xfade_curves._actions["linear"].trigger()
        self.assertEqual(self.panel.play_set()["xfade_curve"], "linear")
        self.assertEqual(self.panel.xfade_view._curve, "linear")

    def test_a_new_curve_is_said_only_while_it_is_heard(self):
        changed = self.panel.apply_play_set(secs=self.panel.play_secs(),
                                            advance=True, pause_off=True,
                                            xfade_curve="scurve")
        self.assertEqual(changed, [])
        self.panel.xfade_check.setChecked(True)
        changed = self.panel.apply_play_set(secs=self.panel.play_secs(),
                                            advance=True, pause_off=True,
                                            xfade_curve="linear")
        self.assertEqual(changed, ["crossfade curve → linear"])

    def test_the_stored_curve_comes_back(self):
        panel = PlayModePanel({"xfade_curve": "scurve"})
        self.addCleanup(reap_widget, panel)
        self.assertEqual(panel.xfade_curve(), "scurve")

    def test_gone_under_a_pause_and_without_advance(self):
        # A pause leaves no gap-less hand-over to crossfade: the row goes, so
        # what the pause switch shows sits straight under it.
        self.panel.pause_check.setChecked(True)
        self.assertTrue(self.panel.xfade_row_box.isHidden())
        self.assertFalse(self.panel.pause_sub_box.isHidden())
        self.panel.pause_check.setChecked(False)
        self.assertFalse(self.panel.xfade_row_box.isHidden())
        self.assertTrue(self.panel.pause_sub_box.isHidden())
        self.panel.advance_check.setChecked(False)
        self.assertTrue(self.panel.xfade_row_box.isHidden())


class PictureTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_it_draws_the_red_and_the_green_curve(self):
        view = CrossfadeView()
        self.addCleanup(reap_widget, view)
        view.set_secs(4.0)
        img = view.grab().toImage()
        colours = {img.pixelColor(x, y).name()
                   for x in range(img.width()) for y in range(img.height())}
        self.assertIn("#e53935", colours)
        self.assertIn("#43a047", colours)

    def test_the_curve_button_offers_each_curve_drawn_and_shows_its_own(self):
        button = CrossfadeCurveButton()
        self.addCleanup(reap_widget, button)
        self.assertEqual(button.curve(), "equal")
        icons = {c: a.icon().pixmap(30, 20).toImage()
                 for c, a in button._actions.items()}
        self.assertEqual(set(icons), set(XFADE_CURVES))
        self.assertNotEqual(icons["equal"], icons["linear"])
        self.assertNotEqual(icons["equal"], icons["scurve"])
        seen = []
        button.curveChanged.connect(seen.append)
        button._actions["scurve"].trigger()
        self.assertEqual((button.curve(), seen), ("scurve", ["scurve"]))
        self.assertFalse(button._actions["equal"].isChecked())
        self.assertEqual(button.icon().pixmap(30, 20).toImage(), icons["scurve"])
        self.assertIn("S-curve", button.toolTip())
        button.set_curve("nonsense")
        self.assertEqual(button.curve(), "equal")

    def test_a_running_fade_shows_a_marker(self):
        view = CrossfadeView()
        self.addCleanup(reap_widget, view)
        view.set_secs(4.0)
        bare = view.grab().toImage()
        # The box reaches 3 s either side of a 4 s ramp: 0.75 of it.
        view.set_progress(3)
        self.assertEqual(view.progress(), 1.75)
        view.set_progress(-1)
        self.assertEqual(view.progress(), -0.75)
        view.set_progress(0.5)
        img = view.grab().toImage()
        self.assertNotEqual(img, bare)
        yellow = [(x, y) for x in range(img.width()) for y in range(img.height())
                  if img.pixelColor(x, y).name() == "#ffd54f"]
        self.assertTrue(yellow)
        # Off there is nothing to run, so no marker either.
        view.set_secs(0)
        off = view.grab().toImage()
        view.set_progress(None)
        self.assertIsNone(view.progress())
        self.assertEqual(view.grab().toImage(), off)

    def test_the_box_is_the_ramp_and_its_lead_either_side(self):
        self.assertEqual(lead_secs(4), 3.0)
        self.assertEqual(lead_secs(10), 0.0)
        self.assertEqual(lead_secs(12), 0.0)

    def test_the_marker_reaches_the_edges_of_the_box(self):
        view = CrossfadeView()
        self.addCleanup(reap_widget, view)
        view.set_secs(4.0)

        def line_x():
            img = view.grab().toImage()
            y = img.height() // 3
            xs = [x for x in range(img.width())
                  if img.pixelColor(x, y).name() == "#ffd54f"]
            return min(xs), max(xs), img.width()

        view.set_progress(-0.75)
        lo, _hi, _w = line_x()
        self.assertLessEqual(lo, 8)
        view.set_progress(1.75)
        _lo, hi, w = line_x()
        self.assertGreaterEqual(hi, w - 9)

    def test_off_is_a_hard_cut(self):
        view = CrossfadeView()
        self.addCleanup(reap_widget, view)
        view.set_secs(0)
        self.assertIn("No crossfade", view.toolTip())
        view.grab()   # paints without a curve to draw

    def test_off_shows_the_red_drop_beside_the_green_rise(self):
        """Marcel: "i want the red line beside the green ... currently only
        green down is seen". The red drop sat under the green rise."""
        view = CrossfadeView()
        self.addCleanup(reap_widget, view)
        view.set_secs(0)
        img = view.grab().toImage()
        y = (5 + img.height() - 5 - 13) // 2      # half-way down the curves

        def xs(main, other):
            return [x for x in range(img.width())
                    if getattr(img.pixelColor(x, y), main)()
                    > getattr(img.pixelColor(x, y), other)() + 40]

        reds, greens = xs("red", "green"), xs("green", "red")
        self.assertTrue(reds, "the red drop is seen")
        self.assertTrue(greens, "the green rise is seen")
        self.assertLess(max(reds), min(greens))


if __name__ == "__main__":
    unittest.main(verbosity=2)
