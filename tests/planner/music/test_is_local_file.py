"""A line of an imported playlist or venue pack that names a network location
is never touched on disk (review #16): opening a UNC path starts an SMB login
that leaks the user's NTLM hash and can hang on a dead host."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from planner.event import venue_pack
from planner.music.library import MusicLibrary
from planner.music.paths import is_local_file
from planner.playlist.m3u import resolve_import_path

UNC = r"\\evil-host\share\x.mp3"


def _touched(spy) -> list[str]:
    return [str(c.args[0]) if c.args else str(c.kwargs) for c in spy.call_args_list]


class IsLocalFileTest(unittest.TestCase):

    def test_network_lines_are_refused_without_a_filesystem_call(self):
        for line in (UNC, "//evil-host/share/x.mp3", "http://evil/x.mp3",
                     "smb://evil/share/x.mp3", f'"{UNC}"'):
            with mock.patch.object(Path, "is_file") as spy:
                self.assertFalse(is_local_file(line), line)
            spy.assert_not_called()

    def test_a_real_local_file_is_one(self):
        d = Path(tempfile.mkdtemp(prefix="dp_local_"))
        f = d / "a.mp3"
        f.write_bytes(b"ID3")
        self.assertTrue(is_local_file(f))
        self.assertFalse(is_local_file(d / "gone.mp3"))

    def test_a_nul_is_not_a_file(self):
        self.assertFalse(is_local_file("a\x00b.mp3"))


class ImportDoesNotReachTheNetworkTest(unittest.TestCase):

    def test_a_unc_line_in_a_playlist_stays_a_ghost(self):
        lib = MusicLibrary()
        cache = mock.Mock()
        with mock.patch.object(Path, "is_file") as spy, \
                mock.patch.object(MusicLibrary, "make_external_entry") as make:
            entry, found, _hit = resolve_import_path(UNC, lib, cache, "Song")
        self.assertFalse(found)
        make.assert_not_called()
        self.assertFalse([t for t in _touched(spy) if "evil-host" in t])
        self.assertEqual(entry.title, "Song")

    def test_a_unc_track_of_a_venue_pack_is_not_statted(self):
        with mock.patch.object(Path, "is_file") as spy:
            self.assertFalse(venue_pack._exists(UNC))
        spy.assert_not_called()


if __name__ == "__main__":
    unittest.main()
