#!/usr/bin/env python3
"""The 🎉 party check reads a loaded Eintanzen list back against its own rules.

Run:  py -m unittest tests.planner.test_party_check -v

`planner/warmup.py` builds a party list under rules nothing re-checks once the
list is on screen and being edited. `planner/party_check.py` is the reverse
pass. Two halves to the evidence here:

* one hand-built list per rule, each breaking exactly that rule, so a finding
  that stops firing is caught and the wording stays readable;
* a list the generator actually built, which must come back with nothing at
  all. That is the half that keeps the two files honest with each other — a
  threshold the check tightens past what the builder does would show up as a
  clean generated list suddenly failing.
"""

import random
import unittest
from pathlib import Path

from planner import party_check as pc
from planner.models import MusicEntry
from planner.warmup import (
    _WARMUP_BALLROOM,
    _WARMUP_LATIN,
    _WARMUP_MODE,
    build_warmup_playlist,
)

# One in-band takt per dance, so the takt rule stays quiet unless a test asks
# for it. Mid-band on purpose: T29 is the middle of 28–30.
_TAKT = {'LW': 29, 'TG': 32, 'WW': 59, 'SF': 29, 'QS': 51,
         'CC': 31, 'SA': 51, 'RB': 25, 'PD': 59, 'JI': 42}

_COUNTER = [0]

# Titles far enough apart that the near-duplicate rule has nothing to say.
_SOCIAL_TITLES = ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot",
                  "golf", "hotel", "india", "juliett", "kilo", "lima", "mike",
                  "november", "oscar", "papa", "quebec", "romeo", "sierra",
                  "victor")


def song(code, *, title=None, bpm=None, duration=180, path=None):
    """One library track of `code`, unique unless told otherwise."""
    _COUNTER[0] += 1
    n = _COUNTER[0]
    return MusicEntry(
        path=Path(path or f"C:/lib/{code}/{code}_{n}.mp3"),
        title=title or f"{code} {n}",
        dance=code,
        bpm=_TAKT[code] if bpm is None else bpm,
        duration=duration)


def listing(*codes):
    """A party list from a flat run of dance codes."""
    return [song(c) for c in codes]


def texts(findings, category=None):
    return [f.text for f in findings
            if category is None or f.category == category]


class PartyCheckBaseTest(unittest.TestCase):
    """The shape of a finding, and the list that breaks nothing."""

    def test_a_correct_evening_reports_nothing(self):
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'TG', 'SF', 'LW',
                          'SA', 'RB', 'CC',
                          'QS', 'WW', 'LW',
                          'JI', 'RB', 'CC')
        self.assertEqual(pc.party_findings(entries), [])

    def test_an_empty_list_reports_nothing(self):
        self.assertEqual(pc.party_findings([]), [])

    def test_a_finding_carries_the_rows_its_segments_point_at(self):
        entries = listing('LW', 'TG', 'QS', 'CC', 'SA', 'JI')
        found = pc.party_findings(entries)
        self.assertTrue(found, "the Latin section opens on Samba, not Rumba")
        for f in found:
            with self.subTest(text=f.text):
                self.assertEqual(
                    f.rows,
                    tuple(dict.fromkeys(t for _s, t in f.segments
                                        if t is not None)))
                self.assertEqual(f.text,
                                 "".join(t for t, _ in f.segments))


class RoundStructureTest(unittest.TestCase):

    def test_a_round_of_two_is_reported_with_its_first_row(self):
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB',              # two, and the evening goes on
                          'LW', 'SF', 'WW')
        found = texts(pc.party_findings(entries), pc.ROUNDS)
        self.assertTrue(any("“Lateinrunde 1” is 2 titles long, not 3" in t
                            for t in found), found)
        short = [f for f in pc.party_findings(entries)
                 if "is 2 titles long" in f.text][0]
        self.assertEqual(short.rows, (3,))

    def test_the_last_round_of_the_evening_may_run_out(self):
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'LW', 'SF')             # the music simply stopped
        self.assertEqual(
            [t for t in texts(pc.party_findings(entries)) if "long, not 3" in t],
            [])

    def test_a_social_interlude_is_one_title_or_two_and_not_a_short_round(self):
        """The builder makes a social round ONE title, or two — "two rounds in
        three hold a single title", so the socials stay the breather between
        the competition rounds. Reporting that as a round of 1 is reporting
        the builder working."""
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI')
        entries.append(song('DISCOFOX', bpm=30))        # a single-title social
        entries += listing('LW', 'SF', 'WW',
                           'SA', 'CC', 'JI')
        entries += [song('SALSA', bpm=30), song('BACHATA', bpm=30)]   # a double
        entries += listing('LW', 'TG', 'QS')
        found = texts(pc.party_findings(entries), pc.ROUNDS)
        self.assertEqual([t for t in found if "long, not 3" in t], [], found)

    def test_a_dance_repeated_inside_a_round_reads_as_two_short_rounds(self):
        """`warmup_rounds` cuts a fresh round at the repeat, which is why the
        check does not carry a rule of its own for it."""
        entries = listing('LW', 'TG', 'LW', 'SF', 'QS', 'WW',
                          'CC', 'RB', 'JI')
        found = texts(pc.party_findings(entries), pc.ROUNDS)
        self.assertTrue(any("“Standardrunde 1” is 2 titles long" in t
                            for t in found), found)

    def test_a_dance_in_three_rounds_running_is_no_finding(self):
        """The promise is coverage — every dance inside three rounds — not
        variety. Four Standard dances on three slots leave one out per round,
        so a dance three rounds running is common and costs nobody their turn:
        the Tango here plays three in a row and every dance is still inside
        each window of three."""
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'TG', 'SF', 'LW',
                          'RB', 'CC', 'SA',
                          'TG', 'QS', 'LW',
                          'JI', 'RB', 'CC',
                          'SF', 'QS', 'LW')
        self.assertEqual(pc.party_findings(entries), [])

    def test_a_dance_that_sits_out_three_rounds_is_reported(self):
        """The Slowfox plays in the second Standard round, then sits out the
        next three — it does come back, so the whole-evening check alone would
        have let it through."""
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'TG', 'SF', 'LW',
                          'SA', 'RB', 'CC',
                          'LW', 'TG', 'QS',       # row 13: SF sits out …
                          'JI', 'RB', 'CC',
                          'LW', 'TG', 'QS',
                          'SA', 'RB', 'JI',
                          'LW', 'TG', 'QS',       # … the third one
                          'CC', 'RB', 'JI',
                          'SF', 'QS', 'LW')
        findings = [f for f in pc.party_findings(entries)
                    if f.category == pc.ROUNDS]
        self.assertEqual(
            [f.text for f in findings],
            ["the Slowfox sits out 3 Standard rounds running, from row 13."])
        self.assertEqual(findings[0].rows, (12,))

    def test_a_dance_not_among_the_openers_is_owed_by_the_third_round(self):
        """The opening round has no Slowfox; the builder forces it in by the
        third, so a list without one until the fourth is a gap from row 1."""
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'LW', 'TG', 'QS',
                          'SA', 'RB', 'CC',
                          'LW', 'TG', 'QS',
                          'JI', 'RB', 'CC',
                          'SF', 'QS', 'LW')
        found = texts(pc.party_findings(entries), pc.ROUNDS)
        self.assertIn(
            "the Slowfox sits out 3 Standard rounds running, from row 1.",
            found)

    def test_two_rounds_out_is_still_inside_the_promise(self):
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'TG', 'SF', 'LW',
                          'SA', 'RB', 'CC',
                          'LW', 'TG', 'QS',
                          'JI', 'RB', 'CC',
                          'LW', 'TG', 'QS',
                          'SA', 'RB', 'JI',
                          'SF', 'QS', 'LW')
        self.assertEqual(pc.party_findings(entries), [])

    def test_the_samba_may_not_run_two_latin_rounds(self):
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'LW', 'SF', 'WW',
                          'SA', 'RB', 'CC',
                          'TG', 'LW', 'QS',
                          'SA', 'RB', 'JI')
        found = texts(pc.party_findings(entries), pc.ROUNDS)
        self.assertTrue(any("the Samba plays two Latin rounds running" in t
                            for t in found), found)

    def test_each_section_has_fixed_openers(self):
        entries = listing('LW', 'SF', 'WW',       # not LW TG QS
                          'CC', 'RB', 'JI')
        found = texts(pc.party_findings(entries), pc.ROUNDS)
        self.assertTrue(any("“Standardrunde 1” opens the section with" in t
                            and "Langsamer Walzer, Tango, Quickstep" in t
                            for t in found), found)

    def test_two_rounds_of_the_same_section_may_not_touch(self):
        """A pair of Standard rounds in a row cannot show up as one long round:
        the repeated dance cuts them apart, and it is the touching pair that is
        worth saying."""
        entries = listing('LW', 'TG', 'QS',
                          'SF', 'WW', 'LW',
                          'CC', 'RB', 'JI')
        found = texts(pc.party_findings(entries), pc.ROUNDS)
        self.assertTrue(any("two Standard rounds run back to back" in t
                            for t in found), found)

    def test_a_social_round_may_fall_anywhere(self):
        entries = [song('LW'), song('TG'), song('QS')]
        entries += [MusicEntry(path=Path(f"C:/lib/mode/{n}.mp3"), title=f"m{n}",
                               dance=None, other_genre=g, duration=180)
                    for n, g in enumerate(("Discofox", "Salsa", "Bachata"))]
        entries += listing('CC', 'RB', 'JI')
        self.assertEqual(
            [t for t in texts(pc.party_findings(entries)) if "back to back" in t],
            [])

    def test_a_dance_that_never_plays_is_a_hole(self):
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'TG', 'QS', 'LW',
                          'SA', 'RB', 'CC',
                          'QS', 'WW', 'LW',
                          'JI', 'RB', 'CC')       # no Slowfox anywhere
        found = texts(pc.party_findings(entries), pc.ROUNDS)
        self.assertTrue(any("the Slowfox never plays — 3 Standard rounds"
                            in t for t in found), found)

    def test_the_wiener_walzer_owes_nothing_while_late_ww_holds_it_back(self):
        """It is not in the builder's coverage set under "late WW" — only its
        0.05 weight puts it in a round at all, and three Standard rounds can
        pass without one."""
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'TG', 'SF', 'LW',
                          'SA', 'RB', 'CC',
                          'QS', 'SF', 'LW',
                          'JI', 'RB', 'CC')
        self.assertEqual(
            [t for t in texts(pc.party_findings(entries)) if "never plays" in t],
            [])
        found = texts(pc.party_findings(entries, late_ww=False))
        self.assertTrue(any("the Wiener Walzer never plays" in t
                            for t in found), found)

    def test_two_rounds_of_a_section_owe_no_coverage(self):
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'LW', 'TG', 'SF',
                          'RB', 'CC', 'SA')
        self.assertEqual(
            [t for t in texts(pc.party_findings(entries)) if "never plays" in t],
            [])


class SpacingTest(unittest.TestCase):

    def test_late_ww_holds_the_wiener_walzer_back(self):
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'WW', 'SF', 'LW')       # row 7, only 6 played
        found = texts(pc.party_findings(entries), pc.SPACING)
        self.assertTrue(any("the Wiener Walzer opens the evening at row 7" in t
                            for t in found), found)

    def test_late_ww_off_lets_it_open(self):
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'WW', 'SF', 'LW')
        self.assertEqual(
            texts(pc.party_findings(entries, late_ww=False), pc.SPACING), [])

    def test_late_pd_holds_the_first_paso_back(self):
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'LW', 'SF', 'WW',
                          'RB', 'PD', 'CC')       # row 11, far short of 40
        found = texts(pc.party_findings(entries), pc.SPACING)
        self.assertTrue(any("a Paso Doble plays at row 11" in t
                            for t in found), found)

    def test_two_pasos_may_not_sit_two_latin_rounds_apart(self):
        entries = (listing('LW', 'TG', 'QS') + listing('PD', 'RB', 'CC')
                   + listing('SF', 'LW', 'WW') + listing('JI', 'RB', 'SA')
                   + listing('TG', 'LW', 'QS') + listing('CC', 'PD', 'RB'))
        found = texts(pc.party_findings(entries, late_pd=False), pc.SPACING)
        self.assertTrue(any("two Paso Dobles sit 2 Latin rounds apart" in t
                            for t in found), found)

    def test_three_latin_rounds_apart_is_the_rule_kept(self):
        entries = (listing('LW', 'TG', 'QS') + listing('PD', 'RB', 'CC')
                   + listing('SF', 'LW', 'WW') + listing('JI', 'RB', 'SA')
                   + listing('TG', 'LW', 'QS') + listing('CC', 'JI', 'RB')
                   + listing('WW', 'SF', 'LW') + listing('PD', 'RB', 'CC'))
        self.assertEqual(
            [t for t in texts(pc.party_findings(entries, late_pd=False))
             if "Paso Dobles sit" in t], [])


class DuplicateTest(unittest.TestCase):

    def test_the_same_file_twice_names_both_rows(self):
        twice = "C:/lib/CC/encore.mp3"
        entries = listing('LW', 'TG', 'QS')
        entries += [song('CC', title="Encore", path=twice), song('RB'),
                    song('JI')]
        entries += [song('LW'), song('SF'),
                    song('CC', title="Encore", path=twice)]
        found = texts(pc.party_findings(entries), pc.DUPLICATES)
        self.assertTrue(any("“Encore” plays 2 times, at row 4, row 9" in t
                            for t in found), found)

    def test_two_files_of_the_same_song_are_near_duplicates(self):
        entries = listing('LW', 'TG', 'QS')
        entries += [song('CC', title="Let It Go"), song('RB'), song('JI')]
        entries += [song('LW'), song('SF'),
                    song('CC', title="Let It Go (Radio Edit)")]
        found = texts(pc.party_findings(entries), pc.DUPLICATES)
        self.assertTrue(any("look like the same song" in t for t in found),
                        found)

    def test_the_same_title_on_two_dances_is_two_songs(self):
        entries = listing('LW', 'TG', 'QS')
        entries += [song('CC', title="Let It Go"), song('RB'), song('JI')]
        entries += [song('LW', title="Let It Go (Waltz Version)"), song('SF'),
                    song('TG')]
        self.assertEqual(texts(pc.party_findings(entries), pc.DUPLICATES), [])


class TaktTest(unittest.TestCase):

    def test_a_track_outside_its_band_is_reported(self):
        entries = listing('LW', 'TG', 'QS', 'CC', 'RB', 'JI')
        entries[2] = song('QS', title="Too fast", bpm=56)     # band is 50–52
        found = texts(pc.party_findings(entries), pc.TAKT)
        self.assertTrue(any("“Too fast” is a Quickstep at T56, outside T50–T52"
                            in t for t in found), found)

    def test_an_unmeasured_track_is_not_this_checks_business(self):
        entries = listing('LW', 'TG', 'QS', 'CC', 'RB', 'JI')
        entries[2] = song('QS', title="No tempo", bpm=0)
        self.assertEqual(texts(pc.party_findings(entries), pc.TAKT), [])

    def test_a_social_dance_has_no_band_to_miss(self):
        entries = listing('LW', 'TG', 'QS')
        entries += [MusicEntry(path=Path("C:/lib/mode/df.mp3"), title="Discofox",
                               dance=None, other_genre="Discofox", duration=180)]
        self.assertEqual(texts(pc.party_findings(entries), pc.TAKT), [])


class LengthTest(unittest.TestCase):

    def test_a_track_over_five_minutes_is_marked(self):
        entries = listing('LW', 'TG', 'QS', 'CC', 'RB', 'JI')
        entries[4] = song('RB', title="The long one", duration=372)
        found = texts(pc.party_findings(entries), pc.LENGTH)
        self.assertTrue(any("“The long one” runs 6:12, past 5:00" in t
                            for t in found), found)

    def test_exactly_five_minutes_still_passes(self):
        entries = listing('LW', 'TG', 'QS', 'CC', 'RB', 'JI')
        entries[4] = song('RB', title="Bang on", duration=pc.LONG_TRACK_SECS)
        self.assertEqual(texts(pc.party_findings(entries), pc.LENGTH), [])

    def test_the_threshold_moves_with_the_caller(self):
        entries = listing('LW', 'TG', 'QS', 'CC', 'RB', 'JI')
        entries[4] = song('RB', title="Four minutes", duration=250)
        self.assertEqual(texts(pc.party_findings(entries), pc.LENGTH), [])
        found = texts(pc.party_findings(entries, long_secs=240), pc.LENGTH)
        self.assertTrue(any("“Four minutes” runs 4:10, past 4:00" in t
                            for t in found), found)


class GeneratedListTest(unittest.TestCase):
    """What the builder produces, the check has to accept.

    This is the test that keeps the two files from drifting: every rule here
    is also a rule `build_warmup_playlist` enforces, so a generated list is
    the one input that must come back empty."""

    def pool(self):
        return [song(d) for d in _WARMUP_BALLROOM + _WARMUP_LATIN
                for _ in range(40)]

    def test_twelve_generated_lists_break_no_rule(self):
        for seed in range(12):
            with self.subTest(seed=seed):
                random.seed(seed)
                built = build_warmup_playlist(self.pool(), max_tracks=60)
                found = pc.party_findings(built)
                self.assertEqual(
                    [f.text for f in found], [],
                    "the builder produced a list its own check rejects")

    def test_generated_lists_with_social_rounds_break_no_rule_either(self):
        """The same promise with the Modetänze switched on. It was never made
        with them before, which is how the check came to call every social
        interlude a short round."""
        # Spelled-out titles, not "BACHATA 469" / "BACHATA 479": a social pool
        # is shallow and drawn from often, so numbered titles one digit apart
        # trip the near-duplicate rule, which is right to say so.
        pool = self.pool() + [song(c, title=w, bpm=30)
                              for c in _WARMUP_MODE for w in _SOCIAL_TITLES]
        for seed in range(12):
            with self.subTest(seed=seed):
                random.seed(seed)
                built = build_warmup_playlist(list(pool), max_tracks=60,
                                              include_modetaenze=True)
                found = pc.party_findings(built)
                self.assertEqual(
                    [f.text for f in found], [],
                    "the builder produced a list its own check rejects")


if __name__ == "__main__":
    unittest.main()
