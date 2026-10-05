#!/usr/bin/env python3
"""Tests for WHEN a new title's playback rate is set (`_load_track`).

Run:  py -m unittest tests.player.test_pitch_gap -v

Every rate change makes the media backend re-init its resampler, and whatever
is already in the audio sink is dropped — that is the short gap you hear. The
rate a title starts on is therefore set while the player is still stopped: the
fader reset, the pushed rate and the 🎚 TSO pitch to the heat tempo all happen
BEFORE play(), where the same re-init costs nothing because there is no sound
yet. Only what could not be resolved that early is repeated afterwards.

`_load_track` is run for real; everything around it (the backend, the player
card, the announcements) records into one shared log instead.
"""

import os
import tempfile
import unittest
from pathlib import Path

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pitch_"))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from player.mix import OutputMix  # noqa: E402
from player.main_player import PlayerControlMixin  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.models import MusicEntry  # noqa: E402
from player.playback_state import PlaybackState  # noqa: E402
from player.between_dances import BetweenDances  # noqa: E402

_MUSIC = Path(r"C:\music\tanzcds")


class _Player:
    """The media backend as far as the load path touches one."""

    def __init__(self, log):
        self.log = log
        self._src = None

    def stop(self):
        pass

    def setSource(self, url):
        self._src = url

    def source(self):
        return self._src

    def play(self):
        self.log.append("play")


class _Card:
    """The big player card: the fader lives here, so every rate change does."""

    def __init__(self, log, tso: bool):
        self.log = log
        self._tso = tso
        self.takt = None
        self.target = None

    def set_takt(self, takt):
        self.takt = takt
        self.log.append("takt")

    def set_current_dance(self, *a):
        pass

    def on_new_track(self):
        self.log.append("fader-reset")

    def apply_tempo(self):
        self.log.append("rate")

    def tso_mode(self) -> bool:
        return self._tso

    def set_tempo_to_target(self, target_bpm: float):
        self.log.append("pitch")
        self.target = target_bpm
        return int(target_bpm)

    def set_now(self, *a):
        pass

    def set_artwork(self, *a):
        pass

    def set_gain(self, *a):
        pass


class _Panel:
    def announce_wait(self) -> bool:
        # ⏳ off, so the load path's real `_announce_start_first` answers "no
        # wait" by itself — the announcement has its own tests.
        return False

    def pd_editing(self) -> bool:
        return False

    def pd_highlight_stop(self) -> bool:
        return False


class _Label:
    """Stands in for the "now playing" label and the status bar alike."""

    def setText(self, _t):
        pass

    def showMessage(self, _t, _ms=0):
        pass


class _Timer:
    def start(self):
        pass


class _Desk(PlayerControlMixin, QWidget):
    """A desk reduced to the load path: the REAL `_load_track` and the REAL
    `_equalize_heat_tempo`, with everything they reach out to stubbed."""

    def __init__(self, table, tso: bool = True, settings=None):
        QWidget.__init__(self)
        self.log = []
        self._settings = dict(settings or {})
        self._player = _Player(self.log)
        self._big_player = _Card(self.log, tso)
        self._play_panel = _Panel()
        self._all_tables = [table]
        self._now_playing = _Label()
        self._fade_timer = _Timer()
        self._preview = None
        self._preview_src = None
        self._playback = PlaybackState()
        self._playback.token = 0
        self._last_load_at = 0.0
        self._playback.path = None
        self._playback.dance = ""
        self._taskbar = None        # 🪟 no shell here: the caption is a no-op
        self._played_marked = False
        self._playback.offset_ms = 0
        self._resume_pos = {}       # ↩ where titles were left (session only)
        self._resume_seek_ms = None
        self._between = BetweenDances()
        self._between.round_start = None
        self._mix = OutputMix()
        self._pd_verify_stop = False
        self.pitch_calls = 0

    # ── Everything the load path calls that is not under test ──
    def _await_loudness(self, path, start):
        return False

    def _resolve_entry(self, path):
        return next((m.entry for m in self._all_tables[0]._row_meta
                     if m and m.entry is not None
                     and str(m.entry.path) == str(path)), None)

    def _ensure_silences(self, path):
        pass

    def _loudness_gain(self, path):
        return 1.0

    def _apply_volume(self):
        pass

    def _stop_play_timer(self):
        pass

    def _sync_big_player_limit(self):
        pass

    def _refresh_next_up(self):
        pass

    def _show_preview(self, path):
        pass

    def _maybe_announce_start(self, ent):
        pass

    def _check_playback(self, token, path, retried=False):
        pass

    def _playing_m3u(self):
        return None

    def _is_playing_mode(self) -> bool:
        return True

    def statusBar(self):
        return _Label()

    def _equalize_heat_tempo(self, auto: bool = False) -> bool:
        self.pitch_calls += 1
        return PlayerControlMixin._equalize_heat_tempo(self, auto)


def _entry(dance: str, i: int, bpm: int) -> MusicEntry:
    return MusicEntry(path=_MUSIC / f"{dance}{i}.mp3", title=f"{dance} {i}",
                      dance=dance, duration=180, bpm=bpm)


class TsoBandTargetTest(unittest.TestCase):
    """🎚 Where in its TSO band a dance is pitched (planner.models)."""

    def target(self, band, mean=25.4, lo=24, hi=26):
        from dancesport_planner import tso_band_target
        return tso_band_target(lo, hi, mean, band)

    def test_the_heat_mean_is_what_the_button_always_did(self):
        self.assertAlmostEqual(self.target("mean"), 25.4)

    def test_the_mean_is_still_pulled_into_the_band(self):
        self.assertAlmostEqual(self.target("mean", mean=22.0), 24.0)
        self.assertAlmostEqual(self.target("mean", mean=30.0), 26.0)

    def test_the_three_fixed_takte(self):
        self.assertAlmostEqual(self.target("lower"), 24.0)
        self.assertAlmostEqual(self.target("middle"), 25.0)
        self.assertAlmostEqual(self.target("upper"), 26.0)

    def test_a_fixed_takt_ignores_what_the_heat_was_recorded_at(self):
        """The point of the setting: the whole dance on ONE takt."""
        for mean in (24.0, 25.5, 26.0):
            with self.subTest(mean=mean):
                self.assertAlmostEqual(self.target("lower", mean=mean), 24.0)

    def test_an_odd_band_halves_the_way_the_user_asked_for(self):
        """"24 and 25 pitched equally → 24.5"."""
        self.assertAlmostEqual(self.target("middle", lo=24, hi=25), 24.5)


class TaktReadoutTest(unittest.TestCase):
    """What the takt readout prints (player.player._takt_text).

    A heat of a T24 and a T25 Rumba is equalized to their mean, 24.5 — and the
    whole-takt readout said "T25" on both, which is what a hard 25 would say
    too. The half takt is the answer to "what is this heat danced at"."""

    def text(self, x):
        from player.player import _takt_text
        return _takt_text(x)

    def test_a_half_takt_is_printed_as_one(self):
        self.assertEqual(self.text(24.5), "24.5")

    def test_a_whole_takt_keeps_its_bare_number(self):
        self.assertEqual(self.text(25.0), "25")
        self.assertEqual(self.text(24.998), "25")

    def test_the_fader_quantisation_does_not_leak_into_the_readout(self):
        """0.1 % fader steps land a hair off the target; the tenth is what the
        operator can act on."""
        self.assertEqual(self.text(24.504), "24.5")
        self.assertEqual(self.text(50.02), "50")

    def test_the_half_still_rounds_up(self):
        """T24.55 reads 24.6, not 24.5 — the old whole-takt rule, one digit
        further out (Python's round() would give the even neighbour)."""
        self.assertEqual(self.text(24.55), "24.6")


class TsoBandSettingTest(unittest.TestCase):
    """Reading the per-dance setting out of gui_settings.json."""

    def band(self, settings, dance="RB"):
        from player.tso import tso_band_of
        return tso_band_of(settings, dance)

    def test_an_unset_dance_keeps_the_heat_mean(self):
        self.assertEqual(self.band({}), "mean")
        self.assertEqual(self.band({"tso_band": {"LW": "lower"}}), "mean")

    def test_a_set_dance_is_read_back(self):
        self.assertEqual(self.band({"tso_band": {"RB": "upper"}}), "upper")

    def test_a_setting_from_the_future_falls_back_instead_of_pitching_wrong(self):
        self.assertEqual(self.band({"tso_band": {"RB": "highest"}}), "mean")
        self.assertEqual(self.band({"tso_band": "lower"}), "mean")


class TaktCountsTest(unittest.TestCase):
    """🎚 The takte a round is made of (planner.models.takt_counts)."""

    def counts(self, *bpms):
        from dancesport_planner import takt_counts
        return takt_counts(list(bpms))

    def test_the_titles_are_counted_per_takt(self):
        self.assertEqual(self.counts(24, 25, 25, 25, 25, 25), {24: 1, 25: 5})

    def test_a_round_on_one_takt_has_one(self):
        self.assertEqual(self.counts(25, 25, 25), {25: 3})

    def test_a_measured_tenth_joins_the_takt_it_is_nearest(self):
        self.assertEqual(self.counts(24.4, 24.6), {24: 1, 25: 1})

    def test_a_title_without_a_takt_counts_for_nothing(self):
        self.assertEqual(self.counts(0, None, 25), {25: 1})

    def test_an_empty_round_has_none(self):
        self.assertEqual(self.counts(), {})


class RoundTaktTargetTest(unittest.TestCase):
    """🎚 The takt a round is danced at (planner.models.round_takt_target)."""

    def target(self, *bpms):
        from dancesport_planner import round_takt_target, takt_counts
        return round_takt_target(takt_counts(list(bpms)))

    def test_two_buckets_meet_in_the_middle(self):
        """Two T24 Rumbas and three T25: a 24 bucket and a 25 bucket, nothing
        in 26 — 24.5, not the 25 a head count says."""
        self.assertAlmostEqual(self.target(24, 24, 25, 25, 25), 24.5)

    def test_a_cheap_whole_takt_up_to_the_majority_is_stepped(self):
        """Five T31 Cha-Chas and a single T30: the one joins them at 31, which
        costs it 3.3%. Meeting at 30.5 would move five titles to spare one."""
        self.assertAlmostEqual(self.target(30, 31, 31, 31, 31, 31), 31.0)

    def test_the_same_holds_for_a_lone_faster_title(self):
        """Five T31 and a single T32: the one brakes 3.1% to join them."""
        self.assertAlmostEqual(self.target(31, 31, 31, 31, 31, 32), 31.0)

    def test_an_even_round_meets_in_the_middle(self):
        """Three T24 and three T25 Rumbas → 24.5, as asked for."""
        self.assertAlmostEqual(self.target(24, 24, 24, 25, 25, 25), 24.5)

    def test_two_titles_a_takt_apart_meet_between_them(self):
        """A two-heat round of one T24 and one T25 → 24.5."""
        self.assertAlmostEqual(self.target(24, 25), 24.5)

    def test_a_round_on_one_takt_is_danced_on_it(self):
        self.assertAlmostEqual(self.target(25, 25, 25), 25.0)

    def test_the_copies_no_longer_vote(self):
        """Averaging the titles gave 24.7 — neither takt, and no middle. The
        buckets are 24 and 25 however many copies sit in them."""
        self.assertAlmostEqual(self.target(24, 25, 25, 25, 25, 25), 24.5)

    def test_the_middle_is_of_the_takte_not_of_the_titles(self):
        """A tie between three takte: 24, 25 and 26 → 25, whatever the counts
        (they are equal by definition here)."""
        self.assertAlmostEqual(self.target(24, 24, 25, 25, 26, 26), 25.0)

    def test_an_empty_round_asks_for_nothing(self):
        self.assertEqual(self.target(), 0.0)


class RoundTaktByDanceTest(unittest.TestCase):
    """🎚 The rounds the rule was written from, dance by dance, band and all.

    A whole takt is only stepped where it stays near the 2% a floor does not
    feel; anything else meets in the middle of the round's takte.
    """

    def target(self, dance, *bpms):
        from dancesport_planner import (TEMPO_RANGES, round_takt_target,
                                        takt_counts)
        lo, hi = TEMPO_RANGES[dance]["S"]
        return round_takt_target(takt_counts(list(bpms)), lo, hi)

    def test_samba_steps_up_to_the_majority(self):
        """T50 against two T51: 2.0%, the cheapest whole takt there is."""
        self.assertAlmostEqual(self.target("SA", 50, 51, 51), 51.0)

    def test_cha_cha_steps_up_to_the_majority(self):
        """3.3% — still under the thumb rule."""
        self.assertAlmostEqual(self.target("CC", 30, 31, 31), 31.0)

    def test_tango_steps_up_to_the_majority(self):
        self.assertAlmostEqual(self.target("TG", 31, 32, 32), 32.0)

    def test_rumba_is_too_slow_for_a_whole_takt(self):
        """T24 → T25 is 4.2%, so the round meets at 24.5 instead."""
        self.assertAlmostEqual(self.target("RB", 24, 25, 25), 24.5)

    def test_the_slow_waltz_is_too_slow_for_one_as_well(self):
        """T28 → T29 is 3.6%: over the rule, and a Waltz is heard on it."""
        self.assertAlmostEqual(self.target("LW", 28, 29, 29), 28.5)

    def test_the_slow_fox_meets_in_the_middle_like_the_waltz(self):
        self.assertAlmostEqual(self.target("SF", 28, 29, 29), 28.5)

    def test_a_paso_doble_of_three_takte_meets_in_the_middle(self):
        """T58+T59+T60: no takt leads, so all three meet at 59."""
        self.assertAlmostEqual(self.target("PD", 58, 59, 60), 59.0)

    def test_the_viennese_majority_is_two_takte_off_the_odd_title(self):
        """Two T58 against a T60: joining the majority is two takte for the
        T60, too far — so the round meets at 59, both sides moving."""
        self.assertAlmostEqual(self.target("WW", 58, 58, 60), 59.0)

    def test_the_samba_majority_pulls_the_faster_titles_down(self):
        """Nine T50 against three T51: braking costs 2.0%, so the round is
        danced at 50 and the nine are played as recorded."""
        self.assertAlmostEqual(
            self.target("SA", *([50] * 9 + [51] * 3)), 50.0)

    def test_a_jive_two_takte_wide_meets_in_the_middle(self):
        """T41+T42+2×T43: the T41 is two takte off the majority, which is too
        far to join — the round is danced at 42."""
        self.assertAlmostEqual(self.target("JI", 41, 42, 43, 43), 42.0)

    def test_a_quickstep_two_takte_wide_does_the_same(self):
        self.assertAlmostEqual(self.target("QS", 50, 52, 52), 51.0)

    def test_a_takt_below_the_band_is_left_out_of_the_middle(self):
        """A T27 Slow Fox is outside the 28-30 band: it is pulled up on its
        own and does not drag the T28 and T29 down with it."""
        self.assertAlmostEqual(self.target("SF", 27, 28, 29), 28.5)

    def test_a_round_entirely_outside_its_band_still_has_a_takt(self):
        """Nothing in the band — then all of it counts again, and the band
        clamp on top does the rest."""
        self.assertAlmostEqual(self.target("SF", 26, 27), 26.5)


class PitchBeforePlayTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _desk(self, tso: bool = True, settings=None, entries=None,
              sections=None):
        self.table = PlaylistTable()
        self.addCleanup(reap_widget, self.table)
        if sections:
            # What heads the ─── strips of a running order: track path →
            # round. The rows themselves never learn it.
            self.table._player_sections = dict(sections)
        self.table.load_warmup(
            entries or [_entry("QS", 1, 50), _entry("QS", 2, 52)],
            "🤸 Eintanzen", "both", "S", False, lambda *a: None, None,
            running_order=bool(sections))
        self.rows = [r for r, m in enumerate(self.table._row_meta)
                     if m and m.entry is not None]
        desk = _Desk(self.table, tso, settings)
        self.addCleanup(reap_widget, desk)
        return desk

    def _play_first(self, desk):
        """What a deck does: mark the row, then hand the path over."""
        self._play_nth(desk, 0)

    def _play_nth(self, desk, i):
        self.table._current_play_row = self.rows[i]
        desk._load_track(self.table._row_meta[self.rows[i]].entry.path)

    def test_the_music_starts_at_the_tempo_it_will_play_at(self):
        desk = self._desk()
        self._play_first(desk)
        self.assertIn("pitch", desk.log)
        self.assertLess(desk.log.index("pitch"), desk.log.index("play"),
                        "pitching after play() is the gap we are removing")

    def test_the_card_is_told_the_unrounded_takt(self):
        """The mean of a T50 and a T51 Quickstep is a half takt, and the card
        has to hear it as one — it is what the readout prints."""
        desk = self._desk()
        self.table.load_warmup(
            [_entry("QS", 1, 50), _entry("QS", 2, 51)],
            "🤸 Eintanzen", "both", "S", False, lambda *a: None, None)
        self.rows = [r for r, m in enumerate(self.table._row_meta)
                     if m and m.entry is not None]
        self._play_first(desk)
        self.assertAlmostEqual(desk._big_player.target, 50.5)

    def test_the_heat_is_pitched_to_its_own_mean_by_default(self):
        """Two Quicksteps at T50 and T52 → the heat is danced at T51."""
        desk = self._desk()
        self._play_first(desk)
        self.assertAlmostEqual(desk._big_player.target, 51.0)

    def test_the_odd_title_steps_up_to_the_takt_of_the_round(self):
        """A single T30 Cha-Cha against five T31: the one comes up to 31."""
        desk = self._desk(entries=[_entry("CC", 1, 30)]
                          + [_entry("CC", n, 31) for n in range(2, 7)])
        self._play_first(desk)
        self.assertAlmostEqual(desk._big_player.target, 31.0)

    def test_the_takt_the_round_is_mostly_on_is_played_as_recorded(self):
        """The five T31 of that same round are not touched — moving five
        titles to meet one is the wrong way round."""
        desk = self._desk(entries=[_entry("CC", 1, 30)]
                          + [_entry("CC", n, 31) for n in range(2, 7)])
        self._play_nth(desk, 1)
        self.assertAlmostEqual(desk._big_player.target, 31.0)

    def test_a_round_of_two_takte_is_pitched_to_the_middle_of_them(self):
        """Two T24 Rumbas against three T25s: the smaller side moves half a
        takt to the 24.5 in the middle instead of a whole one to 25."""
        desk = self._desk(entries=[_entry("RB", n, 24) for n in range(1, 3)]
                          + [_entry("RB", n, 25) for n in range(3, 6)])
        self._play_first(desk)
        self.assertAlmostEqual(desk._big_player.target, 24.5)

    def test_the_bigger_side_of_that_round_comes_down_to_it_too(self):
        """A Rumba round is danced at ONE takt: the three T25s give the same
        half takt the two T24s do."""
        desk = self._desk(entries=[_entry("RB", n, 24) for n in range(1, 3)]
                          + [_entry("RB", n, 25) for n in range(3, 6)])
        self._play_nth(desk, 2)
        self.assertAlmostEqual(desk._big_player.target, 24.5)

    def test_only_the_round_under_the_same_strip_is_counted(self):
        """A running order with two Samba rounds on it. Their rows carry no
        round name — only the ─── strip does — and counting the whole deck
        made the Vorrunde's T50+T51+T51 a 50 round off the Finale's takte."""
        vor = [_entry("SA", 1, 50), _entry("SA", 2, 51), _entry("SA", 3, 51)]
        fin = [_entry("SA", n, 50) for n in range(4, 7)]
        desk = self._desk(
            entries=vor + fin,
            sections={**{str(e.path): "Vorrunde" for e in vor},
                      **{str(e.path): "Finale" for e in fin}})
        self._play_first(desk)
        self.assertAlmostEqual(desk._big_player.target, 51.0)

    def test_the_other_round_of_it_keeps_its_own_takt(self):
        """The Finale of that same order is recorded at T50 throughout, and
        the Vorrunde's T51s have no say in it."""
        vor = [_entry("SA", 1, 50), _entry("SA", 2, 51), _entry("SA", 3, 51)]
        fin = [_entry("SA", n, 50) for n in range(4, 7)]
        desk = self._desk(
            entries=vor + fin,
            sections={**{str(e.path): "Vorrunde" for e in vor},
                      **{str(e.path): "Finale" for e in fin}})
        self._play_nth(desk, 3)
        self.assertAlmostEqual(desk._big_player.target, 50.0)

    def test_no_title_is_pitched_more_than_a_whole_takt(self):
        """A T27 Slow Fox in a round danced at 28.5: it comes up to the 28 its
        band allows and stops there."""
        desk = self._desk(entries=[_entry("SF", 1, 27), _entry("SF", 2, 28),
                                   _entry("SF", 3, 29)])
        self._play_first(desk)
        self.assertAlmostEqual(desk._big_player.target, 28.0)

    def test_a_round_recorded_on_one_takt_is_danced_on_it(self):
        desk = self._desk(entries=[_entry("RB", n, 25) for n in range(1, 4)])
        self._play_first(desk)
        self.assertAlmostEqual(desk._big_player.target, 25.0)

    def test_a_dance_set_to_a_fixed_takt_is_pitched_there_instead(self):
        desk = self._desk(settings={"tso_band": {"QS": "lower"}})
        self._play_first(desk)
        self.assertAlmostEqual(desk._big_player.target, 50.0)

    def test_another_dance_being_set_leaves_this_one_alone(self):
        desk = self._desk(settings={"tso_band": {"RB": "lower"}})
        self._play_first(desk)
        self.assertAlmostEqual(desk._big_player.target, 51.0)

    def test_the_takt_is_known_before_anything_pitches_against_it(self):
        desk = self._desk()
        self._play_first(desk)
        self.assertLess(desk.log.index("takt"), desk.log.index("pitch"))

    def test_the_fader_is_zeroed_into_silence_too(self):
        """Same re-init, same gap — the reset belongs before play() as well."""
        desk = self._desk(tso=False)
        self._play_first(desk)
        self.assertLess(desk.log.index("fader-reset"), desk.log.index("play"))

    def test_the_rate_is_re_asserted_once_the_music_runs(self):
        """Qt may drop a rate set while the player was idle. The re-assert is
        free when it stuck — `apply_tempo` skips a no-op."""
        desk = self._desk()
        self.assertEqual(desk.log.count("rate"), 0)
        self._play_first(desk)
        self.assertGreater(desk.log.count("rate"), 1)
        self.assertGreater(desk.log[::-1].index("rate"), -1)
        self.assertLess(desk.log.index("play"),
                        len(desk.log) - 1 - desk.log[::-1].index("rate"))

    def test_a_pitch_that_worked_is_not_repeated(self):
        """The second try costs a gap — it is only for what the early one
        could not resolve."""
        desk = self._desk()
        self._play_first(desk)
        self.assertEqual(desk.pitch_calls, 1)

    def test_without_tso_nothing_is_pitched_at_all(self):
        desk = self._desk(tso=False)
        self._play_first(desk)
        self.assertEqual(desk.pitch_calls, 0)
        self.assertNotIn("pitch", desk.log)

    def test_a_cued_title_is_not_pitched(self):
        """Drag-drop cues a title without starting it — TSO waits for ⏯."""
        desk = self._desk()
        self.table._current_play_row = self.rows[0]
        desk._load_track(self.table._row_meta[self.rows[0]].entry.path,
                         start=False)
        self.assertEqual(desk.pitch_calls, 0)
        self.assertNotIn("play", desk.log)

    def test_a_second_try_follows_when_the_early_one_found_nothing(self):
        """No deck has claimed the row yet — then the pitch has to happen after
        the music started, gap and all, rather than not at all."""
        desk = self._desk()
        self.table._current_play_row = -1
        desk._load_track(self.table._row_meta[self.rows[0]].entry.path)
        self.assertEqual(desk.pitch_calls, 2)

    def test_it_reports_whether_it_pitched(self):
        """The two tries are told apart by that answer and nothing else."""
        desk = self._desk()
        self.table._current_play_row = -1
        self.assertFalse(desk._equalize_heat_tempo(auto=True))
        desk._playback.path = self.table._row_meta[self.rows[0]].entry.path
        self.table._current_play_row = self.rows[0]
        self.assertTrue(desk._equalize_heat_tempo(auto=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
