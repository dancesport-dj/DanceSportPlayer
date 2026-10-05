#!/usr/bin/env python3
"""Re-rooting a foreign track path onto the folders this PC keeps music in.

Run:  py -m unittest tests.planner.test_path_remap -v

A playlist written on the other PC names `C:\\Users\\…\\my music\\…`, the same
file lives under `F:\\my music` here. The remapper may only ever return a path
that is really on disk — 🧭 Fix paths overwrites .m3u files with what comes
back, so a plausible guess is worse than no answer.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from planner.paths import (PathRemapper, foreign_name, foreign_parts,
                           home_search_roots, parse_remap_paths)


class ParseRemapPathsTest(unittest.TestCase):

    def test_the_text_box_hands_over_one_folder_per_line(self):
        self.assertEqual(
            parse_remap_paths("F:\\my music\n\n  C:\\Users\\me\\my music  \n"),
            ["F:\\my music", "C:\\Users\\me\\my music"])

    def test_the_settings_file_hands_over_a_list(self):
        self.assertEqual(parse_remap_paths(["F:\\my music", ""]), ["F:\\my music"])

    def test_the_same_folder_twice_is_searched_once(self):
        """Case and a trailing separator are the same folder on Windows."""
        self.assertEqual(parse_remap_paths("F:\\My Music\nf:\\my music\\\n"),
                         ["F:\\My Music"])

    def test_a_pasted_path_keeps_its_quotes_out(self):
        self.assertEqual(parse_remap_paths('"F:\\my music"'), ["F:\\my music"])

    def test_nothing_configured_is_no_folders(self):
        self.assertEqual(parse_remap_paths(None), [])


class ForeignPathTest(unittest.TestCase):
    """Reading a path written by the OTHER operating system.

    `Path` only knows its own separator: on macOS `Path("F:\\my music\\x.mp3")`
    is one single filename, backslashes and all, so there is nothing to re-root
    and nothing to match by name. Every .m3u Marcel's Windows machine writes
    carries exactly that shape, so the pieces are cut out by hand instead."""

    def test_a_windows_path_falls_apart_into_its_folders(self):
        self.assertEqual(foreign_parts(r"F:\my music\tanzcds\SB\Senorita.mp3"),
                         ("my music", "tanzcds", "SB", "Senorita.mp3"))

    def test_the_drive_letter_is_not_a_folder(self):
        """C: and F: name a volume that does not exist on a Mac — what the
        search folders have to line up with starts one step later."""
        self.assertEqual(foreign_parts(r"C:\Users\me\my music\x.mp3"),
                         ("Users", "me", "my music", "x.mp3"))

    def test_a_posix_path_falls_apart_the_same_way(self):
        self.assertEqual(
            foreign_parts("/Users/me/Music/tanzcds/SB/Senorita.mp3"),
            ("Users", "me", "Music", "tanzcds", "SB", "Senorita.mp3"))

    def test_both_separators_in_one_path_are_read(self):
        """Hand-edited playlists and Qt file dialogs mix them."""
        self.assertEqual(foreign_parts("F:/my music\\tanzcds/x.mp3"),
                         ("my music", "tanzcds", "x.mp3"))

    def test_a_unc_share_keeps_its_folders_and_drops_the_server(self):
        self.assertEqual(foreign_parts(r"\\nas\musik\tanzcds\x.mp3"),
                         ("nas", "musik", "tanzcds", "x.mp3"))

    def test_the_filename_is_readable_whatever_wrote_it(self):
        self.assertEqual(foreign_name(r"F:\my music\tanzcds\Senorita.mp3"),
                         "Senorita.mp3")
        self.assertEqual(foreign_name("/Users/me/Music/Senorita.mp3"),
                         "Senorita.mp3")

    def test_a_bare_filename_is_left_as_it_is(self):
        self.assertEqual(foreign_parts("Senorita.mp3"), ("Senorita.mp3",))
        self.assertEqual(foreign_name("Senorita.mp3"), "Senorita.mp3")

    def test_nothing_is_nothing(self):
        self.assertEqual(foreign_parts(""), ())
        self.assertEqual(foreign_name(""), "")


class HomeSearchRootsTest(unittest.TestCase):
    """Where to look on a Mac when nothing is configured yet.

    A fresh install on the Mac has no Referenzpfad and no search folders, so
    every `C:`/`F:` path in a carried-over playlist would stay broken with
    nothing to try. The user's own home folder is the one place that is always
    there and always the right neighbourhood."""

    def test_the_mac_offers_the_home_folder_and_its_music(self):
        """Marcel's Mac holds the library at /Users/<user>/Music/my music."""
        with mock.patch.object(sys, "platform", "darwin"):
            roots = home_search_roots()
        self.assertEqual(roots, [Path.home(), Path.home() / "Music"])

    def test_windows_offers_none(self):
        """The drives named in the playlists are the drives of this PC."""
        with mock.patch.object(sys, "platform", "win32"):
            self.assertEqual(home_search_roots(), [])


class PathRemapperTest(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dp_remap_"))
        self.root = self.tmp / "my music"
        self.track = self.root / "tanzcds" / "lateincd" / "005 - Song (SA 50).mp3"
        self.track.parent.mkdir(parents=True)
        self.track.write_bytes(b"x")
        # What the other PC wrote into the playlist.
        self.foreign = Path("C:/Users/me/Documents/datein/my music/tanzcds/"
                            "lateincd/005 - Song (SA 50).mp3")

    def test_it_anchors_on_the_roots_own_folder_name(self):
        got = PathRemapper([self.root]).remap(self.foreign)
        self.assertEqual(got, self.track)

    def test_a_backslash_path_is_re_rooted_on_any_os(self):
        """The shape a Windows .m3u really carries. On macOS `Path` reads the
        whole line as one filename, so this used to find nothing there."""
        foreign = r"F:\my music\tanzcds\lateincd\005 - Song (SA 50).mp3"
        self.assertEqual(PathRemapper([self.root]).remap(foreign), self.track)

    def test_the_mac_finds_the_library_under_the_home_music_folder(self):
        """The real case: `F:\\my music\\…` on the PC, `~/Music/my music/…` on
        the Mac — the whole chain behind the drive letter re-roots in one go."""
        mac_music = self.tmp / "Users" / "masmuster" / "Music"
        track = mac_music / "my music" / "tanzcds" / "lateincd" / "005 - Song (SA 50).mp3"
        track.parent.mkdir(parents=True)
        track.write_bytes(b"x")
        foreign = r"F:\my music\tanzcds\lateincd\005 - Song (SA 50).mp3"
        self.assertEqual(PathRemapper([mac_music]).remap(foreign), track)

    def test_a_root_further_up_still_finds_the_file_by_its_tail(self):
        """The root's name ('my music') need not appear in the foreign path."""
        foreign = Path("D:/anderer name/tanzcds/lateincd/005 - Song (SA 50).mp3")
        self.assertEqual(PathRemapper([self.root]).remap(foreign), self.track)

    def test_the_longest_matching_tail_wins(self):
        """A decoy of the same name one folder up must not be preferred."""
        decoy = self.root / "005 - Song (SA 50).mp3"
        decoy.write_bytes(b"x")
        self.assertEqual(PathRemapper([self.root]).remap(self.foreign), self.track)

    def test_the_first_root_that_has_the_file_wins(self):
        missing = self.tmp / "not there"
        self.assertEqual(PathRemapper([missing, self.root]).remap(self.foreign),
                         self.track)

    def test_a_file_no_root_holds_is_left_alone(self):
        gone = self.foreign.with_name("nowhere.mp3")
        self.assertIsNone(PathRemapper([self.root]).remap(gone))

    def test_a_folder_is_never_offered_as_the_track(self):
        """`…/my music/tanzcds` under a root named 'tanzcds' cuts down to the
        root itself — which exists, and is not a track."""
        foreign = Path("C:/Users/me/my music/tanzcds")
        self.assertIsNone(PathRemapper([self.root / "tanzcds"]).remap(foreign))

    def test_without_a_configured_folder_it_reads_as_empty(self):
        self.assertFalse(PathRemapper([]))
        self.assertIsNone(PathRemapper([]).remap(self.foreign))
        self.assertTrue(PathRemapper([self.root]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
