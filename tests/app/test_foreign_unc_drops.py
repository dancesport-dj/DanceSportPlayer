#!/usr/bin/env python3
"""A UNC line in someone else's dropped .m3u is never opened.

Run:  .venv/Scripts/python.exe -m unittest tests.app.test_foreign_unc_drops -v

`playlist_entries` skips a foreign network line ("no SMB session for it"),
but three other drop paths did not: 🧭 Fix paths stat-ed every line, and the
print and the music-speed check built an external entry, whose tag reader
opened the file. Each of those starts an SMB session with the user's login.
Full review 2026-11-11 #1.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_unc_drops_"))

from PySide6.QtWidgets import QApplication

from gui.window.main_paths import PathFixMixin
from planner.music import paths
from planner.music.library import MusicLibrary

_app = QApplication.instance() or QApplication(sys.argv)

FOREIGN = r"\\evil-host\share\x.mp3"


class EntryForTest(unittest.TestCase):

    def setUp(self):
        paths.set_own_shares({})
        self.addCleanup(paths.set_own_shares, {})
        self.lib = MusicLibrary()

    def test_a_foreign_share_builds_no_external_entry(self):
        with mock.patch.object(MusicLibrary, "make_external_entry") as built:
            self.assertIsNone(self.lib.entry_for(FOREIGN, cache=object()))
        built.assert_not_called()

    def test_the_users_own_share_still_does(self):
        paths.set_own_shares({"library_dir": r"\\nas\music"})
        with mock.patch.object(MusicLibrary, "make_external_entry",
                               return_value="entry") as built:
            self.assertEqual(self.lib.entry_for(r"\\nas\music\x.mp3", cache=object()),
                             "entry")
        built.assert_called_once()


class _Host(PathFixMixin):
    def __init__(self, tracks):
        self._tracks = tracks

    def _remap_index(self):
        return None, None, paths.PathRemapper([])

    def _m3u_track_paths(self, m3u):
        return self._tracks


class CheckDroppedPathsTest(unittest.TestCase):

    def setUp(self):
        paths.set_own_shares({})
        self.addCleanup(paths.set_own_shares, {})

    def test_a_foreign_line_is_unresolved_without_being_touched(self):
        host = _Host([Path(FOREIGN)])
        real_exists = Path.exists

        def exists(p, *a, **kw):
            if str(p).startswith("\\\\"):
                raise AssertionError(f"stat on a foreign share: {p}")
            return real_exists(p, *a, **kw)

        with mock.patch.object(Path, "exists", exists):
            _, summary = host._check_dropped_paths([Path("list.m3u")])
        self.assertEqual(summary["unresolved"], 1)
        self.assertEqual(summary["valid"], 0)


if __name__ == "__main__":
    unittest.main()
