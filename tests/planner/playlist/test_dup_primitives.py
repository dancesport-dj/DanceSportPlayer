"""The building blocks of the duplicate finder, one by one.

Run:  py -m unittest tests.planner.playlist.test_dup_primitives -v

`dup_clashes` and `build_dropped_dup_report` are tested through their results
elsewhere; this pins the pieces they are made of, so a change to one shows up
where it was made: edit distance, the title ratio, the significant words, the
dance rule, the cluster representatives, the exact/similar split between two
playlists, and the Chromaprint recording pairs.
"""
import unittest

import numpy as np

from planner.playlist.checks import (
    _cross_recordings,
    _recording_clusters,
    dance_compatible,
    dance_split,
    levenshtein,
    pair_dups,
    recording_matches,
    sig_tokens,
    similar_reps,
    title_cluster_map,
    title_ratio,
    title_similar,
)


def _rec(idx: int, title: str, dance: str | None = "LW", exact: str | None = None,
         chroma=None) -> dict:
    return {"idx": idx, "title": title, "exact": exact or f"p:{idx}",
            "tkeys": [title], "dance": dance, "chroma": chroma}


def _fp(seed: int, n: int = 800) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 2**32, n, dtype=np.uint32)


class LevenshteinTest(unittest.TestCase):

    def test_known_distances(self):
        for a, b, d in (("kitten", "sitting", 3), ("flaw", "lawn", 2),
                        ("abc", "abc", 0), ("abc", "abd", 1), ("abc", "ab", 1)):
            self.assertEqual(levenshtein(a, b), d, (a, b))

    def test_an_empty_side_costs_the_other_length(self):
        self.assertEqual(levenshtein("", "abcd"), 4)
        self.assertEqual(levenshtein("abcd", ""), 4)
        self.assertEqual(levenshtein("", ""), 0)

    def test_it_is_symmetric(self):
        self.assertEqual(levenshtein("moon river", "moonriver"),
                         levenshtein("moonriver", "moon river"))

    def test_a_cutoff_returns_one_past_the_limit(self):
        self.assertEqual(levenshtein("abcdefgh", "zyxwvuts", max_dist=2), 3)

    def test_a_length_gap_over_the_cutoff_bails_out_at_once(self):
        self.assertEqual(levenshtein("a", "abcdefgh", max_dist=2), 3)

    def test_a_cutoff_does_not_change_a_distance_within_it(self):
        self.assertEqual(levenshtein("kitten", "sitting", max_dist=3), 3)
        self.assertEqual(levenshtein("kitten", "sitting", max_dist=10), 3)


class TitleRatioTest(unittest.TestCase):

    def test_identical_is_one_and_empty_is_zero(self):
        self.assertEqual(title_ratio("moon river", "moon river"), 1.0)
        self.assertEqual(title_ratio("", "moon river"), 0.0)
        self.assertEqual(title_ratio("moon river", ""), 0.0)

    def test_a_typo_in_a_long_title_still_passes(self):
        # 1 edit in 16 characters: 0.9375, over the 0.85 threshold
        self.assertAlmostEqual(title_ratio("tennessee waltzs", "tennessee waltz"),
                               1.0 - 1 / 16, places=3)

    def test_too_many_edits_score_zero_not_a_low_number(self):
        self.assertEqual(title_ratio("moon river", "tennessee waltz"), 0.0)

    def test_a_short_title_allows_no_edit(self):
        # int(0.15 * 4) == 0 edits are allowed, so one swapped letter fails
        self.assertEqual(title_ratio("love", "lave"), 0.0)


class SigTokensTest(unittest.TestCase):

    def test_stopwords_and_tags_are_dropped(self):
        self.assertEqual(sig_tokens("the butterfly waltz instr"),
                         frozenset({"butterfly", "waltz"}))

    def test_only_stopwords_leave_nothing(self):
        self.assertEqual(sig_tokens("the of and"), frozenset())

    def test_it_is_lowercase_split_on_spaces(self):
        self.assertEqual(sig_tokens("moon river"), frozenset({"moon", "river"}))


class TitleSimilarTest(unittest.TestCase):

    def test_containment_needs_two_shared_significant_words(self):
        self.assertTrue(title_similar("butterfly waltz", "butterfly waltz from twilight"))
        self.assertFalse(title_similar("higher", "higher ground"))

    def test_a_dj_prefix_and_instr_do_not_make_a_new_song(self):
        self.assertTrue(title_similar("enjoy the silence", "enjoy the silence instr"))
        self.assertTrue(title_similar("dj ice love yourself", "love yourself"))

    def test_an_empty_title_is_similar_to_nothing(self):
        self.assertFalse(title_similar("", ""))
        self.assertFalse(title_similar("moon river", ""))

    def test_two_different_songs_are_not(self):
        self.assertFalse(title_similar("moon river", "tennessee waltz"))


class DanceCompatibleTest(unittest.TestCase):

    def test_the_same_dance_is_compatible(self):
        self.assertTrue(dance_compatible({"dance": "LW"}, {"dance": "LW"}))

    def test_two_known_different_dances_are_not(self):
        self.assertFalse(dance_compatible({"dance": "LW"}, {"dance": "JI"}))

    def test_an_unknown_dance_on_either_side_is_permissive(self):
        self.assertTrue(dance_compatible({"dance": None}, {"dance": "JI"}))
        self.assertTrue(dance_compatible({"dance": "JI"}, {}))
        self.assertTrue(dance_compatible({}, {}))


class DanceSplitTest(unittest.TestCase):

    def test_one_known_dance_stays_one_group(self):
        reps = [{"dance": "LW"}, {"dance": None}, {"dance": "LW"}]
        self.assertEqual(dance_split(reps), [reps])

    def test_no_known_dance_stays_one_group(self):
        reps = [{"dance": None}, {}]
        self.assertEqual(dance_split(reps), [reps])

    def test_two_dances_split_and_unknowns_join_each_group(self):
        lw, ji, unk = {"dance": "LW"}, {"dance": "JI"}, {"dance": None}
        groups = dance_split([lw, ji, unk])
        self.assertEqual(sorted(len(g) for g in groups), [2, 2])
        self.assertTrue(all(unk in g for g in groups))
        self.assertEqual({g[0]["dance"] for g in groups}, {"LW", "JI"})

    def test_the_groups_never_mix_two_known_dances(self):
        groups = dance_split([{"dance": "LW"}, {"dance": "JI"}, {"dance": "QS"}])
        for g in groups:
            self.assertEqual(len({r["dance"] for r in g if r.get("dance")}), 1)


class SimilarRepsTest(unittest.TestCase):

    def test_copies_of_one_file_collapse_to_the_first(self):
        a, b = _rec(1, "moon river", exact="same"), _rec(2, "moon river", exact="same")
        cmap = title_cluster_map(["moon river"])
        reps = similar_reps([a, b], cmap)
        self.assertEqual(list(reps.values()), [{"same": a}])

    def test_two_files_of_one_song_stay_separate_under_one_cluster(self):
        a, b = _rec(1, "moon river"), _rec(2, "moon river")
        reps = similar_reps([a, b], title_cluster_map(["moon river"]))
        self.assertEqual(len(reps), 1)
        self.assertEqual(len(next(iter(reps.values()))), 2)

    def test_a_record_with_two_keys_lands_in_both_clusters(self):
        r = {"idx": 1, "exact": "x", "dance": "LW", "tkeys": ["moon river", "andy williams"]}
        reps = similar_reps([r], title_cluster_map(r["tkeys"]))
        self.assertEqual(len(reps), 2)

    def test_two_keys_in_one_cluster_register_the_record_once(self):
        r = {"idx": 1, "exact": "x", "dance": "LW",
             "tkeys": ["butterfly waltz", "butterfly waltz from twilight"]}
        reps = similar_reps([r], title_cluster_map(r["tkeys"]))
        self.assertEqual(len(reps), 1)

    def test_a_key_outside_the_map_and_a_record_without_keys_are_skipped(self):
        r = {"idx": 1, "exact": "x", "tkeys": ["unmapped"]}
        self.assertEqual(similar_reps([r, {"idx": 2, "exact": "y"}], {}), {})


class PairDupsTest(unittest.TestCase):

    def test_the_same_file_in_both_is_exact_not_similar(self):
        a = [_rec(1, "moon river", exact="file1")]
        b = [_rec(7, "moon river", exact="file1")]
        exact, similar = pair_dups(a, b)
        self.assertEqual([(p["a"]["idx"], p["b"]["idx"]) for p in exact], [(1, 7)])
        self.assertEqual(similar, [])

    def test_another_recording_of_the_title_is_similar(self):
        exact, similar = pair_dups([_rec(1, "moon river", exact="a")],
                                   [_rec(3, "moon river", exact="b")])
        self.assertEqual(exact, [])
        self.assertEqual([(p["a"]["idx"], p["b"]["idx"]) for p in similar], [(1, 3)])

    def test_the_same_song_in_another_dance_is_no_pair(self):
        self.assertEqual(pair_dups([_rec(1, "beautiful", "LW", "a")],
                                   [_rec(1, "beautiful", "JI", "b")]), ([], []))

    def test_an_unknown_dance_still_pairs(self):
        _exact, similar = pair_dups([_rec(1, "beautiful", None, "a")],
                                    [_rec(1, "beautiful", "JI", "b")])
        self.assertEqual(len(similar), 1)

    def test_different_songs_pair_with_nothing(self):
        self.assertEqual(pair_dups([_rec(1, "moon river", exact="a")],
                                   [_rec(1, "tennessee waltz", exact="b")]), ([], []))

    def test_an_empty_side_gives_nothing(self):
        self.assertEqual(pair_dups([], [_rec(1, "moon river")]), ([], []))
        self.assertEqual(pair_dups([], []), ([], []))

    def test_results_come_in_line_order_of_the_first_list(self):
        a = [_rec(5, "moon river", exact="a5"), _rec(2, "tennessee waltz", exact="a2")]
        b = [_rec(1, "tennessee waltz", exact="b1"), _rec(9, "moon river", exact="b9")]
        _exact, similar = pair_dups(a, b)
        self.assertEqual([p["a"]["idx"] for p in similar], [2, 5])

    def test_one_pair_per_song_however_many_copies(self):
        a = [_rec(1, "moon river", exact="a1"), _rec(2, "moon river", exact="a2")]
        b = [_rec(3, "moon river", exact="b3"), _rec(4, "moon river", exact="b4")]
        _exact, similar = pair_dups(a, b)
        self.assertEqual(len(similar), 1)


class RecordingMatchesTest(unittest.TestCase):

    def test_two_files_with_the_same_audio_pair_up(self):
        fp = _fp(1)
        a, b = _rec(1, "x", exact="a", chroma=fp), _rec(2, "y", exact="b", chroma=fp.copy())
        pairs = recording_matches([a, b])
        self.assertEqual(len(pairs), 1)
        self.assertEqual({id(pairs[0][0]), id(pairs[0][1])}, {id(a), id(b)})

    def test_different_audio_does_not_pair(self):
        a = _rec(1, "x", exact="a", chroma=_fp(1))
        b = _rec(2, "y", exact="b", chroma=_fp(2))
        self.assertEqual(recording_matches([a, b]), [])

    def test_a_record_without_a_fingerprint_is_left_out(self):
        fp = _fp(1)
        recs = [_rec(1, "x", exact="a", chroma=fp), _rec(2, "y", exact="b", chroma=None),
                _rec(3, "z", exact="c", chroma=np.array([], dtype=np.uint32))]
        self.assertEqual(recording_matches(recs), [])

    def test_a_pair_the_caller_already_reports_is_skipped(self):
        fp = _fp(1)
        a, b = _rec(1, "x", exact="a", chroma=fp), _rec(2, "y", exact="b", chroma=fp.copy())
        self.assertEqual(recording_matches([a, b], skip={frozenset((id(a), id(b)))}), [])

    def test_the_same_file_twice_is_not_a_recording_pair(self):
        fp = _fp(1)
        a, b = _rec(1, "x", exact="same", chroma=fp), _rec(2, "y", exact="same", chroma=fp)
        self.assertEqual(recording_matches([a, b]), [])


class RecordingClustersTest(unittest.TestCase):

    def test_a_chain_of_pairs_becomes_one_group_in_line_order(self):
        a, b, c = _rec(3, "a"), _rec(1, "b"), _rec(2, "c")
        groups = _recording_clusters([(a, b), (b, c)])
        self.assertEqual(len(groups), 1)
        self.assertEqual([r["idx"] for r in groups[0]], [1, 2, 3])

    def test_unconnected_pairs_stay_apart(self):
        a, b, c, d = (_rec(i, str(i)) for i in range(4))
        groups = _recording_clusters([(a, b), (c, d)])
        self.assertEqual(sorted(len(g) for g in groups), [2, 2])

    def test_no_pairs_no_groups(self):
        self.assertEqual(_recording_clusters([]), [])


class CrossRecordingsTest(unittest.TestCase):

    def test_only_a_pair_across_the_two_lists_counts(self):
        fp = _fp(1)
        a1 = _rec(1, "x", exact="a1", chroma=fp)
        a2 = _rec(2, "y", exact="a2", chroma=fp.copy())          # same audio, same list
        b1 = _rec(1, "z", exact="b1", chroma=_fp(2))
        self.assertEqual(_cross_recordings([a1, a2], [b1], set()), [])

    def test_a_cross_pair_comes_back_as_a_then_b(self):
        fp = _fp(1)
        a = _rec(4, "x", exact="a", chroma=fp)
        b = _rec(9, "y", exact="b", chroma=fp.copy())
        got = _cross_recordings([a], [b], set())
        self.assertEqual(len(got), 1)
        self.assertIs(got[0][0], a)
        self.assertIs(got[0][1], b)

    def test_another_dance_rules_the_pair_out(self):
        fp = _fp(1)
        a = _rec(1, "x", "LW", "a", fp)
        b = _rec(1, "y", "JI", "b", fp.copy())
        self.assertEqual(_cross_recordings([a], [b], set()), [])

    def test_a_pair_already_reported_is_skipped(self):
        fp = _fp(1)
        a, b = _rec(1, "x", exact="a", chroma=fp), _rec(1, "y", exact="b", chroma=fp.copy())
        self.assertEqual(_cross_recordings([a], [b], {frozenset((id(a), id(b)))}), [])


if __name__ == "__main__":
    unittest.main()
