#!/usr/bin/env python3
"""Tests for the 🤖 AI playlist option (planner.llm + the grid it fills).

Run:  py -m unittest tests.planner.test_ai_playlist -v

The model is never trusted with a file path: it answers with catalog NUMBERS,
so a hallucinated title cannot reach a playlist. These tests pin that contract
from both ends — what goes into the prompt (only TSO-conform candidates) and
what comes back out of a sloppy answer (fenced JSON, bare ints, a round name in
the wrong case, a number past the end of the catalog).

No network and no claude CLI: everything here exercises the pure halves.
"""

import datetime
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_ai_"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QPushButton  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from planner import event_plan, i18n  # noqa: E402
from planner import llm  # noqa: E402
from planner import sound as planner_sound  # noqa: E402
from planner.models import MusicEntry, RoundConfig  # noqa: E402
from gui.ai_dialogs import (  # noqa: E402
    AiPlaylistDialog, AiTranscriptDialog, _Bubble, _ThinkingBubble,
)

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
    """Just the three numbers planner.sound reads off an analysed track."""
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


class DialogTest(unittest.TestCase):
    """The rules are the user's — they come back exactly as typed, and the
    default set is one click away again."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self, settings=None):
        dlg = AiPlaylistDialog(settings if settings is not None else {})
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_defaults(self):
        vals = self._dlg().values()
        self.assertEqual(vals["mode"], "competition")
        self.assertEqual(vals["rules"], llm.DEFAULT_RULES.strip())
        self.assertEqual(vals["model"], llm.CLAUDE_MODEL)

    def test_the_default_model_is_the_latest_opus(self):
        # Marcel: "use latest opus model not a specific one" — the CLI's alias
        # follows each new Opus without a code change.
        self.assertEqual(llm.CLAUDE_MODEL, "opus")

    def test_the_model_is_picked_from_opus_and_sonnet_or_typed(self):
        # Marcel: "show a combobox and make it editable, so the user can choose
        # between sonnet and opus".
        dlg = self._dlg()
        box = dlg._model
        self.assertTrue(box.isEditable())
        self.assertEqual([box.itemText(i) for i in range(box.count())],
                         ["opus", "sonnet"])
        box.setCurrentIndex(1)
        self.assertEqual(dlg.values()["model"], "sonnet")
        box.setEditText("claude-opus-5")
        self.assertEqual(dlg.values()["model"], "claude-opus-5")

    def test_saved_rules_come_back(self):
        dlg = self._dlg({"ai_rules": "Only Tango.", "ai_model": "claude-sonnet-5",
                         "ai_flat_count": 25})
        vals = dlg.values()
        self.assertEqual(vals["rules"], "Only Tango.")
        self.assertEqual(vals["model"], "claude-sonnet-5")
        self.assertEqual(vals["count"], 25)

    def test_reset_button_restores_the_default_rules(self):
        dlg = self._dlg({"ai_rules": "Only Tango."})
        self.assertEqual(dlg.values()["rules"], "Only Tango.")
        reset = next(b for b in dlg.findChildren(QPushButton)
                     if b.text().startswith("↺"))
        reset.click()
        self.assertEqual(dlg.values()["rules"], llm.DEFAULT_RULES.strip())

    def test_an_untouched_rule_set_is_not_frozen_into_the_settings(self):
        """Saving the shipped words would shadow every later change to them —
        which is exactly how the rules came to say nothing about the round
        columns. Empty means "whatever the app ships"."""
        self.assertEqual(
            llm.rules_to_remember(self._dlg().values()["rules"]), "")

    def test_what_the_user_typed_is_remembered_word_for_word(self):
        self.assertEqual(llm.rules_to_remember("Only Tango."), "Only Tango.")

    def test_flat_mode_reports_its_count(self):
        dlg = self._dlg()
        dlg._rb_flat.setChecked(True)
        dlg._count_spin.setValue(40)
        vals = dlg.values()
        self.assertEqual(vals["mode"], "flat")
        self.assertEqual(vals["count"], 40)

    def test_the_chosen_login_comes_back(self):
        dlg = self._dlg({"ai_claude_config_dir": r"C:\Users\x\.claude-profil1"})
        self.assertEqual(dlg.values()["config_dir"],
                         r"C:\Users\x\.claude-profil1")

    def test_no_login_set_means_the_cli_decides(self):
        old = os.environ.pop("CLAUDE_CONFIG_DIR", None)
        try:
            self.assertEqual(self._dlg().values()["config_dir"], "")
        finally:
            if old is not None:
                os.environ["CLAUDE_CONFIG_DIR"] = old

    def test_wish_mode_hands_over_the_pasted_titles(self):
        dlg = self._dlg()
        dlg._rb_wish.setChecked(True)
        dlg._wishes.setPlainText("White wings lw\nmelancolia lw!!\n")
        vals = dlg.values()
        self.assertEqual(vals["mode"], "wishes")
        self.assertEqual(vals["wishes"], "White wings lw\nmelancolia lw!!")

    def test_the_wish_list_comes_back_next_time(self):
        dlg = self._dlg({"ai_wishes": "hey ya qs"})
        self.assertEqual(dlg._wishes.toPlainText(), "hey ya qs")

    def test_the_wish_box_is_only_on_screen_in_wish_mode(self):
        dlg = self._dlg()
        self.assertFalse(dlg._wishes.isVisibleTo(dlg))
        dlg._rb_wish.setChecked(True)
        self.assertTrue(dlg._wishes.isVisibleTo(dlg))
        self.assertFalse(dlg._count_spin.isEnabled())
        dlg._rb_flat.setChecked(True)
        self.assertFalse(dlg._wishes.isVisibleTo(dlg))

    def test_the_brief_takes_more_than_one_line(self):
        """It is the free prompt now — a paragraph has to survive it."""
        dlg = self._dlg()
        dlg._brief.setPlainText("club evening\nkeep it modern")
        self.assertEqual(dlg.values()["brief"], "club evening\nkeep it modern")

    def test_the_track_count_only_applies_to_a_flat_list(self):
        dlg = self._dlg()
        self.assertFalse(dlg._count_spin.isEnabled())
        dlg._rb_flat.setChecked(True)
        self.assertTrue(dlg._count_spin.isEnabled())


class EventDialogTest(unittest.TestCase):
    """🏆 Event: a pasted schedule becomes the day's competitions, read back
    from the table the user may correct; the rest says where the titles come
    from and which variants to plan."""

    SCHEDULE = ("Sa: 10:00 HGR S STD 2-1\n"
                "J & J (LW; TG; CC; RB) VR ZR ER 24 - 12 - 6\n")

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dp_event_dlg_"))
        self.addCleanup(shutil.rmtree, self.root, True)
        for name in ("DanceConvention 2024", "DanceConvention 2025", "WiDaFe 2014"):
            (self.root / name).mkdir()
        orig = event_plan.PLAYLIST_DIR
        event_plan.PLAYLIST_DIR = self.root
        self.addCleanup(setattr, event_plan, "PLAYLIST_DIR", orig)

    def _dlg(self, settings=None):
        dlg = AiPlaylistDialog(settings if settings is not None else {})
        self.addCleanup(reap_widget, dlg)
        dlg._rb_event.setChecked(True)
        return dlg

    def test_the_schedule_becomes_the_competitions(self):
        dlg = self._dlg()
        dlg._event._schedule.setPlainText(self.SCHEDULE)
        vals = dlg.values()
        self.assertEqual(vals["mode"], "event")
        specs = vals["event"]["specs"]
        self.assertEqual([s.label for s in specs], ["HGR S STD", "J & J"])
        self.assertEqual(specs[1].dances, ["LW", "TG", "CC", "RB"])
        self.assertEqual(specs[1].heats, [2, 1, 1])
        self.assertEqual(dlg._event._table.rowCount(), 2)
        self.assertEqual(dlg._event._table.item(0, 3).text(), "2-1")

    def test_a_corrected_row_is_what_gets_planned(self):
        dlg = self._dlg()
        dlg._event._schedule.setPlainText(self.SCHEDULE)
        table = dlg._event._table
        table.item(0, 1).setText("a")
        table.item(0, 2).setText("LW TG QS")
        table.item(0, 3).setText("3 - 2 - 1")
        spec = dlg.values()["event"]["specs"][0]
        self.assertEqual(spec.dance_class, "A")
        self.assertEqual(spec.dances, ["LW", "TG", "QS"])
        self.assertEqual(spec.heats, [3, 2, 1])

    def test_a_cell_that_makes_no_sense_keeps_what_was_read(self):
        dlg = self._dlg()
        dlg._event._schedule.setPlainText(self.SCHEDULE)
        table = dlg._event._table
        table.item(0, 1).setText("X")
        table.item(0, 2).setText("waltz")
        table.item(0, 3).setText("")
        spec = dlg.values()["event"]["specs"][0]
        self.assertEqual((spec.dance_class, spec.heats), ("S", [2, 1]))
        self.assertEqual(spec.dances, ["LW", "TG", "WW", "SF", "QS"])

    def test_a_variant_added_since_the_last_choice_starts_on(self):
        """The choice saved before "last year, renewed" existed leaves it on;
        one made since keeps it off."""
        old = self._dlg({"ai_event_variants": ["like_last_year", "variety"]})
        self.assertEqual(old.values()["event"]["variants"],
                         ["like_last_year", "last_year_renewed", "variety"])
        new = self._dlg({"ai_event_variants": ["like_last_year", "variety"],
                         "ai_event_variants_offered": list(event_plan.PROFILE_ORDER)})
        self.assertEqual(new.values()["event"]["variants"],
                         ["like_last_year", "variety"])

    def test_the_defaults(self):
        ev = self._dlg().values()["event"]
        self.assertEqual(ev["variants"], list(event_plan.PROFILE_ORDER))
        self.assertEqual(ev["new_share"], 0.2)
        self.assertEqual(ev["rare_share"], 0.15)
        self.assertTrue(ev["use_event"])
        self.assertTrue(ev["use_class"])
        self.assertTrue(ev["ai_check"])
        self.assertEqual(ev["year"], datetime.date.today().year)

    def test_the_series_in_the_playlist_folder_are_offered(self):
        dlg = self._dlg()
        combo = dlg._event._series
        names = [combo.itemText(i) for i in range(combo.count())]
        self.assertEqual(names, ["DanceConvention", "WiDaFe"])
        combo.setCurrentText("DanceConvention")
        self.assertEqual(dlg.values()["event"]["series"], "danceconvention")

    def test_a_typed_series_counts_too(self):
        dlg = self._dlg()
        dlg._event._series.setCurrentText("Blue Ribbon 2026")
        self.assertEqual(dlg.values()["event"]["series"], "blue ribbon")

    def test_the_choices_come_back_next_time(self):
        dlg = self._dlg({"ai_event_schedule": "HGR S STD 2-1",
                         "ai_event_series": "WiDaFe",
                         "ai_event_new_share": 35,
                         "ai_event_rare_share": 5,
                         "ai_event_variants": ["variety"],
                         "ai_event_variants_offered": list(event_plan.PROFILE_ORDER),
                         "ai_event_use_event": False,
                         "ai_event_use_class": False,
                         "ai_event_ai_check": False})
        ev = dlg.values()["event"]
        self.assertEqual(ev["schedule"], "HGR S STD 2-1")
        self.assertEqual(ev["series_name"], "WiDaFe")
        self.assertEqual(ev["new_share"], 0.35)
        self.assertEqual(ev["rare_share"], 0.05)
        self.assertEqual(ev["variants"], ["variety"])
        self.assertFalse(ev["use_event"])
        self.assertFalse(ev["use_class"])
        self.assertFalse(ev["ai_check"])

    def test_the_last_plan_can_be_opened_again(self):
        dlg = AiPlaylistDialog({}, event_plan_kept=True)
        self.addCleanup(reap_widget, dlg)
        self.assertFalse(dlg._reopen_btn.isVisibleTo(dlg))
        dlg._rb_event.setChecked(True)
        self.assertTrue(dlg._reopen_btn.isVisibleTo(dlg))
        dlg._reopen_btn.click()
        self.assertEqual(dlg.result(), AiPlaylistDialog.REOPEN_PLAN)

    def test_the_new_share_can_be_typed(self):
        dlg = self._dlg()
        dlg._event._new_share_box.setValue(33)
        self.assertEqual(dlg._event._new_share.value(), 33)
        self.assertEqual(dlg.values()["event"]["new_share"], 0.33)
        dlg._event._new_share.setValue(10)
        self.assertEqual(dlg._event._new_share_box.value(), 10)

    def test_the_rare_share_can_be_typed(self):
        dlg = self._dlg()
        dlg._event._rare_share_box.setValue(25)
        self.assertEqual(dlg._event._rare_share.value(), 25)
        self.assertEqual(dlg.values()["event"]["rare_share"], 0.25)
        dlg._event._rare_share.setValue(0)
        self.assertEqual(dlg._event._rare_share_box.value(), 0)

    def test_the_column_heads_are_not_cut_off(self):
        """'Gruppen pro Runde' showed as 'Gruppen pro Rund' in the German panel."""
        dlg = self._dlg()
        dlg.show()
        QApplication.processEvents()
        head = dlg._event._table.horizontalHeader()
        for col in (1, 2, 3):
            text = dlg._event._table.horizontalHeaderItem(col).text()
            self.assertGreaterEqual(head.sectionSize(col),
                                    head.fontMetrics().horizontalAdvance(text), text)

    def test_the_login_hint_speaks_german(self):
        """The hint reaches its label through a variable, so the coverage scan
        never flagged it and it stayed English in the German dialog."""
        i18n.set_active("de")
        i18n.install_text_hook()
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)
        self.addCleanup(i18n._restore_text_hook)
        for available in (True, False):
            with mock.patch.object(llm, "claude_available", return_value=available):
                dlg = self._dlg()
            texts = " ".join(lbl.text() for lbl in dlg.findChildren(QLabel))
            self.assertNotIn("Runs through the claude CLI", texts)
            self.assertNotIn("claude CLI not found", texts)

    def test_no_plan_kept_no_button(self):
        dlg = self._dlg()
        self.assertFalse(dlg._reopen_btn.isVisibleTo(dlg))

    def test_the_panel_is_only_on_screen_in_event_mode(self):
        dlg = self._dlg()
        self.assertTrue(dlg._event.isVisibleTo(dlg))
        self.assertFalse(dlg._brief.isVisibleTo(dlg))
        dlg._rb_comp.setChecked(True)
        self.assertFalse(dlg._event.isVisibleTo(dlg))
        self.assertTrue(dlg._brief.isVisibleTo(dlg))


class ClaudeLoginTest(unittest.TestCase):
    """Which `claude` login the CLI is pointed at.

    A shell exports CLAUDE_CONFIG_DIR; the GUI started from the desktop has no
    such variable and would take ~/.claude, which need not be the profile that
    is logged in — so the login is a setting, offered from what is on disk.
    """

    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="dp_home_")

    def _make(self, name, marker="settings.json"):
        d = Path(self.home) / name
        d.mkdir(parents=True, exist_ok=True)
        if marker:
            (d / marker).write_text("{}", encoding="utf-8")
        return str(d)

    def test_the_profiles_beside_the_plain_one_are_found(self):
        plain = self._make(".claude")
        one = self._make(".claude-profil1", ".credentials.json")
        two = self._make(".claude-profil2")
        self.assertEqual(llm.claude_config_dirs(self.home),
                         [plain, one, two])

    def test_the_plain_login_comes_first_even_when_it_sorts_later(self):
        self._make(".claude-alpha")
        plain = self._make(".claude")
        self.assertEqual(llm.claude_config_dirs(self.home)[0], plain)

    def test_a_dotfolder_without_a_login_in_it_is_not_offered(self):
        self._make(".claude-empty", marker="")
        self._make(".claudemind", marker="")
        self.assertEqual(llm.claude_config_dirs(self.home), [])

    def test_unrelated_folders_are_left_alone(self):
        self._make(".config")
        self._make("Documents")
        self.assertEqual(llm.claude_config_dirs(self.home), [])

    def test_a_home_that_cannot_be_listed_is_no_crash(self):
        self.assertEqual(
            llm.claude_config_dirs(self.home + "_gone"), [])

    def test_the_environment_is_the_default_when_there_is_one(self):
        old = os.environ.get("CLAUDE_CONFIG_DIR")
        os.environ["CLAUDE_CONFIG_DIR"] = r"C:\Users\x\.claude-profil1"
        try:
            self.assertEqual(llm.default_claude_config_dir(),
                             r"C:\Users\x\.claude-profil1")
        finally:
            if old is None:
                del os.environ["CLAUDE_CONFIG_DIR"]
            else:
                os.environ["CLAUDE_CONFIG_DIR"] = old


class TranscriptWindowTest(unittest.TestCase):
    """The window the steps are written into while the worker is thinking."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self):
        dlg = AiTranscriptDialog()
        self.addCleanup(reap_widget, dlg)
        return dlg

    @staticmethod
    def _bubbles(dlg):
        """Every chat bubble in the thread, oldest first."""
        return dlg.findChildren(_Bubble)

    def test_a_step_lands_with_its_title_and_its_text(self):
        dlg = self._dlg()
        dlg.add_step("sent", "1 · What the model is asked to search", "summary")
        bubble = self._bubbles(dlg)[0]
        labels = " ".join(w.text() for w in bubble.findChildren(QLabel))
        self.assertIn("1 · What the model is asked to search", labels)
        self.assertIn("summary", labels)
        self.assertIn("Planner", labels)              # the app's own side

    def test_the_steps_stay_in_order(self):
        dlg = self._dlg()
        dlg.add_step("sent", "first", "a")
        dlg.add_step("received", "second", "b")
        text = dlg.transcript()
        self.assertLess(text.index("first"), text.index("second"))
        self.assertIn("Model", text)                  # 'it answered'

    def test_each_speaker_gets_its_own_side(self):
        """Like any chat client: what we send is right, the answer is left."""
        dlg = self._dlg()
        dlg.add_step("sent", "ask", "a")
        dlg.add_step("received", "answer", "b")
        sent_row, recv_row = (b.parentWidget() for b in self._bubbles(dlg))
        # A stretch BEFORE the bubble pushes it right, one after it pushes left.
        self.assertIsNotNone(sent_row.layout().itemAt(0).spacerItem())
        self.assertIsNone(recv_row.layout().itemAt(0).spacerItem())

    def test_a_note_is_a_line_between_them_not_a_bubble(self):
        dlg = self._dlg()
        dlg.add_step("note", "What the queries found", "3 queries → 40 tracks")
        self.assertEqual(self._bubbles(dlg), [])
        self.assertIn("3 queries → 40 tracks", dlg.transcript())

    def test_a_long_turn_opens_folded(self):
        """600 catalog rows must not bury the shape of the conversation."""
        dlg = self._dlg()
        body = "\n".join(f"{i}. Track {i}" for i in range(1, 61))
        dlg.add_step("sent", "2 · The tracks it may pick from", body)
        bubble = self._bubbles(dlg)[0]
        self.assertIn("more lines", bubble._more.text())
        self.assertNotIn("60. Track 60", bubble._body.text())
        bubble._more.click()
        self.assertIn("60. Track 60", bubble._body.text())
        # Folded or not, 📋 Copy hands over every line.
        self.assertIn("60. Track 60", dlg.transcript())

    def test_an_unfolded_turn_folds_back_up(self):
        """Unfolding the catalog buries whatever came after it — the same link
        has to put it away again."""
        dlg = self._dlg()
        body = "\n".join(f"{i}. Track {i}" for i in range(1, 61))
        dlg.add_step("sent", "2 · The tracks it may pick from", body)
        bubble = self._bubbles(dlg)[0]
        bubble._more.click()                      # unfold
        self.assertIn("fold back", bubble._more.text())
        bubble._more.click()                      # and back up
        self.assertNotIn("60. Track 60", bubble._body.text())
        self.assertIn("46 more lines", bubble._more.text())
        self.assertFalse(bubble._more.isHidden())

    def test_the_transcript_is_a_window_of_its_own(self):
        """Minimising an owned dialog on Windows loses it: no taskbar button.
        The transcript outlives a long run, so it is a real window."""
        dlg = self._dlg()
        flags = dlg.windowFlags()
        self.assertTrue(flags & Qt.WindowType.Window)
        self.assertTrue(flags & Qt.WindowType.WindowMinimizeButtonHint)
        self.assertIsNone(dlg.parent())

    def test_a_closed_transcript_keeps_everything_and_can_come_back(self):
        """Closing the window only puts it away: 💬 reopens the same thread,
        and only the next run throws it out."""
        from gui.main_generate import GenerateMixin

        dlg = self._dlg()
        dlg.add_step("received", "Why these tracks", "because")
        dlg.show()
        dlg.close()
        self.assertFalse(dlg.isVisible())

        win = SimpleNamespace(_ai_log=dlg)
        GenerateMixin._show_ai_log(win)
        self.assertTrue(dlg.isVisible())
        self.assertIn("because", dlg.transcript())

    def test_reopening_nothing_is_not_a_crash(self):
        from gui.main_generate import GenerateMixin

        GenerateMixin._show_ai_log(SimpleNamespace(_ai_log=None))

    def test_the_status_bar_counts_what_the_run_moves(self):
        """Nothing else says how much of the context window a run eats."""
        dlg = self._dlg()
        dlg.add_step("sent", "the catalog", "x" * 8000)
        dlg.add_step("received", "the picks", "y" * 400)
        text = dlg._usage.text()
        self.assertIn("8.0k chars", text)          # sent
        self.assertIn("400 chars", text)           # and back
        self.assertIn("2.0k tok", text)            # 8000 / 4
        self.assertIn("2.1k tok", text)            # the turn: prompt + reply

    def test_a_note_is_not_context(self):
        # Notes are the planner talking to itself; the model never sees them.
        dlg = self._dlg()
        dlg.add_step("note", "Pool", "z" * 500)
        self.assertEqual(dlg._usage.text(), "")
        self.assertIn("📤 0 chars", dlg.usage_text())


class ThinkingIndicatorTest(unittest.TestCase):
    """A turn takes minutes. While one is out, the thread carries a live
    "the model is typing" bubble — a window that has died looks exactly like a
    window with a finished prompt in it."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self):
        dlg = AiTranscriptDialog()
        self.addCleanup(reap_widget, dlg)
        return dlg

    @staticmethod
    def _thinking(dlg):
        return dlg.findChildren(_ThinkingBubble)

    def test_a_question_leaves_the_model_visibly_thinking(self):
        dlg = self._dlg()
        dlg.add_step("sent", "1 · What to search for", "summary")
        bubble = self._thinking(dlg)[0]
        self.assertTrue(bubble._timer.isActive())
        self.assertIn("thinking", bubble._label.text())

    def test_the_dots_move_and_the_clock_counts(self):
        dlg = self._dlg()
        dlg.add_step("sent", "ask", "a")
        bubble = self._thinking(dlg)[0]
        first = bubble._label.text()
        bubble._tick()
        self.assertNotEqual(bubble._label.text(), first)
        for _ in range(4):                 # 5 ticks × 400 ms = 2 s
            bubble._tick()
        self.assertEqual(bubble.elapsed_text(), "0:02")

    def test_it_sits_at_the_end_of_the_thread_on_the_model_side(self):
        dlg = self._dlg()
        dlg.add_step("sent", "ask", "a")
        row = dlg._open[0][1]
        self.assertIs(dlg._thread.itemAt(dlg._thread.count() - 2).widget(), row)
        self.assertIsNone(row.layout().itemAt(0).spacerItem())

    def test_the_answer_takes_it_away(self):
        dlg = self._dlg()
        dlg.add_step("sent", "ask", "a")
        bubble = self._thinking(dlg)[0]
        dlg.add_step("received", "answer", "b")
        self.assertEqual(dlg._open, [])
        self.assertFalse(bubble._timer.isActive())

    def test_a_note_after_the_answer_does_not_leave_two_of_them(self):
        dlg = self._dlg()
        dlg.add_step("sent", "ask", "a")
        dlg.add_step("received", "answer", "b")
        dlg.add_step("note", "What the queries found", "40 tracks")
        self.assertEqual(len(self._thinking(dlg)), 0)
        dlg.add_step("sent", "ask again", "c")
        self.assertEqual(len(self._thinking(dlg)), 1)

    def test_a_retry_note_keeps_the_waiting_visible(self):
        """A note while the question is still out means the backend wobbled and
        we are waiting again — one indicator, not none and not two."""
        dlg = self._dlg()
        dlg.add_step("sent", "1 · What to search for", "a")
        dlg.add_step("note", "⏳ claude -p — attempt 1 of 4", "HTTP 529")
        self.assertEqual(len(self._thinking(dlg)), 1)
        self.assertIn("1 · What to search for",
                      self._thinking(dlg)[0].findChildren(QLabel)[0].text())
        dlg.add_step("received", "its answer", "b")
        self.assertEqual(len(self._thinking(dlg)), 0)

    def test_parallel_questions_each_keep_their_own_clock(self):
        """The event planner sends every competition's question at once and
        the answers come back in any order: each question out is one bubble,
        and an answer takes away its own — not the last one sent."""
        dlg = self._dlg()
        dlg.add_step("sent", "HGR S STD — the drafts to check", "a")
        first = self._thinking(dlg)[0]
        first._tick()
        dlg.add_step("sent", "SEN I S STD — the drafts to check", "b")
        dlg.add_step("sent", "HGR A LAT — the drafts to check", "c")
        self.assertEqual(len(self._thinking(dlg)), 3)
        self.assertTrue(first._timer.isActive())
        self.assertEqual(first._frame, 1)             # its clock ran on
        self.assertEqual(dlg._status.text(), "Waiting for the model… (3)")
        dlg.add_step("received", "SEN I S STD — its swaps — stub", "[]")
        titles = [b.findChildren(QLabel)[0].text() for b in self._thinking(dlg)]
        self.assertEqual(len(titles), 2)
        self.assertFalse(any("SEN I S STD" in t for t in titles))
        self.assertEqual(dlg._status.text(), "Waiting for the model… (2)")
        dlg.add_step("note", "HGR A LAT — the plan stands", "HTTP 500")
        self.assertEqual(len(self._thinking(dlg)), 1)
        self.assertEqual(dlg._status.text(), "Waiting for the model…")
        dlg.add_step("received", "HGR S STD — its swaps — stub", "[]")
        self.assertEqual(self._thinking(dlg), [])
        self.assertEqual(dlg._status.text(), "Working…")

    def test_new_rows_go_above_the_waiting(self):
        dlg = self._dlg()
        dlg.add_step("sent", "A — the drafts to check", "a")
        dlg.add_step("sent", "B — the drafts to check", "b")
        dlg.add_step("received", "B — its swaps — stub", "[]")
        last = dlg._thread.itemAt(dlg._thread.count() - 2).widget()
        self.assertTrue(last.findChildren(_ThinkingBubble))

    def test_a_parallel_turn_pairs_the_answer_with_its_own_question(self):
        """The biggest turn is a prompt plus ITS reply, not the last prompt
        sent plus whichever reply landed first."""
        dlg = self._dlg()
        dlg.add_step("sent", "A — the drafts to check", "x" * 8000)
        dlg.add_step("sent", "B — the drafts to check", "x" * 400)
        dlg.add_step("received", "A — its swaps — stub", "y" * 400)
        dlg.add_step("received", "B — its swaps — stub", "y" * 400)
        self.assertEqual(dlg._turn_max, 8400)

    def test_the_end_of_the_run_stops_it(self):
        dlg = self._dlg()
        dlg.add_step("sent", "ask", "a")
        bubble = self._thinking(dlg)[0]
        dlg.finish("🤖 Done")
        self.assertEqual(self._thinking(dlg), [])
        self.assertFalse(bubble._timer.isActive())
        self.assertEqual(dlg._status.text(), "🤖 Done")

    def test_the_indicator_is_not_part_of_the_transcript(self):
        """📋 Copy hands over the conversation, not the waiting."""
        dlg = self._dlg()
        dlg.add_step("sent", "ask", "a")
        self.assertNotIn("thinking", dlg.transcript())

    def test_finishing_stops_the_bar_and_says_how_it_went(self):
        dlg = self._dlg()
        dlg.add_step("sent", "asking", "…")
        self.assertEqual(dlg._bar.maximum(), 0)       # indeterminate: still busy
        dlg.finish("🤖 18/18 slots filled by stub")
        self.assertEqual(dlg._bar.maximum(), 1)
        self.assertIn("18/18", dlg._status.text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
