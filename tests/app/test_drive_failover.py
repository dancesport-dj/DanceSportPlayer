#!/usr/bin/env python3
"""🔌 A stick that comes back under another letter still plays.

Run:  py -m unittest tests.app.test_drive_failover -v

Windows hands a USB stick the next free letter: the playlist says
`F:\\music\\x.mp3`, the stick is now `G:`. `resolve_file` tries the same path
on every other local drive before 🧭's search folders, so the row stays
white, the click plays and the backend opens `G:\\music\\x.mp3` — while the
stored path stays `F:`, for the evening the stick is F: again.
"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_failover_"))

from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry
from planner.music import drives
from planner.music.paths import resolve_file
from player.window.main_load import TrackLoadMixin
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)


@unittest.skipUnless(sys.platform == "win32", "drive letters are Windows'")
class _Base(unittest.TestCase):
    """The title on the tmp folder's drive, the playlist pointing at Q:."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dp_failover_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.real = self.tmp / "music" / "x (CC 31).mp3"
        self.real.parent.mkdir(parents=True)
        self.real.write_bytes(b"ID3")
        self.drive = self.real.drive.upper()
        self.stored = "Q:" + str(self.real)[len(self.drive):]
        patch = mock.patch.object(drives, "local_drives",
                                  return_value=frozenset({"Q:", self.drive}))
        patch.start()
        self.addCleanup(patch.stop)


class ResolverTest(_Base):

    def test_the_same_path_on_another_drive_is_found(self):
        self.assertEqual(resolve_file(self.stored, {}), self.real)

    def test_other_drives_leave_out_the_paths_own(self):
        self.assertEqual(drives.on_other_drives(self.stored),
                         [self.drive + str(self.real)[len(self.drive):]])

    def test_a_path_that_is_there_asks_for_no_drive_list(self):
        with mock.patch.object(drives, "local_drives") as listing:
            self.assertEqual(resolve_file(self.real, {}), self.real)
        listing.assert_not_called()

    def test_a_path_on_no_drive_has_no_other_drives(self):
        self.assertEqual(drives.on_other_drives("relative/x.mp3"), [])

    def test_gone_from_every_drive_is_none(self):
        self.assertIsNone(resolve_file(r"Q:\nowhere\gone.mp3", {}))


class _Window(QWidget):
    def __init__(self):
        super().__init__()
        self._settings = {}


class TableTest(_Base):

    def _table(self):
        win = _Window()
        self.addCleanup(reap_widget, win)
        table = PlaylistTable()
        QVBoxLayout(win).addWidget(table)
        return table

    def test_the_row_is_not_red(self):
        entry = MusicEntry(path=Path(self.stored), title="x", dance="CC", bpm=None)
        missing, *_ = self._table()._row_flags(entry)
        self.assertFalse(missing)

    def test_the_click_is_not_refused(self):
        self.assertFalse(self._table()._start_refused(3, self.stored))


class _Loader(TrackLoadMixin):
    def __init__(self):
        me: Any = self
        me._settings = {}


class SourceTest(_Base):

    def test_the_backend_opens_the_file_found(self):
        url = _Loader()._source_url(self.stored)
        self.assertEqual(Path(url.toLocalFile()), self.real)

    def test_a_title_gone_everywhere_opens_its_stored_path(self):
        url = _Loader()._source_url(r"Q:\nowhere\gone.mp3")
        self.assertEqual(Path(url.toLocalFile()), Path(r"Q:\nowhere\gone.mp3"))


if __name__ == "__main__":
    unittest.main()
