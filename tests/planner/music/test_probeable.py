"""The audio probes (ffmpeg, fpcalc) and the playlist-entry builder take paths out of
dropped playlists and saved decks. A foreign network location there is never stat'ed
or handed to a tool (SMB login = NTLM hash leak, dead host = frozen worker) - unless it
lies under a share the user configured themself (library on a NAS). Review 2026-11-06
#1.4, second half."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from gui.decks.playlist_entries import resolve_playlist_entries
from planner.music import paths
from shared.audio import audio_probes, chromaprint

UNC = r"\\evil-host\share\x.mp3"
OWN = r"\\nas\music\a\x.mp3"


class _Shares(unittest.TestCase):

    def setUp(self):
        paths.set_own_shares({"library_dir": r"\\nas\music"})
        self.addCleanup(paths.set_own_shares, {})


class IsProbeableTest(_Shares):

    def test_a_foreign_network_path_is_never_touched(self):
        for line in (UNC, "//evil-host/share/x.mp3", "http://evil/x.mp3"):
            with mock.patch.object(Path, "is_file") as spy:
                self.assertFalse(paths.is_probeable(line), line)
            spy.assert_not_called()

    def test_a_configured_share_is_probed(self):
        with mock.patch.object(Path, "is_file", return_value=True):
            self.assertTrue(paths.is_probeable(OWN))

    def test_a_local_file_is_probed(self):
        with mock.patch.object(Path, "is_file", return_value=True):
            self.assertTrue(paths.is_probeable(r"C:\music\x.mp3"))

    def test_the_shares_follow_the_settings(self):
        paths.set_own_shares({})
        with mock.patch.object(Path, "is_file") as spy:
            self.assertFalse(paths.is_probeable(OWN))
        spy.assert_not_called()


class ProbesTest(_Shares):

    def test_ffmpeg_probe_refuses_a_foreign_path(self):
        with mock.patch.object(audio_probes.subprocess, "Popen") as popen, \
                mock.patch.object(Path, "is_file") as spy:
            self.assertIsNone(audio_probes._ffmpeg_probe(["ffmpeg"], Path(UNC), "x"))
        popen.assert_not_called()
        spy.assert_not_called()

    def test_fingerprint_refuses_a_foreign_path(self):
        with mock.patch.object(chromaprint.subprocess, "Popen") as popen, \
                mock.patch.object(Path, "is_file") as spy:
            self.assertIsNone(chromaprint.fingerprint_file("fpcalc", UNC))
        popen.assert_not_called()
        spy.assert_not_called()


class _Lib:
    def __init__(self):
        self.entries = []
        self.made = []

    def make_external_entry(self, path, cache):
        self.made.append(str(path))
        return SimpleNamespace(path=path)


class PlaylistEntriesTest(_Shares):

    def test_a_foreign_network_line_is_not_read(self):
        lib = _Lib()
        out = resolve_playlist_entries([Path(UNC)], lib, None)
        self.assertEqual(out, [])
        self.assertEqual(lib.made, [])

    def test_a_configured_share_line_is_read(self):
        lib = _Lib()
        out = resolve_playlist_entries([Path(OWN)], lib, None)
        self.assertEqual(len(out), 1)
        self.assertEqual(lib.made, [str(Path(OWN))])


if __name__ == "__main__":
    unittest.main(verbosity=2)
