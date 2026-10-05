#!/usr/bin/env python3
"""Re-reading ONE file's ID3 tags without a restart (MusicLibrary.rescan_tags).

Run:  py -m unittest tests.planner.test_rescan_tags -v

The scan cache is content-addressed, so a track edited in mp3tag is re-read on
the next startup all by itself. Editing it while the app runs is the gap this
closes: the 🏷 context-menu action drops the cached row, reads the tags again
and writes the result onto the entry the deck rows already hold — replacing the
object would leave every row pointing at the stale one.
"""
import os
import tempfile
import threading
import unittest
from pathlib import Path

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_rescan_"))

import planner.db as pdb  # noqa: E402
from planner.library import MusicLibrary  # noqa: E402
from planner.models import MusicEntry  # noqa: E402

_PATH = Path(r"C:\music\Latein\Rumba RB 25.mp3")


class _FakeCache:
    """Stands in for AudioCache: only its identity is used (see _get_scan_cache)."""

    def recorded_fingerprint(self, path):
        return None   # never fingerprinted → no in-app tag edit to lay over it


class _StubScan:
    """The ScanCache seam, as a dict — no DB, no fingerprints.

    `get` answers whatever is stored for the path, so a `forget` that fails to
    clear it makes the re-read return the STALE metadata, which is exactly what
    the tests below have to be able to see.
    """

    def __init__(self, cache, cached=None):
        self._cache = cache
        self._store = {str(_PATH): dict(cached)} if cached else {}
        self.forgotten: list[Path] = []
        self.saves = 0

    def get(self, path):
        return self._store.get(str(path))

    def put(self, path, data):
        self._store[str(path)] = dict(data)

    def forget(self, path):
        self.forgotten.append(path)
        return self._store.pop(str(path), None) is not None

    def save(self):
        self.saves += 1


class RescanTagsTest(unittest.TestCase):

    def setUp(self):
        self.cache = _FakeCache()
        self.lib = MusicLibrary()
        # Stale metadata, as a cache written before the tags were edited: the
        # dance and bpm say Slowfox, the filename says Rumba.
        self.entry = MusicEntry(path=_PATH, title="Old title", dance="SF", bpm=29)
        self.lib.entries = [self.entry]
        self._scan(cached={"title": "Old title", "dance": "SF", "bpm": 29})

    def _scan(self, cached=None):
        self.scan = _StubScan(self.cache, cached)
        self.lib._scan_cache = self.scan
        return self.scan

    def test_the_cached_row_is_dropped_before_the_re_read(self):
        self.lib.rescan_tags(self.entry, self.cache)
        self.assertEqual(self.scan.forgotten, [_PATH])

    def test_the_entry_itself_is_updated_not_replaced(self):
        """Deck rows hold this very object — a fresh MusicEntry would not show."""
        self.lib.rescan_tags(self.entry, self.cache)
        self.assertEqual((self.entry.dance, self.entry.bpm), ("RB", 25))
        self.assertIs(self.lib.entries[0], self.entry)

    def test_the_changed_fields_are_reported(self):
        changed = self.lib.rescan_tags(self.entry, self.cache)
        self.assertEqual(changed["dance"], ("SF", "RB"))
        self.assertEqual(changed["bpm"], (29, 25))

    def test_unchanged_tags_report_nothing(self):
        self.lib.rescan_tags(self.entry, self.cache)     # entry now matches disk
        self._scan()
        self.assertEqual(self.lib.rescan_tags(self.entry, self.cache), {})

    def test_the_librarys_own_entry_is_updated_too(self):
        """A deck row can hold an EXTERNAL entry for a path the library also
        knows — both objects have to end up saying the same thing."""
        external = MusicEntry(path=_PATH, title="Old title", dance="SF", bpm=29)
        self.lib.rescan_tags(external, self.cache)
        self.assertEqual((external.dance, self.entry.dance), ("RB", "RB"))

    def test_the_re_read_is_persisted(self):
        self.lib.rescan_tags(self.entry, self.cache)
        self.assertEqual(self.scan.get(_PATH)["dance"], "RB")
        self.assertGreaterEqual(self.scan.saves, 1)


class ScanCacheForgetTest(unittest.TestCase):
    """The drop itself, against a real scan_meta table."""

    class _FpCache:
        """AudioCache reduced to the one thing ScanCache asks it for."""

        def fingerprint(self, path):
            return "FP-" + Path(path).name

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_rescan_db_"))
        self._saved = (pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
        pdb.AUDIO_DB_FILE = self.dir / "scratch.db"
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False
        self.addCleanup(self._restore)
        self.scan = pdb.ScanCache(self._FpCache())

    def _restore(self):
        try:
            pdb._DB_LOCAL.conn.close()
        except Exception:
            pass
        pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED = self._saved

    def _rows(self) -> int:
        return pdb._db().execute("SELECT COUNT(*) FROM scan_meta").fetchone()[0]

    def test_forgetting_clears_the_row_and_the_next_read_misses(self):
        self.scan.put(_PATH, {"title": "Rumba", "dance": "RB", "bpm": 25})
        self.assertEqual(self._rows(), 1)
        self.assertTrue(self.scan.forget(_PATH))
        self.assertIsNone(self.scan.get(_PATH))
        self.assertEqual(self._rows(), 0)

    def test_only_the_one_file_is_forgotten(self):
        other = Path(r"C:\music\Standard\Slowfox SF 29.mp3")
        self.scan.put(_PATH, {"title": "Rumba"})
        self.scan.put(other, {"title": "Slowfox"})
        self.scan.forget(_PATH)
        self.assertEqual(self.scan.get(other)["title"], "Slowfox")
        self.assertEqual(self._rows(), 1)

    def test_forgetting_an_unknown_file_is_a_no_op(self):
        self.assertFalse(self.scan.forget(_PATH))

    def test_a_file_that_cannot_be_hashed_is_a_no_op(self):
        self.scan._cache = type("_Gone", (), {"fingerprint": lambda s, p: None})()
        self.assertFalse(self.scan.forget(_PATH))


if __name__ == "__main__":
    unittest.main(verbosity=2)
