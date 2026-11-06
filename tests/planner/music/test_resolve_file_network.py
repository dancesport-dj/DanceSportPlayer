"""`resolve_file` backs the row probes of decks, wishlists and pads, and its paths
come out of saved decks and dropped playlists written by someone else. A network
location in there is never stat'ed (SMB login = NTLM hash leak, dead host = frozen
window) - unless it lies under a share the user configured themself (library on a
NAS). Review 2026-11-06 #1.4."""
import unittest
from pathlib import Path
from unittest import mock

from planner.music.paths import is_own_share, resolve_file

UNC = r"\\evil-host\share\x.mp3"


class ResolveFileNetworkTest(unittest.TestCase):

    def test_a_foreign_network_path_is_never_touched(self):
        for line in (UNC, "//evil-host/share/x.mp3", "http://evil/x.mp3"):
            with mock.patch.object(Path, "is_file") as spy:
                self.assertIsNone(resolve_file(line, {}), line)
            spy.assert_not_called()

    def test_a_share_the_user_configured_still_resolves(self):
        settings = {"library_dir": r"\\nas\music"}
        with mock.patch.object(Path, "is_file", return_value=True):
            self.assertEqual(resolve_file(r"\\nas\music\a\x.mp3", settings),
                             Path(r"\\nas\music\a\x.mp3"))

    def test_the_prefix_must_end_on_a_folder_boundary(self):
        self.assertFalse(is_own_share(r"\\nas\music-evil\x.mp3",
                                      {"library_dir": r"\\nas\music"}))
        self.assertTrue(is_own_share("//NAS/Music/x.mp3",
                                     {"library_dir": "\\\\nas\\music\\"}))

    def test_the_search_folders_count_as_own(self):
        self.assertTrue(is_own_share(r"\\nas\alt\x.mp3",
                                     {"remap_paths": [r"\\nas\alt"]}))
        self.assertTrue(is_own_share(r"\\nas\ref\x.mp3",
                                     {"reference_path": r"\\nas\ref"}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
