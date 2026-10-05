#!/usr/bin/env python3
"""❔ F1 — the cheat sheet knows Ctrl + A in 🏆 Tournaments and the ★ click.

Run:  py -m unittest tests.gui.test_shortcuts_tournaments_stars -v

Both came after the sheet was written: Ctrl + A marks every slot of a
Tournaments folder (every entry of the tree in the tracks view), and a click
on the ★ column rates a title. The manual's shortcut chapter lists them; the
sheet it calls "the same list" did not.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_keys_tour_"))

from gui.shortcuts import shortcut_rows  # noqa: E402


class TournamentsAndStarsSheetTest(unittest.TestCase):

    def test_ctrl_a_in_tournaments_is_listed(self):
        rows = [(l, r) for l, r in shortcut_rows()
                if l.startswith("Ctrl + A") and "🏆" in l]
        self.assertEqual(len(rows), 1, shortcut_rows())
        self.assertIn("Del", rows[0][1])

    def test_the_star_click_is_listed(self):
        rows = [(l, r) for l, r in shortcut_rows() if "★" in l]
        self.assertEqual(len(rows), 1, shortcut_rows())
        self.assertIn("clear", rows[0][1])


if __name__ == "__main__":
    unittest.main()
