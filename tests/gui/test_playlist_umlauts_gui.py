#!/usr/bin/env python3
"""The window's own playlist reads keep the umlauts too.

Run:  py -m unittest tests.gui.test_playlist_umlauts_gui -v

A dropped .m3u, the party list a warm-up is built from, the reference base the
cleaner compares, the pause music and the list's cover image were all read as
UTF-8 with the errors thrown away — in a cp1252 list every path with an umlaut
in it pointed nowhere. They are decoded strictly now. A file that can't be
decoded is not quietly read as empty: a drop says so in a toast, a chosen
party list in a message box, and the reference cleaner fails, because an empty
tournament list would make every reference track look unused.
"""

import os
import shutil
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_umlaut_gui_"))

from planner.playlist_text import PlaylistEncodingError  # noqa: E402

_UNDECODABLE = b"\x81\x8d not text \x8f\x90\r\n"


class _Base(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_umlaut_gui_"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.track = self.dir / "Küss mich (TG 32).mp3"
        self.track.write_bytes(b"")

    def _cp1252(self, *lines) -> Path:
        p = self.dir / "list.m3u"
        p.write_bytes(("\r\n".join(("#EXTM3U",) + lines) + "\r\n").encode("cp1252"))
        return p

    def _undecodable(self) -> Path:
        p = self.dir / "bad.m3u"
        p.write_bytes(_UNDECODABLE)
        return p


class DropTest(_Base):
    """The two `_m3u_track_paths` a drop goes through: the window's and a deck's."""

    def _readers(self):
        from gui.main_dupes import DuplicateCheckMixin
        from gui.table_actions import TableActionsMixin
        return (DuplicateCheckMixin._m3u_track_paths,
                TableActionsMixin._m3u_track_paths)

    def test_a_cp1252_list_names_the_umlaut_file(self):
        p = self._cp1252(str(self.track))
        for read in self._readers():
            self.assertEqual(read(object(), p), [self.track], read.__qualname__)

    def test_an_undecodable_list_is_empty_and_says_so(self):
        p = self._undecodable()
        for read in self._readers():
            with mock.patch("gui.common._show_toast") as toast, \
                 self.assertLogs("dancesport.gui", "WARNING"):
                self.assertEqual(read(object(), p), [], read.__qualname__)
            self.assertIn("bad.m3u", toast.call_args.args[1])


class ReferenceCleanerTest(_Base):

    def test_the_reference_is_split_with_its_umlaut_paths(self):
        from gui.workers import _parse_m3u_blocks
        p = self._cp1252("#EXTINF:90,Küss mich", str(self.track))
        blocks = _parse_m3u_blocks(p)
        self.assertEqual([b["path"] for b in blocks], [self.track])
        self.assertEqual(blocks[0]["title"], "Küss mich")

    def test_an_undecodable_reference_fails_the_run(self):
        from gui.workers import _parse_m3u_blocks
        with self.assertRaises(PlaylistEncodingError):
            _parse_m3u_blocks(self._undecodable())

    def test_the_tournament_lists_are_read_by_a_reader_that_fails_too(self):
        from gui.main_dupes import DuplicateCheckMixin
        fake = types.SimpleNamespace(_cache=None)
        w = DuplicateCheckMixin._make_reference_clean_worker(fake, "ref.m3u", [])
        self.addCleanup(w.deleteLater)
        with self.assertRaises(PlaylistEncodingError):
            w._parse_m3u(self._undecodable())


class PartyListTest(_Base):

    def _fake(self):
        from dancesport_planner import MusicEntry
        entry = MusicEntry(path=self.track, title="Küss mich", dance="TG")
        return types.SimpleNamespace(
            _lib=types.SimpleNamespace(entries=[entry]), _cache=None,
            _remap_index=mock.Mock(side_effect=RuntimeError)), entry

    def test_a_cp1252_party_list_resolves_to_the_library(self):
        from gui.main_generate import GenerateMixin
        fake, entry = self._fake()
        got = GenerateMixin._entries_from_m3u_file(fake, self._cp1252(str(self.track)))
        self.assertEqual(got, [entry])

    def test_an_undecodable_party_list_is_refused_with_a_message(self):
        from gui.main_generate import GenerateMixin
        fake, _entry = self._fake()
        with mock.patch("gui.main_generate.QMessageBox") as box:
            got = GenerateMixin._entries_from_m3u_file(fake, self._undecodable())
        self.assertEqual(got, [])
        box.warning.assert_called_once()
        self.assertIn("bad.m3u", box.warning.call_args.args[2])


class PlayerTest(_Base):

    def test_the_pause_music_list_keeps_its_umlaut_paths(self):
        from player.play_mode_panel import PlayModePanel
        p = self._cp1252(str(self.track))
        self.assertEqual(PlayModePanel._read_m3u(str(p)), [str(self.track)])

    def test_an_undecodable_pause_list_is_empty_and_logged(self):
        from player.play_mode_panel import PlayModePanel
        with self.assertLogs("dancesport", "WARNING"):
            self.assertEqual(PlayModePanel._read_m3u(str(self._undecodable())), [])

    def test_the_list_cover_is_found_through_an_umlaut_path(self):
        from player.artwork import playlist_art
        img = self.dir / "Plakat Küss.png"
        img.write_bytes(b"")
        self.assertEqual(playlist_art(self._cp1252(f"#EXTIMG:{img}")), img)

    def test_an_undecodable_list_just_has_no_cover(self):
        from player.artwork import playlist_art
        self.assertIsNone(playlist_art(self._undecodable()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
