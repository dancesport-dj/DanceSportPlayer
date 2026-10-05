#!/usr/bin/env python3
"""The non-tournament library CATEGORIES, and the scan that lets them through.

Run:  py -m unittest tests.planner.test_library_categories -v

`special/` is the umbrella the openings, fanfares, award and Ausmarsch music
live under. It used to be a HARD skip in `MusicLibrary.scan`, so its ~130 loose
files never reached the library at all — not even to search for. They are now
category 'background': they load, they are browsable, and they still stay out
of every generation pool.
"""

import os
import tempfile
import unittest
from pathlib import Path

# Before the first planner import: the scan below writes cache rows, and those
# must never land in the real audio_features.db.
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_cat_state_"))

from planner.db import AudioCache  # noqa: E402
from planner.library import MusicLibrary  # noqa: E402
from planner.models import (  # noqa: E402
    MusicEntry,
    folder_category_of_parts,
    is_non_turnier,
    library_category,
)


def _entry(*parts):
    return MusicEntry(path=Path("C:/lib").joinpath(*parts), title=parts[-1])


class FolderCategoryTest(unittest.TestCase):
    """Which folder means which category."""

    def test_special_is_background(self):
        self.assertEqual(folder_category_of_parts(("special",)), "background")

    def test_a_deeper_folder_still_wins(self):
        # Hymnen sits INSIDE special/ — the anthem category has to survive it.
        self.assertEqual(folder_category_of_parts(("special", "Hymnen")),
                         "anthems")
        self.assertEqual(folder_category_of_parts(("special", "Musikbett")),
                         "background")
        self.assertEqual(folder_category_of_parts(("special", "unangepasst")),
                         "wrong_tempo")

    def test_an_uncategorised_child_of_special_inherits_it(self):
        self.assertEqual(folder_category_of_parts(("special", "dC2024")),
                         "background")

    def test_matching_is_by_whole_segment(self):
        # 'specialVersions' is a different folder and stays uncategorised.
        self.assertEqual(folder_category_of_parts(("specialVersions",)), "")
        self.assertEqual(folder_category_of_parts(("lateincd",)), "")

    def test_a_special_track_is_kept_out_of_generation(self):
        e = _entry("special", "Who moved the Clock today.mp3")
        self.assertEqual(library_category(e), "background")
        self.assertTrue(is_non_turnier(e))

    def test_a_normal_track_is_not(self):
        e = _entry("lateincd", "002 SA Cinema Italiano T51.mp3")
        self.assertEqual(library_category(e), "")
        self.assertFalse(is_non_turnier(e))


class ScanSkipTest(unittest.TestCase):
    """What the competition scan (skip_special=True) actually loads."""

    @classmethod
    def setUpClass(cls):
        cls.root = Path(tempfile.mkdtemp(prefix="dp_cat_"))
        cls.made = (
            "lateincd/002 SA Cinema T51.mp3",
            "special/Who moved the Clock today.mp3",
            "special/Hymnen/Deutschlandlied.mp3",
            "special/dC2024/Opening.mp3",
            "EndrundenALT/03 LW Final.mp3",       # still skipped
            "sox/raw.mp3",                        # hard-excluded, never loads
        )
        for rel in cls.made:
            p = cls.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"not really an mp3")

    def _scan(self, **kw):
        lib = MusicLibrary()
        lib.scan(AudioCache(), music_dir=self.root, learn=False, analyze=False,
                 interactive=False, **kw)
        return {e.path.name for e in lib.entries}

    def test_the_loose_special_file_loads(self):
        self.assertIn("Who moved the Clock today.mp3", self._scan())

    def test_the_categorised_subfolders_load_too(self):
        names = self._scan()
        self.assertIn("Deutschlandlied.mp3", names)
        self.assertIn("Opening.mp3", names)

    def test_endrunden_and_sox_stay_out(self):
        names = self._scan()
        self.assertNotIn("03 LW Final.mp3", names)
        self.assertNotIn("raw.mp3", names)

    def test_sox_stays_out_even_without_the_special_skip(self):
        names = self._scan(skip_special=False)
        self.assertNotIn("raw.mp3", names)
        self.assertIn("03 LW Final.mp3", names)   # only the special skip is off

    def test_what_loaded_from_special_is_soft_excluded(self):
        lib = MusicLibrary()
        lib.scan(AudioCache(), music_dir=self.root, learn=False, analyze=False,
                 interactive=False)
        by_name = {e.path.name: e for e in lib.entries}
        self.assertTrue(is_non_turnier(by_name["Who moved the Clock today.mp3"]))
        self.assertFalse(is_non_turnier(by_name["002 SA Cinema T51.mp3"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
