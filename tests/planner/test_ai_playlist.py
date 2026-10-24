#!/usr/bin/env python3
"""Tests for the 🤖 AI playlist option (planner.generate.llm + the grid it fills).

Run:  py -m unittest tests.planner.test_ai_playlist -v

The model is never trusted with a file path: it answers with catalog NUMBERS,
so a hallucinated title cannot reach a playlist. These tests pin that contract
from both ends — what goes into the prompt (only TSO-conform candidates) and
what comes back out of a sloppy answer (fenced JSON, bare ints, a round name in
the wrong case, a number past the end of the catalog).

No network and no claude CLI: everything here exercises the pure halves.
"""

import os
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_ai_"))

from planner.generate import llm
from planner.music import sound as planner_sound
from planner.models import MusicEntry, RoundConfig

DANCES = ["SA", "CC", "RB"]
_BPM = {"SA": 51, "CC": 31, "RB": 25}


def _entry(dance, i, bpm=None, folder="lateincd", classes=None, pop=0,
           tags=None):
    return MusicEntry(
        path=Path(f"C:/lib/{folder}/{dance}/{dance}_{i}.mp3"),
        title=f"{dance} {i}", dance=dance,
        bpm=_BPM[dance] if bpm is None else bpm,
        year=2000 + i, popularity=pop, classes_ok=classes, comment_tags=tags)


def _library():
    return [_entry(d, i, pop=10 - i) for d in DANCES for i in range(1, 7)]


def _rows(text: str) -> list[str]:
    """A catalog table without its legend — the header line and everything
    under it. The legends are prose above a blank line."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("n |"):
            return lines[i:]
    return lines


def _feat(rms, centroid, drive):
    """Just the three numbers planner.music.sound reads off an analysed track."""
    vec = [0.0] * 84
    vec[82] = drive                                   # mean onset strength
    return SimpleNamespace(rms=rms, centroid=centroid, mfcc=vec)


def _analysed(entries):
    """Give every entry a distinct sound, quiet/dark/soft first."""
    for i, e in enumerate(entries, start=1):
        e.features = _feat(0.1 * i, 1000 + 100 * i, 0.5 * i)
    return entries


def _rounds():
    return [RoundConfig(name="Vorrunde", heats=2, tier="early"),
            RoundConfig(name="Finale", heats=1, tier="final")]


class ParseReplyTest(unittest.TestCase):
    """The answer arrives as text — every shape a model actually produces."""

    def test_plain_json(self):
        out = llm.parse_reply(
            '{"playlist": [{"n": 3, "round": "Finale", "heat": 1}],'
            ' "notes": "short"}')
        self.assertEqual(out["picks"],
                         [{"n": 3, "round": "Finale", "heat": 1, "why": ""}])
        self.assertEqual(out["notes"], "short")

    def test_markdown_fence_and_chatter(self):
        out = llm.parse_reply(
            'Here you go:\n```json\n{"playlist": [{"n": 1}]}\n```\n')
        self.assertEqual(out["picks"],
                         [{"n": 1, "round": "", "heat": 0, "why": ""}])

    def test_a_sentence_after_the_object_is_ignored(self):
        # "Extra data": the object was complete, the model kept talking.
        out = llm.parse_reply(
            '{"playlist": [{"n": 5}], "notes": "done"}\n'
            'Let me know if you want a different final.')
        self.assertEqual([p["n"] for p in out["picks"]], [5])
        self.assertEqual(out["notes"], "done")

    def test_a_model_that_corrects_itself_is_taken_at_its_second_word(self):
        # Seen in the wild: a broken object, then "Wait, let me redo that",
        # then the real answer. The first one it disowned must not be used.
        out = llm.parse_reply(
            '{"playlist": [{"n": 1}, {"n": 1}], "notes": "oops"}\n'
            'Wait, one number repeats. Here is the corrected answer:\n'
            '{"playlist": [{"n": 3}, {"n": 4}], "notes": "fixed"}')
        self.assertEqual([p["n"] for p in out["picks"]], [3, 4])
        self.assertEqual(out["notes"], "fixed")

    def test_a_cut_off_answer_keeps_the_picks_it_managed(self):
        out = llm.parse_reply(
            '{"playlist": [{"n": 1, "why": "opener"}, {"n": 2}, {"n": 3')
        self.assertEqual([p["n"] for p in out["picks"]], [1, 2])
        self.assertEqual(out["picks"][0]["why"], "opener")

    def test_bare_numbers_are_accepted(self):
        out = llm.parse_reply('{"playlist": [4, 9]}')
        self.assertEqual([p["n"] for p in out["picks"]], [4, 9])

    def test_long_notes_are_cut_like_the_refine_notes(self):
        """R14: the notes of a playlist answer were kept at any length."""
        out = llm.parse_reply('{"playlist": [1], "notes": "' + "x " * 2000 + '"}')
        self.assertLessEqual(len(out["notes"]), llm._WHY_MAX * 2)
        self.assertTrue(out["notes"].startswith("x x"))

    def test_no_json_raises(self):
        with self.assertRaises(RuntimeError):
            llm.parse_reply("I'd rather not.")

    def test_empty_playlist_raises(self):
        with self.assertRaises(RuntimeError):
            llm.parse_reply('{"playlist": []}')

    def test_unusable_items_raise(self):
        with self.assertRaises(RuntimeError):
            llm.parse_reply('{"playlist": [{"title": "Smooth"}]}')


class CandidateTest(unittest.TestCase):
    """What the model is allowed to see."""

    def test_off_tempo_and_wrong_class_are_kept_out(self):
        lib = _library()
        lib.append(_entry("SA", 99, bpm=44))              # way under TSO
        lib.append(_entry("SA", 98, classes=["D"]))    # not for S
        got = llm.competition_candidates(lib, "Latin", "S", ["SA"])
        titles = {e.title for e in got}
        self.assertNotIn("SA 99", titles)
        self.assertNotIn("SA 98", titles)
        self.assertIn("SA 1", titles)

    def test_cap_is_shared_over_the_dances(self):
        lib = [_entry(d, i, pop=i) for d in DANCES for i in range(1, 60)]
        got = llm.competition_candidates(lib, "Latin", "S", DANCES,
                                                 cap=30)
        self.assertLessEqual(len(got), 30)
        for d in DANCES:
            self.assertEqual(sum(1 for e in got if e.dance == d), 10)

    def test_catalog_numbers_are_the_position(self):
        lib = _library()[:3]
        lines = _rows(llm.catalog_text(lib))
        self.assertTrue(lines[0].strip().startswith("n |"))
        self.assertTrue(lines[1].strip().startswith("1 |"))
        self.assertIn(lib[2].title, lines[3])

    def test_the_task_names_every_slot(self):
        task = llm.competition_task(
            "Latin", "Hauptgruppe", "S", DANCES, _rounds(), "no covers")
        self.assertIn("Vorrunde: 2 heat(s)", task)
        self.assertIn("9 songs in total", task)   # (2 + 1) heats × 3 dances
        self.assertIn("no covers", task)
        self.assertIn("Samba (SA) 50-52", task)


class WishTaskTest(unittest.TestCase):
    """The pasted sheet reaches the model as it was pasted, with the shorthand
    that makes it readable spelt out around it."""

    WISHES = ("lw\tt\tww\n"
              "White wings lw\ta new life t\tWillow ww\n"
              "melancolia lw!!\tDance of love t\tCity of stars sf")

    def test_the_pasted_lines_are_carried_over_verbatim(self):
        task = llm.wish_task(self.WISHES)
        for line in self.WISHES.splitlines():
            self.assertIn(line, task)

    def test_the_shorthand_is_explained(self):
        task = llm.wish_task(self.WISHES)
        self.assertIn("Langsamer Walzer", task)
        self.assertIn("Slowfox", task)
        self.assertIn("!!", task)

    def test_it_asks_for_one_search_query_per_wish(self):
        task = llm.wish_task(self.WISHES)
        self.assertIn('"search"', task)
        self.assertIn('"limit": 8', task)

    def test_a_named_wish_it_cannot_find_is_left_out_not_replaced(self):
        self.assertIn("notes", llm.wish_task(self.WISHES))

    def test_nothing_but_the_wishes_goes_into_the_list(self):
        """The rules describe a good event playlist and would happily round
        this one out — in wish mode they must not add a single track."""
        task = llm.wish_task(self.WISHES)
        self.assertIn("NOTHING else", task)
        self.assertIn("never add one of their own", task)
        self.assertIn("ends where the wishes end", task)

    def test_no_layout_is_demanded_of_the_wishes(self):
        """The sheet is one way of writing them, not the way: prose, a line
        per wish and a mixture all have to be read as well."""
        task = llm.wish_task("something slow to open with, then "
                                     "White wings, and melancolia !! last")
        self.assertIn("do not expect a fixed layout", task)
        self.assertIn("something slow to open with", task)

    def test_a_wish_that_only_describes_a_track_is_the_models_to_choose(self):
        self.assertIn("DESCRIBES", llm.wish_task(self.WISHES))

    def test_the_brief_is_appended_when_there_is_one(self):
        self.assertIn("for a show",
                      llm.wish_task(self.WISHES, "the list is for a show"))

    def test_no_brief_no_empty_heading(self):
        self.assertNotIn("What this list is for",
                         llm.wish_task(self.WISHES, "   "))


class GridTest(unittest.TestCase):
    """Model answer → the round / heat / dance grid the deck loads."""

    def setUp(self):
        self.cand = _library()
        self.rounds = _rounds()

    def _grid(self, picks):
        return llm.assemble_grid(picks, self.cand, DANCES, self.rounds)

    @staticmethod
    def _filled(grid):
        return sum(1 for heats in grid.values() for h in heats
                   for e in h if e is not None)

    def test_picks_land_where_the_model_put_them(self):
        # catalog is SA 1-6, CC 1-6, RB 1-6 → 1 = "SA 1", 7 = "CC 1", 13 = "RB 1"
        grid = self._grid([{"n": 1, "round": "Finale", "heat": 1},
                           {"n": 7, "round": "Finale", "heat": 1},
                           {"n": 13, "round": "Finale", "heat": 1}])
        self.assertEqual([e.title for e in grid["Finale"][0]],
                         ["SA 1", "CC 1", "RB 1"])
        self.assertEqual(self._filled(grid), 3)

    def test_round_name_case_does_not_matter(self):
        grid = self._grid([{"n": 1, "round": "  finale ", "heat": 1}])
        self.assertEqual(grid["Finale"][0][0].title, "SA 1")

    def test_a_mislabelled_pick_still_gets_a_slot(self):
        """Unknown round / impossible heat → first free slot of its dance,
        rather than a song thrown away over a formatting slip."""
        grid = self._grid([{"n": 2, "round": "Semifinale", "heat": 9}])
        self.assertEqual(grid["Vorrunde"][0][0].title, "SA 2")

    def test_numbers_past_the_catalog_are_dropped(self):
        grid = self._grid([{"n": 999, "round": "Finale", "heat": 1},
                           {"n": 0, "round": "Finale", "heat": 1}])
        self.assertEqual(self._filled(grid), 0)

    def test_a_repeated_pick_is_used_once(self):
        grid = self._grid([{"n": 1, "round": "Finale", "heat": 1},
                           {"n": 1, "round": "Vorrunde", "heat": 1}])
        self.assertEqual(self._filled(grid), 1)

    def test_a_mislabelled_pick_does_not_double_a_track(self):
        """The same number twice — once unplaceable, once in a real slot —
        must not put one Samba into two heats."""
        grid = self._grid([{"n": 1, "round": "Semifinale", "heat": 9},
                           {"n": 1, "round": "Finale", "heat": 1}])
        self.assertEqual(self._filled(grid), 1)

    def test_two_mislabelled_copies_are_placed_once(self):
        grid = self._grid([{"n": 1, "round": "Semifinale", "heat": 9},
                           {"n": 1, "round": "Semifinale", "heat": 9}])
        self.assertEqual(self._filled(grid), 1)

    def test_unfilled_slots_stay_empty(self):
        grid = self._grid([{"n": 1, "round": "Finale", "heat": 1}])
        self.assertEqual(len(grid["Vorrunde"]), 2)
        self.assertTrue(all(e is None for e in grid["Vorrunde"][0]))


class TagTest(unittest.TestCase):
    """The comment tag, as the model gets to read it."""

    def test_class_codes(self):
        e = _entry("SA", 1, classes=["B", "A", "S"])
        self.assertEqual(llm.entry_tags(e), "B,A,S")

    def test_no_comment_is_a_star(self):
        self.assertEqual(llm.entry_tags(_entry("SA", 1)), "*")

    def test_instrumental_is_appended(self):
        e = _entry("SA", 1, classes=["S"])
        e.is_instrumental = True
        self.assertEqual(llm.entry_tags(e), "S+instr")

    def test_instrumental_without_classes(self):
        e = _entry("SA", 1)
        e.is_instrumental = True
        self.assertEqual(llm.entry_tags(e), "*+instr")

    def test_the_free_markers_follow_the_classes(self):
        e = _entry("SA", 1, classes=["A", "S"], tags=["vocal_f", "classic"])
        self.assertEqual(llm.entry_tags(e), "A,S;vocal_f;classic")

    def test_markers_without_a_class_tag(self):
        e = _entry("SA", 1, tags=["eintanzen"])
        self.assertEqual(llm.entry_tags(e), "*;eintanzen")

    def test_markers_and_instr_together(self):
        e = _entry("SA", 1, classes=["S"], tags=["classic"])
        e.is_instrumental = True
        self.assertEqual(llm.entry_tags(e), "S+instr;classic")


class SummaryTest(unittest.TestCase):
    """Step 1 sees only this — one line per dance, no titles at all."""

    def setUp(self):
        self.cand = _library()          # SA/CC/RB x 6, popularity 9…4

    def test_one_line_per_dance_plus_a_header(self):
        lines = llm.library_summary(self.cand).splitlines()
        table = lines[:1 + len(DANCES)]
        self.assertTrue(table[0].startswith("dance |"))
        for code in DANCES:
            self.assertTrue(any(ln.strip().startswith(code) for ln in table[1:]))

    def test_no_track_title_leaks_into_it(self):
        text = llm.library_summary(self.cand)
        for e in self.cand:
            self.assertNotIn(e.title, text)

    def test_the_counts_are_real(self):
        line = next(ln for ln in llm.library_summary(self.cand).splitlines()
                    if ln.strip().startswith("SA"))
        cells = [c.strip() for c in line.split("|")]
        self.assertEqual(cells[1], "6")            # pool
        self.assertEqual(cells[2], "51-51")        # bpm span
        self.assertEqual(cells[3], "6")            # proven (pop 4…9, all >= 3)
        self.assertEqual(cells[4], "0")            # finalists
        self.assertEqual(cells[5], "0")            # semifinalists
        self.assertEqual(cells[6], "0")            # fresh
        self.assertEqual(cells[7], "6")            # unplanned

    def test_the_finalists_are_counted_apart_from_the_proven(self):
        """A pool can be all-proven and still hold nothing a final has used."""
        for e in self.cand[:2]:
            e.final_plays = 3
        self.cand[3].semi_plays = 1
        line = next(ln for ln in llm.library_summary(self.cand).splitlines()
                    if ln.strip().startswith("SA"))
        cells = [c.strip() for c in line.split("|")]
        self.assertEqual(cells[3], "6")            # proven
        self.assertEqual(cells[4], "2")            # …of which finalists
        self.assertEqual(cells[5], "1")            # …and semifinalists

    def test_a_planned_track_stops_counting_as_unplanned(self):
        used = {str(self.cand[0].path).upper()}    # case must not matter
        line = next(ln for ln in llm.library_summary(
            self.cand, used_paths=used).splitlines()
            if ln.strip().startswith("SA"))
        self.assertEqual(line.split("|")[-1].strip(), "5")


class MarkerSummaryTest(unittest.TestCase):
    """The model cannot guess that 'vocal_f' exists — step 1 has to say so."""

    def setUp(self):
        self.cand = _library()
        for i, tags in enumerate(( ["vocal_f", "classic"], ["vocal_f"],
                                   ["classic"], ["eintanzen"] )):
            self.cand[i].comment_tags = tags

    def test_counts_are_ranked_by_how_common_they_are(self):
        self.assertEqual(llm.marker_counts(self.cand),
                         [("classic", 2), ("vocal_f", 2), ("eintanzen", 1)])

    def test_the_rare_tail_is_cut_off(self):
        self.assertEqual(len(llm.marker_counts(self.cand, top=2)), 2)

    def test_the_summary_lists_them(self):
        text = llm.library_summary(self.cand)
        self.assertIn("comment markers", text)
        self.assertIn("vocal_f (2)", text)

    def test_a_pool_without_markers_says_nothing_about_them(self):
        self.assertEqual(llm.marker_counts(_library()), [])
        self.assertNotIn("comment markers",
                         llm.library_summary(_library()))


class QueryParseTest(unittest.TestCase):
    """Step 1's answer — the same sloppiness budget as the picking answer."""

    def test_plain(self):
        got = llm.parse_queries('{"queries": [{"dance": "LW"}]}')
        self.assertEqual(got, [{"dance": "LW"}])

    def test_fence_and_chatter(self):
        got = llm.parse_queries(
            'Sure:\n```json\n{"queries": [{"dance": "SA", "limit": 5}]}\n```')
        self.assertEqual(got, [{"dance": "SA", "limit": 5}])

    def test_junk_is_no_queries_rather_than_an_error(self):
        for text in ("", "no thanks", "{", '{"queries": "all"}', "{oops}"):
            self.assertEqual(llm.parse_queries(text), [])

    def test_non_dict_entries_are_dropped(self):
        got = llm.parse_queries('{"queries": [{"dance": "SA"}, 7, null]}')
        self.assertEqual(got, [{"dance": "SA"}])

    def test_the_number_of_queries_is_capped(self):
        """R3: the answer, not the app, decided how many searches ran."""
        text = '{"queries": [' + ", ".join(['{"dance": "SA"}'] * 5000) + "]}"
        self.assertEqual(len(llm.parse_queries(text)), llm._QUERIES_MAX)


class RunQueriesTest(unittest.TestCase):
    """The search itself — the half that keeps the context small."""

    def setUp(self):
        self.cand = _library()          # 1-6 SA, 7-12 CC, 13-18 RB

    def _run(self, queries, **kw):
        return llm.run_queries(queries, self.cand, **kw)

    def test_a_dance_query_returns_only_that_dance(self):
        got = self._run([{"dance": "CC"}])
        self.assertEqual(sorted(got), [7, 8, 9, 10, 11, 12])

    def test_the_numbers_are_positions_in_the_full_pool(self):
        got = self._run([{"dance": "RB", "limit": 1}])
        self.assertEqual(self.cand[got[0] - 1].dance, "RB")
        self.assertGreaterEqual(got[0], 13)

    def test_pop_is_the_default_order(self):
        got = self._run([{"dance": "SA", "limit": 3}])
        pops = [self.cand[i - 1].popularity for i in got]
        self.assertEqual(pops, sorted(pops, reverse=True))

    def test_fresh_turns_the_order_around(self):
        got = self._run([{"dance": "SA", "sort": "fresh", "limit": 3}])
        pops = [self.cand[i - 1].popularity for i in got]
        self.assertEqual(pops, sorted(pops))

    def test_a_row_is_never_sent_twice(self):
        got = self._run([{"dance": "SA"}, {"dance": "SA"}])
        self.assertEqual(len(got), len(set(got)))
        self.assertEqual(len(got), 6)

    def test_the_total_budget_wins_over_the_query_limits(self):
        got = self._run([{"dance": "SA", "limit": 200},
                         {"dance": "CC", "limit": 200}], rows_max=4)
        self.assertEqual(len(got), 4)

    def test_a_query_limit_is_capped(self):
        got = self._run([{"dance": "SA", "limit": 99999}])
        self.assertLessEqual(len(got), llm._QUERY_MAX)

    def test_a_stopped_run_stops_the_search(self):
        """R3: Cancel did not reach the loop that runs the queries."""
        stop = threading.Event()
        stop.set()
        with self.assertRaises(llm.Cancelled):
            self._run([{"dance": "SA"}], cancel=stop)

    def test_a_nonsense_limit_falls_back_to_the_default(self):
        got = self._run([{"dance": "SA", "limit": "lots"}])
        self.assertEqual(len(got), 6)

    def test_bpm_span_and_single_value(self):
        self.cand.append(_entry("SA", 20, bpm=48))
        self.assertEqual(self._run([{"dance": "SA", "bpm": 48}]), [19])
        self.assertEqual(self._run([{"dance": "SA", "bpm": "47-49"}]), [19])
        self.assertEqual(sorted(self._run([{"dance": "SA", "bpm": "51-52"}])),
                         [1, 2, 3, 4, 5, 6])

    def test_pop_bounds(self):
        self.assertEqual(sorted(self._run([{"dance": "SA", "min_pop": 8}])), [1, 2])
        self.assertEqual(sorted(self._run([{"dance": "SA", "max_pop": 5}])), [5, 6])

    def test_unused_drops_what_a_deck_already_took(self):
        used = {str(self.cand[0].path).lower()}
        got = self._run([{"dance": "SA", "unused": True}], used_paths=used)
        self.assertNotIn(1, got)
        self.assertEqual(len(got), 5)

    def test_class_filters_on_the_comment_tag(self):
        self.cand.append(_entry("SA", 30, classes=["D"]))     # 19
        self.cand.append(_entry("SA", 31, classes=["S"]))     # 20
        got = self._run([{"dance": "SA", "class": "S"}])
        self.assertIn(20, got)          # cleared for S
        self.assertNotIn(19, got)       # D only
        self.assertIn(1, got)           # no comment tag -> cleared for anything

    def test_focus_keeps_only_the_tags_written_for_the_higher_classes(self):
        self.cand.append(_entry("SA", 30, classes=["D", "C", "B", "A", "S"]))
        self.cand.append(_entry("SA", 31, classes=["B", "A", "S"]))
        got = self._run([{"dance": "SA", "focus": True}])
        self.assertEqual(got, [20])     # the B/A/S-only one, nothing else
        # An untagged track is not focused either: nobody said anything about it
        self.assertNotIn(1, got)

    def test_instr_both_ways(self):
        self.cand[0].is_instrumental = True
        self.assertEqual(self._run([{"dance": "SA", "instr": True}]), [1])
        self.assertNotIn(1, self._run([{"dance": "SA", "instr": False}]))

    def test_search_hits_title_and_artist(self):
        self.cand[0].tag_artist = "Klaus Hallen"
        self.assertEqual(self._run([{"search": "hallen"}]), [1])
        self.assertEqual(self._run([{"dance": "CC", "search": "CC 4"}]), [10])

    def test_search_ignores_accents_and_punctuation(self):
        """A wish is typed from memory, the library title carries the accents."""
        self.cand[0].title = "Melancolía"
        self.cand[1].title = "Don't Stop"
        self.assertEqual(self._run([{"search": "melancolia"}]), [1])
        self.assertEqual(self._run([{"search": "MELANCOLIA"}]), [1])
        self.assertEqual(self._run([{"search": "dont stop"}]), [2])

    def test_tag_filters_on_a_comment_marker(self):
        self.cand[0].comment_tags = ["vocal_f", "classic"]
        self.cand[1].comment_tags = ["classic"]
        self.assertEqual(sorted(self._run([{"tag": "classic"}])), [1, 2])
        self.assertEqual(self._run([{"tag": "vocal_f"}]), [1])
        self.assertEqual(self._run([{"tag": "nope"}]), [])

    def test_tag_combines_with_the_other_keys(self):
        self.cand[0].comment_tags = ["classic"]
        self.cand[7].comment_tags = ["classic"]        # a CC one
        self.assertEqual(self._run([{"dance": "SA", "tag": "classic"}]), [1])

    def test_min_fin_keeps_only_what_a_final_has_used(self):
        """Without it the model can only re-rank what the pool happens to hand
        it — and a 600-row budget is spent on the most-played, i.e. heat music."""
        self.cand[2].final_plays = 1
        self.cand[4].final_plays = 5
        self.assertEqual(sorted(self._run([{"dance": "SA", "min_fin": 1}])), [3, 5])
        self.assertEqual(self._run([{"dance": "SA", "min_fin": 2}]), [5])

    def test_sorting_by_finals_puts_the_finalists_first(self):
        self.cand[3].final_plays = 2
        self.cand[5].final_plays = 7
        got = self._run([{"dance": "SA", "sort": "finals", "limit": 3}])
        self.assertEqual(got[:2], [6, 4])

    def test_min_sem_keeps_only_what_a_semifinal_has_used(self):
        """The other half of the same handle: a semifinal is built by hand too,
        and the model cannot ask for that music without a filter for it."""
        self.cand[1].semi_plays = 1
        self.cand[4].semi_plays = 4
        self.assertEqual(sorted(self._run([{"dance": "SA", "min_sem": 1}])), [2, 5])
        self.assertEqual(self._run([{"dance": "SA", "min_sem": 2}]), [5])

    def test_the_two_round_filters_stay_apart(self):
        """A finalist is not a semifinalist — asking for one must not hand over
        the other, or the model plans both rounds out of the same shelf."""
        self.cand[1].semi_plays = 2
        self.cand[4].final_plays = 2
        self.assertEqual(self._run([{"dance": "SA", "min_sem": 1}]), [2])
        self.assertEqual(self._run([{"dance": "SA", "min_fin": 1}]), [5])

    def test_sorting_by_semis_puts_the_semifinalists_first(self):
        self.cand[3].semi_plays = 2
        self.cand[5].semi_plays = 7
        got = self._run([{"dance": "SA", "sort": "semis", "limit": 3}])
        self.assertEqual(got[:2], [6, 4])

    def test_a_query_that_matches_nothing_yields_nothing(self):
        self.assertEqual(self._run([{"dance": "JI"}]), [])

    def test_default_queries_reach_every_dance(self):
        got = self._run(llm.default_queries(self.cand))
        self.assertEqual({self.cand[i - 1].dance for i in got}, set(DANCES))


class CatalogRowsTest(unittest.TestCase):
    """What step 2 actually reads."""

    def setUp(self):
        self.cand = _library()

    def test_only_the_asked_for_rows_are_sent(self):
        text = llm.catalog_rows(self.cand, [7, 13])
        self.assertEqual(len(_rows(text)), 3)           # header + 2
        self.assertIn("CC 1", text)
        self.assertNotIn("SA 1", text)

    def test_a_row_keeps_its_pool_number(self):
        row = _rows(llm.catalog_rows(self.cand, [13]))[1]
        self.assertEqual(row.split("|")[0].strip(), "13")

    def test_the_row_carries_tempo_plays_tags_and_the_used_flag(self):
        e = self.cand[6]                                # CC 1, popularity 9
        e.tag_artist = "Ross Mitchell"
        e.classes_ok = ["A", "S"]
        row = _rows(llm.catalog_rows(
            self.cand, [7], used_paths={str(e.path).lower()}))[1]
        cells = [c.strip() for c in row.split("|")]
        self.assertEqual(cells[1], "CC")                # dance
        self.assertEqual(cells[2], "31")                # bpm
        self.assertEqual(cells[3], "---")               # never analysed
        self.assertEqual(cells[4], "9")                 # plays
        self.assertEqual(cells[5], "0")                 # never in a final
        self.assertEqual(cells[6], "0")                 # nor in a semifinal
        self.assertEqual(cells[7], "yes")               # already planned
        self.assertEqual(cells[8], "A,S")               # comment tag
        self.assertIn("Ross Mitchell", cells[10])

    def test_the_round_counts_are_their_own_columns(self):
        """'pop' says how often, 'fin' and 'sem' say in which round — the whole
        point of the columns is that a heat warhorse, a finalist and a
        semifinalist look different."""
        self.cand[6].final_plays = 4
        self.cand[6].semi_plays = 2
        row = _rows(llm.catalog_rows(self.cand, [7]))[1]
        cells = [c.strip() for c in row.split("|")]
        self.assertEqual(cells[5], "4")
        self.assertEqual(cells[6], "2")

    def test_the_table_always_says_what_fin_and_sem_mean(self):
        """The rules block is user-editable, so the legend cannot rely on it —
        and unlike 'snd' these columns cost no audio analysis to have."""
        text = llm.catalog_rows(self.cand, [7])
        self.assertIn("fin / sem =", text)
        self.assertIn("FINAL", text)
        self.assertIn("SEMIFINAL", text)


class SoundCodeTest(unittest.TestCase):
    """The three digits that stand in for 84 floats."""

    def test_a_dance_is_split_into_fifths_of_its_own(self):
        lib = _analysed([_entry("CC", i) for i in range(1, 11)])
        codes = planner_sound.sound_codes(lib)
        self.assertEqual(codes[str(lib[0].path)], (1, 1, 1))   # quietest
        self.assertEqual(codes[str(lib[-1].path)], (5, 5, 5))  # loudest
        self.assertEqual(len(codes), 10)

    def test_each_dance_is_ranked_against_itself(self):
        """A loud rumba is loud among rumbas — absolute levels say nothing
        across dances, so the ranking never crosses one."""
        quiet_cc = _analysed([_entry("CC", i) for i in range(1, 6)])
        loud_rb = [_entry("RB", i) for i in range(1, 6)]
        for i, e in enumerate(loud_rb, start=1):
            e.features = _feat(50 + i, 9000 + i, 40 + i)
        codes = planner_sound.sound_codes(quiet_cc + loud_rb)
        self.assertEqual(codes[str(quiet_cc[-1].path)][0], 5)
        self.assertEqual(codes[str(loud_rb[0].path)][0], 1)

    def test_an_unanalysed_track_has_no_code(self):
        lib = _analysed([_entry("CC", i) for i in range(1, 6)])
        lib.append(_entry("CC", 99))                    # never analysed
        codes = planner_sound.sound_codes(lib)
        self.assertNotIn(str(lib[-1].path), codes)
        self.assertEqual(planner_sound.code_text(None), "---")
        self.assertEqual(planner_sound.code_text((3, 1, 5)), "315")

    def test_a_stale_short_vector_is_skipped(self):
        """Vectors cached before the rhythm dims existed have no onset value —
        reading index 82 off them would be a lie or a crash."""
        e = _entry("CC", 1)
        e.features = SimpleNamespace(rms=1.0, centroid=1.0, mfcc=[0.0] * 60)
        self.assertEqual(planner_sound.sound_codes([e]), {})


class SoundQueryTest(unittest.TestCase):
    """The model can ask for a corner of the sound, not just a dance."""

    def setUp(self):
        self.cand = _analysed([_entry("CC", i) for i in range(1, 11)])
        self.sound = planner_sound.sound_codes(self.cand)

    def test_a_query_can_ask_for_the_loud_end(self):
        got = llm.run_queries([{"dance": "CC", "energy": "4-5"}],
                                      self.cand, sound=self.sound)
        self.assertEqual(sorted(got), [7, 8, 9, 10])

    def test_the_digits_combine(self):
        got = llm.run_queries(
            [{"dance": "CC", "bright": 1, "drive": "1-2"}],
            self.cand, sound=self.sound)
        self.assertEqual(sorted(got), [1, 2])

    def test_an_unanalysed_track_drops_out_of_a_sound_query(self):
        self.cand.append(_entry("CC", 99))
        got = llm.run_queries([{"dance": "CC", "energy": "1-5"}],
                                      self.cand, sound=self.sound)
        self.assertNotIn(11, got)
        # …but it is still findable by everything else.
        plain = llm.run_queries([{"dance": "CC"}], self.cand)
        self.assertIn(11, plain)

    def test_the_row_and_the_summary_both_carry_the_code(self):
        rows = llm.catalog_rows(self.cand, [1, 10], sound=self.sound)
        self.assertIn("energy (1 quiet", rows)
        self.assertEqual(rows.splitlines()[-1].split("|")[3].strip(), "555")
        summary = llm.library_summary(self.cand, sound=self.sound)
        self.assertIn("10 of 10 tracks are analysed", summary)

    def test_without_codes_nothing_about_sound_is_claimed(self):
        rows = llm.catalog_rows(self.cand, [1])
        self.assertNotIn("energy", rows)
        self.assertNotIn("analysed", llm.library_summary(self.cand))


class PlayedTogetherTest(unittest.TestCase):
    """What the old M3U files know about which tracks go together."""

    def setUp(self):
        self.cand = _library()
        self.history = {
            str(self.cand[0].path): {"turnier_a.m3u", "turnier_b.m3u"},
            str(self.cand[1].path): {"turnier_a.m3u", "turnier_b.m3u"},
            str(self.cand[2].path): {"turnier_a.m3u", "turnier_c.m3u"},
            str(self.cand[3].path): {"turnier_z.m3u"},
        }

    def _of(self, entry):
        return self.history.get(str(entry.path), set())

    def test_pairs_that_share_two_playlists_are_listed_both_ways(self):
        text = llm.played_together([1, 2, 3, 4], self.cand, self._of)
        self.assertIn("  1 with 2", text)
        self.assertIn("  2 with 1", text)
        self.assertIn("played in the same events", text)

    def test_one_shared_playlist_is_a_coincidence(self):
        text = llm.played_together([1, 3], self.cand, self._of)
        self.assertEqual(text, "")

    def test_only_rows_that_were_sent_are_named(self):
        """Naming a row the model cannot pick would be an invitation to
        hallucinate a number."""
        text = llm.played_together([1, 2], self.cand, self._of)
        self.assertIn("  1 with 2", text)
        self.assertNotIn("3", text.split(":", 1)[1])

    def test_no_history_no_block(self):
        self.assertEqual(llm.played_together([1, 2], self.cand, None), "")
        self.assertEqual(
            llm.played_together([1, 2], self.cand, lambda e: set()), "")


class PickReasonsTest(unittest.TestCase):
    """The closing bubble: what the model said about each track it took."""

    def setUp(self):
        self.cand = _library()

    def test_every_pick_gets_its_number_dance_slot_and_reason(self):
        txt = llm.pick_reasons(
            [{"n": 1, "round": "Finale", "heat": 2, "why": "opens hard"}],
            self.cand, "went for punch")
        self.assertIn("went for punch", txt)
        self.assertIn("1 · SA · Finale h2 · SA 1", txt)
        self.assertIn("opens hard", txt)

    def test_the_notes_come_first_and_are_set_apart(self):
        txt = llm.pick_reasons([{"n": 1, "why": "x"}], self.cand,
                                       "the plan")
        self.assertTrue(txt.startswith("the plan"))
        self.assertIn("\n\n", txt.split("x")[0])

    def test_a_pick_without_a_reason_is_still_listed(self):
        txt = llm.pick_reasons([{"n": 2}], self.cand)
        self.assertIn("SA 2", txt)
        self.assertEqual(len(txt.splitlines()), 1)

    def test_the_artist_is_named_when_there_is_one(self):
        self.cand[0].tag_artist = "Klaus Hallen"
        txt = llm.pick_reasons([{"n": 1}], self.cand)
        self.assertIn("Klaus Hallen", txt)

    def test_a_number_past_the_catalog_is_skipped(self):
        self.assertEqual(llm.pick_reasons([{"n": 999}], self.cand), "")
        self.assertEqual(llm.pick_reasons([], self.cand, "notes"), "")

    def test_a_reason_the_model_wrote_as_an_essay_is_cut(self):
        out = llm.parse_reply(
            '{"playlist": [{"n": 1, "why": "' + "ja " * 200 + '"}]}')
        self.assertLessEqual(len(out["picks"][0]["why"]), 200)


class TwoTurnTest(unittest.TestCase):
    """SEARCH -> PICK, with both backends stubbed out."""

    def setUp(self):
        self.cand = _library()
        self.asked = []
        self.real_ask = llm._ask

    def tearDown(self):
        llm._ask = self.real_ask

    def _stub(self, *replies):
        it = iter(replies)

        def fake(system, user, **kw):
            self.asked.append((system, user))
            nxt = next(it)
            if isinstance(nxt, Exception):
                raise nxt
            return nxt, "stub"
        llm._ask = fake

    def test_the_search_round_narrows_what_step_two_sees(self):
        self._stub('{"queries": [{"dance": "CC", "limit": 2}]}',
                   '{"playlist": [{"n": 7}]}')
        picks, _notes, backend = llm.ask_playlist("r", "t", self.cand)
        self.assertEqual(backend, "stub")
        self.assertEqual([p["n"] for p in picks], [7])

        search_user, pick_user = self.asked[0][1], self.asked[1][1]
        self.assertNotIn("CC 1", search_user)          # step 1 sees no titles
        self.assertIn("CC 1", pick_user)               # step 2 sees the rows
        self.assertNotIn("SA 1", pick_user)            # and nothing else

    def test_each_step_gets_its_own_contract(self):
        self._stub('{"queries": [{"dance": "SA"}]}', '{"playlist": [1]}')
        llm.ask_playlist("r", "t", self.cand)
        self.assertIn("min_pop", self.asked[0][0])     # the query language
        self.assertIn('"playlist"', self.asked[1][0])  # the answer format

    def test_a_dead_search_round_still_produces_a_playlist(self):
        self._stub(RuntimeError("no backend"), '{"playlist": [1]}')
        picks, _n, _b = llm.ask_playlist("r", "t", self.cand)
        self.assertEqual([p["n"] for p in picks], [1])
        for code in DANCES:                            # swept, so all dances
            self.assertIn(code + " 1", self.asked[1][1])

    def test_cancel_during_the_search_round_skips_the_sweep(self):
        stop = threading.Event()

        def fake(system, user, **kw):
            stop.set()                  # Cancel pressed as the answer lands
            return '{"queries": [{"dance": "SA"}]}', "stub"
        llm._ask = fake
        with self.assertRaises(llm.Cancelled):
            llm.search_rows("r", "t", self.cand, cancel=stop)

    def test_queries_that_match_nothing_fall_back_to_the_sweep(self):
        self._stub('{"queries": [{"dance": "JI"}]}', '{"playlist": [1]}')
        llm.ask_playlist("r", "t", self.cand)
        self.assertIn("SA 1", self.asked[1][1])

    def test_a_number_that_was_not_offered_is_dropped(self):
        # Step two sees only the CC rows; 1 is an SA track it was never shown,
        # and a number the model made up would put that track in the deck.
        self._stub('{"queries": [{"dance": "CC", "limit": 2}]}',
                   '{"playlist": [{"n": 7}, {"n": 1}]}')
        steps = []
        picks, _n, _b = llm.ask_playlist(
            "r", "t", self.cand, on_step=lambda *s: steps.append(s))
        self.assertEqual([p["n"] for p in picks], [7])
        self.assertTrue(any(role == "note" and "1" in text
                            for role, _title, text in steps),
                        "the transcript says which number was dropped")

    def test_an_answer_of_only_numbers_never_offered_fails(self):
        self._stub('{"queries": [{"dance": "CC", "limit": 2}]}',
                   '{"playlist": [{"n": 1}, {"n": 2}]}')
        with self.assertRaises(RuntimeError):
            llm.ask_playlist("r", "t", self.cand)

    def test_a_dead_picking_round_is_reported(self):
        self._stub('{"queries": [{"dance": "SA"}]}', RuntimeError("both down"))
        with self.assertRaises(RuntimeError):
            llm.ask_playlist("r", "t", self.cand)


class TranscriptTest(unittest.TestCase):
    """What the window is allowed to show: every prompt and every reply.

    The run used to be a spinner and then a filled grid — nothing said what
    had been asked. `on_step` reports it as it happens.
    """

    def setUp(self):
        self.cand = _library()
        self.steps = []
        self.real_ask = llm._ask

    def tearDown(self):
        llm._ask = self.real_ask

    def _stub(self, *replies):
        it = iter(replies)

        def fake(system, user, **kw):
            nxt = next(it)
            if isinstance(nxt, Exception):
                raise nxt
            return nxt, "stub"
        llm._ask = fake

    def _run(self):
        return llm.ask_playlist(
            "r", "t", self.cand,
            on_step=lambda *a: self.steps.append(a))

    def test_both_questions_and_both_answers_are_reported(self):
        self._stub('{"queries": [{"dance": "CC", "limit": 2}]}',
                   '{"playlist": [{"n": 7}]}')
        self._run()
        roles = [role for role, _t, _x in self.steps]
        self.assertEqual(roles, ["sent", "received", "note", "sent", "received"])

    def test_the_prompts_are_reported_verbatim(self):
        self._stub('{"queries": [{"dance": "CC", "limit": 2}]}',
                   '{"playlist": [{"n": 7}]}')
        self._run()
        sent = [text for role, _t, text in self.steps if role == "sent"]
        self.assertNotIn("CC 1", sent[0])      # step 1: the summary only
        self.assertIn("CC 1", sent[1])         # step 2: the rows it may pick
        got = [text for role, _t, text in self.steps if role == "received"]
        self.assertEqual(got[1], '{"playlist": [{"n": 7}]}')

    def test_the_query_pass_in_between_is_reported_too(self):
        self._stub('{"queries": [{"dance": "CC", "limit": 2}]}',
                   '{"playlist": [{"n": 7}]}')
        self._run()
        note = [text for role, _t, text in self.steps if role == "note"][-1]
        self.assertIn("1 query", note)
        self.assertIn(f"of {len(self.cand)} tracks", note)

    def test_a_dead_search_round_says_so(self):
        self._stub(RuntimeError("no backend"), '{"playlist": [1]}')
        self._run()
        notes = [t for role, t, _x in self.steps if role == "note"]
        self.assertIn("1 · The search round failed", notes)

    def test_a_watcher_that_throws_does_not_sink_the_run(self):
        self._stub('{"queries": [{"dance": "CC"}]}', '{"playlist": [7]}')

        def boom(*_a):
            raise RuntimeError("the window is gone")
        with self.assertLogs("dancesport.llm", level="ERROR"):
            picks, _n, _b = llm.ask_playlist(
                "r", "t", self.cand, on_step=boom)
        self.assertEqual([p["n"] for p in picks], [7])

    def test_nobody_watching_is_the_normal_case(self):
        self._stub('{"queries": [{"dance": "CC"}]}', '{"playlist": [7]}')
        picks, _n, _b = llm.ask_playlist("r", "t", self.cand)
        self.assertEqual([p["n"] for p in picks], [7])


if __name__ == "__main__":
    unittest.main(verbosity=2)
