"""A competition training list goes out with its rounds and heats as comments.

Run:  .venv/Scripts/python.exe -m unittest tests.planner.playlist.test_competition_training_m3u -v
"""
import tempfile
import unittest
from pathlib import Path

from planner.models import MusicEntry
from planner.playlist.m3u import export_flat_m3u, m3u_marker_heats, read_m3u_tracks

_DANCES = ["SA", "CC"]


def _entries():
    out = []
    # round 1: 3 heats of each dance, the final: 1 heat of each
    for d, n in [("SA", 3), ("CC", 3), ("SA", 1), ("CC", 1)]:
        for i in range(n):
            out.append(MusicEntry(path=Path(f"C:/m/{d}{len(out)}.mp3"),
                                  title=f"{d}{len(out)}", dance=d, duration=120))
    return out


class CompetitionTrainingM3uTest(unittest.TestCase):
    def export(self, plan):
        out = Path(tempfile.mkdtemp(prefix="dp_ctm3u_")) / "list.m3u8"
        export_flat_m3u(_entries(), "x", out_path=out, heat_rounds=plan)
        return out

    def test_the_rounds_and_heats_are_written_as_comments_and_read_back(self):
        out = self.export([("Runde 1", 3, 6), ("Finale", 1, 2)])
        text = out.read_text(encoding="utf-8")
        self.assertIn("# ══ Runde 1 (3 Heats) ══", text)
        self.assertIn("# ══ Finale (1 Heat) ══", text)
        self.assertEqual(m3u_marker_heats(out),
                         [("Runde 1", 3, 6), ("Finale", 1, 2)])

    def test_the_track_order_is_kept(self):
        out = self.export([("Runde 1", 3, 6), ("Finale", 1, 2)])
        self.assertEqual([p.name for p, _t in read_m3u_tracks(out)],
                         [e.path.name for e in _entries()])

    def test_a_plan_that_does_not_fit_the_list_is_left_out(self):
        out = self.export([("Runde 1", 3, 9)])
        self.assertEqual(m3u_marker_heats(out), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
