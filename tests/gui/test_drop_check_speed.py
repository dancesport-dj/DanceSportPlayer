#!/usr/bin/env python3
"""⏱ Dropping many titles into a list that holds many: the duplicate check must
neither freeze the window nor go unreported.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_drop_check_speed -v

Measured before the fix: 150 titles dropped on a list of 150 took 83 s, 71 s of
it in `title_cluster_map`, rebuilt for every single dropped title. The clusters
are now built once per drop, and a bar with a Cancel button reports the rest.
"""
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from tests.gui.test_same_audio_dupes import _ScratchDbTest

_WORDS = ["Moon", "River", "Candela", "Tango", "Blue", "Night", "Fire", "Dream"]


def _name(i: int, tag: str) -> str:
    return f"{_WORDS[i % 8]} {_WORDS[(i // 8) % 8]} {tag}{i} (LW 29)"


class _FakeBusy:
    """Stands in for gui.common.BusyDialog: records, never shows."""
    made: list = []

    class _Signal:
        def __init__(self):
            self.slots = []

        def connect(self, slot):
            self.slots.append(slot)

    def __init__(self, parent=None, message="", cancelable=False):
        self.message, self.cancelable = message, cancelable
        self.cancel_requested = self._Signal()
        self.progress, self.finished, self.cancel_at = [], 0, None
        _FakeBusy.made.append(self)

    def show_after(self, ms=500):
        pass

    def set_progress(self, done, total, detail="", eta_seconds=-1.0):
        self.progress.append((done, total))
        if self.cancel_at is not None and done >= self.cancel_at:
            for slot in self.cancel_requested.slots:
                slot()

    def finish(self):
        self.finished += 1


class _Base(_ScratchDbTest):

    def setUp(self):
        super().setUp()
        _FakeBusy.made = []

    def wishlist(self, n_held: int):
        held = [self.file("C", _name(i, "h"), bytes([i % 251]) * 600 + i.to_bytes(4, "big"))
                for i in range(n_held)]
        t = self.table()
        t.load_wishlist([self.entry(p) for p in held], play_cb=None, suggester=None)
        t._prime_chroma = lambda _entries: None      # no fpcalc in a unit test
        return t, t._row_meta.entries()

    def dropped(self, n: int, first: int = 1000):
        return [self.entry(self.file("F", _name(first + i, "d"),
                                     bytes([(first + i) % 251]) * 600 + (first + i).to_bytes(4, "big")))
                for i in range(n)]


class ClustersOncePerDropTest(_Base):

    def test_the_title_clusters_are_built_once_per_drop_not_per_title(self):
        t, held = self.wishlist(12)
        new = self.dropped(12)
        with mock.patch("gui.table.table_dynamic.title_cluster_map",
                        wraps=__import__("planner.playlist.checks",
                                         fromlist=["x"]).title_cluster_map) as built:
            t._drop_dup_pairs(new, held)
        self.assertLessEqual(built.call_count, 2)

    def test_the_deck_check_builds_them_once_too(self):
        held = [self.file("C", _name(i, "h")) for i in range(10)]
        t = self.static_deck([[self.entry(p)] for p in held])
        t._prime_chroma = lambda _entries: None
        new = self.dropped(10)
        with mock.patch("gui.table.table_dynamic.title_cluster_map",
                        wraps=__import__("planner.playlist.checks",
                                         fromlist=["x"]).title_cluster_map) as built, \
                mock.patch.object(type(t), "_ask_drop_duplicates", return_value=[]):
            t._ask_deck_duplicates(new, False)
        self.assertLessEqual(built.call_count, 2)


class PerTitleNotPerPairTest(_Base):
    """Marcel, 2026-11-13: 400 titles dragged onto a party list of 400 still
    took long. Measured: 248 s, 183 of it in 64,653 full Chromaprint compares
    (one per pair) and 31 in hashing each held title again for every dropped
    one. A drop now looks at each title once, and compares two fingerprints in
    full only when they share words, the shortlist Check duplicates uses."""

    _RNG = __import__("numpy").random.default_rng(11)

    def chroma(self, entries, words):
        for e, w in zip(entries, words, strict=True):
            self.cache.put_chroma(e.path, w, 150.0)

    def song(self):
        return self._RNG.integers(0, 2 ** 32, 600, dtype="uint64").astype("uint32")

    def test_each_title_is_fingerprinted_once_per_drop_not_once_per_pair(self):
        t, held = self.wishlist(12)
        new = self.dropped(12)
        with mock.patch.object(self.cache, "fingerprint",
                               wraps=self.cache.fingerprint) as fp:
            t._drop_dup_pairs(new, held)
        self.assertLessEqual(fp.call_count, 2 * (len(new) + len(held)))

    def test_only_fingerprints_that_share_words_are_compared_in_full(self):
        from planner.music import chroma_match
        t, held = self.wishlist(10)
        new = self.dropped(10)
        songs = [self.song() for _ in range(20)]
        reencode = songs[3].copy()
        flip = self._RNG.random(len(reencode)) < 0.3          # 30 % of the words differ
        reencode[flip] ^= self._RNG.integers(1, 2 ** 32, int(flip.sum()),
                                             dtype="uint64").astype("uint32")
        cut = songs[7][50:530]                                 # starts 6 s late
        self.chroma(held, songs[:10])
        self.chroma(new, [*songs[10:18], reencode, cut])
        with mock.patch("gui.table.table_dynamic.chroma_match.compare",
                        wraps=chroma_match.compare) as compare:
            pairs = t._drop_dup_pairs(new, held)
        self.assertEqual(sorted((p[0].path.name, p[1].path.name) for p in pairs),
                         sorted([(new[8].path.name, held[3].path.name),
                                 (new[9].path.name, held[7].path.name)]))
        self.assertEqual(compare.call_count, 2, "unrelated pairs were compared in full")

    def test_a_fingerprint_outside_the_drop_is_still_compared_in_full(self):
        """The shortlist only covers what the drop's scope indexed: anything
        else keeps the full compare, so no twin goes unseen for lack of an index."""
        t, held = self.wishlist(2)
        song = self.song()
        self.chroma(held, [self.song(), song])
        twin = self.dropped(1)[0]
        self.chroma([twin], [song[40:560]])
        self.assertIs(t._chroma_twin(twin, held), held[1])

    def test_a_copy_without_identical_words_is_the_drops_price(self):
        """Review D.A, kept on purpose: one bit flipped in every word still
        scores as the same recording, but shares no identical word, so a drop
        passes it over while a single title compares it in full. Real
        re-encodes keep most words identical; Check duplicates pays the same."""
        from planner.music import chroma_match
        t, held = self.wishlist(2)
        song = self.song()
        bit = self._RNG.integers(0, 32, len(song), dtype="uint64").astype("uint32")
        copy = song ^ (np.uint32(1) << bit)
        self.assertTrue(chroma_match.is_same(chroma_match.compare(song, copy)))
        self.assertEqual(len(np.intersect1d(song, copy)), 0)
        self.chroma(held, [self.song(), song])
        twin = self.dropped(1)[0]
        self.chroma([twin], [copy])
        self.assertIs(t._chroma_twin(twin, held), held[1])
        self.assertEqual(t._drop_dup_pairs([twin], held), [])


class MoveOutOfTheWishlistTest(_Base):
    """Marcel, 2026-11-13: "dragging 400 title from wishlist to party list
    freezes the ui". Measured on real tracks: the drop itself took a second,
    then taking the titles out of the wishlist 10.7 s (empty party list) and
    32.7 s (one of 400), with no bar: each dragged row read every party
    title's audio keys again. They are read once per move now."""

    def drag(self, n_wish: int, n_party: int):
        from types import SimpleNamespace

        from PySide6.QtCore import Qt
        wish, wished = self.wishlist(n_wish)
        party = self.table()
        party.load_warmup([*self.dropped(n_party), *wished], "Party", "", "S", True,
                          lambda _p: None, None)
        wish._drag_src_rows = list(range(len(wish._row_meta)))
        event = SimpleNamespace(source=lambda: wish,
                                modifiers=lambda: Qt.KeyboardModifier.NoModifier)
        return wish, party, event

    def test_each_title_is_fingerprinted_once_per_move_not_once_per_pair(self):
        wish, party, event = self.drag(12, 12)
        with mock.patch.object(self.cache, "fingerprint",
                               wraps=self.cache.fingerprint) as fp:
            moved = party._move_from_drag_source(event, pre_planned=set())
        self.assertEqual(moved, 12)
        self.assertEqual(len(wish._row_meta), 0)
        self.assertLessEqual(fp.call_count, 2 * (12 + 24))

    def test_a_title_the_party_list_does_not_hold_stays_in_the_wishlist(self):
        wish, party, event = self.drag(4, 2)
        kept = wish._row_meta[2].entry
        # The party list lost one wished title (the drop skipped it, say).
        party.load_warmup([e for e in party._row_meta.entries() if e.path != kept.path],
                          "Party", "", "S", True, lambda _p: None, None)
        self.assertEqual(party._move_from_drag_source(event, pre_planned=set()), 3)
        self.assertEqual([m.entry.path for m in wish._row_meta if m and m.entry],
                         [kept.path])


class StillFindsTheTwinsTest(_Base):
    """The speed-up must not change who counts as a twin."""

    def test_a_cut_of_a_held_title_is_found_among_many(self):
        t, held = self.wishlist(10)
        friends = self.file("C", "Friends and Lovers (LW 29)", b"fl" * 300)
        t.load_wishlist([*[self.entry(Path(str(e.path))) for e in held], self.entry(friends)],
                        play_cb=None, suggester=None)
        t._prime_chroma = lambda _entries: None
        cut = self.entry(self.file("F", "Friends and Lovers Cut Version (LW 29)", b"fc" * 300))
        pairs = t._drop_dup_pairs([*self.dropped(6), cut], t._row_meta.entries())
        self.assertEqual([(p[0].path.name, p[1].path.name, p[2]) for p in pairs],
                         [(cut.path.name, friends.name, False)])

    def test_a_different_dance_is_not_a_twin(self):
        t = self.table()
        t.load_wishlist([self.entry(self.file("C", "Friends and Lovers (CC 32)"), "CC")],
                        play_cb=None, suggester=None)
        t._prime_chroma = lambda _entries: None
        other = self.entry(self.file("F", "Friends and Lovers Cut Version (RB 25)",
                                     b"zz" * 300), "RB")
        self.assertEqual(t._drop_dup_pairs([other], t._row_meta.entries()), [])

    def test_a_title_chain_through_another_dance_is_no_twin(self):
        """A ~ B and B ~ C does not make A a twin of C once B is another dance."""
        t = self.table()
        a = self.entry(self.file("C", "Dancing in the Moonlight Now (CC 32)", b"a" * 300), "CC")
        b = self.entry(self.file("C", "Dancing in the Moonlight Now Remix (RB 25)", b"b" * 300), "RB")
        t.load_wishlist([a, b], play_cb=None, suggester=None)
        t._prime_chroma = lambda _entries: None
        c = self.entry(self.file("F", "Dancing in the Moonlight Now Remix Extended Cut (RB 25)",
                                 b"c" * 300), "RB")
        pairs = t._drop_dup_pairs([c], t._row_meta.entries())
        self.assertEqual([p[1] for p in pairs], [b])


class ProgressTest(_Base):

    def setUp(self):
        super().setUp()
        patcher = mock.patch("gui.table.table_dynamic.BusyDialog", _FakeBusy)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_long_check_shows_a_cancelable_bar_that_counts_the_titles(self):
        t, held = self.wishlist(6)
        t._DROP_PROGRESS_AFTER = 0.0
        t._drop_dup_pairs(self.dropped(6), held)
        self.assertEqual(len(_FakeBusy.made), 1)
        bar = _FakeBusy.made[0]
        self.assertTrue(bar.cancelable)
        self.assertEqual(bar.progress[-1][1], 6)
        self.assertEqual(bar.finished, 1)

    def test_a_quick_check_shows_no_bar(self):
        t, held = self.wishlist(3)
        t._drop_dup_pairs(self.dropped(3), held)      # the default delay is 0.5 s
        self.assertEqual(_FakeBusy.made, [])

    def test_cancel_drops_the_whole_drop(self):
        t, held = self.wishlist(6)
        t._DROP_PROGRESS_AFTER = 0.0
        orig = _FakeBusy.__init__

        def cancelling(self, *a, **kw):
            orig(self, *a, **kw)
            self.cancel_at = 1
        with mock.patch.object(_FakeBusy, "__init__", cancelling):
            self.assertIsNone(t._drop_dup_pairs(self.dropped(6), held))
        self.assertEqual(_FakeBusy.made[0].finished, 1)

    def test_cancel_in_the_wishlist_adds_nothing(self):
        t, held = self.wishlist(4)
        t._DROP_PROGRESS_AFTER = 0.0
        new = self.dropped(5)
        orig = _FakeBusy.__init__

        def cancelling(self, *a, **kw):
            orig(self, *a, **kw)
            self.cancel_at = 1
        with mock.patch.object(_FakeBusy, "__init__", cancelling):
            self.assertIsNone(t._split_drop(held, new))

    def test_the_deck_check_reports_and_cancels_too(self):
        held = [self.file("C", _name(i, "h")) for i in range(4)]
        t = self.static_deck([[self.entry(p)] for p in held])
        t._prime_chroma = lambda _entries: None
        t._DROP_PROGRESS_AFTER = 0.0
        orig = _FakeBusy.__init__

        def cancelling(self, *a, **kw):
            orig(self, *a, **kw)
            self.cancel_at = 1
        with mock.patch.object(_FakeBusy, "__init__", cancelling):
            self.assertIsNone(t._ask_deck_duplicates(self.dropped(6), False))
        self.assertEqual(_FakeBusy.made[0].finished, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
