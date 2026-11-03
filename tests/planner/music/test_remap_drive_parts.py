"""A drive part inside a foreign path must not re-root the candidate (review item 52)."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from planner.music.paths import PathRemapper


@unittest.skipUnless(sys.platform == "win32", "drive parts re-root on Windows only")
class DrivePartTests(unittest.TestCase):
    def test_a_drive_part_never_leaves_the_root(self):
        root = Path(tempfile.gettempdir()) / "dp_remap_root"
        with mock.patch.object(Path, "is_file", return_value=True):
            found = PathRemapper._under(r"F:\music\D:\x.mp3", root)
        self.assertIsNotNone(found)
        self.assertTrue(found.is_relative_to(root), found)


if __name__ == "__main__":
    unittest.main()
