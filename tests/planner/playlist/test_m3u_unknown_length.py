"""A song whose length is not known goes out as #EXTINF:-1, as m3u readers expect.

Run:  .venv/Scripts/python.exe -m pytest tests/planner/playlist/test_m3u_unknown_length.py -n0

#EXTINF:0 reads as "this track is 0 seconds long": a player that sums the list
or shows the length per row takes it at its word.
"""
import tempfile
import unittest
from pathlib import Path

from planner.models import MusicEntry
from planner.playlist.m3u import export_flat_m3u, export_m3u


def song(name, duration, dance="SA"):
    return MusicEntry(path=Path(f"C:/Musik/{name}.mp3"), title=name, dance=dance, duration=duration)


def extinf_lengths(out: Path) -> list[str]:
    return [ln.split(",", 1)[0].removeprefix("#EXTINF:")
            for ln in out.read_text(encoding="utf-8").splitlines() if ln.startswith("#EXTINF:")]


class UnknownLengthTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def test_a_flat_list(self):
        out = export_flat_m3u([song("Known", 95), song("Unknown", 0)], "x", out_path=self.dir / "flat.m3u")
        self.assertEqual(extinf_lengths(out), ["95", "-1"])

    def test_a_training_list(self):
        out = export_flat_m3u([song("Known", 95), song("Unknown", 0)], "x", out_path=self.dir / "t.m3u8",
                              heat_rounds=[("Finale", 2, 1)])
        self.assertEqual(extinf_lengths(out), ["95", "-1"])

    def test_a_competition_draw(self):
        playlist = {"Finale": [[song("Known", 95)], [song("Unknown", 0)]]}
        out = export_m3u(playlist, ["SA"], "x", out_path=self.dir / "draw.m3u")
        self.assertEqual(extinf_lengths(out), ["95", "-1"])


if __name__ == "__main__":
    unittest.main()
