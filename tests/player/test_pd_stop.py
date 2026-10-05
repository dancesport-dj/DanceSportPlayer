"""Tests for the Paso Doble highlight stop policy (player.main_player._arm_pd_stop):
which detected mark the music is cut on, and what stands in when detection
couldn't pin a highlight down."""
import os
import tempfile
import unittest
from pathlib import Path
from player.playback_state import PlaybackState
from player.between_dances import BetweenDances


def _player_mixin():
    # Same lazy import as test_silence: player.main_player pulls in gui.dialogs,
    # which resolves the state files at import time.
    os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                          tempfile.mkdtemp(prefix="dp_pd_"))
    from player.main_player import PlayerControlMixin
    return PlayerControlMixin


class _FakePanel:
    def __init__(self, n=2, on=True, editing=False):
        self._n = n
        self._on = on
        self._editing = editing

    def pd_highlight_stop(self):
        return self._on

    def pd_highlight_n(self):
        return self._n

    def pd_editing(self):
        return self._editing


class _FakeWindow:
    """Just enough MainWindow for _arm_pd_stop."""

    PATH = Path(r"C:\music\paso.mp3")

    def __init__(self, highlights, dur=126.0, n=2, on=True, editing=False,
                 takt=0.0):
        self._pd_highlights = {str(self.PATH): list(highlights)}
        self._play_panel = _FakePanel(n, on, editing)
        self._cache = None            # no DB → never "manually learned"
        self._pd_stop_at = None
        self._dur = dur
        self._takt = takt             # 0 = unscanned tempo

    def _track_duration(self, _path):
        return self._dur

    def _track_takt(self, _path):
        return self._takt

    def _sync_big_player_limit(self):
        pass

    def arm(self):
        self._arm_pd_stop(self.PATH)
        return self._pd_stop_at


class PdStopTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        class Win(_FakeWindow, _player_mixin()):
            pass
        cls.Win = Win

    def test_clean_detection_stops_at_the_chosen_highlight(self):
        # Real output for "15 Espana Cani (PD 60)".
        w = self.Win([43.65, 78.69, 121.67], n=2)
        self.assertAlmostEqual(w.arm(), 78.69)

    def test_highlight_one_is_used_when_asked_for(self):
        w = self.Win([43.65, 78.69, 121.67], n=1)
        self.assertAlmostEqual(w.arm(), 43.65)

    def test_missing_highlight_two_falls_back_to_the_phrase_position(self):
        # Real output for "13 Spanish Gipsy Dance (PD 60)": h2 not found, so the
        # positional pick is the finale — which must never be highlight 2.
        w = self.Win([57.03, None, 125.92], n=2, takt=60)
        self.assertAlmostEqual(w.arm(), 78.0)

    def test_nothing_detected_yet_still_arms_a_stop(self):
        # Detection still running: the standard phrasing holds the fort.
        w = self.Win([], n=2)
        self.assertAlmostEqual(w.arm(), 78.0)   # takt unknown → the T60 position
        self.assertAlmostEqual(self.Win([], n=1).arm(), 45.0)

    def test_fallback_for_highlight_two_follows_the_tempo(self):
        # The choreography hits the same bar, so a slower PD reaches it later.
        for takt, want in ((58, 82.0), (59, 80.0), (60, 78.0), (62, 76.0)):
            with self.subTest(takt=takt):
                w = self.Win([], n=2, dur=180.0, takt=takt)
                self.assertAlmostEqual(w.arm(), want)

    def test_off_track_mark_is_re_anchored_to_a_mark_in_the_zone(self):
        # A detected mark inside the phrase zone beats the positional pick.
        w = self.Win([20.0, 74.0, 121.0], n=1)
        self.assertAlmostEqual(w.arm(), 45.0)   # h1 zone 35–55: 20 is no h1…
        w = self.Win([20.0, 47.0, 121.0], n=1)
        self.assertAlmostEqual(w.arm(), 47.0)   # …and 47 sits in the zone

    def test_a_mark_outside_its_zone_loses_to_the_phrase_position(self):
        # Real output for "13 Spanish Gipsy Dance (PD 60)": 57 s is 12 s late
        # for a highlight 1 — the detector took a different crash for the rung.
        # The choreography lands on a fixed bar, so the phrase position is the
        # better bet than a mark that measurably isn't one.
        w = self.Win([57.03, 78.0, 125.92], n=1)
        self.assertAlmostEqual(w.arm(), 45.0)

    def test_a_late_highlight_two_falls_back_instead_of_overrunning(self):
        # Real output for "15-Boris Myagkov Big Band – El Bailador": h2 at 1:35
        # is 17 s past the phrase — stopping there overruns the heat.
        w = self.Win([44.0, 95.0, 122.0], dur=127.6, n=2)
        self.assertAlmostEqual(w.arm(), 78.0)

    def test_an_early_highlight_one_falls_back_too(self):
        # Real output for "12 Espana Cani (PD 60) 1": 34.7 s, ~9 s early — the
        # same edit detected cleanly in its siblings sits at 43.6.
        w = self.Win([34.7, 73.9, 121.7], dur=126.8, n=1)
        self.assertAlmostEqual(w.arm(), 45.0)

    def test_the_zone_follows_the_tempo(self):
        # 82 s is highlight 2 at T58 — in the zone there, 4 s past it at T60.
        self.assertAlmostEqual(self.Win([44.0, 82.0, 121.0], takt=58).arm(),
                               82.0)
        self.assertAlmostEqual(self.Win([44.0, 90.0, 121.0], takt=60).arm(),
                               78.0)

    def test_short_track_never_gets_a_fallback_past_its_end(self):
        # A 46 s snippet has no room for a 0:45 phrase stop — nothing invented.
        w = self.Win([], dur=46.0, n=2)
        self.assertIsNone(w.arm())

    def test_short_track_stops_at_highlight_one_instead(self):
        # Under the highlight-2 zone the request drops to highlight 1, and the
        # 44 s mark in the zone wins over the positional 28 s pick.
        w = self.Win([28.0, 44.0, 58.0], dur=59.0, n=2)
        self.assertAlmostEqual(w.arm(), 44.0)

    def test_finale_highlight_plays_the_track_out(self):
        # The 70 s crash IS the 80 s song's ending — don't clip the last seconds
        # (and the fallback can't stand in either, it lands past the end).
        w = self.Win([44.0, 70.0], dur=80.0, n=2)
        self.assertIsNone(w.arm())

    def test_disabled_option_arms_nothing(self):
        w = self.Win([43.65, 78.69, 121.67], n=2, on=False)
        self.assertIsNone(w.arm())

    def test_edit_mode_suspends_the_stop(self):
        # ✏️ Hand-marking: the title must play through, otherwise the mark just
        # set becomes the stop and the song ends the moment it's made.
        w = self.Win([43.65, 78.69, 121.67], n=2, editing=True)
        self.assertIsNone(w.arm())


class PdStopAtTest(unittest.TestCase):
    """The stop policy on its own — no window, no panel, no cache."""

    @classmethod
    def setUpClass(cls):
        from player.pd_stop import pd_stop_at
        cls.stop = staticmethod(pd_stop_at)

    def test_a_learned_mark_is_the_exact_stop(self):
        # Hand-set: no zone, no finale rule — the mark IS where it ends.
        self.assertAlmostEqual(
            self.stop([40.0, 95.0], 2, manual=True, duration=100.0, takt=60),
            95.0)

    def test_fewer_learned_marks_than_asked_stop_at_the_last(self):
        self.assertAlmostEqual(
            self.stop([40.0], 2, manual=True, duration=126.0, takt=60), 40.0)

    def test_no_learned_mark_plays_to_the_end(self):
        self.assertIsNone(
            self.stop([None], 1, manual=True, duration=126.0, takt=60))

    def test_auto_marks_go_through_the_zone(self):
        self.assertAlmostEqual(
            self.stop([57.03, 78.0, 125.92], 1, manual=False, duration=126.0,
                      takt=60), 45.0)


class _TickPlayer:
    """Just enough media player for the fade tick."""

    def __init__(self, pos_ms):
        from PySide6.QtMultimedia import QMediaPlayer
        self._state = QMediaPlayer.PlaybackState.PlayingState
        self._pos = pos_ms

    def playbackState(self):
        return self._state

    def position(self):
        return self._pos

    def playbackRate(self):
        return 1.0


class _TickPanel(_FakePanel):
    def __init__(self, on):
        super().__init__(on=on)

    def timed_enabled(self):
        return True

    def play_secs(self):
        return 100

    def fade_secs(self):
        return 2.0

    def play_set(self):
        return {"secs": 100, "fade": 2.0}


class _TickDesk:
    """A desk playing a Paso Doble, with everything the fade tick touches
    stubbed out — the media backend, the pause music and the timed end all
    have tests of their own."""

    def __init__(self, on, pos_ms):
        from player.mix import OutputMix
        self._playback = PlaybackState()
        self._playback.dance = "PD"
        self._playback.path = Path(r"C:\music\paso.mp3")
        self._play_panel = _TickPanel(on)
        self._all_tables = ()    # no list: the panel's values are the ones
        self._player = _TickPlayer(pos_ms)
        self._mix = OutputMix()
        self._cache = None
        self._pd_stop_at = None
        self._pd_worker = None
        self._between = BetweenDances()
        self._between.pending = None
        self._fade_now_end = None
        self._playback.offset_ms = 0
        self._played_marked = True
        self._countdown = ""
        self._ended = []

    def _is_playing_mode(self):
        return True

    def _maybe_skip_silence(self):
        return False

    def _apply_volume(self):
        pass

    def _set_countdown(self, text):
        self._countdown = text

    def _on_timed_end(self, why):
        self._ended.append(why)


class PdWithoutTheStopTest(unittest.TestCase):
    """🐂 off = an ordinary title.

    The highlight stop is the only thing that ends a Paso Doble musically;
    without it the dance would run to the end of the file while every other
    title is cut at the play length. So with the switch off the fade tick has
    to treat it like any other dance: ramp down and cut."""

    def setUp(self):
        class Desk(_TickDesk, _player_mixin()):
            pass
        self.Desk = Desk

    def test_the_fade_ramps_a_paso_doble_down_like_any_other_title(self):
        d = self.Desk(on=False, pos_ms=99_000)      # 1 s of a 100 s cut left
        d._on_play_tick()
        self.assertAlmostEqual(d._mix.fade, 0.5)
        self.assertEqual(d._countdown, "⏳  0:01")

    def test_the_play_length_cuts_it(self):
        d = self.Desk(on=False, pos_ms=101_000)
        d._on_play_tick()
        self.assertEqual(d._ended, ["play length reached"])

    def test_under_the_stop_it_is_still_never_faded(self):
        d = self.Desk(on=True, pos_ms=99_000)
        d._on_play_tick()
        self.assertEqual(d._mix.fade, 1.0)
        self.assertEqual(d._ended, [])
        self.assertEqual(d._countdown, "🐂  plays to the end")


class PdH2PositionTest(unittest.TestCase):
    """The tempo → highlight-2 position curve behind the fallback."""

    @classmethod
    def setUpClass(cls):
        from player.pd_stop import pd_h2_position
        cls.pos = staticmethod(pd_h2_position)

    def test_the_measured_tempos_are_honoured_verbatim(self):
        self.assertAlmostEqual(self.pos(58), 82.0)
        self.assertAlmostEqual(self.pos(59), 80.0)
        self.assertAlmostEqual(self.pos(60), 78.0)
        self.assertAlmostEqual(self.pos(62), 76.0)

    def test_between_two_measured_tempos_it_interpolates(self):
        self.assertAlmostEqual(self.pos(58.5), 81.0)
        self.assertAlmostEqual(self.pos(61), 77.0)

    def test_outside_the_table_the_same_bar_scales_with_the_tempo(self):
        # 82 s of music at T58 is 79.3 bars — reached sooner at 64, later at 54.
        self.assertAlmostEqual(self.pos(64), 76.0 * 62 / 64)
        self.assertAlmostEqual(self.pos(54), 82.0 * 58 / 54)
        self.assertGreater(self.pos(54), self.pos(58))
        self.assertLess(self.pos(64), self.pos(62))

    def test_an_unknown_tempo_gets_the_default_position(self):
        for takt in (0, 0.0, None, -1):
            with self.subTest(takt=takt):
                self.assertAlmostEqual(self.pos(takt), 78.0)


class PdMarkMergeTest(unittest.TestCase):
    """The 🎯 mark ruler: same rules as the iOS editor."""

    @classmethod
    def setUpClass(cls):
        # staticmethod(): a bare function on the class would swallow self.
        cls.merge = staticmethod(_player_mixin()._merge_pd_mark)

    def test_first_mark_is_kept(self):
        self.assertEqual(self.merge([], 42.0), [42.0])

    def test_a_nearby_tap_moves_the_mark_instead_of_stacking(self):
        # Within _PD_MARK_SNAP (3 s) the second tap is a correction.
        self.assertEqual(self.merge([44.0], 45.5), [45.5])

    def test_a_distant_tap_adds_a_mark_and_stays_sorted(self):
        self.assertEqual(self.merge([78.0], 44.0), [44.0, 78.0])

    def test_a_fourth_mark_replaces_the_nearest_one(self):
        self.assertEqual(self.merge([44.0, 78.0, 121.0], 90.0),
                         [44.0, 90.0, 121.0])

    def test_three_marks_is_the_ceiling(self):
        self.assertEqual(len(self.merge([10.0, 50.0, 90.0], 130.0)), 3)


if __name__ == "__main__":
    unittest.main()
