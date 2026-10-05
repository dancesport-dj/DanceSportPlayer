#!/usr/bin/env python3
"""The 🎉 party check speaks German too.

Run:  py -m unittest tests.planner.test_party_check_i18n -v

Every finding is a sentence built by `%`, and a `%`-built string is never a
catalog key — so the whole report stayed English in a German app, right down
to the "row 7" the jump link is written on.

The engine is where they are built, so this is where they are checked: the
lists come from tests.planner.test_party_check, one per rule, and each is read
back in German. Nothing here asserts an English wording — that file already
does, and the two together are what says a template was translated rather than
rewritten.

`DEFAULT_LANGUAGE` is English and `t()` is then the identity, so a test that
does not switch the language cannot see a missing entry at all. Hence
`i18n.set_active("de")` in setUp: that is the switch this file exists for.
"""

import unittest

from planner import i18n
from planner import party_check as pc
from tests.planner.test_party_check import listing, song, texts


class _German(unittest.TestCase):
    """The same lists as the English tests, read back in German."""

    def setUp(self):
        i18n.set_active("de")

    def tearDown(self):
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def found(self, entries, category=None, **kw):
        return texts(pc.party_findings(entries, **kw), category)

    def assertSays(self, found, fragment):
        self.assertTrue(any(fragment in t for t in found),
                        "%r is still English:\n%s"
                        % (fragment, "\n".join(found)))


class RoundSentenceTest(_German):

    def test_the_row_a_finding_points_at(self):
        """The jump link itself — "row 7" is a sentence too."""
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'WW', 'SF', 'LW')
        self.assertSays(self.found(entries, pc.SPACING), "Zeile 7")

    def test_a_short_round(self):
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB',
                          'LW', 'SF', 'WW')
        self.assertSays(self.found(entries, pc.ROUNDS),
                        "„Lateinrunde 1“ ist nur 2 Titel lang statt 3")

    def test_a_dance_that_sits_out_three_rounds(self):
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'LW', 'TG', 'QS',
                          'SA', 'RB', 'CC',
                          'LW', 'TG', 'QS',
                          'JI', 'RB', 'CC',
                          'SF', 'QS', 'LW')
        self.assertSays(self.found(entries, pc.ROUNDS),
                        "Slowfox setzt 3 Standardrunden hintereinander aus, "
                        "ab Zeile 1.")

    def test_the_samba_two_rounds_running(self):
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'LW', 'SF', 'WW',
                          'SA', 'RB', 'CC',
                          'TG', 'LW', 'QS',
                          'SA', 'RB', 'JI')
        self.assertSays(self.found(entries, pc.ROUNDS),
                        "die Samba läuft in zwei Lateinrunden hintereinander")

    def test_the_fixed_openers_of_a_section(self):
        entries = listing('LW', 'SF', 'WW',
                          'CC', 'RB', 'JI')
        self.assertSays(self.found(entries, pc.ROUNDS),
                        "„Standardrunde 1“ eröffnet die Sektion mit")

    def test_two_rounds_of_the_same_section_touching(self):
        entries = listing('LW', 'TG', 'QS',
                          'SF', 'WW', 'LW',
                          'CC', 'RB', 'JI')
        found = self.found(entries, pc.ROUNDS)
        self.assertSays(found, "zwei Standardrunden laufen direkt hintereinander")
        self.assertSays(found, "ohne eine Runde der anderen Sektion dazwischen.")

    def test_a_dance_that_never_plays(self):
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'TG', 'QS', 'LW',
                          'SA', 'RB', 'CC',
                          'QS', 'WW', 'LW',
                          'JI', 'RB', 'CC')
        self.assertSays(self.found(entries, pc.ROUNDS),
                        "Slowfox kommt nie vor — in 3 Standardrunden")


class SpacingSentenceTest(_German):

    def test_the_wiener_walzer_held_back(self):
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'WW', 'SF', 'LW')
        found = self.found(entries, pc.SPACING)
        self.assertSays(found, "der Wiener Walzer eröffnet den Abend bei")
        self.assertSays(found, "„Wiener Walzer spät“ hält ihn zurück")

    def test_the_first_paso_held_back(self):
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'LW', 'SF', 'WW',
                          'RB', 'PD', 'CC')
        found = self.found(entries, pc.SPACING)
        self.assertSays(found, "ein Paso Doble läuft bei")
        self.assertSays(found, "„Paso Doble spät“ hält den ersten zurück")

    def test_two_pasos_too_close(self):
        entries = (listing('LW', 'TG', 'QS') + listing('PD', 'RB', 'CC')
                   + listing('SF', 'LW', 'WW') + listing('JI', 'RB', 'SA')
                   + listing('TG', 'LW', 'QS') + listing('CC', 'PD', 'RB'))
        found = self.found(entries, pc.SPACING, late_pd=False)
        self.assertSays(found,
                        "zwischen zwei Paso Dobles liegen nur 2 Lateinrunden")
        self.assertSays(found, "die Regel sagt 3.")


class TitleSentenceTest(_German):

    def test_the_same_file_twice(self):
        twice = "C:/lib/CC/encore_de.mp3"
        entries = listing('LW', 'TG', 'QS')
        entries += [song('CC', title="Encore", path=twice), song('RB'),
                    song('JI')]
        entries += [song('LW'), song('SF'),
                    song('CC', title="Encore", path=twice)]
        self.assertSays(self.found(entries, pc.DUPLICATES),
                        "„Encore“ läuft 2 mal, bei Zeile 4, Zeile 9.")

    def test_two_files_of_the_same_song(self):
        entries = listing('LW', 'TG', 'QS')
        entries += [song('CC', title="Let It Go"), song('RB'), song('JI')]
        entries += [song('LW'), song('SF'),
                    song('CC', title="Let It Go (Radio Edit)")]
        self.assertSays(self.found(entries, pc.DUPLICATES),
                        "sehen nach demselben Lied aus, bei")

    def test_a_title_outside_its_tempo_band(self):
        entries = listing('LW', 'TG', 'QS', 'CC', 'RB', 'JI')
        entries[2] = song('QS', title="Zu schnell", bpm=56)
        self.assertSays(self.found(entries, pc.TAKT),
                        "„Zu schnell“ ist ein Quickstep mit T56, "
                        "außerhalb von T50–T52")

    def test_an_over_long_title(self):
        entries = listing('LW', 'TG', 'QS', 'CC', 'RB', 'JI')
        entries[4] = song('RB', title="Der Lange", duration=372)
        self.assertSays(self.found(entries, pc.LENGTH),
                        "„Der Lange“ läuft 6:12, länger als 5:00")


class EnglishIsUnchangedTest(unittest.TestCase):
    """The catalog is a lookup on the English string, so English has to come
    back byte for byte — the restructured section phrase most of all."""

    def test_the_section_phrase_still_reads_the_way_it_did(self):
        entries = listing('LW', 'TG', 'QS',
                          'CC', 'RB', 'JI',
                          'LW', 'SF', 'WW',
                          'SA', 'RB', 'CC',
                          'TG', 'LW', 'QS',
                          'SA', 'RB', 'JI')
        found = texts(pc.party_findings(entries), pc.ROUNDS)
        self.assertTrue(
            any("the Samba plays two Latin rounds running, the second at "
                "row 16." in t for t in found), found)


if __name__ == "__main__":
    unittest.main()
