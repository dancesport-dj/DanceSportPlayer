#!/usr/bin/env python3
"""A day of competitions, planned in three variants from where its titles come.

Run:  py -m unittest tests.planner.test_event_variants -v

Every slot of every competition is filled from one of three sources:

  event  — what this event played for this competition in earlier years,
           the same round where it can
  class  — what other events played for the same class
  new    — titles that sound like those (timbre) but were never played at
           this class: the suggestions

The three profiles only differ in how much of each they take — "like last
year" leans on the event, "variety" brings in the most new titles. Across the
day no title is played twice (Paso Doble excepted), and a title with history
at one competition is kept for that one.
"""

import shutil
import tempfile
import time
import unittest
from pathlib import Path

from dancesport_planner import MusicEntry, MusicLibrary
from planner import event_plan
from planner import library as planner_library
from planner.competition import parse_competition_schedule

_STD = ("LW", "TG", "WW", "SF", "QS")
_BPM = {"LW": 29, "TG": 32, "WW": 59, "SF": 29, "QS": 50}


class EventFixture:
    """A library and a playlist folder of its own; the AI tests share it."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dp_variants_"))
        self.addCleanup(shutil.rmtree, self.root, True)
        orig = planner_library.PLAYLIST_DIR
        planner_library.PLAYLIST_DIR = self.root
        self.addCleanup(setattr, planner_library, "PLAYLIST_DIR", orig)
        self.lib = MusicLibrary()
        self.sounds_like = {}      # new title → (entry, anchor, similarity)

    def entry(self, title, dance, *, s_plays=0, months_ago=0):
        e = MusicEntry(
            path=Path(rf"C:\music\standardcd\{title} ({dance} {_BPM[dance]}).mp3"),
            title=title, dance=dance, bpm=_BPM[dance],
            added=time.time() - months_ago * 30.44 * 86400)
        if s_plays:
            e.class_plays = {"S": s_plays}
            e.popularity = s_plays
        self.lib.entries.append(e)
        return e

    def write(self, rel, entries):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("#EXTM3U\n" + "\n".join(str(e.path) for e in entries)
                     + "\n", encoding="utf-8")

    def similar(self, anchor, n=10, same_dance=True, min_display=0.0, method=None):
        return [(sim, e) for e, a, sim in self.sounds_like.values()
                if a is anchor and sim >= min_display][:n]

    def event_list(self, rel, tag):
        """A 2-1 list: two preliminary heats per dance, then the final."""
        vr = [self.entry(f"{tag} VR{h} {d}", d, s_plays=3)
              for d in _STD for h in (1, 2)]
        er = [self.entry(f"{tag} ER {d}", d, s_plays=3) for d in _STD]
        self.write(rel, vr + er)
        return vr, er

    def plan(self, schedule, profile, editions=None, *, use_class=True,
             new_share=None, rare_share=None):
        specs = parse_competition_schedule(schedule)
        if editions is None:
            editions = event_plan.past_editions("danceconvention", root=self.root)
        cands = [event_plan.gather_candidates(self.lib, s, editions,
                                              similar=self.similar,
                                              use_class=use_class)
                 for s in specs]
        return event_plan.plan_variant(cands, profile, new_share=new_share,
                                       rare_share=rare_share)

    @staticmethod
    def picks(comp):
        return [p for heats in comp.grid.values() for heat in heats
                for p in heat if p is not None]


class EventVariantTest(EventFixture, unittest.TestCase):

    # ── the event's own history ────────────────────────────────────────────

    def test_like_last_year_keeps_last_years_final(self):
        _vr, er = self.event_list("DanceConvention 2025/HGR_S_STD.m3u", "DC")
        comp, = self.plan("HGR S STD 2-1", "like_last_year")
        final = comp.grid[comp.rounds[-1].name][0]
        self.assertEqual([p.entry for p in final], er)
        self.assertEqual({p.tier for p in final}, {"event"})
        self.assertEqual(final[0].source, "DanceConvention 2025 / HGR_S_STD")

    def test_every_slot_is_filled(self):
        self.event_list("DanceConvention 2025/HGR_S_STD.m3u", "DC")
        comp, = self.plan("HGR S STD 2-1", "variety")
        self.assertEqual(len(self.picks(comp)), 3 * 5)

    def test_without_history_the_class_lists_carry_it(self):
        """Jug A had no list at the DanceConvention 2025."""
        self.event_list("DanceConvention 2025/HGR_S_STD.m3u", "DC")
        self.event_list("12.03.2025 Krefeld/JUG_A_STD.m3u", "KR")
        comp, = self.plan("Jug A STD 2-1", "like_last_year")
        tiers = {p.tier for p in self.picks(comp)}
        self.assertNotIn("event", tiers)
        self.assertIn("class", tiers)
        self.assertEqual(len(self.picks(comp)), 15)

    # ── "like last year": last year is the base ────────────────────────────

    def test_like_last_year_keeps_all_of_last_year(self):
        """Other HGR S lists exist, but last year covers every slot."""
        vr, er = self.event_list("DanceConvention 2025/HGR_S_STD.m3u", "DC")
        self.event_list("12.03.2025 Krefeld/HGR_S_STD.m3u", "KR")
        comp, = self.plan("HGR S STD 2-1", "like_last_year")
        self.assertEqual({p.tier for p in self.picks(comp)}, {"event"})
        self.assertEqual({p.entry.title for p in self.picks(comp)},
                         {e.title for e in vr + er})

    def test_like_last_year_fills_the_extra_slots(self):
        """This year dances 3-2-1 where last year danced 2-1: last year's
        15 titles stay, the other 15 slots come from the class lists."""
        self.event_list("DanceConvention 2025/HGR_S_STD.m3u", "DC")
        self.event_list("12.03.2025 Krefeld/HGR_S_STD.m3u", "KR")
        self.event_list("13.03.2025 Krefeld/HGR_S_STD.m3u", "KR2")
        comp, = self.plan("HGR S STD 3-2-1", "like_last_year")
        tiers = [p.tier for p in self.picks(comp)]
        self.assertEqual(len(tiers), 30)
        self.assertEqual(tiers.count("event"), 15)
        self.assertEqual(tiers.count("class"), 15)

    def test_like_last_year_is_the_reference(self):
        """Marcel: like last year should be a reference for compare — it
        keeps last year as it was. It may offer titles to swap, but none may
        be put in beforehand."""
        er = self.with_new_titles()
        comp, = self.plan("HGR S STD 2-1", "like_last_year")
        self.assertEqual({p.tier for p in self.picks(comp)}, {"event"})
        self.assertEqual([p for p in self.picks(comp) if p.replaces], [])
        final = comp.grid[comp.rounds[-1].name][0]
        self.assertEqual([p.entry for p in final], er[:5])
        self.assertEqual(final[0].suggestion.tier, "new")
        self.assertIs(final[0].suggestion.anchor, er[0])

    # ── "last year, renewed": sound-alikes in some of last year's slots ────

    def test_renewed_swaps_a_share_of_last_year_for_sound_alikes(self):
        """Marcel: the really new one should be similar to last year, where
        some titles are replaced with similar ones. A swapped slot names the
        title of last year it stands in for, and sounds like that very one."""
        er = self.with_new_titles()
        comp, = self.plan("HGR S STD 2-1", "last_year_renewed")
        swapped = [p for p in self.picks(comp) if p.replaces is not None]
        self.assertEqual(len(swapped), int(event_plan.RENEW_SHARE * 15))
        final = comp.grid[comp.rounds[-1].name][0]
        for j, pick in enumerate(final):
            if pick.replaces is None:
                continue
            self.assertEqual(pick.tier, "new")
            self.assertIs(pick.replaces.entry, er[j])
            self.assertIs(pick.anchor, er[j])
            self.assertIn(er[j].title, pick.source)
        self.assertEqual({p.tier for p in self.picks(comp) if p.replaces is None},
                         {"event"})

    def test_renewed_keeps_the_favourites(self):
        """Marcel: keep Grade and Gratitude and replace the second waltz —
        the titles the class has played least go first."""
        er = self.with_new_titles()
        er[2].class_plays = {"S": 30}
        comp, = self.plan("HGR S STD 2-1", "last_year_renewed")
        final = comp.grid[comp.rounds[-1].name][0]
        self.assertIs(final[2].entry, er[2])
        self.assertEqual([p.replaces is not None for p in final],
                         [True, True, False, True, True])

    def test_renewed_swaps_only_for_a_real_sound_alike(self):
        """A new title below NEW_MIN_SIM stands in for nobody: last year stays."""
        self.with_new_titles()
        for title, (e, anchor, _sim) in list(self.sounds_like.items()):
            self.sounds_like[title] = (e, anchor, event_plan.NEW_MIN_SIM - 0.1)
        comp, = self.plan("HGR S STD 2-1", "last_year_renewed")
        self.assertEqual({p.tier for p in self.picks(comp)}, {"event"})

    def test_renewed_offers_a_replacement_for_the_titles_it_kept(self):
        """Offered, not applied: the new title that sounds like that very one."""
        er = self.with_new_titles()
        er[2].class_plays = {"S": 30}
        comp, = self.plan("HGR S STD 2-1", "last_year_renewed")
        final = comp.grid[comp.rounds[-1].name][0]
        self.assertEqual(final[2].suggestion.tier, "new")
        self.assertIs(final[2].suggestion.anchor, er[2])
        self.assertIsNone(final[0].suggestion)       # swapped already

    def test_a_suggestion_is_nowhere_else_in_the_day(self):
        self.with_new_titles()
        comps = self.plan("HGR S STD 2-1\nHGR II S STD 2-1", "last_year_renewed")
        grid = [str(p.entry.path) for c in comps for p in self.picks(c)]
        offered = [str(p.suggestion.entry.path) for c in comps
                   for p in self.picks(c) if p.suggestion]
        self.assertTrue(offered)
        self.assertEqual(len(offered), len(set(offered)))
        self.assertFalse(set(offered) & set(grid))
        self.assertEqual(len(grid), len(set(grid)))

    # ── how much of each ───────────────────────────────────────────────────

    def with_new_titles(self):
        _vr, er = self.event_list("DanceConvention 2025/HGR_S_STD.m3u", "DC")
        self.event_list("12.03.2025 Krefeld/HGR_S_STD.m3u", "KR")
        for anchor in er:
            for i in range(3):
                new = self.entry(f"New {i} {anchor.dance}", anchor.dance)
                self.sounds_like[new.title] = (new, anchor, 0.9 - i / 100)
        return er

    def test_like_last_year_suggests_nothing_new(self):
        self.with_new_titles()
        comp, = self.plan("HGR S STD 2-1", "like_last_year")
        self.assertNotIn("new", {p.tier for p in self.picks(comp)})

    def test_variety_brings_in_new_titles(self):
        self.with_new_titles()
        comp, = self.plan("HGR S STD 2-1", "variety")
        tiers = [p.tier for p in self.picks(comp)]
        self.assertGreaterEqual(tiers.count("new"), 4)       # ≈30 % of 15
        self.assertLess(tiers.count("event"), tiers.count("class"))

    def test_the_profiles_lean_differently_on_the_event(self):
        self.with_new_titles()
        counts = {}
        for profile in event_plan.PROFILE_ORDER:
            comp, = self.plan("HGR S STD 2-1", profile)
            counts[profile] = [p.tier for p in self.picks(comp)].count("event")
        self.assertGreater(counts["like_last_year"], counts["proven_fresh"])
        self.assertGreater(counts["proven_fresh"], counts["variety"])

    def test_the_new_share_can_be_set(self):
        """The dialog's slider: the other tiers keep their proportion."""
        quota = event_plan.profile_quota("proven_fresh", 0.4)
        for tier, share in {"event": 0.375, "class": 0.225, "new": 0.4}.items():
            self.assertAlmostEqual(quota[tier], share)
        self.assertEqual(event_plan.profile_quota("variety"),
                         event_plan.PROFILES["variety"])
        self.assertEqual(event_plan.profile_quota("like_last_year", 0.5),
                         event_plan.PROFILES["like_last_year"])

    def test_the_rare_share_can_be_set_too(self):
        quota = event_plan.profile_quota("proven_fresh", 0.2, 0.2)
        for tier, share in {"event": 0.375, "class": 0.225,
                            "new": 0.2, "rare": 0.2}.items():
            self.assertAlmostEqual(quota[tier], share)
        self.assertEqual(event_plan.profile_quota("like_last_year", 0.2, 0.3),
                         event_plan.PROFILES["like_last_year"])

    # ── rarely played ──────────────────────────────────────────────────────

    def with_rare_titles(self):
        er = self.with_new_titles()
        rare = {}
        for plays in range(4):
            e = self.entry(f"Rare {plays} LW", "LW", s_plays=plays, months_ago=60)
            self.sounds_like[e.title] = (e, er[0], 0.5 + plays / 10)
            rare[plays] = e
        return rare

    def cands(self, schedule="HGR S STD 2-1"):
        spec, = parse_competition_schedule(schedule)
        return event_plan.gather_candidates(
            self.lib, spec, event_plan.past_editions("danceconvention", root=self.root),
            similar=self.similar)

    def test_rarely_played_is_at_most_twice_at_the_class(self):
        """Titles the class has hardly heard: never, once or twice — the most
        alike first."""
        rare = self.with_rare_titles()
        c = self.cands()
        got = [p.entry for p in c.rare["LW"] if p.entry in rare.values()]
        self.assertEqual(got, [rare[2], rare[1], rare[0]])
        self.assertEqual({p.tier for p in c.rare["LW"]}, {"rare"})

    def test_rarely_played_takes_fresh_titles_too(self):
        """Marcel: rare holds the new titles as well — and a fresh title
        played once or twice at the class fell between new and rare."""
        self.with_rare_titles()
        once = self.entry("Fresh once LW", "LW", s_plays=1)
        c = self.cands()
        new = {p.entry.title for p in c.new["LW"]}
        rare = {p.entry.title for p in c.rare["LW"]}
        self.assertTrue(new)
        self.assertLessEqual(new, rare)
        self.assertIn(once.title, rare)
        self.assertNotIn(once.title, new)

    def test_a_rare_title_says_how_often_it_was_played(self):
        rare = self.with_rare_titles()
        sources = {p.entry.title: p.source for p in self.cands().rare["LW"]}
        self.assertIn("never played at the class", sources[rare[0].title])
        self.assertIn("played 2× at the class", sources[rare[2].title])
        self.assertIn("70%", sources[rare[2].title])

    def test_a_title_of_the_class_lists_is_not_rare(self):
        """Played at the class and on the class tier already: it is offered
        there, not twice."""
        self.with_rare_titles()
        c = self.cands()
        klass = {str(p.entry.path) for rnd in c.klass for ps in rnd.values() for p in ps}
        self.assertTrue(klass)
        self.assertFalse(klass & {str(p.entry.path) for p in c.rare["LW"]})

    def test_a_swap_keeps_the_day_but_no_paso_twice_in_a_round(self):
        """Two slots of a variant swap their titles, each with the replacement
        offered for it. The day keeps its titles, so only Paso Doble — which
        may repeat, but not in a round — can break it."""
        self.event_list("DanceConvention 2025/HGR_S_STD.m3u", "DC")
        comps = self.plan("HGR S STD 2-1", "like_last_year")
        vr1, vr2, final = (0, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0)
        a, b = event_plan.slot_pick(comps, vr1), event_plan.slot_pick(comps, final)
        self.assertEqual(event_plan.swap_conflict(comps, vr1, final), "")
        event_plan.swap_slots(comps, vr1, final)
        self.assertIs(event_plan.slot_pick(comps, vr1), b)
        self.assertIs(event_plan.slot_pick(comps, final), a)
        paso = event_plan.Pick(MusicEntry(
            path=Path(r"C:\music\lateincd\Paso (PD 61).mp3"), title="Paso",
            dance="PD", bpm=61), "library", "")
        event_plan.put_slot(comps, vr2, paso)
        event_plan.put_slot(comps, final, paso)
        self.assertEqual(event_plan.swap_conflict(comps, vr1, final),
                         "already plays in that round")
        self.assertIs(event_plan.slot_pick(comps, vr1), b)      # nothing moved

    def test_a_remix_points_to_its_song(self):
        """Marcel: a remix keeps its own plays — but the list says whose
        version it is and how often that song was played at the class."""
        self.with_rare_titles()
        self.entry("Willow", "WW", s_plays=7, months_ago=60)
        remix = self.entry("Willow (DJ Maksy Viennese Waltz Remix)", "WW",
                           months_ago=60)
        sources = {p.entry.title: p.source for p in self.cands().rare["WW"]}
        self.assertIn("never played at the class", sources[remix.title])
        self.assertIn("a version of Willow (WW), played 7× at the class",
                      sources[remix.title])

    def test_the_rare_share_brings_rare_titles(self):
        self.with_rare_titles()
        comp, = self.plan("HGR S STD 2-1", "variety", rare_share=0.3)
        self.assertIn("rare", {p.tier for p in self.picks(comp)})
        comp, = self.plan("HGR S STD 2-1", "like_last_year", rare_share=0.5)
        self.assertEqual({p.tier for p in self.picks(comp)}, {"event"})

    def test_rare_titles_are_offered_for_a_slot(self):
        self.with_rare_titles()
        spec, = parse_competition_schedule("HGR S STD 2-1")
        c = self.cands()
        comps = event_plan.plan_variant([c], "variety")
        alts = event_plan.slot_alternatives(c, comps, (0, 1, 0, 0))
        self.assertIn("rare", alts)

    def test_no_new_share_no_new_titles(self):
        self.with_new_titles()
        comp, = self.plan("HGR S STD 2-1", "variety", new_share=0.0)
        self.assertNotIn("new", {p.tier for p in self.picks(comp)})

    def test_a_larger_new_share_brings_more_new_titles(self):
        self.with_new_titles()
        counts = []
        for share in (0.1, 0.5):
            comp, = self.plan("HGR S STD 2-1", "proven_fresh", new_share=share)
            counts.append([p.tier for p in self.picks(comp)].count("new"))
        self.assertLess(counts[0], counts[1])

    def test_like_last_year_ignores_the_new_share(self):
        self.with_new_titles()
        comp, = self.plan("HGR S STD 2-1", "like_last_year", new_share=0.5)
        self.assertEqual({p.tier for p in self.picks(comp)}, {"event"})

    def test_without_the_class_lists(self):
        """Only the event's own history, new titles that sound like it, and
        the library for what is left."""
        self.with_new_titles()
        comp, = self.plan("HGR S STD 3-2-1", "variety", use_class=False)
        tiers = {p.tier for p in self.picks(comp)}
        self.assertNotIn("class", tiers)
        self.assertEqual(len(self.picks(comp)), 30)

    def test_without_event_and_class_the_library_and_the_fresh(self):
        """Fresh titles are new with nothing to compare them to, too."""
        self.with_new_titles()
        comp, = self.plan("HGR S STD 2-1", "variety", editions=[],
                          use_class=False)
        tiers = {p.tier for p in self.picks(comp)}
        self.assertIn("new", tiers)
        self.assertLessEqual(tiers, {"library", "new"})

    def test_a_new_title_says_what_it_sounds_like(self):
        self.with_new_titles()
        comp, = self.plan("HGR S STD 2-1", "variety")
        new = [p for p in self.picks(comp) if p.tier == "new"][0]
        self.assertIn(self.sounds_like[new.entry.title][1].title, new.source)
        self.assertIn("%", new.source)

    def test_a_new_title_says_how_much_it_sounds_alike_three_ways(self):
        """Marcel: timbre Gaussian/KL, librosa timbre + rhythm and the chroma
        cover match — the source names where the title sits in each."""
        self.with_new_titles()
        fixture = self

        class Three:
            def __call__(self, *args, **kwargs):
                return fixture.__class__.similar(fixture, *args, **kwargs)

            def views(self, anchor, other):
                return {"timbre": 0.97, "groove": 0.9, "melody": 0.62}

        self.similar = Three()
        comp, = self.plan("HGR S STD 2-1", "variety")
        new = [p for p in self.picks(comp) if p.tier == "new"][0]
        self.assertIn("(timbre top 3 %, groove top 10 %, melody top 38 %)", new.source)

    # ── one round, one sound ───────────────────────────────────────────────

    def with_class_lists(self):
        """Jug A without history: three class lists fill its slots."""
        self.event_list("12.03.2025 Krefeld/JUG_A_STD.m3u", "KR")
        self.event_list("13.03.2025 Krefeld/JUG_A_STD.m3u", "KX")
        self.event_list("14.03.2025 Krefeld/JUG_A_STD.m3u", "KY")

    def test_the_heats_of_a_round_sound_alike(self):
        """Marcel: the music of one round should be similar — Vorrunde 1 WW
        and Vorrunde 2 WW. A later heat takes, among its tier's next free
        titles, the one most like the first heat's title of that dance."""
        self.with_class_lists()
        plain, = self.plan("Jug A STD 2-1", "like_last_year")
        first, second = plain.grid[plain.rounds[0].name]
        free = [p.entry for p in self.cands("Jug A STD 2-1").klass[0]["LW"]
                if p.entry not in (first[0].entry, second[0].entry)
                and p.entry not in [q.entry for q in self.picks(plain)]]
        alike = free[-1] if free else None
        self.assertIsNotNone(alike, "the class lists leave a title for the test")
        fixture = self

        class Sound:
            def __call__(self, *args, **kwargs):
                return fixture.__class__.similar(fixture, *args, **kwargs)

            def views(self, anchor, other):
                s = 0.95 if other is alike else 0.2
                return {"timbre": s, "groove": s, "melody": s}

            def agreement(self, anchor, other):
                return 0.95 if (anchor is first[0].entry and other is alike) else 0.2

        self.similar = Sound()
        comp, = self.plan("Jug A STD 2-1", "like_last_year")
        heat1, heat2 = comp.grid[comp.rounds[0].name]
        self.assertIs(heat1[0].entry, first[0].entry)
        self.assertIs(heat2[0].entry, alike)
        self.assertIn(first[0].entry.title, heat2[0].like_heat)
        self.assertIn("timbre top 5 %", heat2[0].like_heat)
        self.assertEqual(heat1[0].like_heat, "")

        # Moved elsewhere, the title no longer answers to that first heat.
        comps = [comp]
        a, b = (0, 0, 1, 0), (0, 0, 0, 0)
        event_plan.swap_slots(comps, a, b)
        self.assertEqual(event_plan.slot_pick(comps, b).like_heat, "")
        event_plan.put_slot(comps, a, event_plan.slot_pick(comps, b))
        self.assertEqual(event_plan.slot_pick(comps, a).like_heat, "")
        comp.grid[comp.rounds[0].name][1][0] = heat2[0]
        event_plan.put_slot(comps, a, heat2[0])
        self.assertEqual(event_plan.slot_pick(comps, a).like_heat, "")

    def test_the_events_own_titles_stay_as_played(self):
        """Last year's heats are last year's: no reordering by sound."""
        vr, _er = self.event_list("DanceConvention 2025/HGR_S_STD.m3u", "DC")
        fixture = self

        class Sound:
            def __call__(self, *args, **kwargs):
                return fixture.__class__.similar(fixture, *args, **kwargs)

            def agreement(self, anchor, other):
                return 0.99 if other.title == "DC VR1 LW" else 0.1

        self.similar = Sound()
        comp, = self.plan("HGR S STD 2-1", "like_last_year")
        heat1, heat2 = comp.grid[comp.rounds[0].name]
        self.assertEqual({heat1[0].entry.title, heat2[0].entry.title},
                         {"DC VR1 LW", "DC VR2 LW"})
        self.assertEqual(heat2[0].like_heat, "")

    def test_a_title_already_played_at_the_class_is_not_new(self):
        er = self.with_new_titles()
        played = self.entry("Played LW", "LW", s_plays=1)
        self.sounds_like[played.title] = (played, er[0], 0.99)
        comp, = self.plan("HGR S STD 2-1", "variety")
        self.assertNotIn(played, [p.entry for p in self.picks(comp)
                                  if p.tier == "new"])

    def test_another_file_of_a_played_song_is_not_new(self):
        """The real J&J plan offered 'A New Life — sounds like A New Life (99%)'."""
        er = self.with_new_titles()
        copy = MusicEntry(path=Path(rf"C:\music\standardcd\cd2\{er[0].title} (LW 29).mp3"),
                          title=er[0].title, dance="LW", bpm=29)
        self.lib.entries.append(copy)
        self.sounds_like[copy.title + " copy"] = (copy, er[0], 0.99)
        spec, = parse_competition_schedule("HGR S STD 2-1")
        cands = event_plan.gather_candidates(
            self.lib, spec, event_plan.past_editions("danceconvention", root=self.root),
            similar=self.similar)
        new = [p.entry for p in cands.new["LW"]]
        self.assertIn(self.sounds_like["New 0 LW"][0], new)
        self.assertNotIn(copy, new)

    def test_a_new_title_came_into_the_archive_lately(self):
        """New means new in the archive: Willow was never played at the class
        and sounds right, but has been in the library since 2020."""
        er = self.with_new_titles()
        old = self.entry("Willow LW", "LW", months_ago=70)
        recent = self.entry("Recent LW", "LW", months_ago=17)
        older = self.entry("Older LW", "LW", months_ago=19)
        unknown = self.entry("Unknown LW", "LW")
        unknown.added = None
        for e in (old, recent, older, unknown):
            self.sounds_like[e.title] = (e, er[0], 0.99)
        spec, = parse_competition_schedule("HGR S STD 2-1")
        cands = event_plan.gather_candidates(
            self.lib, spec, event_plan.past_editions("danceconvention", root=self.root),
            similar=self.similar)
        new = [p.entry for p in cands.new["LW"]]
        self.assertIn(recent, new)
        for e in (old, older, unknown):
            self.assertNotIn(e, new)
        self.assertIn(old, [p.entry for p in cands.library["LW"]])

    def test_every_fresh_title_is_new_the_most_alike_first(self):
        """Few fresh titles reach 80 %: the new tier takes them all, sorted by
        how much they sound like the proven ones, so a new slot stays new.
        Only one that really sounds alike is offered as a title's stand-in."""
        er = self.with_new_titles()
        far = self.entry("Far LW", "LW")
        self.sounds_like[far.title] = (far, er[0], 0.35)
        silent = self.entry("Silent LW", "LW")      # no timbre neighbour at all
        spec, = parse_competition_schedule("HGR S STD 2-1")
        cands = event_plan.gather_candidates(
            self.lib, spec, event_plan.past_editions("danceconvention", root=self.root),
            similar=self.similar)
        new = cands.new["LW"]
        self.assertEqual([p.entry for p in new[-2:]], [far, silent])
        self.assertIn("35%", new[-2].source)
        self.assertIsNone(new[-2].anchor)
        self.assertIs(new[0].anchor, er[0])

    def test_a_new_title_says_when_it_came(self):
        self.with_new_titles()
        spec, = parse_competition_schedule("HGR S STD 2-1")
        cands = event_plan.gather_candidates(
            self.lib, spec, event_plan.past_editions("danceconvention", root=self.root),
            similar=self.similar)
        self.assertIn(time.strftime("%m/%Y"), cands.new["LW"][0].source)

    # ── one day, no title twice ────────────────────────────────────────────

    def test_no_title_twice_in_a_day(self):
        self.event_list("DanceConvention 2025/HGR_S_STD.m3u", "DC")
        self.event_list("12.03.2025 Krefeld/HGR_S_STD.m3u", "KR")
        comps = self.plan("HGR S STD 2-1\nHGR II S STD 2-1", "proven_fresh")
        paths = [str(p.entry.path) for c in comps for p in self.picks(c)]
        self.assertEqual(len(paths), len(set(paths)))

    def test_a_title_with_history_stays_with_its_competition(self):
        """Last year's SEN I final Slow Waltz also sits in a Krefeld HGR S list,
        the only one HGR S has. HGR S comes first in the day — it must still
        leave the title to SEN I."""
        _vr, sen_er = self.event_list("DanceConvention 2025/MAS_I_S_STD.m3u", "SEN")
        self.write("12.03.2025 Krefeld/HGR_S_STD.m3u", [sen_er[0]])
        hgr, sen = self.plan("HGR S STD 2-1\nSEN I S STD 2-1", "like_last_year")
        self.assertNotIn(sen_er[0], [p.entry for p in self.picks(hgr)])
        self.assertIn(sen_er[0], [p.entry for p in self.picks(sen)])

    def test_the_more_important_competition_chooses_first(self):
        """Jug A runs first that day, HGR S ranks first: HGR S gets the most
        played waltz. The competitions stay in the day's order."""
        top = [self.entry(f"Plays {n} {d}", d, s_plays=n)
               for d in _STD for n in range(3, 9)]
        jug, hgr = self.plan("Jug A STD 2-1\nHGR S STD 2-1", "variety")
        self.assertEqual((jug.spec.label, hgr.spec.label), ("Jug A STD", "HGR S STD"))
        self.assertIs(hgr.grid["Finale"][0][0].entry, top[5])
        self.assertNotIn(top[5], [p.entry for p in self.picks(jug)])

    def test_the_grid_loads_as_a_playlist(self):
        _vr, er = self.event_list("DanceConvention 2025/HGR_S_STD.m3u", "DC")
        comp, = self.plan("HGR S STD 2-1", "like_last_year")
        playlist = comp.playlist()
        self.assertEqual(list(playlist), [rc.name for rc in comp.rounds])
        self.assertEqual(playlist[comp.rounds[-1].name][0], er)


if __name__ == "__main__":
    unittest.main(verbosity=2)
