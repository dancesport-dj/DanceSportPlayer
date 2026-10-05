#!/usr/bin/env python3
"""❔ F1 — what the cheat sheet says a 📚 library row does.

Run:  py -m unittest tests.gui.test_shortcuts_library_row -v

The sheet said "▶ / double-click a 📚 library row: preview that track in the
mini player". Only ▶ previews: a double-click on any other column hands the
file to the system's audio player (`LibraryBrowser._on_double_click`). The
sheet has to say both, each with what it really does.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_keys_lib_"))

from gui.shortcuts import shortcut_rows  # noqa: E402


class LibraryRowSheetTest(unittest.TestCase):

    @staticmethod
    def library_rows():
        return {left: right for left, right in shortcut_rows()
                if "📚" in left}

    def test_a_double_click_is_not_sold_as_a_preview(self):
        for left, right in self.library_rows().items():
            if "double-click" in left.lower():
                self.assertNotIn("Preview", right, left)

    def test_the_double_click_opens_the_external_player(self):
        rows = self.library_rows()
        double = [r for l, r in rows.items() if "double-click" in l.lower()]
        self.assertEqual(len(double), 1, rows)
        self.assertIn("external", double[0])

    def test_play_still_previews_in_the_mini_player(self):
        rows = self.library_rows()
        play = [r for l, r in rows.items() if l.startswith("▶")]
        self.assertEqual(len(play), 1, rows)
        self.assertIn("mini player", play[0])


if __name__ == "__main__":
    unittest.main()
