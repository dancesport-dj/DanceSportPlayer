"""♻️ The one-time import of the old JSON audio cache survives a damaged entry.

Run:  py -m unittest tests.planner.music.test_legacy_json_migration -v

Every vector was read with d['bpm'] and friends, so one entry missing a
field raised KeyError and the whole import stopped. The JSON file is only
renamed after a finished import, so the next start met the same entry again.
A damaged entry is now left out and the rest goes in.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from planner.music import db
from planner.music.db import AudioCache

_GOOD = {"bpm": 120.0, "centroid": 1500.0, "rms": 0.1, "mfcc": [0.5] * 13}


class LegacyMigrationTest(unittest.TestCase):

    def migrate(self, entries):
        legacy = Path(tempfile.mkdtemp(prefix="dp_legacy_")) / "audio_cache.json"
        legacy.write_text(json.dumps({"version": 6, "entries": entries}),
                          encoding="utf-8")
        cache = AudioCache()
        with mock.patch.object(db, "CACHE_FILE", legacy):
            cache._migrate_json()
        return cache, legacy

    def test_a_damaged_entry_is_left_out_and_the_rest_imported(self):
        cache, legacy = self.migrate({
            "fp_good": _GOOD,
            "fp_no_bpm": {"centroid": 1.0, "rms": 0.1, "mfcc": [0.5] * 13},
            "fp_not_a_dict": "oops",
        })
        self.assertIn("fp_good", cache._data)
        self.assertNotIn("fp_no_bpm", cache._data)
        self.assertNotIn("fp_not_a_dict", cache._data)
        row = db._db().execute(
            "SELECT bpm FROM features WHERE fp = ?", ("fp_good",)).fetchone()
        self.assertEqual(row, (120.0,))
        # Done, so it is not imported again on the next start.
        self.assertFalse(legacy.exists())
        self.assertTrue(legacy.with_suffix(".json.bak").exists())


if __name__ == "__main__":
    unittest.main()
