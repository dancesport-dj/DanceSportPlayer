"""🎵 Check-Music findings in German.

Run:  py -m unittest tests.planner.test_checks_i18n -v

The per-track issues and the round-structure warnings are assembled from
numbers, names and takte, so the Qt text hook never finds them in the
catalog: a German floor read "Too slow: T27 (label), TSO 28-30" in the report,
the row tooltips and the drop toasts. Each message goes through i18n.t with
placeholders; the leading emoji stays, because the report ranks by it.
"""
import unittest
from pathlib import Path
from types import SimpleNamespace

from planner import i18n
from planner.checks import grid_structure_findings, track_issues
from planner.models import MusicEntry

_BEATS_PER_BAR = {"LW": 3, "TG": 2, "WW": 3, "SF": 4, "QS": 4}
_TEMPO_RATIOS = (1.0, 2.0, 0.5, 3.0, 1 / 3, 4.0, 0.25, 1.5, 2 / 3)


def _e(dance, takt=None, measured=None, duration=0, title=None):
    feats = SimpleNamespace(bpm=float(measured)) if measured else None
    return MusicEntry(path=Path(rf"C:\music\{dance}{takt or measured}.mp3"),
                      title=title or f"{dance} {takt}", dance=dance, bpm=takt,
                      duration=duration, features=feats)


def _issues(e, **kw):
    args = dict(beats_per_bar=_BEATS_PER_BAR, tempo_ratios=_TEMPO_RATIOS,
                tempo_pct=10.0, min_secs=105, max_secs=240)
    args.update(kw)
    return track_issues(e, **args)


def _text(findings):
    return ["".join(t for t, _ in f) for f in findings]


class GermanTrackIssuesTest(unittest.TestCase):

    def setUp(self):
        i18n.set_active("de")
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)

    def test_too_slow_and_short(self):
        issues = _issues(_e("WW", 55, duration=90))
        self.assertEqual(issues, ["🐢 Zu langsam: T55 (Label), TSO 58-60",
                                  "⏱ Kurz: 1:30 (≤ 1:45 Spiellänge)"])

    def test_too_fast_from_the_measured_tempo(self):
        issues = _issues(_e("WW", None, measured=195.0, duration=120))
        self.assertEqual(issues, ["🐇 Zu schnell: T65 (gemessen), TSO 58-60"])

    def test_tempo_mismatch(self):
        issues = _issues(_e("WW", 59, measured=200.0, duration=110))
        self.assertEqual(len(issues), 1)
        self.assertTrue(issues[0].startswith("⚡ Tempo: gemessen ~200"), issues[0])

    def test_short_after_silence(self):
        issues = _issues(_e("WW", 59, duration=110), silence_secs=10.0)
        self.assertEqual(issues, ["⏱ Kurz: echte Spielzeit 1:40 — 1:50 Datei "
                                  "minus 10 s Stille (≤ 1:45)"])

    def test_long_and_hiss(self):
        issues = _issues(_e("WW", 59, duration=300), check_long=True,
                         noise_db=-40.0)
        self.assertEqual(issues, ["⏳ Lang: 5:00 (> 4:00)",
                                  "🔇 Rauschen: nie leiser als -40 dB (> -50 dB)"])


class GermanGridFindingsTest(unittest.TestCase):

    def setUp(self):
        i18n.set_active("de")
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)

    def test_uneven_dance_counts(self):
        pl = {"Vorrunde": [[_e("LW", 29), _e("WW", 58)],
                           [_e("LW", 29), None]]}
        self.assertEqual(_text(grid_structure_findings(pl, ["LW", "WW"], _BEATS_PER_BAR)),
                         ["„Vorrunde“: ungleiche Tanzanzahl — Wiener Walzer 1/2 "
                          "(fehlt in Gruppe 2)"])

    def test_taper(self):
        pl = {"Vorrunde": [[_e("WW", 59)]] * 3,
              "Semi": [[_e("WW", 59)]] * 3,
              "Endrunde": [[_e("WW", 59)]] * 2}
        self.assertEqual(_text(grid_structure_findings(pl, ["WW"], _BEATS_PER_BAR)),
                         ["Finale „Endrunde“ hat 2 Gruppen, erwartet 1.",
                          "Semifinale „Semi“ hat 3 Gruppen, erwartet 2."])

    def test_heat_tempo_spread(self):
        pl = {"Vorrunde": [[_e("WW", 58, title="A")], [_e("WW", 60, title="B")]]}
        self.assertEqual(_text(grid_structure_findings(pl, ["WW"], _BEATS_PER_BAR)),
                         ["„Vorrunde“: Die Wiener Walzer-Gruppen weichen um 2 Takte ab "
                          "(erlaubt: 1) — Gruppe 1: T58 „A“, Gruppe 2: T60 „B“"])


class EnglishUnchangedTest(unittest.TestCase):
    """The English texts are the catalog keys — they must read as before."""

    def test_track_issue(self):
        self.assertEqual(_issues(_e("WW", 55, duration=90)),
                         ["🐢 Too slow: T55 (label), TSO 58-60",
                          "⏱ Short: 1:30 (≤ 1:45 play length)"])

    def test_heat_tempo_spread(self):
        pl = {"Vorrunde": [[_e("WW", 58, title="A")], [_e("WW", 60, title="B")]]}
        self.assertEqual(_text(grid_structure_findings(pl, ["WW"], _BEATS_PER_BAR)),
                         ["“Vorrunde”: Wiener Walzer heats differ by 2 takte (allowed: 1) — "
                          "heat 1: T58 “A”, heat 2: T60 “B”"])


if __name__ == "__main__":
    unittest.main()
