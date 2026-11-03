#!/usr/bin/env python3
"""An imported .m3u finds its files the way playback does, and reads their tags.

Run:  py -m unittest tests.gui.test_import_finds_like_playback -v

A list carried from another machine used to split in two. Playback asked
`resolve_file`, which also looks on the other local drives, so the title played.
The import only asked the search folders, so the row kept the foreign path: no
tags, and on a Mac the whole backslash line in the Title column, because `Path`
reads a Windows path there as one long filename. 🏷 Re-read MP3 tags then tested
that same foreign path and said the file was gone.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path, PurePosixPath
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_import_finds_"))

from PySide6.QtWidgets import QApplication

from planner.models import MusicEntry
from planner.music.db import AudioCache
from planner.music.library import MusicLibrary
from tests.db_support import use_scratch_db
from tests.qt_test_support import reap_widget, stub_window_startup

NAME = "Yo No Se Manana (SA 30).mp3"
FOREIGN = "Q:\\my music\\salsa\\" + NAME


class ForeignNameTitleTest(unittest.TestCase):
    """The title of a file that is not here comes from its name, whichever OS
    wrote the path. `PurePosixPath` reads a Windows path the way macOS does."""

    def test_a_windows_path_on_a_mac_titles_the_row_with_the_filename(self):
        scan = mock.Mock()
        scan.get.return_value = None
        entry = MusicLibrary()._make_entry(PurePosixPath(FOREIGN), scan)
        self.assertEqual(entry.title, "Yo No Se Manana")


class ImportFindsLikePlaybackTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        from PySide6.QtCore import QSettings
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_import_finds_qs_"))
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_import_finds_lib_"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        use_scratch_db(self, self.dir / "scratch.db")
        self.real = self.dir / "stick" / "my music" / "salsa" / NAME
        self.real.parent.mkdir(parents=True)
        self.real.write_bytes(b"\0" * 16)
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.win._library.lib = MusicLibrary()
        self.win._library.cache = AudioCache()
        self.win._settings["remap_paths"] = []
        self.win._settings["reference_path"] = ""
        self.win._show_import_remap_report = lambda _reports: None
        self.m3u = self.dir / "carried.m3u"
        self.m3u.write_text(f"#EXTM3U\n{FOREIGN}\n", encoding="utf-8")
        # The stick came back under another letter: only the other-drives look
        # finds it, so nothing in the search folders can answer for it.
        patcher = mock.patch("planner.music.paths.on_other_drives",
                             lambda path: [str(self.real)] if "Q:" in str(path) else [])
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_party_list_row_holds_the_file_playback_would_find(self):
        entries = self.win._entries_from_m3u_file(self.m3u)
        self.assertEqual([Path(e.path) for e in entries], [self.real])

    def test_an_imported_deck_row_holds_the_file_playback_would_find(self):
        self.win._import_playlist_path(str(self.m3u))
        paths = [Path(e.path) for e in self.win._deckset.table._row_meta.entries()]
        self.assertEqual(paths, [self.real])

    def test_a_row_keeping_the_foreign_path_still_rereads_its_tags(self):
        """A session restored before the stick came back: the row keeps the
        path it has, and the re-read goes to the file playback would use."""
        entry = MusicEntry(path=Path(FOREIGN), title=FOREIGN, dance=None)
        self.win._rescan_entry_tags(entry)
        self.assertEqual(entry.title, "Yo No Se Manana")
        self.assertEqual(Path(entry.path), Path(FOREIGN))


if __name__ == "__main__":
    unittest.main(verbosity=2)
