"""📁 The skip-folder list is matched accent-folded (#68)."""
import unittest

from tools.find_missing_metadata import is_skipped_path


class SkipFoldersTest(unittest.TestCase):

    def test_an_accented_forro_folder_is_skipped(self):
        for path in ("D:/Music/Forró/a.mp3", "D:/Music/FORRÓ/a.mp3",
                     "D:/Music/Forro/a.mp3", "D:/Music/Forró/a.mp3"):  # NFC, caps, plain, NFD
            with self.subTest(path=path):
                self.assertTrue(is_skipped_path(path))

    def test_other_folders_are_not(self):
        self.assertFalse(is_skipped_path("D:/Music/Latin/a.mp3"))


if __name__ == "__main__":
    unittest.main()
