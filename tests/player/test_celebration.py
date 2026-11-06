#!/usr/bin/env python3
"""🥇 The final plays on: a title of the final comes back up after its fade.

Run:  py -m unittest tests.player.test_celebration -v

Item 24. Marcel: off / the last dance of the final / every dance of the final,
with the level it comes back at and how long it takes up and down. Only the
play-length fade sets it off. The title plays on until 🔉↓ fades it, the next
title starts or its file ends.

Only under ✋ Manual. Marcel: "in auto mode together with the break song it
makes not sense" — under ⏭ Auto the ⏸ pause and its music follow every title,
so a title of the final just ends there (it used to come back up in place of
the pause music).
"""

import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_celebrate_"))

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication, QGroupBox

from gui.decks.running_order import Row
from planner.playing.celebration import (
    CELEBRATE_DIP_PCT,
    CELEBRATE_DOWN_SECS,
    CELEBRATE_HOLD_SECS,
    CELEBRATE_PCT,
    CELEBRATE_UP_SECS,
    celebrate_dip_pct,
    celebrate_down_secs,
    celebrate_hold_secs,
    celebrate_level,
    celebrate_mode,
    celebrate_pct,
    celebrate_up_secs,
    celebrates,
)
from player.audio.between_dances import BetweenDances
from player.audio.fade_now import FadeNow
from player.audio.mix import OutputMix
from player.audio.playback_state import PlaybackState
from player.audio.resume_marks import ResumeMarks
from player.window.main_load import TrackLoadMixin
from player.window.main_pause import PauseMusicMixin
from player.window.main_player import PlayerControlMixin
from tests.gui.test_dance_play_secs import _WindowCase
from tests.qt_test_support import reap_widget


class SettingTest(unittest.TestCase):

    def test_off_unless_set(self):
        self.assertEqual(celebrate_mode({}), "off")
        self.assertEqual(celebrate_mode({"celebrate_mode": "loud"}), "off")
        self.assertEqual(celebrate_mode({"celebrate_mode": "all"}), "all")

    def test_the_level(self):
        # Marcel: 40 % was too quiet to celebrate to; 50 % out of the box.
        self.assertEqual(celebrate_pct({}), 50)
        self.assertEqual(celebrate_pct({}), CELEBRATE_PCT)
        self.assertEqual(celebrate_pct({"celebrate_pct": 60}), 60)
        self.assertEqual(celebrate_pct({"celebrate_pct": "x"}), CELEBRATE_PCT)
        self.assertEqual(celebrate_pct({"celebrate_pct": 0}), 5)
        self.assertEqual(celebrate_pct({"celebrate_pct": 400}), 100)

    def test_the_seconds(self):
        self.assertEqual(celebrate_up_secs({}), CELEBRATE_UP_SECS)
        self.assertEqual(celebrate_down_secs({}), CELEBRATE_DOWN_SECS)
        self.assertEqual(celebrate_up_secs({"celebrate_up_secs": 5}), 5.0)
        self.assertEqual(celebrate_down_secs({"celebrate_down_secs": 99}), 10.0)
        self.assertEqual(celebrate_down_secs({"celebrate_down_secs": -1}), 0.0)

    def test_it_holds_at_the_dip_for_three_seconds(self):
        """Marcel: it came straight back up; give the couples a moment at the
        dip first."""
        self.assertEqual(celebrate_hold_secs({}), 3.0)
        self.assertEqual(celebrate_hold_secs({}), CELEBRATE_HOLD_SECS)
        self.assertEqual(celebrate_hold_secs({"celebrate_hold_secs": 0}), 0.0)
        self.assertEqual(celebrate_hold_secs({"celebrate_hold_secs": 99}), 10.0)
        self.assertEqual(celebrate_hold_secs({"celebrate_hold_secs": "x"}), 3.0)

    def test_which_titles(self):
        for mode, last, want in (("off", True, False), ("off", False, False),
                                 ("last", True, True), ("last", False, False),
                                 ("all", True, True), ("all", False, True)):
            with self.subTest(mode=mode, last=last):
                self.assertEqual(celebrates(mode, "Endrunde", last), want)

    def test_only_in_the_final(self):
        for name in ("Vorrunde", "1. Zwischenrunde", "Semifinal", ""):
            with self.subTest(name=name):
                self.assertFalse(celebrates("all", name, True))

    def test_it_comes_up(self):
        self.assertEqual(celebrate_level(0.0, 4.0, 40), 0.0)
        self.assertAlmostEqual(celebrate_level(2.0, 4.0, 40), 0.2)
        self.assertAlmostEqual(celebrate_level(9.0, 4.0, 40), 0.4)
        self.assertAlmostEqual(celebrate_level(0.0, 0.0, 40), 0.4)

    def test_the_defaults(self):
        """Marcel: out of the box it comes back at 50 %, dips to 5 %, holds
        there 3 s, comes up over 3 s and goes down over 3 s."""
        self.assertEqual((celebrate_pct({}), celebrate_dip_pct({}),
                          celebrate_hold_secs({}), celebrate_up_secs({}),
                          celebrate_down_secs({})), (50, 5, 3.0, 3.0, 3.0))

    def test_the_dip(self):
        """F21: how low the play-length fade takes it before it comes back.
        0 = all the way down."""
        self.assertEqual(celebrate_dip_pct({}), CELEBRATE_DIP_PCT)
        self.assertEqual(celebrate_dip_pct({"celebrate_dip_pct": 20}), 20)
        self.assertEqual(celebrate_dip_pct({"celebrate_dip_pct": 0}), 0)
        self.assertEqual(celebrate_dip_pct({"celebrate_dip_pct": "x"}),
                         CELEBRATE_DIP_PCT)
        self.assertEqual(celebrate_dip_pct({"celebrate_dip_pct": -5}), 0)

    def test_the_dip_goes_no_lower_than_the_level_it_comes_back_at(self):
        self.assertEqual(celebrate_dip_pct({"celebrate_dip_pct": 70,
                                            "celebrate_pct": 40}), 40)

    def test_it_comes_up_from_the_dip(self):
        self.assertAlmostEqual(celebrate_level(0.0, 4.0, 40, 20), 0.2)
        self.assertAlmostEqual(celebrate_level(2.0, 4.0, 40, 20), 0.3)
        self.assertAlmostEqual(celebrate_level(9.0, 4.0, 40, 20), 0.4)

    def test_it_stays_at_the_dip_for_the_hold(self):
        self.assertAlmostEqual(celebrate_level(1.5, 4.0, 40, 20, 2.0), 0.2)
        self.assertAlmostEqual(celebrate_level(4.0, 4.0, 40, 20, 2.0), 0.3)
        self.assertAlmostEqual(celebrate_level(9.0, 4.0, 40, 20, 2.0), 0.4)

    def test_at_once_after_the_hold(self):
        self.assertAlmostEqual(celebrate_level(1.0, 0.0, 40, 0, 2.0), 0.0)
        self.assertAlmostEqual(celebrate_level(2.5, 0.0, 40, 0, 2.0), 0.4)


class _Rows:
    def __init__(self, rounds):
        self.rows = [SimpleNamespace(round_name=r, entry=SimpleNamespace(
            path=Path(f"C:/m/{i}.mp3"))) for i, r in enumerate(rounds)]

    def at(self, row):
        return self.rows[row] if 0 <= row < len(self.rows) else None


class _Table:
    def __init__(self, rounds, row):
        self._row_meta = _Rows(rounds)
        self._current_play_row = row

    def currentRow(self):
        return self._current_play_row

    def round_at(self, row):
        m = self._row_meta.at(row)
        return m.round_name if m is not None else ""

    def next_song_row(self, row, step):
        r = row + step
        m = self._row_meta.at(r)
        return (r, m.entry.path) if m is not None else (-1, None)


class _Media:
    def __init__(self):
        self.pos = 95_000
        self.seeked = None

    def position(self):
        return self.pos

    def duration(self):
        return 215_000

    def playbackRate(self):
        return 1.0

    def playbackState(self):
        return QMediaPlayer.PlaybackState.PlayingState

    def setPosition(self, ms):
        self.seeked = ms

    def pause(self):
        pass


class _Desk:
    """The desk's celebration and pause paths, on stubbed players and lists."""

    _begin_celebration = PlayerControlMixin._begin_celebration
    _celebrating = PlayerControlMixin._celebrating
    _celebration_tick = PlayerControlMixin._celebration_tick
    _celebration_due = PlayerControlMixin._celebration_due
    _celebration_choice = PlayerControlMixin._celebration_choice
    _round_place = PlayerControlMixin._round_place
    _round_place_at = PlayerControlMixin._round_place_at
    _celebration_of = PlayerControlMixin._celebration_of
    _cut_fade_floor = PlayerControlMixin._cut_fade_floor
    _sync_big_player_limit = PlayerControlMixin._sync_big_player_limit
    _fade_out_now = PlayerControlMixin._fade_out_now
    _playing_row = PauseMusicMixin._playing_row

    def __init__(self, settings, rounds, row, advance=False):
        self._settings = settings
        self._deckset = SimpleNamespace(all_tables=[_Table(rounds, row)])
        # 🥇 The list's own switch; the old settings word only seeds it here.
        self._vals = {"celebrate": settings.get("celebrate_mode", "off") != "off"}
        self._advance = advance
        self._player = _Media()
        self._playback = PlaybackState()
        self._playback.path = Path("C:/m/WW.mp3")
        self._playback.token = 7
        self._mix = OutputMix()
        self._mix.fade = 0.0
        self._fade_now = FadeNow()
        self._big_player = None
        self._fade_timer = SimpleNamespace(start=lambda: None)
        self._countdown = ""

    def _engine_list(self):
        return self._deckset.all_tables[0]

    def _on_tournament_length(self, table):
        return True

    _panel_list = _engine_list

    def _list_vals(self, table):
        return self._vals

    def _autosave_playlist(self):
        pass

    def _looping(self):
        return False

    def _playing_advance(self):
        return self._advance

    def _pv(self, key):
        return {"fade": 2.0}[key]

    def _apply_volume(self):
        pass

    def _set_countdown(self, text):
        self._countdown = text

    def _set_fade_indicator(self, on):
        pass


FINAL = ["Endrunde"] * 5
SEMI_THEN_FINAL = ["Semifinal"] * 5 + ["Endrunde"] * 5


class PlaysOnTest(unittest.TestCase):
    """✋ Manual: the title plays on, right on the main player."""

    def test_off_it_ends_as_always(self):
        d = _Desk({}, FINAL, 4)
        self.assertFalse(d._begin_celebration())
        self.assertFalse(d._celebrating())

    def test_any_dance_of_any_round_plays_on(self):
        for rounds, row in ((FINAL, 4), (FINAL, 2), (SEMI_THEN_FINAL, 2)):
            with self.subTest(row=row, rounds=rounds[0]):
                d = _Desk({"celebrate_mode": "all"}, rounds, row)
                self.assertTrue(d._begin_celebration())
                self.assertTrue(d._celebrating())


class SwitchTest(unittest.TestCase):
    """🥇 The switch is the list's: on, every title of it plays on."""

    def test_on_makes_every_title_play_on(self):
        d = _Desk({}, SEMI_THEN_FINAL, 2)
        self.assertFalse(d._celebration_due())
        d._vals["celebrate"] = True
        self.assertTrue(d._celebration_due())
        self.assertTrue(d._begin_celebration())

    def test_off_beats_nothing_else_it_is_just_off(self):
        d = _Desk({"celebrate_mode": "all"}, FINAL, 2)
        self.assertTrue(d._celebration_due())
        d._vals["celebrate"] = False
        self.assertFalse(d._celebration_due())

    def test_auto_still_wins(self):
        d = _Desk({}, FINAL, 2, advance=True)
        d._vals["celebrate"] = True
        self.assertFalse(d._celebration_due())


class _Panel:
    """The ▶ panel's 🥇 button as Qt drives it: a click flips the check first,
    then tells the desk."""

    def __init__(self):
        self.on = False
        self.desk = None

    def set_pd_loaded(self, on):
        pass

    def set_celebrate(self, on):
        self.on = on

    def click(self):
        self.on = not self.on
        self.desk._on_celebrate_toggled(self.on)


class _LoadingDesk(_Desk):
    """The same desk, loading titles through the real `_adopt_track`."""

    _adopt_track = TrackLoadMixin._adopt_track
    _sync_celebrate_btn = PlayerControlMixin._sync_celebrate_btn
    _on_celebrate_toggled = PlayerControlMixin._on_celebrate_toggled

    def __init__(self, settings, rounds, row):
        super().__init__(settings, rounds, row)
        self._play_panel = _Panel()
        self._play_panel.desk = self
        self._playback.path = None
        self._playback.closing = None
        self._between = BetweenDances()
        self._last_played = None

    def _resolve_entry(self, path):
        return None

    def _row_dance(self, path):
        return "WW"

    def _sync_dance_len(self):
        pass

    def _resume_mark_for(self, path):
        return 0

    def _pre_roll_ms_for(self, path):
        return 0

    def _refresh_resume_marks(self, path):
        pass

    def _sync_taskbar_title(self):
        pass

    def load(self, row):
        """Mark the row, then load its title — as a click on the row does."""
        self._deckset.all_tables[0]._current_play_row = row
        self._adopt_track(Path(f"C:/m/{row}.mp3"))


class ShownTest(unittest.TestCase):
    """🥇 What the switch shows: the list's value, whatever title is loaded."""

    def test_it_shows_the_lists_value(self):
        d = _LoadingDesk({"celebrate_mode": "all"}, FINAL, 2)
        d._sync_celebrate_btn()
        self.assertTrue(d._play_panel.on)
        d._vals["celebrate"] = False
        d._sync_celebrate_btn()
        self.assertFalse(d._play_panel.on)

    def test_a_click_is_for_the_whole_list(self):
        d = _LoadingDesk({}, SEMI_THEN_FINAL, 2)
        d.load(2)
        d._play_panel.click()
        self.assertTrue(d._vals["celebrate"])
        self.assertTrue(d._celebration_due())
        d.load(7)   # another round, same list: still on
        self.assertTrue(d._play_panel.on)
        self.assertTrue(d._celebration_due())
        d._play_panel.click()
        self.assertFalse(d._vals["celebrate"])
        self.assertFalse(d._celebration_due())


class AutoTest(unittest.TestCase):
    """⏭ Auto: the pause and its music follow each title — nothing plays on."""

    def test_no_dance_of_the_final_plays_on(self):
        for mode, row in (("last", 4), ("all", 2), ("all", 4)):
            with self.subTest(mode=mode, row=row):
                d = _Desk({"celebrate_mode": mode}, FINAL, row, advance=True)
                self.assertFalse(d._celebration_due())
                self.assertFalse(d._begin_celebration())
                self.assertFalse(d._celebrating())

    def test_the_cut_fades_it_all_the_way(self):
        d = _Desk({"celebrate_mode": "all", "celebrate_dip_pct": 20}, FINAL, 2,
                  advance=True)
        self.assertEqual(d._cut_fade_floor(), 0.0)

    def test_it_comes_up_to_its_level_and_counts_the_file_down(self):
        d = _Desk({"celebrate_mode": "last", "celebrate_pct": 50,
                   "celebrate_dip_pct": 0, "celebrate_up_secs": 4,
                   "celebrate_hold_secs": 0}, FINAL, 4)
        d._begin_celebration()
        d._playback.celebrate = (d._playback.token, time.monotonic() - 2.0)
        self.assertTrue(d._celebration_tick())
        self.assertAlmostEqual(d._mix.fade, 0.25, places=2)
        self.assertEqual(d._countdown, "🥇  2:00")
        d._playback.celebrate = (d._playback.token, time.monotonic() - 9.0)
        d._celebration_tick()
        self.assertAlmostEqual(d._mix.fade, 0.5)

    def test_it_holds_at_the_dip_before_it_comes_up(self):
        d = _Desk({"celebrate_mode": "last", "celebrate_pct": 40,
                   "celebrate_dip_pct": 0, "celebrate_up_secs": 4,
                   "celebrate_hold_secs": 2}, FINAL, 4)
        d._begin_celebration()
        d._playback.celebrate = (d._playback.token, time.monotonic() - 1.5)
        d._celebration_tick()
        self.assertAlmostEqual(d._mix.fade, 0.0, places=2)
        d._playback.celebrate = (d._playback.token, time.monotonic() - 4.0)
        d._celebration_tick()
        self.assertAlmostEqual(d._mix.fade, 0.2, places=2)

    def test_a_new_title_ends_it(self):
        d = _Desk({"celebrate_mode": "last"}, FINAL, 4)
        d._begin_celebration()
        d._playback.token += 1   # what every load and stop does
        self.assertFalse(d._celebrating())
        self.assertFalse(d._celebration_tick())

    def test_it_comes_up_from_where_the_dip_left_it(self):
        d = _Desk({"celebrate_mode": "last", "celebrate_pct": 40,
                   "celebrate_dip_pct": 20, "celebrate_up_secs": 4}, FINAL, 4)
        d._begin_celebration()
        d._celebration_tick()
        self.assertAlmostEqual(d._mix.fade, 0.2, places=2)

    def test_the_cut_fades_it_down_to_the_dip(self):
        d = _Desk({"celebrate_mode": "last", "celebrate_dip_pct": 20}, FINAL, 4)
        self.assertAlmostEqual(d._cut_fade_floor(), 0.2)

    def test_the_cut_fades_a_title_that_just_ends_all_the_way(self):
        settings = {"celebrate_dip_pct": 20}   # the list's switch is off
        for row in (4, 2):
            with self.subTest(row=row):
                self.assertEqual(_Desk(settings, FINAL, row)._cut_fade_floor(), 0.0)

    def test_fade_out_now_takes_its_own_seconds_from_its_level(self):
        d = _Desk({"celebrate_mode": "last", "celebrate_down_secs": 6,
                   "hand_fade_secs": 1}, FINAL, 4)
        d._begin_celebration()
        d._mix.fade = 0.4
        d._fade_out_now()
        self.assertTrue(d._fade_now.running)
        self.assertAlmostEqual(d._fade_now.level(d._fade_now.remaining()), 0.4,
                               places=2)
        self.assertAlmostEqual(d._fade_now.remaining(), 6.0, places=1)


class _Big:
    """The card as `_sync_big_player_limit` arms it."""

    def __init__(self):
        self.limit = None
        self.fade_at = "untouched"

    def set_limit(self, ms, glyph="hourglass", to_end=False, then=None):
        self.limit = (ms, glyph, to_end, then)

    def set_pd_marks(self, marks, armed=None):
        pass

    def set_celebrate_mark(self, ms):
        self.mark = ms

    def set_wave_overlay(self, silences, fade_start_ms, start_ms=0,
                         fade_in_end_ms=None):
        self.fade_at = fade_start_ms


class _CardDesk(_Desk):
    """The celebration desk with the card's limit synced, 1:30 to play."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._big_player = _Big()
        self._silences = {}

    def _pd_runs_to_its_highlight(self):
        return False

    def _play_limit_secs(self):
        return 90

    def _play_end_secs(self):
        return 90.0

    def _silence_stop_ms(self):
        return None

    def _unarmed_pd_marks(self):
        return []


class CardTest(unittest.TestCase):
    """F21: the card says a title will play on, and spans what it plays.

    Marcel saw nothing of it — the panel only named "Jive — its own length" —
    and while it played on, the seek bar and the waveform stayed cut at 1:30."""

    def test_before_the_cut_the_card_says_it_plays_on(self):
        d = _CardDesk({"celebrate_mode": "last"}, FINAL, 4)
        d._sync_big_player_limit()
        self.assertEqual(d._big_player.limit, (90_000, "hourglass", False, "trophy"))

    def test_a_title_that_just_ends_says_nothing(self):
        for settings, row, advance in (({}, 4, False),
                                       ({}, 2, False),
                                       ({"celebrate_mode": "all"}, 2, True)):
            with self.subTest(settings=settings, row=row, advance=advance):
                d = _CardDesk(settings, FINAL, row, advance=advance)
                d._sync_big_player_limit()
                self.assertIsNone(d._big_player.limit[3])

    def test_playing_on_the_card_runs_to_the_files_end(self):
        d = _CardDesk({"celebrate_mode": "last"}, FINAL, 4)
        d._sync_big_player_limit()
        self.assertTrue(d._begin_celebration())
        self.assertEqual(d._big_player.limit, (None, "trophy", True, None))
        self.assertIsNone(d._big_player.fade_at)

    def test_the_card_is_told_where_it_went_to_the_celebration(self):
        d = _CardDesk({"celebrate_mode": "last"}, FINAL, 4)
        d._player.position = lambda: 88_000
        self.assertTrue(d._begin_celebration())
        self.assertEqual(d._playback.celebrate_at_ms, 88_000)
        self.assertEqual(d._big_player.mark, 88_000)

    def test_a_running_order_names_its_final_in_the_strips(self):
        """An imported running order keeps the round in its ─── strips, not
        on the row — `round_at` knows it either way."""
        d = _CardDesk({"celebrate_mode": "last"}, [""] * 5, 4)
        d._deckset.all_tables[0].round_at = lambda _row: "Endrunde"
        self.assertTrue(d._begin_celebration())


class _ReplayDesk(_CardDesk):
    """The card desk with the ↩ marks and the ⏮ rewind, ↩ switched on."""

    _remember_stop_point = TrackLoadMixin._remember_stop_point
    _note_resume = TrackLoadMixin._note_resume
    _clear_resume = TrackLoadMixin._clear_resume
    _on_back_to_start = TrackLoadMixin._on_back_to_start
    remember_pos = TrackLoadMixin.remember_pos

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._settings["remember_pos"] = True
        self._resume = ResumeMarks()
        self._resume_seek_ms = None

    def _is_playing_mode(self):
        return True

    def _refresh_resume_marks(self, _path=None):
        pass


class ReplayTest(unittest.TestCase):
    """F21: "on replay the waveform is full instead of 1:30 — it works only
    the first time". Stopped while it played on, the title kept a ↩ mark
    past its cut: played again it was picked up there, the 1:30 counted
    from that point and ran past the file's end, so the card spanned it all."""

    def playing_on(self):
        d = _ReplayDesk({"celebrate_mode": "last"}, FINAL, 4)
        self.assertTrue(d._begin_celebration())
        d._player.pos = 130_000
        return d

    def test_a_title_stopped_while_it_plays_on_keeps_no_mark(self):
        d = self.playing_on()
        d._remember_stop_point()
        self.assertIsNone(d._resume.get(d._playback.path))

    def test_nor_an_older_one(self):
        d = self.playing_on()
        d._resume.note(d._playback.path, 40_000, 215_000)
        d._remember_stop_point()
        self.assertIsNone(d._resume.get(d._playback.path))

    def test_stopped_before_its_cut_it_still_keeps_one(self):
        d = _ReplayDesk({"celebrate_mode": "last"}, FINAL, 4)
        d._player.pos = 40_000
        d._remember_stop_point()
        self.assertEqual(d._resume.get(d._playback.path), 40_000)

    def test_rewound_it_is_cut_at_its_length_again(self):
        """⏮ 0:00 starts the title over: the celebration is over with it."""
        d = self.playing_on()
        d._on_back_to_start()
        self.assertFalse(d._celebrating())
        self.assertEqual(d._big_player.limit, (90_000, "hourglass", False, "trophy"))


class PlayerCardTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from player.widgets.player import BigPlayerWidget
        self.card = BigPlayerWidget(QMediaPlayer())
        self.addCleanup(reap_widget, self.card)
        self.card._dur = 215_000

    def test_the_cut_shows_the_trophy_after_it(self):
        from shared.appearance.icons import WARN
        from shared.appearance.icons import html as icon_html
        self.card.set_limit(90_000, then="trophy")
        text = self.card._limit_lbl.text()
        self.assertIn(icon_html("trophy", 11, WARN), text)
        self.assertLess(text.index(icon_html("hourglass", 11, WARN)),
                        text.index(icon_html("trophy", 11, WARN)))
        self.assertEqual(self.card._wave._span, 90_000)

    def test_playing_on_spans_the_whole_file(self):
        self.card.set_limit(90_000, then="trophy")
        self.card.set_limit(None, "trophy", to_end=True)
        self.assertEqual(self.card._wave._span, 215_000)
        self.assertEqual(self.card._slider.maximum(), 215_000)


class PanelTest(_WindowCase):
    """F21: the ▶ panel names it too — Marcel looked there and read only
    "Jive — its own length"."""

    def setUp(self):
        super().setUp()
        self.win._list_vals(self.b)["celebrate"] = True

    def test_the_last_dance_of_the_final_plays_on(self):
        self.b._row_meta.append(Row(dance="WW", round_name="Endrunde"))
        self.play(self.b, "WW")
        self.assertFalse(self.panel.len_dance_lbl.isHidden())
        self.assertIn("then plays on", self.panel.len_dance_lbl.text())

    def test_without_a_length_of_its_own_it_still_says_so(self):
        self.b._row_meta.append(Row(dance="LW", round_name="Endrunde"))
        self.play(self.b, "LW")
        self.assertFalse(self.panel.len_dance_lbl.isHidden())
        self.assertEqual(self.panel.len_dance_lbl.text(),
                         "Plays on after its length")

    def test_another_round_plays_on_too(self):
        self.b._row_meta.append(Row(dance="WW", round_name="Semifinal"))
        self.play(self.b, "WW")
        self.assertIn("then plays on", self.panel.len_dance_lbl.text())

    def test_a_list_with_the_switch_off_says_nothing_of_it(self):
        self.win._list_vals(self.b)["celebrate"] = False
        self.b._row_meta.append(Row(dance="WW", round_name="Endrunde"))
        self.play(self.b, "WW")
        self.assertNotIn("plays on", self.panel.len_dance_lbl.text())

    def test_the_switch_is_hidden_with_a_full_length(self):
        self.play(self.b, "LW")
        self.panel._secs = 0
        self.panel.set_dance_len("", "", None)
        self.assertTrue(self.panel.celebrate_btn.isHidden())
        self.panel._secs = 90
        self.panel.set_dance_len("", "", None)
        self.assertFalse(self.panel.celebrate_btn.isHidden())

    def test_a_full_length_says_nothing_of_playing_on(self):
        """Nothing is cut with 'full', so the golden line must not promise it."""
        self.play(self.b, "WW")
        self.panel._secs = 0
        self.panel.set_dance_len("", "", None, plays_on=True)
        self.assertTrue(self.panel.len_dance_lbl.isHidden())
        self.panel.set_dance_len("WW", "Waltz", 0, plays_on=True)
        self.assertNotIn("plays on", self.panel.len_dance_lbl.text())
        self.panel._secs = 90
        self.panel.set_dance_len("", "", None, plays_on=True)
        self.assertIn("lays on", self.panel.len_dance_lbl.text())

    def test_untouched_the_tournament_set_follows_settings_in_a_final(self):
        """Like a dance's own length: the set decides until the hand does."""
        self.win._settings["celebrate_mode"] = "last"
        self.win._list_vals(self.b)["celebrate"] = None
        places = {0: ("Endrunde", False), 1: ("Endrunde", True)}
        self.win._round_place_at = lambda t, row: places[row]
        self.assertFalse(self.win._celebration_of(self.b, 0))
        self.assertTrue(self.win._celebration_of(self.b, 1))

    def test_the_hand_overrides_the_set_either_way(self):
        self.win._settings["celebrate_mode"] = "all"
        self.win._round_place_at = lambda t, row: ("Endrunde", False)
        self.win._list_vals(self.b)["celebrate"] = None
        self.assertTrue(self.win._celebration_of(self.b, 0))
        self.win._list_vals(self.b)["celebrate"] = False
        self.assertFalse(self.win._celebration_of(self.b, 0))
        self.win._list_vals(self.b)["celebrate"] = True
        self.assertTrue(self.win._celebration_of(self.b, 2))

    def test_off_the_tournament_set_only_the_switch_counts(self):
        self.win._settings["celebrate_mode"] = "all"
        self.b._row_meta.append(Row(dance="LW", round_name="Endrunde"))
        self.win._list_vals(self.b)["secs"] = 61   # a length of its own
        self.win._list_vals(self.b)["celebrate"] = None
        self.assertFalse(self.win._celebration_of(self.b, 0))
        self.win._list_vals(self.b)["celebrate"] = True
        self.assertTrue(self.win._celebration_of(self.b, 0))

    def test_the_switch_follows_the_list_clicked(self):
        a = self.win._deckset.tableA
        self.win._on_table_focused(a)
        self.assertFalse(self.panel.celebrate_btn.isChecked())
        self.win._on_table_focused(self.b)
        self.assertTrue(self.panel.celebrate_btn.isChecked())

    def test_its_text_is_translated(self):
        from planner.i18n.lang_de import CATALOG
        for text in ("%s — its own length, then plays on",
                     "Plays on after its length"):
            with self.subTest(text=text):
                self.assertIn(text, CATALOG)


class DialogTest(unittest.TestCase):
    """🎛 Playsets keeps the mode; the numbers are on 🔊 Sound & player."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_off_by_default(self):
        self.assertEqual(self._dialog({}).values()["celebrate_mode"], "off")

    def test_the_mode_is_saved(self):
        dlg = self._dialog({"celebrate_mode": "last"})
        self.assertEqual(dlg._celebrate_mode.currentData(), "last")
        dlg._celebrate_mode.setCurrentIndex(dlg._celebrate_mode.findData("all"))
        self.assertEqual(dlg.values()["celebrate_mode"], "all")

    def test_it_sits_in_the_tournament_set(self):
        """F20: the final plays on in a competition; the 🎉 party set has no
        final, so the box belongs under 🏆 and nowhere near 🎉."""
        dlg = self._dialog({})
        holder = dlg._celebrate_box.parentWidget()
        while holder is not None and not isinstance(holder, QGroupBox):
            holder = holder.parentWidget()
        self.assertIsNotNone(holder)
        self.assertEqual(holder.title(), "🏆  Tournament set")

    def test_its_text_is_translated(self):
        from planner.i18n.lang_de import CATALOG
        dlg = self._dialog({})
        texts = [dlg._celebrate_box.title(), dlg._celebrate_hint.text(),
                 dlg._celebrate_mode.toolTip(),
                 "Level, dip and times: 🔊 Sound & player."]
        texts += [dlg._celebrate_mode.itemText(i)
                  for i in range(dlg._celebrate_mode.count())]
        for text in texts:
            with self.subTest(text=text[:20]):
                self.assertIn(text, CATALOG)


class SoundTabTest(unittest.TestCase):
    """The numbers live in ⚙ Settings → 🔊 Sound & player."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_defaults_when_nothing_is_stored(self):
        vals = self._dialog({}).values()
        self.assertEqual(vals["celebrate_pct"], CELEBRATE_PCT)
        self.assertEqual(vals["celebrate_dip_pct"], CELEBRATE_DIP_PCT)
        self.assertEqual(vals["celebrate_hold_secs"], CELEBRATE_HOLD_SECS)
        self.assertEqual(vals["celebrate_up_secs"], CELEBRATE_UP_SECS)
        self.assertEqual(vals["celebrate_down_secs"], CELEBRATE_DOWN_SECS)

    def test_the_numbers_are_shown_and_saved(self):
        dlg = self._dialog({"celebrate_pct": 55, "celebrate_dip_pct": 15,
                            "celebrate_hold_secs": 1.5, "celebrate_up_secs": 4,
                            "celebrate_down_secs": 2})
        self.assertEqual(dlg._celebrate_pct.value(), 55)
        self.assertEqual(dlg._celebrate_dip.value(), 15)
        self.assertEqual(dlg._celebrate_hold.value(), 1.5)
        dlg._celebrate_hold.setValue(4.0)
        dlg._celebrate_down.setValue(6.0)
        vals = dlg.values()
        self.assertEqual(vals["celebrate_pct"], 55)
        self.assertEqual(vals["celebrate_hold_secs"], 4.0)
        self.assertEqual(vals["celebrate_up_secs"], 4.0)
        self.assertEqual(vals["celebrate_down_secs"], 6.0)

    def test_reset_puts_them_back(self):
        dlg = self._dialog({"celebrate_pct": 55, "celebrate_hold_secs": 5})
        dlg._reset_sound_numbers()
        self.assertEqual(dlg._celebrate_pct.value(), CELEBRATE_PCT)
        self.assertEqual(dlg._celebrate_hold.value(), CELEBRATE_HOLD_SECS)

    def test_its_text_is_translated(self):
        from planner.i18n.lang_de import CATALOG
        for text in ("Level:", "Dip to:", "Hold:", "Up over:", "Down over:",
                     "🥇 Celebration — the music plays on"):
            with self.subTest(text=text[:20]):
                self.assertIn(text, CATALOG)

    def test_its_heading_is_plain_text_not_bold(self):
        from PySide6.QtWidgets import QLabel
        dlg = self._dialog({})
        heads = [lbl for lbl in dlg.findChildren(QLabel)
                 if "Celebration" in lbl.text() and "plays on" in lbl.text()]
        self.assertEqual(len(heads), 1)
        self.assertNotIn("<b>", heads[0].text())


if __name__ == "__main__":
    unittest.main()
