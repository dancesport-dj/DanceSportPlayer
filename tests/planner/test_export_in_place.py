#!/usr/bin/env python3
"""Saving a playlist over the file it came from, and failing half-way.

Run:  py -m unittest tests.planner.test_export_in_place -v

The exports opened their target with 'w' and wrote track by track, so the
old file was truncated the moment the save began: anything that raised
between the first line and the last — a path the Referenzpfad mapper could
not re-root, a full USB stick — left half a playlist where the whole one had
been. The new one is written next to it and only swapped in once it is whole.
"""
import tempfile
import unittest
from pathlib import Path

from planner.config import replacing_text
from planner.models import MusicEntry
from planner.playlist.m3u import export_flat_m3u, export_m3u

OLD = "#EXTM3U\n#EXTINF:180,Mondschein über Wien\nF:\\music\\old.mp3\n"


def _entry(path: str, dance="CC"):
    return MusicEntry(path=Path(path), title=Path(path).stem, dance=dance,
                      duration=180)


def _fails_on_b(p: Path) -> Path:
    if p.stem == "b":
        raise OSError("cannot re-root b")
    return p


class TitleStaysOneLineTest(unittest.TestCase):
    """A tag can hold a newline; the importers read every line that is not a
    comment as a track path, so the text after it came back as a phantom track."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_export_title_"))

    def _lines(self, out: Path) -> list[str]:
        return out.read_text(encoding="utf-8").splitlines()

    def test_a_newline_in_the_title_does_not_add_a_line_flat(self):
        e = _entry(r"F:\music\a.mp3")
        e.title = "Song\nF:\\music\\phantom.mp3\r\nmore"
        out = export_flat_m3u([e], "x", out_path=self.dir / "flat.m3u")
        lines = self._lines(out)
        paths = [ln for ln in lines if ln and not ln.startswith("#")]
        self.assertEqual(paths, [r"F:\music\a.mp3"])
        self.assertTrue(any(ln.startswith("#EXTINF:180,Song F:") for ln in lines))

    def test_a_newline_in_the_title_does_not_add_a_line_with_heats(self):
        e = _entry(r"F:\music\a.mp3")
        e.title = "Song\nF:\\music\\phantom.mp3"
        out = export_m3u({"Final": [[e]]}, ["CC"], "x", out_path=self.dir / "heat.m3u")
        paths = [ln for ln in self._lines(out) if ln and not ln.startswith("#")]
        self.assertEqual(paths, [r"F:\music\a.mp3"])


class ExportInPlaceTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_export_in_place_"))
        self.out = self.dir / "Grünwald.m3u"
        self.out.write_text(OLD, encoding="utf-8")

    def _left_intact(self):
        self.assertEqual(self.out.read_text(encoding="utf-8"), OLD)
        self.assertEqual([p.name for p in self.dir.iterdir()], [self.out.name])

    def test_a_flat_export_that_fails_half_way_leaves_the_old_file(self):
        with self.assertRaises(OSError):
            export_flat_m3u([_entry(r"F:\music\a.mp3"), _entry(r"F:\music\b.mp3")],
                            "x", out_path=self.out, path_for=_fails_on_b)
        self._left_intact()

    def test_a_grid_export_that_fails_half_way_leaves_the_old_file(self):
        playlist = {"Final": [[_entry(r"F:\music\a.mp3"),
                               _entry(r"F:\music\b.mp3", "RB")]]}
        with self.assertRaises(OSError):
            export_m3u(playlist, ["CC", "RB"], "x", out_path=self.out,
                       path_for=_fails_on_b)
        self._left_intact()

    def test_a_save_that_works_replaces_it_whole(self):
        export_flat_m3u([_entry(r"F:\music\a.mp3")], "x", out_path=self.out)
        self.assertIn(r"F:\music\a.mp3", self.out.read_text(encoding="utf-8"))
        self.assertEqual([p.name for p in self.dir.iterdir()], [self.out.name])

    def test_the_helper_on_its_own(self):
        with self.assertRaises(RuntimeError), replacing_text(self.out) as f:
            f.write("#EXTM3U\n")
            raise RuntimeError("half-way")
        self._left_intact()


if __name__ == "__main__":
    unittest.main(verbosity=2)
