"""Tests for how the resolve dialog groups cross-playlist duplicates
(DuplicateResolveDialog._build_cross_cliques).

The pairwise report says "this song is in A and B" and "…in B and C"; the
dialog has to see one song in three playlists, or the operator gets three
half-controls for the same song. It could not be tested before: the copies were
identified by the id() of a live QTableWidget, so the input had to be a running
window. They are numbered slots now, so plain dicts are enough.
"""
import os
import tempfile
import unittest


def _cliques():
    os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                          tempfile.mkdtemp(prefix="dp_dupc_"))
    from gui.duplicate_dialog import DuplicateResolveDialog
    return DuplicateResolveDialog._build_cross_cliques


def _side(slot, idx=1):
    return {"slot": slot, "entry": object(), "idx": idx,
            "path": f"C:\\music\\{slot}.mp3"}


def _pair(file_a, file_b, a, b, kind="exact"):
    return {"file_a": file_a, "file_b": file_b, kind: [{"a": a, "b": b}]}


class CrossCliqueTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.build = staticmethod(_cliques())

    def test_a_shared_song_makes_one_clique_of_both_copies(self):
        cliques, roots = self.build([_pair("A", "B", _side(0), _side(1))])
        self.assertEqual(len(cliques), 1)
        members, = cliques.values()
        self.assertEqual(sorted(m["slot"] for m in members), [0, 1])

    def test_three_playlists_are_one_clique_not_two_pairs(self):
        # A+B and B+C are separate rows of the report but the same song.
        cliques, roots = self.build([
            _pair("A", "B", _side(0), _side(1)),
            _pair("B", "C", _side(1), _side(2)),
        ])
        self.assertEqual(len(cliques), 1)
        self.assertEqual(len(set(roots.values())), 1)
        members, = cliques.values()
        self.assertEqual(sorted(m["slot"] for m in members), [0, 1, 2])

    def test_two_different_songs_stay_apart(self):
        cliques, roots = self.build([
            _pair("A", "B", _side(0), _side(1)),
            _pair("A", "B", _side(2), _side(3)),
        ])
        self.assertEqual(len(cliques), 2)

    def test_copies_carry_the_playlist_they_sit_in(self):
        cliques, roots = self.build([_pair("A", "B", _side(0), _side(1))])
        members, = cliques.values()
        self.assertEqual(sorted(m["playlist"] for m in members), ["A", "B"])

    def test_members_are_sorted_by_playlist_then_position(self):
        cliques, roots = self.build([
            _pair("B", "A", _side(0, idx=7), _side(1, idx=2)),
            _pair("A", "A", _side(1, idx=2), _side(2, idx=1)),
        ])
        members, = cliques.values()
        self.assertEqual([(m["playlist"], m["idx"]) for m in members],
                         [("A", 1), ("A", 2), ("B", 7)])

    def test_a_copy_without_a_slot_cannot_be_resolved(self):
        # Dropped-file records have no deck row behind them.
        loose = {"entry": object(), "idx": 1, "path": "x.m3u"}
        cliques, roots = self.build([_pair("A", "drop.m3u", _side(0), loose)])
        members, = cliques.values()
        self.assertEqual([m["slot"] for m in members], [0])

    def test_similar_matches_group_like_exact_ones(self):
        cliques, roots = self.build(
            [_pair("A", "B", _side(0), _side(1), kind="similar")])
        self.assertEqual(len(cliques), 1)

    def test_an_empty_report_has_no_cliques(self):
        self.assertEqual(self.build([]), ({}, {}))
        self.assertEqual(self.build(None), ({}, {}))


if __name__ == "__main__":
    unittest.main()
