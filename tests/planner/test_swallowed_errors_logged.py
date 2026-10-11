#!/usr/bin/env python3
"""A failure the code shrugs off still leaves a debug line with its traceback.

Run:  py -m unittest tests.planner.test_swallowed_errors_logged -v

The tag readers, the DB helpers and the reference-clean worker caught
`Exception` and went on with a default — `except Exception: pass`. That keeps
the scan going, which is right, but a file that never got a length or a year
left nothing behind to say why.
"""

import os
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import planner.db as pdb
import planner.parsing as parsing

SONG = Path(r"C:\music\tanzcds\standardcd\TG\Tanguera (TG 32).mp3")


def _boom(*args, **kwargs):
    raise RuntimeError("a header mutagen cannot parse")


class SwallowedErrorsLoggedTest(unittest.TestCase):

    def assertLoggedWithTraceback(self, logger, call):
        with self.assertLogs(logger, "DEBUG") as logs:
            call()
        self.assertTrue(any(r.exc_info for r in logs.records),
                        [r.getMessage() for r in logs.records])

    def test_reading_the_length(self):
        with mock.patch.object(parsing, "MutagenFile", _boom):
            self.assertLoggedWithTraceback(
                "dancesport.parsing",
                lambda: self.assertEqual(parsing._read_duration(SONG), 0))

    def test_reading_the_tag(self):
        with mock.patch.object(parsing, "ID3", _boom):
            self.assertLoggedWithTraceback(
                "dancesport.parsing",
                lambda: self.assertIsNone(parsing._id3_of(SONG)))

    def test_reading_the_year(self):
        tags = mock.MagicMock()
        tags.__contains__.side_effect = _boom
        self.assertLoggedWithTraceback(
            "dancesport.parsing",
            lambda: self.assertEqual(parsing._detect_year("Tanguera 2019", SONG, tags), 2019))

    def test_counting_the_global_index(self):
        with mock.patch.object(pdb, "_db", _boom):
            self.assertLoggedWithTraceback(
                "dancesport.db",
                lambda: self.assertEqual(pdb.global_index_count(), 0))

    def test_fingerprinting_for_the_reference_clean(self):
        from gui.workers import ReferenceCleanWorker
        worker = ReferenceCleanWorker.__new__(ReferenceCleanWorker)
        worker._cache = mock.Mock(fingerprint=_boom)
        self.assertLoggedWithTraceback(
            "dancesport.workers",
            lambda: self.assertTrue(worker._hard_key(SONG).startswith("p:")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
