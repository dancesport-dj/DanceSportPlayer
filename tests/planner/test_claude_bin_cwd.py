"""A claude.exe in the current folder is not the claude CLI (review item 31).

Windows' lookup tries the current folder first, so a planted claude.exe would
otherwise run with every prompt the app sends.
"""
import os
import unittest
from pathlib import Path
from unittest import mock

from planner.generate import llm


class ResolveClaudeBinCwdTests(unittest.TestCase):
    def resolve(self, found):
        with mock.patch.dict(os.environ, {"CLAUDE_BIN": ""}), \
                mock.patch.object(llm.shutil, "which", return_value=found), \
                mock.patch.object(llm, "_CLAUDE_BIN_FALLBACKS", ()):
            return llm.resolve_claude_bin()

    def test_a_copy_in_the_current_folder_is_skipped(self):
        self.assertIsNone(self.resolve(str(Path.cwd() / "claude.exe")))

    def test_a_copy_elsewhere_on_the_path_is_used(self):
        elsewhere = str(Path.cwd().parent / "bin" / "claude.exe")
        self.assertEqual(self.resolve(elsewhere), elsewhere)


if __name__ == "__main__":
    unittest.main()
