#!/usr/bin/env python3
"""🧭 One resolver finds a moved file for decks, wishlists and cartwall pads.

Run:  py -m unittest tests.app.test_resolve_file -v

A path written on another PC (`F:\\my music\\tanzcds\\…`) names a drive this
PC may not have. An imported playlist was already re-rooted under the
Reference path and the search folders (⚙ Settings); a wishlist fed from an
.m3u, a restored deck or wishlist and a 🎛 pad were not — the pad stayed red
and the wishlist line was dropped. Now all of them ask
`planner.music.paths.resolve_file`, the search 🧭 Fix paths runs, and none of
them rewrites the stored path: the stick may come back under its old letter.
"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_resolve_file_"))

from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from gui.table.playlist_table import PlaylistTable
from gui.window.main_restore import RestoreMixin
from planner.models import MusicEntry
from planner.music.paths import resolve_file, search_roots
from planner.playing import cartwall as pc
from player.widgets.cartwall import CartwallWidget
from player.window.main_cartwall import CartwallMixin
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)

FOREIGN = r"F:\my music\tanzcds\lateincd\08 Trijntje Oosterhuis - Another Saturday Night cc31.mp3"


class _Base(unittest.TestCase):
    """A music folder at <tmp>/datein/my music/tanzcds holding the one title."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dp_resolve_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = self.tmp / "datein" / "my music" / "tanzcds"
        self.real = self.root / "lateincd" / Path(FOREIGN.replace("\\", "/")).name
        self.real.parent.mkdir(parents=True)
        self.real.write_bytes(b"ID3")
        # Written as Marcel wrote it: forward slashes, a backslash at the end.
        self.settings = {"reference_path": self.root.as_posix().replace(
            "/tanzcds", "\\tanzcds")}


class ResolverTest(_Base):

    def test_a_path_that_is_there_is_itself(self):
        self.assertEqual(resolve_file(self.real, self.settings), self.real)

    def test_a_foreign_path_lands_under_the_reference_path(self):
        self.assertEqual(resolve_file(FOREIGN, self.settings), self.real)

    def test_forward_slashes_work_too(self):
        self.assertEqual(resolve_file(FOREIGN.replace("\\", "/"), self.settings),
                         self.real)

    def test_a_search_folder_is_tried_after_the_reference_path(self):
        settings = {"reference_path": str(self.tmp / "elsewhere"),
                    "remap_paths": [str(self.root)]}
        self.assertEqual(resolve_file(FOREIGN, settings), self.real)

    def test_nothing_found_is_none(self):
        self.assertIsNone(resolve_file(r"F:\gone\nowhere.mp3", self.settings))

    def test_no_settings_only_takes_what_is_there(self):
        self.assertIsNone(resolve_file(FOREIGN, {}))
        self.assertEqual(resolve_file(self.real, None), self.real)

    def test_the_roots_are_fix_paths_roots(self):
        roots = search_roots({"reference_path": "R", "remap_paths": ["S1", "S2"]})
        self.assertEqual(roots[:3], ["R", "S1", "S2"])


class _Window(QWidget):
    def __init__(self, settings):
        super().__init__()
        self._settings = settings


class WishlistM3uTest(_Base):

    def test_a_dropped_m3u_line_is_found_under_the_reference_path(self):
        win = _Window(self.settings)
        self.addCleanup(reap_widget, win)
        table = PlaylistTable()
        QVBoxLayout(win).addWidget(table)
        seen = []
        stub: Any = table

        def entry_for(path):
            seen.append(Path(path))
            return MusicEntry(path=Path(path), title="CC", dance="CC", bpm=None)

        stub._entry_for = entry_for
        stub._append_entry = lambda entry, notify=True: None
        m3u = self.tmp / "wish.m3u"
        m3u.write_text("#EXTM3U\n" + FOREIGN + "\n", encoding="utf-8")
        table._append_m3u(m3u)
        self.assertEqual(seen, [self.real])


class _Lib:
    def __init__(self, known):
        self.known = known
        self.asked = []

    def entry_for(self, path, _cache=None, require_file=False):
        self.asked.append(str(path))
        if str(path) == str(self.known):
            return MusicEntry(path=Path(path), title="CC", dance="CC", bpm=None)
        return None


class _Restore(RestoreMixin):
    def __init__(self, settings, lib):
        me: Any = self
        me._settings = settings
        me._library = SimpleNamespace(resolver=lambda: lib, cache=None,
                                      restore_memo=None)


class RestoreTest(_Base):

    def test_a_restored_foreign_path_is_found_under_the_reference_path(self):
        lib = _Lib(self.real)
        entry = _Restore(self.settings, lib)._resolve_entry(FOREIGN)
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(Path(entry.path), self.real)

    def test_a_path_found_as_it_is_is_not_searched(self):
        lib = _Lib(self.real)
        _Restore(self.settings, lib)._resolve_entry(str(self.real))
        self.assertEqual(lib.asked, [str(self.real)])


class _Voices:
    def __init__(self):
        self.fired = []

    def is_playing(self, _key):
        return False

    def fire(self, key, pad):
        self.fired.append((key, pad.path))
        return True


class _Status:
    def __init__(self):
        self.text = ""

    def showMessage(self, text, *_a):
        self.text = text


class _Desk(CartwallMixin):
    def __init__(self, settings, wall):
        me: Any = self
        me._settings = settings
        me._cartwall = wall
        me._cart_voices = _Voices()
        status = _Status()
        me.statusBar = lambda: status


class CartwallPadTest(_Base):

    def _wall(self, path):
        wall = CartwallWidget()
        self.addCleanup(reap_widget, wall)
        page = pc.Page(name="1")
        page.pads[(0, 0)] = pc.CartPad(path=path)
        wall.set_wall((2, 2), [page])
        return wall

    def test_a_pad_on_a_moved_file_fires_the_file_found(self):
        wall = self._wall(FOREIGN)
        desk = _Desk(self.settings, wall)
        stub: Any = desk
        stub._file_check_for_wall()
        desk._on_pad_clicked((0, 0, 0))
        self.assertEqual(stub._cart_voices.fired, [((0, 0, 0), str(self.real))])
        # The stored path stays: the stick may come back as F:.
        pad = wall.pad_at((0, 0, 0))
        assert pad is not None
        self.assertEqual(pad.path, FOREIGN)

    def test_a_pad_found_elsewhere_is_not_red(self):
        wall = self._wall(FOREIGN)
        _Desk(self.settings, wall)._file_check_for_wall()
        wall.refresh_missing()
        self.assertEqual(wall._missing, set())

    def test_a_pad_found_nowhere_stays_red_and_silent(self):
        wall = self._wall(r"F:\gone\nowhere.mp3")
        desk = _Desk(self.settings, wall)
        stub: Any = desk
        stub._file_check_for_wall()
        wall.refresh_missing()
        self.assertEqual(wall._missing, {(0, (0, 0))})
        desk._on_pad_clicked((0, 0, 0))
        self.assertEqual(stub._cart_voices.fired, [])


if __name__ == "__main__":
    unittest.main()
