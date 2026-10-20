#!/usr/bin/env python3
"""The Check-music drop tab runs its ffmpeg probes side by side.

Run:  py -m unittest tests.gui.test_music_probe_pool -v

With 🔇 on, every uncached track costs a 2-3 s noise probe, and borderline
short ones a silence probe on top. Run one after the other on the GUI thread,
20 tournament lists (741 probes) took over half an hour. The probes now run on
a small pool while the check walks the tracks in order. A barrier the fake
probes must pass together proves they overlap; a serial run would break it.
"""

import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from PySide6.QtWidgets import QApplication, QWidget

import gui.window.main_music as main_music
from gui.window.main_music import MusicCheckMixin
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])


class _Cache:
    def __init__(self):
        self.noise = {}
        self.silences = {}
        self.saves = 0

    def get_noise_floor(self, path, touch_disk=True):
        return self.noise.get(str(path))

    def put_noise_floor(self, path, floor_db):
        self.noise[str(path)] = floor_db

    def get_silences(self, path, touch_disk=True):
        return self.silences.get(str(path))

    def put_silences(self, path, spans):
        self.silences[str(path)] = spans

    def save(self):
        self.saves += 1


class _Host(QWidget, MusicCheckMixin):
    _MIN_PLAY_SECS = 105
    _check_noise = True

    def __init__(self, durations):
        super().__init__()
        self._settings = {}
        self._library = SimpleNamespace(lib=object(), cache=_Cache())
        self._durations = durations
        self.seen = []

    def _external_entry(self, path):
        return SimpleNamespace(path=path, duration=self._durations[path.name])

    def _track_issues(self, e, probe_silence=True, in_final=False):
        # What the real one asks for, minus the tempo / length rules.
        dur = int(e.duration)
        self.seen.append((e.path.name, self._track_noise_floor(e),
                          self._track_silence_total(e, dur)))
        return []


class ProbePoolTest(unittest.TestCase):

    def _run(self, durations, barrier_parties):
        host = _Host(durations)
        self.addCleanup(reap_widget, host)
        barrier = threading.Barrier(barrier_parties, timeout=3)

        def meet():
            try:
                barrier.wait()
                return True
            except threading.BrokenBarrierError:
                return False

        def noise(ffmpeg, p):
            return -60.0 if meet() else None

        def silences(ffmpeg, p):
            return [[0.0, 2.5]] if meet() else None

        tracks = [Path(f"C:/t/{n}") for n in durations]
        with mock.patch.object(main_music, "find_ffmpeg", return_value="ffmpeg"), \
                mock.patch.object(main_music, "measure_noise_floor", noise), \
                mock.patch.object(main_music, "detect_silences", silences):
            box = host._dropped_music_results(tracks, lambda d, t: None)
        self.addCleanup(reap_widget, box)
        return host

    def test_noise_probes_overlap(self):
        host = self._run({"a.mp3": 200, "b.mp3": 200, "c.mp3": 200}, 3)
        self.assertEqual(host.seen, [("a.mp3", -60.0, 0.0),
                                     ("b.mp3", -60.0, 0.0),
                                     ("c.mp3", -60.0, 0.0)])
        self.assertEqual(len(host._library.cache.noise), 3)

    def test_silence_probes_overlap_with_noise(self):
        # A borderline-short track gets both probes; all four meet at once.
        host = self._run({"a.mp3": 100, "b.mp3": 100}, 4)
        self.assertEqual(host.seen, [("a.mp3", -60.0, 2.5),
                                     ("b.mp3", -60.0, 2.5)])
        self.assertEqual(host._library.cache.silences,
                         {str(Path("C:/t/a.mp3")): [[0.0, 2.5]],
                          str(Path("C:/t/b.mp3")): [[0.0, 2.5]]})

    def test_open_deck_probes_overlap(self):
        # The open-deck tab of Check music probes the same way.
        host = _Host({})
        self.addCleanup(reap_widget, host)
        host._BEATS_PER_BAR = {}
        songs = [SimpleNamespace(entry=SimpleNamespace(
                     path=Path(f"C:/t/{n}.mp3"), duration=200, bpm=0, dance="",
                     features=None, title=n),
                     round_name="Vorrunde", tier="") for n in "abc"]
        table = SimpleNamespace(_row_meta=SimpleNamespace(songs=lambda: songs))
        host._checkable_deck_tables = lambda: [table]
        host.deck = lambda t: SimpleNamespace(name="Deck")
        host._playlist_structure_findings = lambda t: []
        barrier = threading.Barrier(3, timeout=3)

        def noise(ffmpeg, p):
            try:
                barrier.wait()
                return -60.0
            except threading.BrokenBarrierError:
                return None

        with mock.patch.object(main_music, "find_ffmpeg", return_value="ffmpeg"), \
                mock.patch.object(main_music, "measure_noise_floor", noise):
            host._compute_music_suspects(lambda d, t, n: None)
        self.assertEqual([s[1] for s in host.seen], [-60.0, -60.0, -60.0])


if __name__ == "__main__":
    unittest.main()
