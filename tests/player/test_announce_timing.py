#!/usr/bin/env python3
"""Tests for WHEN the next dance is called into the pause.

Run:  py -m unittest tests.player.test_announce_timing -v

The announcement used to start a fixed 5 s before the pause ended, but it is
assembled from clips whose total varies — "Nächster Tanz: West Coast Swing,
Heat 5" runs over six seconds and the music came in on the last word. So the
lead is measured from the clips that will actually play, and the advance is
held back while the voice is still going, with a beat of quiet after it.
"""

import tempfile
import time
import unittest
from pathlib import Path

from planner import i18n, terms
from player import announce
from player.announce import announce_secs, clip_secs
from player.main_pause import _ANNOUNCE_LEAD, _ANNOUNCE_TAIL, PauseMusicMixin
from gui.running_order import Row, RunningOrder
from player.between_dances import BetweenDances


def _measure(path: Path, start_ms: int, end_ms: int):
    """Pretend the ffmpeg trim probe measured this clip."""
    announce._BOUNDS[str(path)] = (start_ms, end_ms)


class _ClipRoot(unittest.TestCase):
    """A recorded voice made of files whose length the test decides."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dp_lead_"))
        for gender in ("female", "male"):
            folder = self.root / "german" / gender
            folder.mkdir(parents=True)
            for name in ("next_dance", "LW", "WCS", "heat", "1", "5"):
                (folder / f"{name}.mp3").write_bytes(b"")
        self._real_dir = announce._CLIP_DIR
        announce._CLIP_DIR = self.root
        self.addCleanup(setattr, announce, "_CLIP_DIR", self._real_dir)
        self._real_bounds = dict(announce._BOUNDS)
        self.addCleanup(self._restore_bounds)
        # The clips are German; an English screen would ask for English ones.
        real_lang, real_terms = i18n.active_language(), terms._english_terms
        self.addCleanup(i18n.set_active, real_lang)
        self.addCleanup(setattr, terms, "_english_terms", real_terms)
        self.addCleanup(setattr, terms, "_german_kept", terms._german_kept)
        i18n.set_active("de")
        terms.apply_settings({})

    def _restore_bounds(self):
        announce._BOUNDS.clear()
        announce._BOUNDS.update(self._real_bounds)

    def clip(self, gender, name):
        return self.root / "german" / gender / f"{name}.mp3"


class ClipSecsTest(_ClipRoot):
    """How long the queued fragments take to speak."""

    def test_the_measured_words_and_the_breaths_between_them(self):
        # Two clips of 1.0 s each, plus the one gap between them.
        for name in ("next_dance", "LW"):
            _measure(self.clip("female", name), 200, 1200)
        self.assertAlmostEqual(
            clip_secs([self.clip("female", "next_dance"),
                       self.clip("female", "LW")]),
            2.0 + announce._CLIP_GAP_MS / 1000.0)

    def test_only_the_spoken_span_counts_not_the_studio_silence(self):
        # The clip is 2 s long on disk but the word is the middle second —
        # playback seeks past the head and cuts at the tail.
        _measure(self.clip("female", "LW"), 500, 1500)
        self.assertAlmostEqual(clip_secs([self.clip("female", "LW")]), 1.0)

    def test_a_single_fragment_has_no_gap_to_pay_for(self):
        _measure(self.clip("female", "LW"), 0, 1000)
        self.assertAlmostEqual(clip_secs([self.clip("female", "LW")]), 1.0)

    def test_a_clip_nobody_measured_counts_as_the_longest_one_recorded(self):
        """The first announcement of a session plays its clips whole, and on a
        machine without ffmpeg every one of them does. Guessing short would put
        the music back over the voice — the very thing the lead is for."""
        self.assertAlmostEqual(clip_secs([self.clip("female", "LW")]),
                               announce._CLIP_ASSUMED_MS / 1000.0)

    def test_nothing_queued_takes_no_time(self):
        self.assertEqual(clip_secs([]), 0.0)


class AnnounceSecsTest(_ClipRoot):
    """The length of the whole announcement, as far as it can be known."""

    def test_the_heat_makes_the_announcement_longer(self):
        for name in ("next_dance", "WCS", "heat", "5"):
            _measure(self.clip("female", name), 0, 1000)
            _measure(self.clip("male", name), 0, 1000)
        plain = announce_secs("WCS", root=self.root)
        with_heat = announce_secs("WCS", heat=5, root=self.root)
        self.assertAlmostEqual(with_heat - plain,
                               2.0 + 2 * announce._CLIP_GAP_MS / 1000.0)

    def test_the_longer_voice_decides(self):
        """A mixed evening only picks the voice when it speaks, so the lead has
        to cover either of them."""
        for name in ("next_dance", "LW"):
            _measure(self.clip("female", name), 0, 800)
            _measure(self.clip("male", name), 0, 1400)
        self.assertAlmostEqual(announce_secs("LW", root=self.root),
                               2.8 + announce._CLIP_GAP_MS / 1000.0)

    def test_over_the_music_there_is_no_lead_in_to_pay_for(self):
        for gender in ("female", "male"):
            for name in ("next_dance", "LW"):
                _measure(self.clip(gender, name), 0, 1000)
        self.assertAlmostEqual(announce_secs("LW", now=True, root=self.root), 1.0)

    def test_the_takt_hands_it_to_the_synthesiser_whose_length_is_unknown(self):
        # No clip exists for a tempo, so the whole sentence is read by Windows
        # and nothing here can time it. 0 = "don't know", not "instant".
        for name in ("next_dance", "LW"):
            _measure(self.clip("female", name), 0, 1000)
        self.assertEqual(announce_secs("LW", takt=29, root=self.root), 0.0)

    def test_a_dance_never_recorded_is_not_ours_to_time_either(self):
        self.assertEqual(announce_secs("QS", root=self.root), 0.0)

    def test_no_voice_installed_at_all(self):
        self.assertEqual(announce_secs("LW", root=self.root / "nope"), 0.0)


class _Panel:
    def __init__(self, takt=False, heat=True):
        self._takt = takt
        self._heat = heat

    def announce_takt(self):
        return self._takt

    def announce_heat(self):
        return self._heat


class _Entry:
    def __init__(self, bpm=None):
        self.bpm = bpm
        self.path = "x.mp3"   # what the armed advances below name


class _Deck:
    def __init__(self, dance, bpm=None):
        self._row_meta = RunningOrder([Row(dance=dance, entry=_Entry(bpm))])
        self._row_round_hdr = {}
        self._current_play_row = -1


class AnnounceLeadTest(_ClipRoot):
    """How far before the end of the pause the voice starts."""

    def setUp(self):
        super().setUp()
        self.win = PauseMusicMixin()
        self.win._play_panel = _Panel()
        self.win._between = BetweenDances()
        self.win._between.pending = (_Deck("LW"), 0, "x.mp3")

    def test_a_short_call_keeps_the_settled_five_seconds(self):
        """Late enough that the couples are already on the floor — that timing
        was chosen, and a two-second call must not drag it forward."""
        for gender in ("female", "male"):
            for name in ("next_dance", "LW", "heat", "1"):
                _measure(self.clip(gender, name), 0, 500)
        self.assertLess(announce_secs("LW", heat=1, root=self.root),
                        _ANNOUNCE_LEAD)
        self.assertAlmostEqual(self.win._announce_lead(), _ANNOUNCE_LEAD)

    def test_a_long_call_starts_early_enough_to_finish(self):
        # 4 × 1.5 s of words: the announcement outlasts the old fixed lead.
        self.win._between.pending = (_Deck("WCS"), 0, "x.mp3")
        for gender in ("female", "male"):
            for name in ("next_dance", "WCS", "heat", "1"):
                _measure(self.clip(gender, name), 0, 1500)
        spoken = announce_secs("WCS", heat=1, root=self.root)
        self.assertGreater(spoken, _ANNOUNCE_LEAD)
        self.assertAlmostEqual(self.win._announce_lead(), spoken + _ANNOUNCE_TAIL)

    def test_the_hall_gets_a_beat_of_quiet_before_the_music(self):
        self.win._between.pending = (_Deck("WCS"), 0, "x.mp3")
        for gender in ("female", "male"):
            for name in ("next_dance", "WCS", "heat", "1"):
                _measure(self.clip(gender, name), 0, 1500)
        self.assertGreaterEqual(
            self.win._announce_lead() - announce_secs("WCS", heat=1,
                                                      root=self.root),
            _ANNOUNCE_TAIL)

    def test_an_unmeasurable_announcement_falls_back_to_the_fixed_lead(self):
        # With the takt asked for, Windows reads the whole sentence and nothing
        # here can time it — the settled lead is all there is to go on.
        self.win._play_panel = _Panel(takt=True)
        self.win._between.pending = (_Deck("LW", bpm=29), 0, "x.mp3")
        self.assertAlmostEqual(self.win._announce_lead(), _ANNOUNCE_LEAD)

    def test_nothing_queued_still_answers(self):
        self.win._between.pending = None
        self.assertAlmostEqual(self.win._announce_lead(), _ANNOUNCE_LEAD)


class _Announcer:
    def __init__(self, speaking=False):
        self.speaking = speaking


class AnnounceHoldTest(unittest.TestCase):
    """The pause is over but the voice is not — the measurement behind the
    estimate. A clip that ran long, or a synthesiser nobody can time, must not
    have the next title come in over its last word."""

    def setUp(self):
        self.win = PauseMusicMixin()
        self.win._between = BetweenDances()
        self.win._between.pending = (_Deck("LW"), 0, "x.mp3")
        self.win._announcer = _Announcer()
        self.win._between.quiet_until = 0.0
        self.win._countdown = ""
        self.win._set_countdown = lambda text: setattr(self.win, "_countdown",
                                                       text)

    def test_the_music_waits_while_the_voice_is_still_going(self):
        self.win._announcer.speaking = True
        self.assertTrue(self.win._hold_for_announcement())

    def test_the_hall_says_what_it_is_waiting_for(self):
        self.win._announcer.speaking = True
        self.win._hold_for_announcement()
        self.assertIn("🔈", self.win._countdown)

    def test_it_still_waits_a_beat_after_the_last_word(self):
        self.win._announcer.speaking = True
        self.win._hold_for_announcement()
        self.win._announcer.speaking = False      # the voice stopped just now
        self.assertTrue(self.win._hold_for_announcement())

    def test_and_then_lets_the_music_in(self):
        self.win._announcer.speaking = True
        self.win._hold_for_announcement()
        self.win._announcer.speaking = False
        self.win._between.quiet_until = time.monotonic() - 0.01
        self.assertFalse(self.win._hold_for_announcement())

    def test_a_silent_announcer_at_the_deadline_holds_nothing(self):
        self.assertFalse(self.win._hold_for_announcement())

    def test_no_pause_running_means_nothing_to_hold(self):
        self.win._between.pending = None
        self.win._announcer.speaking = True
        self.assertFalse(self.win._hold_for_announcement())


if __name__ == "__main__":
    unittest.main()
