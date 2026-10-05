#!/usr/bin/env python3
"""Ctrl+S must not freeze the window while it thinks.

Run:  py -m unittest tests.gui.test_save_progress -v

Writing the .m3u is nothing (600 tracks: 4 ms). The wait is in turning saved
PATHS back into entries — a path the library no longer knows has its tags read
off the disk, ~50 ms each — and in repainting the progress bar once per track,
which cost 250 ms per 600 tracks all by itself. So the resolve reports progress,
and the bar is repainted about twenty times a second instead of per track.
"""

import os
import tempfile
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_save_"))

from pathlib import Path  # noqa: E402

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from gui.main_export import ExportMixin  # noqa: E402
from gui.main_persist import PersistenceMixin  # noqa: E402
from planner.models import MusicEntry  # noqa: E402

_app = QApplication.instance() or QApplication([])


class _Resolver(PersistenceMixin):
    """Just the two rebuild helpers, with a resolve that costs nothing."""

    def __init__(self):
        self.asked: list[str] = []

    def _resolve_entry(self, path: str):
        self.asked.append(path)
        if "gone" in path:
            return None
        return MusicEntry(path=Path(path), title=Path(path).stem, dance="LW")


class _Exporter(QWidget, ExportMixin):
    pass


def _grid(rounds: int, heats: int, dances: int) -> list:
    return [{"name": f"Round {r}", "heats": heats,
             "grid": {str(h): {str(d): rf"C:\music\{r}_{h}_{d}.mp3"
                               for d in range(dances)}
                      for h in range(heats)}}
            for r in range(rounds)]


class GridRebuildProgressTest(unittest.TestCase):

    def setUp(self):
        self.res = _Resolver()

    def test_it_reports_every_track_it_resolves(self):
        ticks = []
        pl = self.res._playlist_from_grid(_grid(2, 3, 5), 5, lambda *a: ticks.append(a))
        self.assertEqual(len(self.res.asked), 30)
        self.assertEqual([t[0] for t in ticks], list(range(1, 31)))
        self.assertEqual({t[1] for t in ticks}, {30})       # total known up front
        self.assertEqual(ticks[-1][2], "1_2_4.mp3")         # …and which file it is on
        self.assertEqual([len(h) for h in pl["Round 0"]], [5, 5, 5])

    def test_it_still_works_without_a_callback(self):
        pl = self.res._playlist_from_grid(_grid(1, 1, 5), 5)
        self.assertEqual(len(pl["Round 0"][0]), 5)

    def test_empty_slots_dont_stall_the_bar_below_100(self):
        # Real grids carry a None for every "no song found" slot (serialized, not
        # omitted) — the reported total must match the number of songs actually
        # resolved, or the bar stalls at the filled fraction and never reaches 100%.
        grid = _grid(1, 1, 5)
        grid[0]["grid"]["0"]["3"] = None
        grid[0]["grid"]["0"]["4"] = None
        ticks = []
        self.res._playlist_from_grid(grid, 5, lambda *a: ticks.append(a))
        self.assertEqual(len(self.res.asked), 3)
        self.assertEqual([t[0] for t in ticks], [1, 2, 3])
        self.assertEqual({t[1] for t in ticks}, {3})

    def test_a_flat_list_reports_and_drops_the_missing(self):
        ticks = []
        paths = [r"C:\music\a.mp3", r"C:\music\gone.mp3", r"C:\music\b.mp3"]
        out = self.res._resolve_paths(paths, lambda *a: ticks.append(a))
        self.assertEqual([e.title for e in out], ["a", "b"])
        self.assertEqual([t[0] for t in ticks], [1, 2, 3])   # the gone one still ticks


class ExportBarThrottleTest(unittest.TestCase):

    def setUp(self):
        self.win = _Exporter()
        self.addCleanup(reap_widget, self.win)

    def test_the_bar_is_not_repainted_once_per_track(self):
        painted = []

        def fn(cb):
            for i in range(1, 601):
                cb(i, 600, f"track {i}")
            return "done"

        with _spy_on_progress(painted):
            out = self.win._run_export("💾 Saving…", fn)
        self.assertEqual(out, "done")
        self.assertLess(len(painted), 100, "the bar is still repainting per track")
        self.assertEqual(painted[-1][0], 600, "the last tick must always land")

    def test_a_slow_export_keeps_getting_ticks(self):
        painted = []

        def fn(cb):
            for i in range(1, 4):
                time.sleep(0.06)      # slower than the 50 ms throttle
                cb(i, 3, "")
            return None

        with _spy_on_progress(painted):
            self.win._run_export("💾 Saving…", fn)
        self.assertEqual([p[0] for p in painted], [1, 2, 3])


class _spy_on_progress:
    """Record what reaches BusyDialog.set_progress during the block."""

    def __init__(self, sink):
        self._sink = sink

    def __enter__(self):
        from gui import common
        self._real = common.BusyDialog.set_progress
        sink = self._sink

        def spy(dlg, done, total, detail="", eta_seconds=-1.0):
            sink.append((done, total, detail))
        common.BusyDialog.set_progress = spy
        return self

    def __exit__(self, *exc):
        from gui import common
        common.BusyDialog.set_progress = self._real
        return False


if __name__ == "__main__":
    unittest.main()
