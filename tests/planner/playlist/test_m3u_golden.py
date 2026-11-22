"""The playlist exports, compared whole with golden files (tests/golden_support.py).

Run:  .venv/Scripts/python.exe -m pytest tests/planner/playlist/test_m3u_golden.py -n0
      (UPDATE_GOLDEN=1 in front rewrites tests/planner/playlist/golden/)
"""
import tempfile
import unittest
from pathlib import Path, PureWindowsPath

from planner.models import MusicEntry
from planner.playlist import m3u
from planner.playlist.m3u import export_flat_m3u, export_m3u
from tests.golden_support import assert_golden

GOLDEN = Path(__file__).parent / "golden"


def song(name, dance, bpm=None, duration=95, year=None, title=None):
    return MusicEntry(path=Path(f"C:/Musik/{dance or 'Misc'}/{name}.mp3"), title=title or name, dance=dance,
                      bpm=bpm, duration=duration, year=year)


def windows_path(p: Path) -> PureWindowsPath:
    """The same path text on every platform: the files are pinned as Windows writes them."""
    return PureWindowsPath(p)


class M3uGoldenTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.addCleanup(m3u.set_m3u_format, "utf-8")

    def check(self, out: Path, golden: str):
        assert_golden(self, GOLDEN / golden, out.read_bytes())

    def test_a_competition_draw(self):
        # Two dances; a two-heat round with a slot nothing was found for, and a
        # final. One title has a line break in it, one song no BPM.
        playlist = {
            "Vorrunde": [[song("Magalenha", "SA", bpm=50), song("Corazón", "CC", bpm=30)],
                         [song("Bailando", "SA", title="Bailando\n(Radio Edit)"), None]],
            "Finale": [[song("Mas Que Nada", "SA", bpm=51, duration=110),
                        song("Smooth", "CC", bpm=31, duration=120)]],
        }
        out = export_m3u(playlist, ["SA", "CC"], "x", out_path=self.dir / "draw.m3u",
                         path_for=windows_path)
        self.check(out, "competition_draw.m3u")

    def test_a_flat_list(self):
        songs = [song("Ännchen von Tharau", "LW", year=1999), song("Libertango", "TG"),
                 song("Untagged", None, duration=0)]
        out = export_flat_m3u(songs, "x", out_path=self.dir / "flat.m3u", path_for=windows_path)
        self.check(out, "flat.m3u")

    def test_a_competition_training_list(self):
        songs = [song(f"Samba {i}", "SA") for i in range(1, 3)] + [song(f"Cha {i}", "CC") for i in range(1, 3)] \
            + [song("Samba Final", "SA"), song("Cha Final", "CC")]
        out = export_flat_m3u(songs, "x", out_path=self.dir / "training.m3u8", path_for=windows_path,
                              heat_rounds=[("Runde 1", 2, 4), ("Finale", 1, 2)])
        self.check(out, "training.m3u8")

    def test_the_bom_format(self):
        m3u.set_m3u_format("utf-8-sig")
        out = export_flat_m3u([song("Über den Wolken", "SF")], "x", out_path=self.dir / "bom.m3u",
                              path_for=windows_path)
        self.check(out, "flat_bom.m3u")


if __name__ == "__main__":
    unittest.main()
