#!/usr/bin/env python3
"""A UNC line from someone else's playlist is not a playable row.

Run:  py -m unittest tests.app.test_foreign_unc_rows -v

`resolve_file` refuses a foreign share, but `_source_url` used to fall back to
the raw path, so the media backend opened an SMB session for it, and
`next_song_row` handed that row to the auto-advance. Security audit run-2 #2.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_unc_rows_"))

from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from gui.table.playlist_table import PlaylistTable
from gui.table.table_host import TableHost
from player.audio.playback_state import PlaybackState
from player.window.main_load import TrackLoadMixin
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)

FOREIGN = r"\\evil-host\share\x.mp3"


class _Loader(TrackLoadMixin):
    def __init__(self, settings=None):
        me = self
        me._settings = settings or {}
        me._playback = PlaybackState()


class SourceUrlTest(unittest.TestCase):

    def test_a_foreign_share_opens_nothing(self):
        for line in (FOREIGN, "//evil-host/share/x.mp3", r"/\evil-host\share\x.mp3"):
            with self.subTest(line=line), mock.patch.object(Path, "is_file") as spy:
                self.assertTrue(_Loader()._source_url(line).isEmpty())
            spy.assert_not_called()

    def test_the_users_own_share_still_opens_its_path(self):
        url = _Loader({"library_dir": r"\\nas\music"})._source_url(r"\\nas\music\x.mp3")
        self.assertFalse(url.isEmpty())

    def test_a_local_title_gone_everywhere_keeps_its_stored_path(self):
        url = _Loader()._source_url(str(Path(tempfile.gettempdir()) / "gone.mp3"))
        self.assertFalse(url.isEmpty())


class _Window(QWidget):
    def __init__(self, settings):
        super().__init__()
        self._settings = settings


class NextSongRowTest(unittest.TestCase):

    def _table(self, paths, settings=None):
        win = _Window(settings or {})
        self.addCleanup(reap_widget, win)
        table = PlaylistTable()
        QVBoxLayout(win).addWidget(table)
        table._row_meta = [SimpleNamespace(entry=SimpleNamespace(path=p))
                           for p in paths]
        return table

    def test_auto_advance_skips_a_foreign_share(self):
        here = Path(tempfile.gettempdir()) / "a.mp3"
        table = self._table([here, FOREIGN, here])
        with mock.patch.object(Path, "is_file") as spy:
            self.assertEqual(table.next_song_row(0, 1), (2, here))
            self.assertEqual(table.next_song_row(2, -1), (0, here))
        spy.assert_not_called()

    def test_a_foreign_line_with_a_local_copy_still_plays(self):
        table = self._table([FOREIGN])
        with mock.patch.object(TableHost, "file_there", return_value=True):
            self.assertEqual(table.next_song_row(-1, 1), (0, FOREIGN))

    def test_the_users_own_share_is_not_skipped(self):
        own = r"\\nas\music\x.mp3"
        table = self._table([own], {"library_dir": r"\\nas\music"})
        self.assertEqual(table.next_song_row(-1, 1), (0, own))


if __name__ == "__main__":
    unittest.main()
