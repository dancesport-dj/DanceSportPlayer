#!/usr/bin/env python3
"""Tier 1 (2026-11-04): a party / competition list on a real MainWindow.

Run:  py -m unittest tests.gui.test_click_tier1_party_list -v

1. A title can be removed from the list (Del key and context menu).
2. A title can be dragged from the list to the wishlist.
"""
import unittest

from PySide6.QtCore import Qt

from tests.gui.monkey_support import ClickThrough


class PartyListTierOneTest(ClickThrough):
    def party(self, op):
        """A competition training list: the window's own loader, with heats."""
        win = self.win
        lib = [e for e in win._library.lib.entries if e.dance][:60] if hasattr(win._library.lib, "entries") else []
        self.assertTrue(lib, "no library entries")
        win._warmup_opts = {"mode": "competition", "competition": {
            "style": "Latin", "dance_class": "S", "dances": ["CC", "SA"],
            "heats": 3, "rounds": 2, "final_heats": 1}}
        win._on_warmup_done(lib[:12])
        return win._deckset.warmup_table

    def test_del_removes_a_title(self):
        with self.clicking() as op:
            panel = self.party(op)
            before = self.titles(panel)
            self.click_cell(panel, self.song_rows(panel)[2], 0)
            op.answer(lambda w: "Remove" in (getattr(w, "windowTitle", lambda: "")()),
                      lambda w: next(b for b in w.buttons()
                                     if "with slot" in b.text()).click())
            self.key(Qt.Key.Key_Delete, widget=panel)
            self.assertEqual(len(self.titles(panel)), len(before) - 1)

    def test_title_drags_to_the_wishlist(self):
        with self.clicking() as op:
            panel = self.party(op)
            wish = self.win._deckset.wishlists[0]
            n = len(self.titles(wish))
            self.drag(panel, self.song_rows(panel)[1], wish)
            self.assertEqual(len(self.titles(wish)), n + 1)

    def test_wishlist_clean_counts_the_party_list(self):
        """3: 'Remove tracks already in a playlist' knows the party list too."""
        with self.clicking() as op:
            panel = self.party(op)
            wish = self.win._deckset.wishlists[0]
            held = [self.entry_at(r, panel) for r in self.song_rows(panel)]
            outside = next(e for e in self.win._library.lib.entries
                           if e.dance and e.path not in {h.path for h in held})
            wish.load_wishlist([held[0], held[1], outside], self.win._play_or_stop, None)
            self.assertEqual(self.win._clean_wishlist_against_playlists(wish), 2)
            self.assertEqual(len(self.titles(wish)), 1)


if __name__ == "__main__":
    unittest.main()
