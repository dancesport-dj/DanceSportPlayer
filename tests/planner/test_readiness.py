#!/usr/bin/env python3
"""🚦 Event readiness: the checks that already exist, as one pre-flight.

Run:  py -m unittest tests.planner.test_readiness -v

Before an event, the DJ wants one answer: will tonight's lists play? Missing
files (or a whole drive that is not plugged in), tracks the 🔊 equalizer has no
loudness for, tracks the 🔇 skip has no silence probe for, Paso Dobles without
highlights and duplicates across the decks were each a separate check. The
readiness report runs them together and grades each green, yellow or red.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from planner import readiness
from planner.readiness import FAIL, OK, WARN, readiness_findings


class _Cache:
    """Only what the report asks of the AudioCache."""

    def __init__(self, lufs=(), silences=(), pd=()):
        self.lufs, self.silences, self.pd = set(lufs), set(silences), set(pd)

    def get_lufs(self, path, touch_disk=True):
        return -14.0 if str(path) in self.lufs else None

    def get_silences(self, path, touch_disk=True):
        return [] if str(path) in self.silences else None

    def get_pd_highlights(self, path):
        return [10.0, None, 60.0] if str(path) in self.pd else None


class ReadinessTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_ready_"))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def track(self, name, dance="LW"):
        p = self.dir / f"{name}.mp3"
        p.write_bytes(b"ID3")
        return (p, dance)

    def by_key(self, findings):
        return {f.key: f for f in findings}

    def test_a_fully_prepared_evening_is_green(self):
        lw, pd = self.track("Valse"), self.track("Espana", "PD")
        everything = {str(lw[0]), str(pd[0])}
        found = readiness_findings(
            [lw, pd], _Cache(everything, everything, {str(pd[0])}),
            {"within": [], "cross": []})
        self.assertEqual({f.level for f in found}, {OK})
        self.assertEqual(readiness.overall(found), OK)

    def test_a_missing_file_is_red_and_fixed_by_the_path_fixer(self):
        gone = (self.dir / "Gone.mp3", "TG")
        f = self.by_key(readiness_findings([gone], _Cache(), {}))["files"]
        self.assertEqual((f.level, f.fix), (FAIL, "paths"))
        self.assertIn("Gone", f.detail)

    def test_an_unplugged_drive_is_named(self):
        # A drive letter that cannot exist on any machine.
        gone = (Path("Ω:/tanzcds/standardcd/LW/Valse.mp3"), "LW")
        f = self.by_key(readiness_findings([gone, gone], _Cache(), {}))["files"]
        self.assertEqual(f.level, FAIL)
        self.assertIn("Ω:", f.detail)

    def test_tracks_off_the_referenzpfad_are_yellow_like_the_path_fixer_says(self):
        """Marcel: the line said "every title is where the list says" while
        🧭 Fix paths reported 93 valid tracks not on the Referenzpfad."""
        ref = self.dir / "tanzcds"
        (ref / "LW").mkdir(parents=True)
        (ref / "LW" / "Valse.mp3").write_bytes(b"ID3")
        (self.dir / "LW").mkdir()
        elsewhere = self.dir / "LW" / "Valse.mp3"
        elsewhere.write_bytes(b"ID3")
        lonely = self.track("Treat You Better B")
        on_ref = (ref / "LW" / "Valse.mp3", "LW")
        found = readiness_findings([(elsewhere, "LW"), lonely, on_ref], _Cache(), {},
                                   reference_root=str(ref))
        f = self.by_key(found)["files"]
        self.assertEqual((f.level, f.fix, f.count), (WARN, "paths", 2))
        self.assertIn("Reference path", f.detail)
        self.assertIn("Treat You Better B", f.detail)

    def test_without_a_referenzpfad_present_files_stay_green(self):
        f = self.by_key(readiness_findings([self.track("Valse")], _Cache(), {}))["files"]
        self.assertEqual(f.level, OK)

    def test_unmeasured_tracks_are_yellow_with_their_fix(self):
        lw = self.track("Valse")
        f = self.by_key(readiness_findings([lw], _Cache(), {}))
        self.assertEqual((f["loudness"].level, f["loudness"].fix), (WARN, "loudness"))
        self.assertEqual((f["silences"].level, f["silences"].fix), (WARN, "silences"))
        self.assertEqual(f["loudness"].count, 1)

    def test_only_paso_dobles_need_highlights(self):
        lw, pd = self.track("Valse"), self.track("Espana", "PD")
        f = self.by_key(readiness_findings([lw, pd], _Cache(), {}))["pd"]
        self.assertEqual((f.level, f.count, f.fix), (WARN, 1, "pd"))

    def test_without_paso_dobles_the_highlights_are_green(self):
        f = self.by_key(readiness_findings([self.track("Valse")], _Cache(), {}))["pd"]
        self.assertEqual(f.level, OK)

    def test_a_missing_file_is_not_also_counted_as_unmeasured(self):
        gone = (self.dir / "Gone.mp3", "PD")
        f = self.by_key(readiness_findings([gone], _Cache(), {}))
        self.assertEqual((f["loudness"].count, f["silences"].count, f["pd"].count),
                         (0, 0, 0))

    def test_each_track_counts_once(self):
        lw = self.track("Valse")
        f = self.by_key(readiness_findings([lw, lw, lw], _Cache(), {}))["loudness"]
        self.assertEqual(f.count, 1)

    def test_duplicates_are_yellow_and_open_the_resolve_dialog(self):
        rec = {"title": "Valse"}
        report = {"within": [{"file": "A", "clusters": [{"members": [rec, rec]}]}],
                  "cross": [{"file_a": "A", "file_b": "B",
                             "exact": [(rec, rec)], "similar": [(rec, rec)]}]}
        f = self.by_key(readiness_findings([self.track("Valse")], _Cache(), report))
        self.assertEqual((f["duplicates"].level, f["duplicates"].count,
                          f["duplicates"].fix), (WARN, 3, "duplicates"))

    def test_nothing_to_play_is_yellow(self):
        found = readiness_findings([], _Cache(), {})
        self.assertEqual([(f.key, f.level) for f in found], [("empty", WARN)])

    def test_without_a_cache_the_measurements_are_unknown(self):
        f = self.by_key(readiness_findings([self.track("Valse")], None, {}))
        self.assertNotIn("loudness", f)
        self.assertIn("files", f)

    def test_the_worst_light_wins(self):
        found = readiness_findings([(self.dir / "Gone.mp3", "LW")], _Cache(), {})
        self.assertEqual(readiness.overall(found), FAIL)

    def test_the_music_check_is_left_out_when_it_did_not_run(self):
        found = readiness_findings([self.track("Valse")], None, {})
        self.assertNotIn("music", self.by_key(found))

    def test_a_clean_music_check_is_green(self):
        found = self.by_key(readiness_findings([self.track("Valse")], None, {},
                                               music=([], [])))
        self.assertEqual((found["music"].level, found["music"].fix), (OK, None))

    def test_music_problems_are_yellow_and_open_the_report(self):
        titles = ["Moon", "Sun", "Star", "Comet"]
        found = self.by_key(readiness_findings(
            [self.track("Valse")], None, {}, music=(titles, ["Deck A"])))
        music = found["music"]
        self.assertEqual((music.level, music.count, music.fix), (WARN, 5, "music"))
        self.assertIn("4 titles with a tempo or length problem: Moon, Sun, Star, …",
                      music.detail)
        self.assertIn("1 playlists with uneven rounds or heats: Deck A", music.detail)


if __name__ == "__main__":
    unittest.main(verbosity=2)
