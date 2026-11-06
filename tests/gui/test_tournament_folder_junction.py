"""A dropped folder with a junction back to a parent is read once (review item 12).

`Path.is_dir()` follows a junction, so `_folder_node` recursed until Python
gave up with RecursionError on the worker thread, which died silently and the
drop reported "no playlist found".
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tourn_junction_"))

from gui.tournament_tree import TournamentTree


class _Walker:
    """Only what `_folder_node` touches: itself."""
    _folder_node = TournamentTree._folder_node


def _names(node) -> list:
    out = []
    for child in node["children"]:
        out.append(child["name"])
        out.extend(_names(child) if "children" in child else [])
    return out


@unittest.skipUnless(sys.platform == "win32", "junctions are a Windows thing")
class DroppedFolderJunctionTests(unittest.TestCase):
    def test_a_junction_back_to_a_parent_is_not_followed(self):
        with tempfile.TemporaryDirectory(prefix="dp_tourn_j_") as d:
            root = Path(d)
            (root / "Sa").mkdir()
            (root / "Sa" / "a.m3u").write_text("x.mp3\n")
            (root / "top.m3u").write_text("y.mp3\n")
            link = root / "Sa" / "loop"
            made = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(root)],
                                  capture_output=True)
            if made.returncode != 0:
                self.skipTest("mklink /J not available here")
            try:
                node = _Walker()._folder_node(root)
            finally:
                os.rmdir(link)
        self.assertEqual(sorted(_names(node)), ["Sa", "a", "top"])

    def test_a_directory_symlink_back_to_a_parent_is_not_followed_either(self):
        """The guard asked is_junction() only. A symlink to a directory is followed
        by is_dir() the same way. Creating one needs a privilege this test may not
        have, so a junction stands in and reports itself as a symlink."""
        from unittest import mock
        with tempfile.TemporaryDirectory(prefix="dp_tourn_s_") as d:
            root = Path(d)
            (root / "Sa").mkdir()
            (root / "Sa" / "a.m3u").write_text("x.mp3\n")
            link = root / "Sa" / "loop"
            made = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(root)],
                                  capture_output=True)
            if made.returncode != 0:
                self.skipTest("mklink /J not available here")
            real_symlink = Path.is_symlink
            try:
                with mock.patch.object(Path, "is_junction", lambda self: False),                         mock.patch.object(Path, "is_symlink",
                                          lambda self: self.name == "loop"
                                          or real_symlink(self)):
                    node = _Walker()._folder_node(root)
            finally:
                os.rmdir(link)
        self.assertEqual(sorted(_names(node)), ["Sa", "a"])


if __name__ == "__main__":
    unittest.main()
