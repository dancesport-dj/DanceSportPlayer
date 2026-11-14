#!/usr/bin/env python3
"""A red row's foreign network path is not tested on disk later (review 7.A).

Run:  py -m unittest tests.gui.test_ghost_row_network_sites -v

The import of someone else's list or pack keeps a `\\\\host\\share` line as a
red row and touches nothing. Later steps walked the rows and tested the file:
readiness, Find this title, Edit tags, the export notes. Each test offers the
Windows login to that host and hangs the GUI thread on a dead one. Each site
here gets a ghost entry and every file test on a UNC path fails the test.
"""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_ghost_sites_"))

from planner.music import paths

GHOST = r"\\10.255.255.1\share\LW - Song.mp3"


def _refuse_network(real):
    def guarded(self, *args, **kwargs):
        if str(self).startswith("\\\\"):
            raise AssertionError(f"touched {self}")
        return real(self, *args, **kwargs)
    return guarded


def _refuse_network_os(real):
    def guarded(path, *args, **kwargs):
        if str(path).startswith("\\\\"):
            raise AssertionError(f"touched {path}")
        return real(path, *args, **kwargs)
    return guarded


class GhostSitesTest(unittest.TestCase):

    def setUp(self):
        self.addCleanup(paths.set_own_shares, {})
        paths.set_own_shares({})
        for name in ("stat", "exists", "is_file", "iterdir"):
            patcher = mock.patch.object(Path, name, _refuse_network(getattr(Path, name)))
            patcher.start()
            self.addCleanup(patcher.stop)
        # The os.path probes too: readiness asked os.path.exists of the
        # share's root, which stalled one run in three for 21 s.
        for name in ("exists", "isfile", "isdir"):
            patcher = mock.patch.object(
                os.path, name, _refuse_network_os(getattr(os.path, name)))
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_readiness_counts_the_ghost_as_missing(self):
        from planner.event.readiness import readiness_findings
        findings = readiness_findings([(Path(GHOST), "Langsamer Walzer")], None, {})
        self.assertTrue(findings)

    def test_find_this_title_looks_in_no_foreign_folder(self):
        from planner.playlist.missing_title import folder_matches
        self.assertEqual(folder_matches(GHOST, (".mp3",)), [])

    def test_edit_tags_takes_the_ghost_for_no_mp3_on_disk(self):
        from gui.dialogs.tag_edit_dialog import _mp3_on_disk
        self.assertFalse(_mp3_on_disk(SimpleNamespace(path=GHOST)))

    def test_applying_tag_edits_writes_no_ghost_mp3(self):
        # The editor's apply tested every edited row on disk before writing.
        from gui.window.main_tags import TagEditMixin
        ghost = SimpleNamespace(path=GHOST)
        dlg = SimpleNamespace(
            form_changes=dict, form_mp3s=list, reset_requested=False,
            changes_for=lambda e: {"rating": 3}, write_app_to_mp3=lambda: True,
            raw_edits=lambda e: {})
        written, stored = [], []
        host = SimpleNamespace(
            _library=SimpleNamespace(
                lib=SimpleNamespace(edit_tags=lambda es, c, ch: stored.append(ch) or []),
                cache=object()),
            _copies_of=lambda e: [e],
            _write_into_mp3=lambda e, *a: written.append(e) or [])
        TagEditMixin._apply_tag_dialog(host, [ghost], dlg)
        self.assertEqual(written, [])
        self.assertEqual(stored, [{"rating": 3}])   # the DB still takes it

    def test_the_export_note_puts_the_ghost_under_gone(self):
        from gui.window.main_export import _off_reference_text
        mapper = SimpleNamespace(missing=[Path(GHOST)], root="D:/Musik")
        self.assertIn("LW - Song", _off_reference_text(mapper))


if __name__ == "__main__":
    unittest.main()
