"""A Windows junction that loops back must not make the library scan endless (review item 13).

`DirEntry.is_dir(follow_symlinks=False)` is still true for a junction, so a
junction pointing at one of its own parents was walked again and again until
the path grew too long, listing every file once per round.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from planner.music.library import library_mp3s


def _junction(link: Path, target: Path) -> bool:
    done = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                          capture_output=True)
    return done.returncode == 0


@unittest.skipUnless(sys.platform == "win32", "junctions are a Windows thing")
class JunctionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="dp_junction_")
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _mp3(self, folder: Path, name: str) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(b"ID3")

    def test_a_junction_back_to_a_parent_is_not_walked_again(self):
        self._mp3(self.root, "top.mp3")
        self._mp3(self.root / "sub", "deep.mp3")
        if not _junction(self.root / "sub" / "loop", self.root):
            self.skipTest("mklink /J not available here")
        try:
            names = sorted(p.name for p, _ in library_mp3s(self.root))
        finally:
            os.rmdir(self.root / "sub" / "loop")   # a junction is removed, not emptied
        self.assertEqual(names, ["deep.mp3", "top.mp3"])

    def test_a_junction_to_another_folder_is_still_followed(self):
        outside = Path(tempfile.mkdtemp(prefix="dp_junction_out_"))
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        self._mp3(outside, "far.mp3")
        self._mp3(self.root, "near.mp3")
        if not _junction(self.root / "link", outside):
            self.skipTest("mklink /J not available here")
        try:
            names = sorted(p.name for p, _ in library_mp3s(self.root))
        finally:
            os.rmdir(self.root / "link")
        self.assertEqual(names, ["far.mp3", "near.mp3"])


if __name__ == "__main__":
    unittest.main()
