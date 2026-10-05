"""The ⚡ Generate hint line in German.

Run:  py -m unittest tests.planner.test_hints_i18n -v

The hints are joined into one label (`_show_hints`), so the Qt text hook only
ever sees the whole line, which is never a catalog key: a German floor read
"✦ 3/4 songs are fresh (75% new)." under every generated playlist. Each hint
goes through i18n.t with placeholders where it is built.
"""
import unittest
from pathlib import Path

from planner import i18n
from planner.models import MusicEntry, RoundConfig
from planner.suggester import generate_hints, source_gap_hint


class _Lib:
    def __init__(self, entries):
        self.entries = entries

    def by_dance(self, d):
        return [e for e in self.entries if e.dance == d]


def _e(title, popularity, bpm=59):
    return MusicEntry(path=Path(rf"C:\music\{title}.mp3"), title=title, dance="WW",
                      bpm=bpm, popularity=popularity)


class GermanHintsTest(unittest.TestCase):

    def setUp(self):
        i18n.set_active("de")
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)

    def test_library_and_freshness_hints(self):
        songs = [_e("A", 1, bpm=55), _e("B", 0, bpm=55), _e("C", 0, bpm=55)]
        rounds = [RoundConfig(name="Endrunde", heats=2, tier="final")]
        hints = generate_hints(_Lib(songs), {"Endrunde": [songs[:2], songs[2:]]},
                               ["WW"], "S", rounds)
        self.assertEqual(hints, [
            "⚠ Wiener Walzer: nur 1 bewährte(r) Titel — Finals brauchen 2; "
            "rechne mit neuen Lückenfüllern.",
            "♪ Wiener Walzer: kein Titel nahe am idealen Tempo von 59 bpm.",
            "✦ 2/3 Titel sind neu (66 %)."])

    def test_source_gap(self):
        pl = {"Runde 1": [[_e("A", 1), None]]}
        self.assertEqual(
            source_gap_hint(pl, ["WW", "LW"], "📂 party.m3u"),
            "⚠ Aus 📂 party.m3u ließen sich 1 von 2 Slots nicht füllen (Langsamer Walzer 1) — "
            "parke dort mehr Titel oder stell die Quelle zurück auf die Favoriten-Bibliothek.")


class EnglishUnchangedTest(unittest.TestCase):
    """The English texts are the catalog keys — they must read as before."""

    def test_freshness(self):
        songs = [_e("A", 1), _e("B", 0)]
        hints = generate_hints(_Lib(songs), {"R": [songs]}, ["WW"], "S", [])
        self.assertEqual(hints, ["✦ 1/2 songs are fresh (50% new)."])


if __name__ == "__main__":
    unittest.main()
