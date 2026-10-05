#!/usr/bin/env python3
"""Tests for planner.m3u.numbered_folder_m3u — the 🧳 USB-export copy step.

Run:  py -m unittest tests.planner.test_bundle_m3u -v

Each playlist becomes its own folder: the tracks are copied next to the M3U
as ``0_0_1 - Title WW29.mp3`` (index = play order, title from #EXTINF, dance
code + takt from the section header / [T29] tag / source filename) and the
path lines are rewritten to those bare filenames, so the folder plays in
order even without the M3U. Works on real temp files only: sources are tiny
fake .mp3 files, the folder is a second temp dir. No library, no GUI.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from planner.m3u import numbered_folder_m3u


class NumberedFolderM3uTest(unittest.TestCase):
    def setUp(self):
        self.src = Path(tempfile.mkdtemp(prefix="dp_bundle_src_"))
        self.folder = Path(tempfile.mkdtemp(prefix="dp_bundle_out_"))

    def tearDown(self):
        shutil.rmtree(self.src, ignore_errors=True)
        shutil.rmtree(self.folder, ignore_errors=True)

    def _mp3(self, rel: str, content: bytes = b"ID3fake") -> Path:
        p = self.src / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
        return p

    def _m3u(self, name: str, lines) -> Path:
        p = self.folder / name
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return p

    def test_tracks_copied_numbered_and_rewritten_comments_kept(self):
        a = self._mp3("cha/Song A (CC 30).mp3", b"AAA")
        b = self._mp3("rumba/Song B (RB 26).mp3", b"BBB")
        m3u = self._m3u("comp.m3u", [
            "#EXTM3U",
            "# ══ Runde 1 (1 Heat) ══",
            "#EXTINF:120,Song A",
            str(a),
            "#EXTINF:110,Song B",
            str(b),
        ])
        copied, missing = numbered_folder_m3u(m3u)
        self.assertEqual(missing, 0)
        # Dance code + takt come from the source filename convention "(CC 30)".
        self.assertEqual([p.name for p in copied],
                         ["0_0_1 - Song A CC30.mp3", "0_0_2 - Song B RB26.mp3"])

        lines = m3u.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], "#EXTM3U")
        self.assertEqual(lines[1], "# ══ Runde 1 (1 Heat) ══")   # comments untouched
        self.assertEqual(lines[3], "0_0_1 - Song A CC30.mp3")
        self.assertEqual(lines[5], "0_0_2 - Song B RB26.mp3")
        # Copies land NEXT TO the M3U, contents intact.
        self.assertEqual((self.folder / "0_0_1 - Song A CC30.mp3").read_bytes(),
                         b"AAA")
        self.assertEqual((self.folder / "0_0_2 - Song B RB26.mp3").read_bytes(),
                         b"BBB")

    def test_dance_from_section_header_takt_from_extinf_tag(self):
        # No code in the source filename → the # ── Dance ── header and the
        # exporter's [T29] tag (stripped from the copied name) must fill in.
        a = self._mp3("misc/My Waltz Song.mp3")
        m3u = self._m3u("comp.m3u", [
            "#EXTM3U",
            "# ── Wiener Walzer ──",
            "#EXTINF:95,My Waltz Song [T29]",
            str(a),
        ])
        copied, missing = numbered_folder_m3u(m3u)
        self.assertEqual(missing, 0)
        self.assertEqual(copied[0].name, "0_0_1 - My Waltz Song WW29.mp3")

    def test_missing_source_counted_line_left_index_consumed(self):
        a = self._mp3("cha/Song A (CC 30).mp3")
        ghost = str(self.src / "gone" / "Ghost (JI 42).mp3")
        m3u = self._m3u("comp.m3u", [
            "#EXTM3U",
            "#EXTINF:120,Song A",
            str(a),
            "#EXTINF:100,Ghost",
            ghost,
            "#EXTINF:110,Song A",
            str(a),
        ])
        copied, missing = numbered_folder_m3u(m3u)
        self.assertEqual(missing, 1)
        lines = m3u.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[4], ghost)   # unresolved line stays absolute
        # The ghost consumed index 2, so the numbering mirrors the slots.
        self.assertEqual(lines[6], "0_0_3 - Song A CC30.mp3")

    def test_title_from_extinf_sanitized_filename_stem_fallback(self):
        a = self._mp3("cha/Song (CC 30).mp3")
        b = self._mp3("rumba/Plain Rumba (RB 26).mp3")
        m3u = self._m3u("comp.m3u", [
            "#EXTM3U",
            '#EXTINF:120,Bad/Title: "X?"',
            str(a),
            str(b),   # no EXTINF → cleaned filename stem is the title
        ])
        copied, missing = numbered_folder_m3u(m3u)
        self.assertEqual(missing, 0)
        self.assertEqual(copied[0].name, "0_0_1 - Bad_Title_ _X__ CC30.mp3")
        self.assertEqual(copied[1].name, "0_0_2 - Plain Rumba RB26.mp3")

    def test_same_track_twice_gets_two_numbered_copies(self):
        a = self._mp3("cha/Song A (CC 30).mp3")
        m3u = self._m3u("comp.m3u", [str(a), str(a)])
        copied, missing = numbered_folder_m3u(m3u)
        self.assertEqual(missing, 0)
        self.assertEqual([p.name for p in copied],
                         ["0_0_1 - Song A CC30.mp3",
                          "0_0_2 - Song A CC30.mp3"])
        self.assertTrue(all(p.is_file() for p in copied))

    def test_underscore_index_beyond_ten(self):
        paths = [self._mp3(f"cha/Song {i:02d} (CC 30).mp3") for i in range(1, 13)]
        m3u = self._m3u("comp.m3u", [str(p) for p in paths])
        copied, missing = numbered_folder_m3u(m3u)
        self.assertEqual(missing, 0)
        self.assertEqual(copied[9].name, "0_1_0 - Song 10 CC30.mp3")
        self.assertEqual(copied[11].name, "0_1_2 - Song 12 CC30.mp3")


if __name__ == "__main__":
    unittest.main()
