"""🔒 find_missing_metadata keeps its read-only promise (#59)."""
import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from planner.music import db as pdb
from tests.db_support import use_scratch_db
from tools import find_missing_metadata as tool


class ReadOnlyTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_fmm_ro_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.db_file = use_scratch_db(self, self.dir / "scratch.db")

    def run_tool(self):
        out = io.StringIO()
        with (mock.patch.object(sys, "argv", ["find_missing_metadata"]),
              mock.patch.object(pdb, "_db", side_effect=AssertionError("read-write opener used")),
              contextlib.redirect_stdout(out)):
            try:
                tool.main()
            except SystemExit as exc:
                return exc.code, out.getvalue()
        return 0, out.getvalue()

    def test_an_absent_database_is_not_created(self):
        code, _out = self.run_tool()
        self.assertNotEqual(code, 0)
        self.assertFalse(self.db_file.exists())

    def test_an_existing_database_is_read_without_the_migrating_opener(self):
        pdb._db()           # the app's own open builds the schema
        code, _out = self.run_tool()
        self.assertEqual(code, 0)


class NoPathTest(unittest.TestCase):
    """A track whose file is on an unplugged drive still reaches the report (#78)."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_fmm_np_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")

    def test_a_track_with_no_file_row_is_reported_not_ignored(self):
        conn = pdb._db()
        conn.execute("INSERT INTO scan_meta (ckey, title) VALUES ('fp1::lost song', 'Lost Song')")
        conn.commit()
        out = io.StringIO()
        with (mock.patch.object(sys, "argv", ["find_missing_metadata"]),
              contextlib.redirect_stdout(out)):
            tool.main()
        report = out.getvalue()
        self.assertIn("ignored (outside standardcd / lateincd):  0", report)
        self.assertIn("Lost Song", report)


if __name__ == "__main__":
    unittest.main()
