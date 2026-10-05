#!/usr/bin/env python3
"""export_m3u / export_flat_m3u write each track path through `path_for`.

Run:  py -m unittest tests.planner.test_export_path_for -v

The desk hands in a mapper that re-roots every track under the Referenzpfad, so
a list holding C: and F: copies of the library leaves as one or the other.
"""

import tempfile
import unittest
from pathlib import Path

from planner.m3u import export_flat_m3u, export_m3u
from planner.models import MusicEntry

_DIR = Path(tempfile.mkdtemp(prefix="dp_export_path_for_"))


def _entry(path: str, dance="CC"):
    return MusicEntry(path=Path(path), title=Path(path).stem, dance=dance,
                      duration=180)


def _track_lines(m3u: Path) -> list[str]:
    return [ln for ln in m3u.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")]


def _to_c(p: Path) -> Path:
    return Path(str(p).replace("F:", "C:"))


class ExportPathForTest(unittest.TestCase):

    def test_flat_export_writes_the_mapped_path(self):
        out = export_flat_m3u([_entry(r"F:\music\a.mp3"), _entry(r"C:\music\b.mp3")],
                              "x", out_path=_DIR / "flat.m3u", path_for=_to_c)
        self.assertEqual(_track_lines(out), [r"C:\music\a.mp3", r"C:\music\b.mp3"])

    def test_grid_export_writes_the_mapped_path(self):
        playlist = {"Final": [[_entry(r"F:\music\a.mp3"),
                               _entry(r"C:\music\b.mp3", "RB")]]}
        out = export_m3u(playlist, ["CC", "RB"], "x", out_path=_DIR / "grid.m3u",
                         path_for=_to_c)
        self.assertEqual(_track_lines(out), [r"C:\music\a.mp3", r"C:\music\b.mp3"])

    def test_without_a_mapper_the_path_is_written_as_is(self):
        out = export_flat_m3u([_entry(r"F:\music\a.mp3")], "x",
                              out_path=_DIR / "plain.m3u")
        self.assertEqual(_track_lines(out), [r"F:\music\a.mp3"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
