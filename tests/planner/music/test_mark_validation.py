"""🛡 Imported Paso Doble marks are checked before they are stored (review #27):
a hand-made file must not attach unbounded data, and a restore must not copy
rows that import_manual_pd would have refused."""
import contextlib
import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

import planner.music.db as pdb
import planner.music.db_upkeep as upkeep
from tests.db_support import use_scratch_db


class MarkImportTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_marks_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
        self.cache = pdb.AudioCache()

    def _stored(self):
        return pdb._db().execute("SELECT fp FROM pd_highlights").fetchall()

    def test_an_enormous_times_list_is_refused(self):
        n, _ = self.cache.import_manual_pd([
            {"fp": "a", "times": [1.0] * 100_000},
            {"fp": "b", "times": [1.0, 2.0]}])
        self.assertEqual(n, 1)
        self.assertEqual(self._stored(), [("b",)])

    def test_an_enormous_fingerprint_is_refused(self):
        n, _ = self.cache.import_manual_pd([
            {"fp": "x" * 10_000, "times": [1.0]},
            {"fp": "ok", "afp": "y" * 10_000, "times": [1.0]}])
        self.assertEqual(n, 0)


class RestoreValidationTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_restore_marks_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
        pdb._db().execute("INSERT INTO tag_edits (fp, rating) VALUES ('fp1', 4)")
        self.backup = upkeep.backup_user_data()
        pdb._db().execute("DELETE FROM tag_edits")

    def _put(self, fp, times):
        with contextlib.closing(sqlite3.connect(self.backup)) as bak:
            bak.execute("INSERT OR REPLACE INTO pd_highlights (fp, times, manual) "
                        "VALUES (?,?,1)", (fp, times))
            bak.commit()

    def test_a_bad_mark_in_a_backup_is_skipped_the_good_one_restored(self):
        self._put("good", json.dumps([1.5, 2.0]))
        self._put("neg", json.dumps([-1.0]))
        self._put("junk", "{not json")
        self._put("huge", json.dumps([1.0] * 100_000))
        self._put("str", json.dumps(["a"]))
        _edits, marks, _plays = upkeep.restore_user_data(self.backup)
        self.assertEqual(marks, 1)
        self.assertEqual(pdb._db().execute("SELECT fp FROM pd_highlights").fetchall(),
                         [("good",)])


if __name__ == "__main__":
    unittest.main()
