"""🏷️ A no-repeat set holds paths and title marks; only the paths are expanded.

Run:  .venv/Scripts/python.exe -m unittest tests.planner.test_suggester_title_marks -v

A whole-round re-roll passes the set the other rounds built, paths and
"title:" marks together, back through `expand_used`. A mark is not a file name:
read as one it became "title:title moon river", which would hold back a song
really called "Title Moon River".
"""
import unittest
from pathlib import Path

from planner.generate.suggester import _TITLE_MARK, PlaylistSuggester
from planner.models import MusicEntry
from planner.music.library import MusicLibrary


def _suggester() -> PlaylistSuggester:
    lib = MusicLibrary()
    lib.entries.append(MusicEntry(path=Path(r"C:\music\StandardCD\Moon River (LW 29).mp3"),
                                  title="Moon River (LW 29)", dance="LW", bpm=29))
    return PlaylistSuggester(lib, seed=1)


class TitleMarksTest(unittest.TestCase):

    def test_a_title_mark_passes_through_unchanged(self):
        mark = _TITLE_MARK + "moon river"
        self.assertEqual(_suggester().expand_used({mark}), {mark})

    def test_a_path_still_brings_its_title(self):
        path = r"C:\music\StandardCD\Moon River (LW 29).mp3"
        used = _suggester().expand_used({path})
        self.assertEqual(used, {path, _TITLE_MARK + "moon river"})


if __name__ == "__main__":
    unittest.main()
