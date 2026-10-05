#!/usr/bin/env python3
"""The AI pass over an event day: one question per competition, swaps back.

Run:  py -m unittest tests.planner.test_event_ai -v

The three variants are planned without any model (test_event_variants). The
model then sees all three drafts of one competition and a numbered catalogue
of its candidates, and answers with swaps: this slot, this row, this reason.
Every swap is checked against the same rules the planner keeps — a number it
was shown, the slot's own dance, no title twice in the day, no title from
another competition's history. In "like last year" a swap is only offered
next to last year's title. And when the model fails, the plan stands.
"""

import json
import re
import threading
import unittest

from planner import event_plan
from planner.competition import parse_competition_schedule
from tests.planner.test_event_variants import EventFixture


class FakeModel:
    """Stands in for `llm._ask`: records every question, answers with swaps."""

    def __init__(self, answer):
        self.answer = answer      # (call index, user prompt) → swaps, notes
        self.calls = []

    def __call__(self, system, user):
        self.calls.append((system, user))
        swaps, notes = self.answer(len(self.calls) - 1, user)
        return json.dumps({"swaps": swaps, "notes": notes}), "fake"


def number_of(user, title):
    """The catalogue number a title was shown under, or None."""
    m = re.search(rf"^\s*(\d+) \|.*\| {re.escape(title)}$", user, re.MULTILINE)
    return int(m.group(1)) if m else None


def swap(variant, rnd, dance, n, why="", heat=1):
    return {"variant": variant, "round": rnd, "heat": heat, "dance": dance,
            "n": n, "why": why}


class EventAiTest(EventFixture, unittest.TestCase):

    def day(self, schedule):
        specs = parse_competition_schedule(schedule)
        editions = event_plan.past_editions("danceconvention", root=self.root)
        cands = [event_plan.gather_candidates(self.lib, s, editions,
                                              similar=self.similar)
                 for s in specs]
        variants = {p: event_plan.plan_variant(cands, p)
                    for p in event_plan.PROFILE_ORDER}
        return cands, variants

    def with_new_titles(self):
        _vr, er = self.event_list("DanceConvention 2025/HGR_S_STD.m3u", "DC")
        self.event_list("12.03.2025 Krefeld/HGR_S_STD.m3u", "KR")
        for anchor in er:
            for i in range(5):
                new = self.entry(f"New {i} {anchor.dance}", anchor.dance)
                self.sounds_like[new.title] = (new, anchor, 0.9 - i / 100)
        return er

    def day_paths(self, comps):
        return {str(p.entry.path) for c in comps for p in self.picks(c)}

    def unused_new(self, cands, comps, dance, of=0):
        """A new title of `dance` that this variant plays nowhere today."""
        day = self.day_paths(comps)
        offered = {str(p.suggestion.entry.path) for c in comps
                   for p in self.picks(c) if p.suggestion}
        for p in cands[of].new[dance]:
            if str(p.entry.path) not in day | offered:
                return p
        self.fail(f"no unused new {dance} title")

    def refine(self, cands, variants, answer):
        model = FakeModel(answer)
        out = event_plan.refine_with_ai(variants, cands, ask=model).variants
        return out, model

    # ── a swap is applied ──────────────────────────────────────────────────

    def test_a_swap_replaces_the_slot_and_keeps_its_source(self):
        self.with_new_titles()
        cands, variants = self.day("HGR S STD 2-1")
        new = self.unused_new(cands, variants["variety"], "LW")
        before = variants["variety"][0].grid["Finale"][0][0]

        out, _ = self.refine(cands, variants, lambda i, user: (
            [swap("variety", "Finale", "LW", number_of(user, new.entry.title),
                  "brighter than the last one")], {"variety": "One swap."}))

        comp = out["variety"][0]
        slot = comp.grid["Finale"][0][0]
        self.assertIs(slot.entry, new.entry)
        self.assertEqual(slot.tier, "new")
        self.assertEqual(slot.source, new.source)
        self.assertEqual(slot.why, "brighter than the last one")
        self.assertEqual(comp.notes, "One swap.")
        # The drafts it was handed are left alone.
        self.assertIs(variants["variety"][0].grid["Finale"][0][0], before)

    def test_renewed_takes_a_swap_as_a_suggestion(self):
        er = self.with_new_titles()
        er[0].class_plays = {"S": 30}           # a favourite: it stays
        cands, variants = self.day("HGR S STD 2-1")
        new = self.unused_new(cands, variants["last_year_renewed"], "LW")

        out, _ = self.refine(cands, variants, lambda i, user: (
            [swap("last_year_renewed", "Finale", "LW",
                  number_of(user, new.entry.title), "fresher")], {}))

        slot = out["last_year_renewed"][0].grid["Finale"][0][0]
        self.assertIs(slot.entry, er[0])
        self.assertEqual(slot.tier, "event")
        self.assertIs(slot.suggestion.entry, new.entry)
        self.assertEqual(slot.suggestion.why, "fresher")

    def test_like_last_year_takes_a_swap_as_a_suggestion(self):
        """The reference stays as last year played it: the AI's swap is only
        offered next to the title."""
        er = self.with_new_titles()
        cands, variants = self.day("HGR S STD 2-1")
        new = self.unused_new(cands, variants["like_last_year"], "LW")

        out, _ = self.refine(cands, variants, lambda i, user: (
            [swap("like_last_year", "Finale", "LW",
                  number_of(user, new.entry.title), "fresher")], {}))

        slot = out["like_last_year"][0].grid["Finale"][0][0]
        self.assertIs(slot.entry, er[0])
        self.assertEqual(slot.tier, "event")
        self.assertIs(slot.suggestion.entry, new.entry)
        self.assertEqual(slot.suggestion.why, "fresher")

    def test_two_titles_can_trade_places(self):
        """The real HGR S answer moved the final-proven waltz from the
        preliminary into the final and the final's waltz back — two swaps
        that each duplicate a title until the other one is in."""
        self.with_new_titles()
        cands, variants = self.day("HGR S STD 2-1")
        grid = variants["variety"][0].grid
        prelim, final = grid["Vorrunde"][0][0].entry, grid["Finale"][0][0].entry

        out, _ = self.refine(cands, variants, lambda i, user: (
            [swap("variety", "Vorrunde", "LW", number_of(user, final.title)),
             swap("variety", "Finale", "LW", number_of(user, prelim.title))], {}))

        grid = out["variety"][0].grid
        self.assertIs(grid["Vorrunde"][0][0].entry, final)
        self.assertIs(grid["Finale"][0][0].entry, prelim)

    def test_half_a_trade_is_undone_whole(self):
        """Only one side of the trade is a valid swap: the other title would
        then play twice, so neither goes in."""
        self.with_new_titles()
        cands, variants = self.day("HGR S STD 2-1")
        grid = variants["variety"][0].grid
        before = [p.entry for p in self.picks(variants["variety"][0])]
        final = grid["Finale"][0][0].entry

        out, _ = self.refine(cands, variants, lambda i, user: (
            [swap("variety", "Vorrunde", "LW", number_of(user, final.title)),
             swap("variety", "Finale", "LW", 9999)], {}))

        self.assertEqual([p.entry for p in self.picks(out["variety"][0])], before)

    # ── a swap that breaks a rule is ignored ───────────────────────────────

    def assertIgnored(self, cands, variants, variant, rnd, dance, n, heat=1):
        before = [[p.entry if p else None for p in h]
                  for h in variants[variant][0].grid[rnd]]
        out, _ = self.refine(cands, variants, lambda i, user: (
            [swap(variant, rnd, dance, n(user), heat=heat)], {}))
        after = [[p.entry if p else None for p in h]
                 for h in out[variant][0].grid[rnd]]
        self.assertEqual(after, before)

    def test_a_number_it_was_not_shown_is_ignored(self):
        self.with_new_titles()
        cands, variants = self.day("HGR S STD 2-1")
        self.assertIgnored(cands, variants, "variety", "Finale", "LW",
                           lambda user: 9999)

    def test_a_title_of_another_dance_is_ignored(self):
        self.with_new_titles()
        cands, variants = self.day("HGR S STD 2-1")
        tango = self.unused_new(cands, variants["variety"], "TG")
        self.assertIgnored(cands, variants, "variety", "Finale", "LW",
                           lambda user: number_of(user, tango.entry.title))

    def test_a_title_already_played_that_day_is_ignored(self):
        self.with_new_titles()
        cands, variants = self.day("HGR S STD 2-1")
        prelim_lw = variants["variety"][0].grid["Vorrunde"][0][0].entry
        self.assertIgnored(cands, variants, "variety", "Finale", "LW",
                           lambda user: number_of(user, prelim_lw.title))

    def test_a_title_from_another_competitions_history_is_ignored(self):
        self.with_new_titles()
        sen_vr, sen_er = self.event_list("DanceConvention 2025/MAS_I_S_STD.m3u", "SEN")
        # A class list of its own, so variety leaves some of SEN's history out.
        self.event_list("12.03.2025 Krefeld/MAS_I_S_STD.m3u", "KRSEN")
        cands, variants = self.day("HGR S STD 2-1\nSEN I S STD 2-1")
        sen_day = self.day_paths(variants["variety"])
        spare = [e for e in sen_vr + sen_er
                 if e.dance == "LW" and str(e.path) not in sen_day]
        self.assertTrue(spare, "every SEN LW title is placed in variety")
        seen = []

        def answer(i, user):
            n = number_of(user, spare[0].title) if i == 0 else None
            seen.append(n)
            return ([swap("variety", "Finale", "LW", n)] if n else [], {})

        out, _ = self.refine(cands, variants, answer)
        self.assertIsNotNone(seen[0], "the SEN title is not in HGR's catalogue")
        self.assertNotIn(spare[0], [p.entry for p in self.picks(out["variety"][0])])

    # ── the model fails ────────────────────────────────────────────────────

    def test_when_the_model_fails_the_plan_stands(self):
        self.with_new_titles()
        cands, variants = self.day("HGR S STD 2-1")

        def broken(system, user):
            raise RuntimeError("Both backends failed.")

        out = event_plan.refine_with_ai(variants, cands, ask=broken).variants
        for profile in event_plan.PROFILE_ORDER:
            self.assertEqual(
                [p.entry for p in self.picks(out[profile][0])],
                [p.entry for p in self.picks(variants[profile][0])])

    def test_an_answer_without_json_leaves_the_plan(self):
        self.with_new_titles()
        cands, variants = self.day("HGR S STD 2-1")
        out = event_plan.refine_with_ai(
            variants, cands, ask=lambda s, u: ("Sorry, I cannot help.", "fake")).variants
        self.assertEqual([p.entry for p in self.picks(out["variety"][0])],
                         [p.entry for p in self.picks(variants["variety"][0])])

    # ── one question per competition ───────────────────────────────────────

    def test_one_question_per_competition_with_every_draft(self):
        self.with_new_titles()
        cands, variants = self.day("HGR S STD 2-1\nHGR II S STD 2-1")
        _out, model = self.refine(cands, variants, lambda i, user: ([], {}))
        self.assertEqual(len(model.calls), 2)
        for i, (_system, user) in enumerate(model.calls):
            drafts = dict(re.findall(r'^Draft "(\w+)"(.*?)(?=^Draft "|\Z)',
                                     user, re.MULTILINE | re.DOTALL))
            self.assertEqual(set(drafts), set(event_plan.PROFILE_ORDER))
            for profile, text in drafts.items():
                for p in self.picks(variants[profile][i]):
                    self.assertIn(f"#{number_of(user, p.entry.title)} ", text)
        # Only HGR S has a last year to offer replacements for.
        self.assertIn("→ suggested #", model.calls[0][1])

    def test_a_swap_in_one_competition_blocks_the_title_in_the_next(self):
        self.with_new_titles()
        cands, variants = self.day("HGR S STD 2-1\nHGR II S STD 2-1")
        new = self.unused_new(cands, variants["variety"], "LW")
        shown = []

        def answer(i, user):
            n = number_of(user, new.entry.title)
            shown.append(n)
            return [swap("variety", "Finale", "LW", n)] if n else [], {}

        out, _ = self.refine(cands, variants, answer)
        self.assertTrue(all(shown), "the title is not in both catalogues")
        first, second = out["variety"]
        self.assertIs(first.grid["Finale"][0][0].entry, new.entry)
        self.assertIsNot(second.grid["Finale"][0][0].entry, new.entry)

    # ── asked all at once, the higher-ranked competition decides first ─────

    def test_the_competitions_rank_by_class_and_age(self):
        """Marcel: S before A before B, HGR S most important, then Jug A/S,
        then SEN I S and on with age — and younger groups first, so HGR A
        comes third. One class step weighs as much as one senior age step."""
        day = ["J & J (LW; TG; CC; RB) VR ZR ER 24 - 12 - 6", "SEN V S STD 2-1",
               "SENI I S STD 2-1", "HGR A STD 2-1", "Jug A STD 2-1",
               "HGR S STD 2-1", "SEN II S STD 2-1", "Jug B STD 2-1",
               "HGR B STD 2-1"]
        specs = parse_competition_schedule("\n".join(day))
        ranked = sorted(specs, key=event_plan.competition_rank)
        self.assertEqual([s.label for s in ranked],
                         ["HGR S STD", "Jug A STD", "HGR A STD", "Jug B STD",
                          "SENI I S STD", "HGR B STD", "SEN II S STD",
                          "SEN V S STD", "J & J"])

    def test_the_higher_ranked_competition_gets_a_contested_title(self):
        """Both answers want the same free waltz. HGR S runs second that day
        but ranks first, so it gets it; HGR II S keeps its draft."""
        self.with_new_titles()
        cands, variants = self.day("HGR II S STD 2-1\nHGR S STD 2-1")
        new, answer = self.lw_swap(cands, variants, of=1)
        result = event_plan.refine_with_ai(
            variants, cands, ask=lambda s, u: (answer(u), "fake"))
        hgr2, hgr = result.variants["variety"]
        self.assertIs(hgr.grid["Finale"][0][0].entry, new.entry)
        self.assertIsNot(hgr2.grid["Finale"][0][0].entry, new.entry)

    def test_a_lost_swap_is_kept_for_the_last_word(self):
        """Marcel wants to see what the AI wanted and did not get, to choose
        it anyway."""
        self.with_new_titles()
        cands, variants = self.day("HGR II S STD 2-1\nHGR S STD 2-1")
        new = self.unused_new(cands, variants["variety"], "LW", of=1)
        result = event_plan.refine_with_ai(variants, cands, ask=lambda s, u: (
            json.dumps({"swaps": [swap("variety", "Finale", "LW",
                                       number_of(u, new.entry.title),
                                       "the brightest waltz")]}), "fake"))
        hgr2, hgr = result.variants["variety"]
        self.assertEqual(hgr.refused, [])
        [lost] = hgr2.refused
        self.assertEqual((lost.round, lost.heat, lost.dance), ("Finale", 0, 0))
        self.assertIs(lost.pick.entry, new.entry)
        self.assertEqual(lost.pick.why, "the brightest waltz")
        self.assertEqual(lost.reason, "already plays that day")
        # The drafts it was handed keep no such list.
        self.assertEqual(variants["variety"][0].refused, [])

    def test_a_second_round_asks_where_a_swap_was_lost(self):
        """The competition that lost a title is offered a second round. Its
        question says what did not go in and why, so the model can fill the
        slot another way; asking the same again adds nothing twice."""
        self.with_new_titles()
        cands, variants = self.day("HGR II S STD 2-1\nHGR S STD 2-1")
        new, answer = self.lw_swap(cands, variants, of=1)
        asked = []

        def ask(system, user):
            asked.append(user)
            return answer(user), "fake"

        first = event_plan.refine_with_ai(variants, cands, ask=ask)
        self.assertEqual(first.second_round, [0])
        self.assertNotIn("did not go in", asked[0] + asked[1])

        asked.clear()
        second = event_plan.refine_with_ai(first.variants, cands, ask=ask,
                                           only=first.second_round)
        [user] = asked
        self.assertIn('competition "HGR II S STD"', user)
        self.assertIn("did not go in", user)
        self.assertIn(f"variety Finale heat 1 LW: #{number_of(user, new.entry.title)} "
                      f"{new.entry.title} — already plays that day", user)
        self.assertEqual(len(second.variants["variety"][0].refused), 1)
        self.assertEqual(second.second_round, [])

    def test_a_swap_that_names_no_real_title_is_not_kept(self):
        self.with_new_titles()
        cands, variants = self.day("HGR S STD 2-1")
        result = event_plan.refine_with_ai(variants, cands, ask=lambda s, u: (
            json.dumps({"swaps": [swap("variety", "Finale", "LW", 9999)]}), "fake"))
        self.assertEqual(result.variants["variety"][0].refused, [])

    # ── asked all at once, a rate limit leaves the rest for later ──────────

    def lw_swap(self, cands, variants, of=0):
        """An answer that puts an unused new waltz into the variety final."""
        new = self.unused_new(cands, variants["variety"], "LW", of)
        return new, lambda user: json.dumps({"swaps": [swap(
            "variety", "Finale", "LW", number_of(user, new.entry.title))]})

    def test_the_competitions_are_asked_at_the_same_time(self):
        """One question took 506 s on the real plan; five in a row are 40 min.
        Each fake answer waits until the other question has been asked too —
        asked one after the other, the first would wait in vain."""
        self.with_new_titles()
        cands, variants = self.day("HGR S STD 2-1\nHGR II S STD 2-1")
        both = threading.Barrier(2, timeout=5)

        def ask(system, user):
            both.wait()
            return json.dumps({"swaps": []}), "fake"

        result = event_plan.refine_with_ai(variants, cands, ask=ask)
        self.assertEqual(result.failed, [])
        self.assertEqual(result.pending, [])

    def test_a_rate_limit_leaves_the_competition_for_later(self):
        self.with_new_titles()
        cands, variants = self.day("HGR S STD 2-1\nHGR II S STD 2-1")
        new, answer = self.lw_swap(cands, variants)

        def ask(system, user):
            if 'competition "HGR II S STD"' in user:
                raise RuntimeError("Both backends failed.\n\nclaude -p — claude -p "
                                   "exited 1: Claude AI usage limit reached|1759000000")
            return answer(user), "fake"

        result = event_plan.refine_with_ai(variants, cands, ask=ask)
        self.assertEqual(result.pending, [1])
        self.assertEqual(result.failed, [])
        self.assertEqual(result.reset_at, 1759000000)
        self.assertIn("usage limit", result.limit)
        self.assertIs(result.variants["variety"][0].grid["Finale"][0][0].entry,
                      new.entry)

    def test_continuing_asks_only_what_is_left(self):
        self.with_new_titles()
        cands, variants = self.day("HGR S STD 2-1\nHGR II S STD 2-1")
        new, answer = self.lw_swap(cands, variants)
        asked = []

        def ask(system, user):
            asked.append(user)
            return answer(user), "fake"

        first = event_plan.refine_with_ai(variants, cands, ask=ask, only=[0])
        later = event_plan.refine_with_ai(first.variants, cands, ask=ask, only=[1])
        self.assertEqual(len(asked), 2)
        self.assertIn('competition "HGR II S STD"', asked[1])
        # The first answer stays, and still keeps its title from the second.
        hgr, hgr2 = later.variants["variety"]
        self.assertIs(hgr.grid["Finale"][0][0].entry, new.entry)
        self.assertIsNot(hgr2.grid["Finale"][0][0].entry, new.entry)

    def test_the_limit_messages_are_recognised(self):
        from planner import llm
        for text in ("claude -p exited 1: You've hit your limit · resets 3pm",
                     "claude -p exited 1: 5-hour limit reached ∙ resets 11pm",
                     "HTTP 429: Too Many Requests",
                     'openrouter — {"error": {"type": "rate_limit_error"}}'):
            self.assertTrue(llm.is_rate_limited(RuntimeError(text)), text)
        self.assertFalse(llm.is_rate_limited(RuntimeError("Invalid model name")))
        self.assertIsNone(llm.rate_limit_reset("You've hit your limit · resets 3pm"))

    # ── what the window says about a run ───────────────────────────────────

    def test_the_summary_names_every_competition_and_variant(self):
        self.with_new_titles()
        cands, variants = self.day("HGR S STD 2-1\nHGR II S STD 2-1")
        result = event_plan.RefineResult(variants, failed=[1])
        result.variants["variety"][0].notes = "Brighter final."
        text = event_plan.describe_result(result, cands)
        self.assertIn("HGR S STD", text)
        self.assertIn("HGR II S STD", text)
        self.assertIn("Variety: 15/15", text)
        self.assertIn("Brighter final.", text)
        self.assertIn("the plan stands", text)

    def test_the_summary_counts_the_swaps_kept_for_the_last_word(self):
        self.with_new_titles()
        cands, variants = self.day("HGR S STD 2-1")
        comp = variants["variety"][0]
        pick = comp.grid["Finale"][0][0]
        comp.refused.append(event_plan.RefusedSwap("Finale", 0, 0, pick, "taken"))
        result = event_plan.RefineResult(variants, pending=[0])
        text = event_plan.describe_result(result, cands)
        self.assertIn("1 swap not applied", text)
        self.assertIn("limit", text)

    def test_waiting_for_the_limit(self):
        self.assertEqual(event_plan.retry_delay(1000.0, now=400.0), 660)
        self.assertEqual(event_plan.retry_delay(1000.0, now=2000.0), 60,
                         "a reset already past: ask again soon, not at once")
        self.assertEqual(event_plan.retry_delay(None, now=0.0),
                         event_plan.RETRY_UNKNOWN_S)

    def test_any_other_failure_is_no_reason_to_wait(self):
        self.with_new_titles()
        cands, variants = self.day("HGR S STD 2-1")

        def ask(system, user):
            raise RuntimeError("claude -p exited 1: Invalid model name")

        result = event_plan.refine_with_ai(variants, cands, ask=ask)
        self.assertEqual(result.failed, [0])
        self.assertEqual(result.pending, [])
        self.assertIsNone(result.reset_at)


if __name__ == "__main__":
    unittest.main(verbosity=2)
