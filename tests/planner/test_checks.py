"""Tests for the per-track Check-Music rules in planner.checks: tempo
mismatch (⚡ measured vs filename label), TSO takt window (🐢/🐇), play
length (⏱ short / opt-in ⏳ long, minus in-file silence) and the takt
resolution (entry_takt). The round-structure rules already have their own
suite (test_heat_tempo); the ImportMixin wrapper that feeds settings into
these rules gets one integration check at the end."""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from planner.checks import entry_takt, is_final_round, track_issues
from planner.models import MusicEntry

# The GUI's defaults (dancesport_gui) — the rules take them as parameters.
_BEATS_PER_BAR = {"LW": 3, "TG": 2, "WW": 3, "SF": 4, "QS": 4}
_TEMPO_RATIOS = (1.0, 2.0, 0.5, 3.0, 1 / 3, 4.0, 0.25, 1.5, 2 / 3)


def _e(dance, takt=None, measured=None, duration=0):
    feats = SimpleNamespace(bpm=float(measured)) if measured else None
    return MusicEntry(path=Path(rf"C:\music\{dance}{takt or measured}.mp3"),
                      title=f"{dance} {takt}", dance=dance, bpm=takt,
                      duration=duration, features=feats)


def _issues(e, **kw):
    args = dict(beats_per_bar=_BEATS_PER_BAR, tempo_ratios=_TEMPO_RATIOS,
                tempo_pct=10.0, min_secs=105, max_secs=240)
    args.update(kw)
    return track_issues(e, **args)


class EntryTaktTest(unittest.TestCase):

    def test_filename_label_wins(self):
        self.assertEqual(entry_takt(_e("WW", 59, measured=200.0),
                                    _BEATS_PER_BAR), 59)

    def test_measured_fallback_divides_by_meter(self):
        # 180 beats/min in a 3/4 Wiener Walzer → T60.
        self.assertEqual(entry_takt(_e("WW", None, measured=180.0),
                                    _BEATS_PER_BAR), 60)

    def test_unknown_is_zero(self):
        self.assertEqual(entry_takt(_e("WW"), _BEATS_PER_BAR), 0)


class TempoMismatchTest(unittest.TestCase):

    def test_measured_backs_up_the_label(self):
        # WW label T59 → 177 beats/min expected; 175 measured is within 10%.
        self.assertEqual(_issues(_e("WW", 59, measured=175.0, duration=110)), [])

    def test_mismatch_is_flagged(self):
        # 200 measured vs 177 expected → ~13% off even after ratio excuses.
        issues = _issues(_e("WW", 59, measured=200.0, duration=110))
        self.assertEqual(len(issues), 1)
        self.assertIn("⚡ Tempo", issues[0])

    def test_octave_slip_is_excused(self):
        # The detector doubled the tempo (354 = 2 × 177) — not a real mismatch.
        self.assertEqual(_issues(_e("WW", 59, measured=354.0, duration=110)), [])

    def test_no_label_no_tempo_check(self):
        # QS measured 204 beats/min → T51, inside TSO — and no ⚡ without a label.
        self.assertEqual(_issues(_e("QS", None, measured=204.0, duration=110)), [])


class TsoRangeTest(unittest.TestCase):

    def test_too_slow(self):
        issues = _issues(_e("LW", 26, duration=110))   # TSO 28-30
        self.assertEqual(issues, ["🐢 Too slow: T26 (label), TSO 28-30"])

    def test_too_fast(self):
        issues = _issues(_e("WW", 62, duration=110))   # TSO 58-60
        self.assertEqual(issues, ["🐇 Too fast: T62 (label), TSO 58-60"])

    def test_measured_source_is_named(self):
        # No label; QS measured 224 beats/min → T56 > TSO 50-52, source "measured".
        issues = _issues(_e("QS", None, measured=224.0, duration=110))
        self.assertEqual(issues, ["🐇 Too fast: T56 (measured), TSO 50-52"])

    def test_unknown_dance_has_no_window(self):
        self.assertEqual(_issues(_e("", 62, duration=110)), [])


class PlayLengthTest(unittest.TestCase):

    def test_short_track_is_flagged(self):
        issues = _issues(_e("WW", 59, duration=100))
        self.assertEqual(issues, ["⏱ Short: 1:40 (≤ 1:45 play length)"])

    def test_silence_shrinks_the_real_play_length(self):
        # 2:30 on disk minus 50 s of stillness → 1:40 real play, under 1:45.
        issues = _issues(_e("WW", 59, duration=150), silence_secs=50.0)
        self.assertEqual(issues, ["⏱ Short: real play 1:40 — 2:30 file minus "
                                  "50s silence (≤ 1:45)"])

    def test_long_is_opt_in(self):
        e = _e("WW", 59, duration=300)
        self.assertEqual(_issues(e), [])
        self.assertEqual(_issues(e, check_long=True),
                         ["⏳ Long: 5:00 (> 4:00)"])

    def test_thresholds_are_parameters(self):
        # A 3:00 track is short when the minimum is raised to 3:20.
        issues = _issues(_e("WW", 59, duration=180), min_secs=200)
        self.assertEqual(issues, ["⏱ Short: 3:00 (≤ 3:20 play length)"])

    def test_unknown_duration_is_not_short(self):
        self.assertEqual(_issues(_e("WW", 59, duration=0)), [])

    def test_a_short_paso_doble_is_only_a_problem_in_the_final(self):
        # PD is played to the first highlight in the early rounds — 1:20 is a
        # normal length there, and only a final needs the whole España cañí.
        pd = _e("PD", 60, duration=80)
        self.assertEqual(_issues(pd), [])
        self.assertEqual(_issues(pd, in_final=True),
                         ["⏱ Short: 1:20 (≤ 1:45 play length)"])

    def test_the_other_dances_are_short_wherever_they_stand(self):
        self.assertEqual(len(_issues(_e("WW", 59, duration=80))), 1)

    def test_a_long_paso_doble_is_still_checked(self):
        # Only the SHORT rule steps aside; ⏳ Long is untouched by it.
        self.assertEqual(_issues(_e("PD", 60, duration=300), check_long=True),
                         ["⏳ Long: 5:00 (> 4:00)"])


class FinalRoundTest(unittest.TestCase):
    """Which slot counts as the final — the PD length rule hangs off this."""

    def test_the_tier_says_so(self):
        self.assertTrue(is_final_round("Runde 4", "final"))
        self.assertFalse(is_final_round("Runde 4", "semi"))

    def test_an_imported_playlist_only_has_the_name(self):
        # A dropped .m3u carries round names, never a tier.
        self.assertTrue(is_final_round("Finale"))
        self.assertTrue(is_final_round("2. Endrunde"))
        self.assertTrue(is_final_round("FINAL"))

    def test_a_semifinal_is_not_the_final(self):
        # Both languages spell it with "final" in the middle of the word.
        self.assertFalse(is_final_round("Halbfinale"))
        self.assertFalse(is_final_round("Semifinal"))
        self.assertFalse(is_final_round("Viertelfinale"))

    def test_anything_else_is_not_the_final(self):
        self.assertFalse(is_final_round("Vorrunde"))
        self.assertFalse(is_final_round("Zwischenrunde", ""))
        self.assertFalse(is_final_round())


class HissTest(unittest.TestCase):
    """🔇 background noise: how quiet the track ever gets (measured by the
    caller, see test_noise_floor)."""

    def test_a_hissy_floor_is_flagged(self):
        issues = _issues(_e("WW", 59, duration=150), noise_db=-37.0)
        self.assertEqual(issues, ["🔇 Hiss: never quieter than -37 dB "
                                  "(> -50 dB)"])

    def test_a_clean_track_is_quiet_enough(self):
        self.assertEqual(_issues(_e("WW", 59, duration=150), noise_db=-78.0), [])

    def test_digital_silence_is_never_hiss(self):
        self.assertEqual(
            _issues(_e("WW", 59, duration=150), noise_db=float("-inf")), [])

    def test_unmeasured_is_no_issue(self):
        """The check is opt-in — without a measurement nothing is claimed."""
        self.assertEqual(_issues(_e("WW", 59, duration=150), noise_db=None), [])

    def test_threshold_is_a_parameter(self):
        e = _e("WW", 59, duration=150)
        self.assertEqual(_issues(e, noise_db=-60.0), [])
        self.assertEqual(len(_issues(e, noise_db=-60.0, noise_max_db=-70.0)), 1)


class MixinWrapperTest(unittest.TestCase):
    """The ImportMixin wrapper feeds Settings → 🎵 Checks thresholds and the
    silence cache into the pure rules — one end-to-end check."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                              tempfile.mkdtemp(prefix="dp_checks_"))
        from gui.main_import import ImportMixin

        class Win(ImportMixin):
            _BEATS_PER_BAR = _BEATS_PER_BAR
            _TEMPO_RATIOS = _TEMPO_RATIOS
            _MIN_PLAY_SECS = 105
            _MAX_PLAY_SECS = 240
            _NOISE_FLOOR_DB = -50.0
            _cache = None
            _settings = {"check_min_play_secs": 200}

        cls.win = Win()

    def test_settings_thresholds_reach_the_rules(self):
        # 3:00 is fine by the default 1:45 minimum but short at the user's 3:20.
        issues = self.win._track_issues(_e("WW", 59, duration=180))
        self.assertEqual(issues, ["⏱ Short: 3:00 (≤ 3:20 play length)"])


if __name__ == "__main__":
    unittest.main()
