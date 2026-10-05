#!/usr/bin/env python3
"""A grid edit looks up what is on record without touching the disk.

Run:  py -m unittest tests.gui.test_edit_no_stat -v

Every edit re-gates 🔊 over every deck track, re-runs the live Check-Music
marks over the edited deck and, with 🆕 Unplanned on, re-filters the whole
library. Each lookup went through the cache's `path::mtime` key, i.e. one
`stat` per track — 3,859 of them for the library filter, per edit, and a
sleeping USB disk turns each into a wait. These lookups only gate and flag;
the fingerprint last recorded for the path is what they need.
"""

import threading
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import planner.db as pdb
from gui.main_analyze import AnalysisMixin
from gui.main_decks import DeckLayoutMixin
from gui.main_music import MusicCheckMixin


class _ScratchCache(unittest.TestCase):
    """A real AudioCache over a throw-away DB, with two measured tracks."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_nostat_"))
        saved = (pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
        pdb.AUDIO_DB_FILE = self.dir / "scratch.db"
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False
        self.addCleanup(self._restore, saved)
        self.cache = pdb.AudioCache()
        self.tracks = []
        for name in ("a", "b"):
            p = self.dir / f"{name}.mp3"
            p.write_bytes(b"audio of " + name.encode() * 500)
            self.cache.put_lufs(p, -14.0)
            self.cache.put_silences(p, [[0.0, 2.5]])
            self.cache.put_noise_floor(p, -60.0)
            self.tracks.append(p)
        self.cache.save()

    @staticmethod
    def _restore(saved):
        try:
            pdb._DB_LOCAL.conn.close()
        except Exception:
            pass
        pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED = saved

    def stats(self):
        """Count every Path.stat made inside the block."""
        real = Path.stat
        calls = []

        def counting(path, *a, **kw):
            calls.append(path)
            return real(path, *a, **kw)
        patcher = mock.patch.object(Path, "stat", counting)
        patcher.start()
        self.addCleanup(patcher.stop)
        return calls


class RecordedLookupTest(_ScratchCache):

    def test_the_recorded_values_come_back_without_a_stat(self):
        calls = self.stats()
        p = self.tracks[0]
        self.assertEqual(self.cache.get_lufs(p, touch_disk=False), -14.0)
        self.assertEqual(self.cache.get_silences(p, touch_disk=False), [[0.0, 2.5]])
        self.assertEqual(self.cache.get_noise_floor(p, touch_disk=False), -60.0)
        self.assertEqual(calls, [])

    def test_a_restarted_cache_knows_them_from_the_database(self):
        self.cache = pdb.AudioCache()
        calls = self.stats()
        self.assertEqual(self.cache.get_lufs(self.tracks[1], touch_disk=False), -14.0)
        self.assertEqual(calls, [])

    def test_a_track_never_hashed_is_unknown_and_not_read(self):
        fresh = self.dir / "fresh.mp3"
        fresh.write_bytes(b"never seen")
        calls = self.stats()
        with mock.patch.object(pdb, "_fingerprints") as hashing:
            self.assertIsNone(self.cache.get_lufs(fresh, touch_disk=False))
            self.assertIsNone(self.cache.recorded_fingerprint(fresh))
        hashing.assert_not_called()
        self.assertEqual(calls, [])


class EditHooksTest(_ScratchCache):
    """The three things every edit runs, on the real mixin methods."""

    def window(self):
        entries = [SimpleNamespace(path=p, duration=180) for p in self.tracks]
        table = SimpleNamespace(_row_meta=SimpleNamespace(entries=lambda: list(entries)))
        panel = mock.Mock()
        browser = mock.Mock()
        browser.unplanned_active.return_value = True
        win = SimpleNamespace(
            _cache=self.cache, _play_panel=panel, _lib_browser=browser,
            _lib=SimpleNamespace(entries=entries), _check_noise=True,
            _visible_deck_tables=lambda: [table],
            _deck_dedup_index=lambda: (set(), {"some other fp"}),
            _check_min_secs=lambda: 105)
        return win, entries

    def test_the_loudness_gate_does_not_stat(self):
        win, _ = self.window()
        calls = self.stats()
        AnalysisMixin._sync_loudness_available(win)
        win._play_panel.set_loudness_available.assert_called_once_with(True, 0)
        self.assertEqual(calls, [])

    def test_the_live_marks_lookups_do_not_stat(self):
        win, entries = self.window()
        calls = self.stats()
        self.assertEqual(
            MusicCheckMixin._track_silence_total(win, entries[0], 180, probe=False), 2.5)
        self.assertEqual(
            MusicCheckMixin._track_noise_floor(win, entries[0], probe=False), -60.0)
        self.assertEqual(calls, [])

    def test_the_unplanned_library_filter_does_not_stat(self):
        win, _ = self.window()
        calls = self.stats()
        DeckLayoutMixin._refresh_library_planned_filter(win)
        win._lib_browser.set_planned_paths.assert_called_once_with(set())
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
