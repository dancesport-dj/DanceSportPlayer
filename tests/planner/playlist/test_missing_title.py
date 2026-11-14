"""🔭 A red title's file is gone: the files of the library that are that song.

Run:  py -m unittest tests.planner.playlist.test_missing_title -v
"""
import tempfile
import unittest
from pathlib import Path

from planner.models import MusicEntry
from planner.playlist import missing_title


class SameSongFilesTest(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def entry(self, name, dance="LW", exists=True) -> MusicEntry:
        p = self.dir / f"{name}.mp3"
        if exists:
            p.write_bytes(b"x")
        return MusicEntry(path=p, title=name, dance=dance, bpm=None)

    def find(self, missing, entries, dance="LW", skip=()):
        gone = self.dir / "gone" / f"{missing}.mp3"
        return [Path(e.path).stem for e in
                missing_title.same_song_files(gone, dance, entries, skip)]

    def test_a_renamed_cut_is_found(self):
        cut = self.entry("1-14 A New Life (LW 29)_cut")
        other = self.entry("Moon River (LW 29)")
        self.assertEqual(self.find("A New Life (LW 29)", [other, cut]),
                         ["1-14 A New Life (LW 29)_cut"])

    def test_the_same_title_comes_before_a_longer_version(self):
        longer = self.entry("Friends and Lovers Cut Version (SW 12)", "SW")
        same = self.entry("07 Friends and Lovers (SW 12)", "SW")
        self.assertEqual(self.find("Friends and Lovers (SW 12)", [longer, same], "SW"),
                         [same.path.stem, longer.path.stem])

    def test_another_dance_is_another_song(self):
        rumba = self.entry("Candela (RB 26)", "RB")
        self.assertEqual(self.find("Candela (CC 32)", [rumba], "CC"), [])

    def test_an_unknown_dance_matches_any(self):
        found = self.entry("Candela (RB 26)", "RB")
        self.assertEqual(len(self.find("Candela", [found], None)), 1)

    def test_a_file_that_is_not_there_is_not_offered(self):
        ghost = self.entry("A New Life (LW 29)_cut", exists=False)
        self.assertEqual(self.find("A New Life (LW 29)", [ghost]), [])

    def test_a_file_the_list_holds_already_is_left_out(self):
        held = self.entry("A New Life (LW 29)_cut")
        self.assertEqual(self.find("A New Life (LW 29)", [held], skip=[held.path]), [])

    def test_a_short_title_is_not_found_inside_a_longer_one(self):
        longer = self.entry("Rio de Janeiro Nights (SB 50)", "SB")
        self.assertEqual(self.find("Rio (SB 50)", [longer], "SB"), [])

    def test_the_missing_path_itself_is_never_the_answer(self):
        entry = self.entry("A New Life (LW 29)", exists=True)
        found = missing_title.same_song_files(entry.path, "LW", [entry])
        self.assertEqual(found, [])


class FolderMatchesTest(unittest.TestCase):
    """The file may have been renamed in its own folder, which the library has
    not scanned again: the folder it was in is looked at on disk too."""

    EXTS = (".mp3", ".flac")

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def touch(self, name) -> Path:
        p = self.dir / name
        p.write_bytes(b"x")
        return p

    def names(self, missing) -> list[str]:
        return [p.name for p in
                missing_title.folder_matches(self.dir / missing, self.EXTS)]

    def test_the_cut_removed_in_the_same_folder_is_found(self):
        self.touch("A New Life (LW 29).mp3")
        self.touch("Moon River (LW 29).mp3")
        self.assertEqual(self.names("A New Life (LW 29)_cut.mp3"),
                         ["A New Life (LW 29).mp3"])

    def test_the_same_title_comes_before_a_longer_version(self):
        self.touch("Friends and Lovers Cut Version (SW 12).mp3")
        self.touch("07 Friends and Lovers (SW 12).flac")
        self.assertEqual(self.names("Friends and Lovers (SW 12)_cut.mp3"),
                         ["07 Friends and Lovers (SW 12).flac",
                          "Friends and Lovers Cut Version (SW 12).mp3"])

    def test_only_audio_files_count(self):
        self.touch("A New Life (LW 29).txt")
        self.assertEqual(self.names("A New Life (LW 29)_cut.mp3"), [])

    def test_the_missing_file_itself_is_left_out(self):
        self.touch("A New Life (LW 29).mp3")
        self.assertEqual(self.names("A New Life (LW 29).mp3"), [])

    def test_a_folder_that_is_gone_finds_nothing(self):
        self.assertEqual(
            missing_title.folder_matches(self.dir / "nope" / "A.mp3", self.EXTS), [])


if __name__ == "__main__":
    unittest.main()
