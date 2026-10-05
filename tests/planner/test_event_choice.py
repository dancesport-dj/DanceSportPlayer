#!/usr/bin/env python3
"""The last word on an event plan: what else fits a slot, and putting it in.

Run:  py -m unittest tests.planner.test_event_choice -v

The comparison window shows the variants side by side, and a click on a slot
offers what else could go there: the replacement "like last year" suggests,
the titles the AI wanted and did not get, and the free titles of each tier.
Whatever is picked goes in — a title that already plays that day only after a
warning, since the day's rules are the planner's, not a law.
"""

import unittest

from planner import event_plan
from planner.competition import parse_competition_schedule
from tests.planner.test_event_variants import EventFixture


class EventChoiceTest(EventFixture, unittest.TestCase):

    def day(self, schedule="HGR S STD 2-1", profile="variety", twins=False):
        _vr, er = self.event_list("DanceConvention 2025/HGR_S_STD.m3u", "DC")
        self.event_list("12.03.2025 Krefeld/HGR_S_STD.m3u", "KR")
        if twins:           # a new title that sounds like each of the final's
            for anchor in er:
                new = self.entry(f"New {anchor.dance}", anchor.dance)
                self.sounds_like[new.title] = (new, anchor, 0.9)
        for d in ("LW", "TG"):
            for n in range(3):
                self.entry(f"Library {d} {n}", d, s_plays=5, months_ago=60)
        editions = event_plan.past_editions("danceconvention", root=self.root)
        self.cands = [event_plan.gather_candidates(self.lib, s, editions,
                                                   similar=self.similar)
                      for s in parse_competition_schedule(schedule)]
        return event_plan.plan_variant(self.cands, profile)

    # ── what else fits ────────────────────────────────────────────────────

    def test_the_alternatives_are_free_titles_of_the_slots_dance(self):
        comps = self.day()
        key = (0, 1, 0, 0)                  # the final's Slow Waltz
        alts = event_plan.slot_alternatives(self.cands[0], comps, key)
        playing = {str(p.entry.path) for p in self.picks(comps[0])}
        titles = [p for tier in alts.values() for p in tier]
        self.assertTrue(titles)
        for p in titles:
            self.assertEqual(p.entry.dance, "LW")
            self.assertNotIn(str(p.entry.path), playing)
        self.assertEqual(list(alts), [t for t in ("event", "class", "new", "rare", "library")
                                      if t in alts])

    def test_a_title_is_offered_once(self):
        comps = self.day()
        alts = event_plan.slot_alternatives(self.cands[0], comps, (0, 1, 0, 0))
        paths = [str(p.entry.path) for tier in alts.values() for p in tier]
        self.assertEqual(len(paths), len(set(paths)))

    def test_the_alternatives_are_capped_per_tier(self):
        comps = self.day()
        alts = event_plan.slot_alternatives(self.cands[0], comps, (0, 1, 0, 0),
                                            limit=1)
        self.assertTrue(all(len(v) == 1 for v in alts.values()))

    # ── putting one in ────────────────────────────────────────────────────

    def test_a_chosen_title_goes_into_the_slot(self):
        comps = self.day()
        key = (0, 1, 0, 0)
        alt = event_plan.slot_alternatives(self.cands[0], comps, key)["library"][0]
        self.assertEqual(event_plan.slot_conflict(comps, key, alt), "")
        event_plan.put_slot(comps, key, alt)
        self.assertIs(event_plan.slot_pick(comps, key).entry, alt.entry)

    def test_a_title_that_already_plays_is_named(self):
        comps = self.day()
        prelim = event_plan.slot_pick(comps, (0, 0, 0, 0))    # VR heat 1, LW
        self.assertEqual(event_plan.slot_conflict(comps, (0, 1, 0, 0), prelim),
                         "already plays that day")
        before = event_plan.slot_pick(comps, (0, 1, 0, 0))
        self.assertIs(before, event_plan.slot_pick(comps, (0, 1, 0, 0)))

    def test_accepting_a_suggestion_puts_it_in(self):
        comps = self.day(profile="last_year_renewed")
        key = next((0, r, h, j) for r, h, j, p in event_plan._grid_picks(comps[0])
                   if p.suggestion is not None)
        offered = event_plan.slot_pick(comps, key).suggestion
        self.assertEqual(event_plan.slot_conflict(comps, key, offered), "")
        event_plan.put_slot(comps, key, offered)
        now = event_plan.slot_pick(comps, key)
        self.assertIs(now.entry, offered.entry)
        self.assertIsNone(now.suggestion)

    def test_a_swapped_slot_goes_back_to_last_year(self):
        comps = self.day(profile="last_year_renewed", twins=True)
        key = next((0, r, h, j) for r, h, j, p in event_plan._grid_picks(comps[0])
                   if p.replaces is not None)
        last_year = event_plan.slot_pick(comps, key).replaces
        self.assertEqual(event_plan.slot_conflict(comps, key, last_year), "")
        event_plan.put_slot(comps, key, last_year)
        now = event_plan.slot_pick(comps, key)
        self.assertIs(now.entry, last_year.entry)
        self.assertEqual(now.tier, "event")
        self.assertIsNone(now.replaces)

    def test_a_stand_in_put_elsewhere_replaces_nothing_there(self):
        renewed = self.day(profile="last_year_renewed", twins=True)
        stand_in = next(p for *_slot, p in event_plan._grid_picks(renewed[0])
                        if p.replaces is not None)
        variety = event_plan.plan_variant(self.cands, "variety")
        event_plan.put_slot(variety, (0, 1, 0, 0), stand_in)
        self.assertIsNone(event_plan.slot_pick(variety, (0, 1, 0, 0)).replaces)

    def test_a_refused_swap_taken_anyway_leaves_the_list(self):
        comps = self.day()
        key = (0, 1, 0, 0)
        alt = event_plan.slot_alternatives(self.cands[0], comps, key)["library"][0]
        lost = event_plan.RefusedSwap(comps[0].rounds[1].name, 0, 0, alt,
                                      "already plays that day")
        comps[0].refused.append(lost)
        event_plan.put_slot(comps, key, alt)
        self.assertEqual(comps[0].refused, [])

    def test_the_refused_swaps_of_a_slot(self):
        comps = self.day()
        alt = event_plan.slot_alternatives(self.cands[0], comps, (0, 1, 0, 0))["library"][0]
        lost = event_plan.RefusedSwap(comps[0].rounds[1].name, 0, 0, alt, "x")
        comps[0].refused.append(lost)
        self.assertEqual(event_plan.slot_refused(comps[0], (0, 1, 0, 0)), [lost])
        self.assertEqual(event_plan.slot_refused(comps[0], (0, 1, 0, 1)), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
