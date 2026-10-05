#!/usr/bin/env python3
"""🧭 What 📂 Import reports after re-rooting a carried-over playlist.

Run:  .venv\\Scripts\\python.exe -m unittest tests.gui.test_import_remap_report -v
(needs PySide6 — gui.main_import imports Qt at module level)

A playlist written on the PC names `F:\\my music\\…`; on the Mac, or on a PC
that keeps the library elsewhere, the import re-roots those lines under the
search folders. That is a change to what the deck points at, so it is not done
silently: the report says how many lines moved, how many are still gone, and —
behind the details — every single old → new pair.

The builder is pure so the wording can be pinned without a dialog; the dialog
does nothing but show what comes out of here.
"""

import os
import tempfile
import unittest
from pathlib import Path

if "DANCEPLAYLIST_STATE_DIR" not in os.environ:
    os.environ["DANCEPLAYLIST_STATE_DIR"] = tempfile.mkdtemp(prefix="dp_state_")

OLD = "F:\\my music\\tanzcds\\lateincd\\SB\\Senorita (SB 50).mp3"
NEW = Path("/Users/me/Music/my music/tanzcds/lateincd/SB/Senorita (SB 50).mp3")
OLD_2 = "F:\\my music\\tanzcds\\lateincd\\CC\\Havana (CC 31).mp3"
NEW_2 = Path("/Users/me/Music/my music/tanzcds/lateincd/CC/Havana (CC 31).mp3")


def _res(remapped=(), missing=0, raw=2):
    """An import result, cut down to what the report reads."""
    return {"remapped": list(remapped), "missing": missing, "raw": raw}


class RemapReportTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from gui.main_import import build_import_remap_report
        cls.build = staticmethod(build_import_remap_report)

    def test_an_import_that_moved_nothing_reports_nothing(self):
        """The Windows case: every path resolved, so no dialog at all."""
        self.assertIsNone(self.build(_res(), "finale.m3u"))

    def test_the_summary_counts_the_lines_that_moved(self):
        rep = self.build(_res([(OLD, NEW), (OLD_2, NEW_2)]), "finale.m3u")
        self.assertIsNotNone(rep)
        self.assertIn("2", rep["text"])
        self.assertIn("finale.m3u", rep["text"])

    def test_one_moved_line_is_not_reported_in_the_plural(self):
        rep = self.build(_res([(OLD, NEW)]), "finale.m3u")
        self.assertIn("1 track", rep["text"])
        self.assertNotIn("1 tracks", rep["text"])

    def test_the_details_carry_every_old_and_new_path(self):
        rep = self.build(_res([(OLD, NEW), (OLD_2, NEW_2)]), "finale.m3u")
        for part in (OLD, str(NEW), OLD_2, str(NEW_2)):
            self.assertIn(part, rep["details"])

    def test_what_is_still_gone_is_said_too(self):
        rep = self.build(_res([(OLD, NEW)], missing=3), "finale.m3u")
        self.assertIn("3", rep["text"])

    def test_a_playlist_nothing_could_be_found_for_still_reports(self):
        """The Mac-without-search-folders case: no dialog would leave the user
        with an empty-looking deck and no reason given."""
        rep = self.build(_res(missing=2), "finale.m3u")
        self.assertIsNotNone(rep)
        self.assertIn("2", rep["text"])
        self.assertEqual(rep["details"], "")

    def test_the_file_the_playlist_still_points_at_is_never_invented(self):
        """Only what the remapper answered is listed — it answers with files
        that exist, and the report must not add to that."""
        rep = self.build(_res([(OLD, NEW)], missing=1), "finale.m3u")
        self.assertEqual(rep["details"].count("→"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
