#!/usr/bin/env python3
"""Unit tests for the pure parsing/scoring helpers in dancesport_planner.

Run:  py -m unittest tests.planner.test_parsing -v
(or:  .venv\\Scripts\\python.exe -m unittest test_parsing -v)

These functions are pure (filename/text in, value out), so the tests need no
music library, no DB and no Qt — they pin down the regex behavior that the
scan and the competition importer depend on.
"""

import unittest
from unittest import mock
from pathlib import Path

from dancesport_planner import (
    parse_competition_schedule, competition_matches_file,
)
from planner.competition import _is_superseded_playlist, _round_stage_value
from planner.parsing import (
    dance_from_folders, _clean_title, _detect_bpm, _detect_dance,
    _parse_class_tag, _song_title_keys, parse_comment_markers, version_base_keys,
)
from planner.similarity import _kl_to_sim


class DetectBpmTest(unittest.TestCase):
    """BPM values are bars per minute encoded in many filename styles."""

    def test_glued_uppercase_t_marker(self):
        self.assertEqual(_detect_bpm("Hello CattailsT28"), 28)
        self.assertEqual(_detect_bpm("Diosa marinaT32"), 32)

    def test_t_marker_with_boundary(self):
        self.assertEqual(_detect_bpm("Some Song T50"), 50)

    def test_parenthetical_code(self):
        self.assertEqual(_detect_bpm("My Waltz (LW 29)"), 29)
        self.assertEqual(_detect_bpm("Fiesta (Samba 50)"), 50)

    def test_parenthetical_multiword_name(self):
        self.assertEqual(_detect_bpm("Track (Slow Waltz 29)"), 29)
        self.assertEqual(_detect_bpm("Track (Paso Doble 60)"), 60)

    def test_parenthetical_tournament_tempo_marker(self):
        self.assertEqual(_detect_bpm("Song (Langsamer Walzer 29 TM)"), 29)
        self.assertEqual(_detect_bpm("Song (Tango - 33 T_M)"), 33)

    def test_bare_parenthetical_number(self):
        self.assertEqual(_detect_bpm("viennese waltz(58)"), 58)

    def test_bpm_suffix(self):
        self.assertEqual(_detect_bpm("Track 50bpm"), 50)

    def test_code_dash_number(self):
        self.assertEqual(_detect_bpm("[TG-32] Tanguera"), 32)
        self.assertEqual(_detect_bpm("WW-59 Wien bleibt Wien"), 59)

    def test_glued_pitch_suffix(self):
        self.assertEqual(_detect_bpm("Rb 25gepitched"), 25)

    def test_name_glued_number(self):
        self.assertEqual(_detect_bpm("Tango32"), 32)
        self.assertEqual(_detect_bpm("ChaCha 30"), 30)

    def test_skips_out_of_range_first_hit(self):
        # Track number 'WW 10' is out of range (10 < 15) → keep looking, find vw59.
        self.assertEqual(_detect_bpm("WW 10 Goldener Saal vw59"), 59)

    def test_slow_non_tournament_tempo_is_parsed(self):
        # Floor is 15 so a slow practice version reads as a (filterable) tempo,
        # not as bpm=None that would slip past the in-tempo filter.
        self.assertEqual(_detect_bpm("Rumba 19"), 19)

    def test_no_tempo(self):
        self.assertIsNone(_detect_bpm("Just A Song Title"))

    def test_out_of_range_only(self):
        self.assertIsNone(_detect_bpm("Track T99"))


class DetectDanceTest(unittest.TestCase):

    def test_code_token(self):
        self.assertEqual(_detect_dance("LW Moon River"), 'LW')
        self.assertEqual(_detect_dance("01 QS Sing Sing Sing"), 'QS')

    def test_full_name(self):
        self.assertEqual(_detect_dance("La Cumparsita Tango"), 'TG')
        self.assertEqual(_detect_dance("Slow Waltz Dream"), 'LW')

    def test_code_glued_to_bpm(self):
        # Fallback: code fused to BPM digits, e.g. (RB24)
        self.assertEqual(_detect_dance("Besame Mucho (RB24)"), 'RB')

    def test_alias_normalisation(self):
        # TA is an alias for Tango
        self.assertEqual(_detect_dance("TA 33 El Choclo"), 'TG')

    def test_no_dance(self):
        self.assertIsNone(_detect_dance("Some Random Pop Song"))


class DanceFromFoldersTest(unittest.TestCase):
    """Folder-structure fallback: dance name in a parent folder, optionally with
    quality/round qualifiers appended or as their own subfolders."""

    def test_plain_dance_folder(self):
        self.assertEqual(dance_from_folders(Path(r"D:\music\Samba\track.mp3")), 'SA')
        self.assertEqual(
            dance_from_folders(Path(r"D:\music\Langsamer Walzer\track.mp3")), 'LW')

    def test_quality_suffix(self):
        self.assertEqual(
            dance_from_folders(Path(r"D:\music\Samba gut\track.mp3")), 'SA')
        self.assertEqual(
            dance_from_folders(Path(r"D:\music\Samba sehr gut\track.mp3")), 'SA')
        self.assertEqual(
            dance_from_folders(Path(r"D:\music\Samba nicht so gut\track.mp3")), 'SA')

    def test_qualifier_subfolders_fall_through_to_dance_parent(self):
        self.assertEqual(dance_from_folders(
            Path(r"D:\music\Samba gut\vorrunden\track.mp3")), 'SA')
        self.assertEqual(dance_from_folders(
            Path(r"D:\music\Tango\endrunden\track.mp3")), 'TG')
        self.assertEqual(dance_from_folders(
            Path(r"D:\music\Quickstep\nicht gut\track.mp3")), 'QS')

    def test_multiword_dance_with_suffix(self):
        self.assertEqual(dance_from_folders(
            Path(r"D:\music\Wiener Walzer sehr gut\track.mp3")), 'WW')

    def test_qualifier_only_folders_match_nothing(self):
        self.assertIsNone(dance_from_folders(
            Path(r"D:\music\Party\nicht gut\track.mp3")))

    def test_no_dance_folder(self):
        self.assertIsNone(dance_from_folders(
            Path(r"D:\music\Charts 2024\track.mp3")))


class RoundStageValueTest(unittest.TestCase):
    """0=Vorrunde, 10·n=n-th Zwischenrunde, 50=Halbfinale, 60=Endrunde."""

    def test_vorrunde(self):
        for tok in ('VR', 'vor', 'Vorrunde'):
            self.assertEqual(_round_stage_value(tok), 0, tok)

    def test_zwischenrunde(self):
        self.assertEqual(_round_stage_value('ZR'), 10)
        self.assertEqual(_round_stage_value('1ZR'), 10)
        self.assertEqual(_round_stage_value('2ZR'), 20)
        self.assertEqual(_round_stage_value('3ZR'), 30)

    def test_halbfinale(self):
        for tok in ('SEMI', 'HF', 'Halbfinale'):
            self.assertEqual(_round_stage_value(tok), 50, tok)

    def test_endrunde(self):
        for tok in ('ER', 'Finale', 'final', 'FIN'):
            self.assertEqual(_round_stage_value(tok), 60, tok)

    def test_non_round_tokens(self):
        for tok in ('LAT', 'SEN', 'Jive', '2019', ''):
            self.assertIsNone(_round_stage_value(tok), tok)


class SupersededPlaylistTest(unittest.TestCase):
    """Old/auto-dumped lists must not feed popularity learning. Paths here are
    relative (the function treats non-PLAYLIST_DIR paths as already relative)."""

    def test_old_marker_directories(self):
        self.assertTrue(_is_superseded_playlist(Path("alt/SEN_I_LAT.m3u")))
        self.assertTrue(_is_superseded_playlist(Path("alte Listen/x.m3u")))
        self.assertTrue(_is_superseded_playlist(Path("07.8.2011alt/x.m3u")))
        self.assertTrue(_is_superseded_playlist(Path("old/x.m3u")))

    def test_old_marker_filename_suffix(self):
        self.assertTrue(_is_superseded_playlist(Path("HGR_S_STD_alt.m3u")))

    def test_abschlussveranstaltung_is_spared(self):
        # 'alt' inside 'Abschlussveranstaltung' is followed by 'u' → not a marker.
        self.assertFalse(
            _is_superseded_playlist(Path("Abschlussveranstaltung 2019/SEN_I_LAT.m3u")))

    def test_export_dumps(self):
        self.assertTrue(_is_superseded_playlist(Path("ExportM3U.m3u")))
        self.assertTrue(_is_superseded_playlist(Path("ExportUnused.m3u")))

    def test_merged_lists(self):
        self.assertTrue(_is_superseded_playlist(Path("musik_zusammen_einfach.m3u")))
        self.assertTrue(_is_superseded_playlist(Path("latein_merged_pre_6.m3u")))

    def test_alle_lists_but_halle_is_spared(self):
        self.assertTrue(_is_superseded_playlist(Path("alleSTD.m3u")))
        self.assertFalse(_is_superseded_playlist(Path("Turnier Halle 2019.m3u")))

    def test_holding_bins(self):
        self.assertTrue(_is_superseded_playlist(Path("neu_r.m3u")))
        self.assertTrue(_is_superseded_playlist(Path("zu_sortieren.m3u")))
        self.assertTrue(_is_superseded_playlist(Path("unsortiert_LAT.m3u")))
        self.assertTrue(_is_superseded_playlist(Path("liste_all.m3u")))
        self.assertTrue(_is_superseded_playlist(Path("Ball_2019.m3u")))
        self.assertTrue(_is_superseded_playlist(Path("Reserve_STD.m3u")))

    def test_token_lookalikes_survive(self):
        # 'neu'/'ball' only match as whole tokens: city/event names survive.
        self.assertFalse(_is_superseded_playlist(Path("Neuss Open 2018.m3u")))
        self.assertFalse(_is_superseded_playlist(Path("Galaball Turnier.m3u")))

    def test_per_dance_collection_dumps(self):
        self.assertTrue(_is_superseded_playlist(Path("Jive.m3u")))
        self.assertTrue(_is_superseded_playlist(Path("Jive_2.m3u")))
        self.assertTrue(_is_superseded_playlist(Path("LAT_Jive.m3u")))
        self.assertTrue(_is_superseded_playlist(Path("Tango Standard.m3u")))

    def test_mixed_names_survive(self):
        self.assertFalse(_is_superseded_playlist(Path("Jive Hits 2018.m3u")))

    def test_working_drafts(self):
        # Pre-selection pools: they hold the whole filtered library, so counting
        # them would mark hundreds of never-danced titles as played.
        self.assertTrue(_is_superseded_playlist(Path("Standard_filter_final.m3u")))
        self.assertTrue(_is_superseded_playlist(Path("gesamt_standard_pre.m3u")))
        self.assertTrue(_is_superseded_playlist(Path("gesamt.m3u")))
        self.assertTrue(_is_superseded_playlist(Path("standard_pre_4.m3u")))
        self.assertTrue(_is_superseded_playlist(Path("Vorsortierungen/LW_pre.m3u")))
        # …and anything sitting in a sorting folder, whatever it is called.
        self.assertTrue(_is_superseded_playlist(Path("grundsortierung/Modetaenze.m3u")))

    def test_words_starting_with_pre_survive(self):
        # 'pre' counts as a whole token only — an event is not a draft.
        self.assertFalse(_is_superseded_playlist(Path("Preisverleihung 2019.m3u")))
        self.assertFalse(_is_superseded_playlist(Path("Premiere HGR S STD.m3u")))

    def test_normal_event_playlist_survives(self):
        self.assertFalse(
            _is_superseded_playlist(Path("20.05.2023 Turnier Krefeld/SEN_I_LAT.m3u")))
        self.assertFalse(_is_superseded_playlist(Path("HGR S STD Finale.m3u")))


class ParseCompetitionScheduleTest(unittest.TestCase):

    def test_full_line(self):
        specs = parse_competition_schedule("Fr: SEN I LAT (12) 6-3-2-1")
        self.assertEqual(len(specs), 1)
        spec = specs[0]
        self.assertEqual(spec.style, 'Latin')
        self.assertEqual(spec.heats, [6, 3, 2, 1])
        self.assertEqual(spec.couples, 12)
        self.assertEqual(spec.label, 'SEN I LAT')

    def test_docstring_example(self):
        specs = parse_competition_schedule("U21 STD (50) 4-4-3-2-1")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0].style, 'Standard')
        self.assertEqual(specs[0].heats, [4, 4, 3, 2, 1])
        self.assertEqual(specs[0].couples, 50)

    def test_multiline_skips_invalid(self):
        text = (
            "Fr: SEN I LAT 6-3-2-1\n"
            "\n"
            "just a comment line\n"          # no style, no numbers → skipped
            "HGR S STD\n"                    # style but no round numbers → skipped
            "So: HGR S STD 5-2-1\n"
        )
        specs = parse_competition_schedule(text)
        self.assertEqual(len(specs), 2)
        self.assertEqual(specs[0].style, 'Latin')
        self.assertEqual(specs[1].style, 'Standard')
        self.assertEqual(specs[1].heats, [5, 2, 1])

    def test_no_style_token_skipped(self):
        self.assertEqual(parse_competition_schedule("SEN I 6-3-2-1"), [])

    def test_heats_outside_range_dropped(self):
        # 0 and >30 are not plausible heat counts.
        specs = parse_competition_schedule("SEN I LAT 99-6-3")
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0].heats, [6, 3])

    # ── a real event schedule (DanceConvention 2026) ─────────────────────────

    def test_start_time_is_not_part_of_the_label(self):
        spec, = parse_competition_schedule("18:30  Jug A STD 2 -1")
        self.assertEqual(spec.label, 'Jug A STD')
        self.assertEqual(spec.heats, [2, 1])

    def test_day_and_time_together(self):
        spec, = parse_competition_schedule("Sa: 9.30 HGR S STD 2-1")
        self.assertEqual(spec.label, 'HGR S STD')

    def test_start_class_comes_from_the_label(self):
        """'Jug A' is an A-class event — it used to be read as S."""
        spec, = parse_competition_schedule("Jug A STD 2-1")
        self.assertEqual(spec.dance_class, 'A')
        spec, = parse_competition_schedule("SEN V S STD 2-1")
        self.assertEqual(spec.dance_class, 'S')

    def test_a_d_class_line_dances_the_d_programme(self):
        spec, = parse_competition_schedule("HGR II D STD 3-1")
        self.assertEqual(spec.dance_class, 'D')
        self.assertEqual(spec.dances, ['LW', 'TG', 'SF', 'QS'])

    def test_no_class_in_the_label_stays_s(self):
        spec, = parse_competition_schedule("SEN I LAT 6-3-2-1")
        self.assertEqual(spec.dance_class, 'S')

    def test_jack_and_jill_line(self):
        """Its own dances in brackets, Standard and Latin mixed, and the numbers
        after the named rounds are couples — the heats follow from them."""
        spec, = parse_competition_schedule(
            "J & J (LW; TG; CC; RB) VR ZR ER 24 - 12 - 6")
        self.assertEqual(spec.label, 'J & J')
        self.assertEqual(spec.dances, ['LW', 'TG', 'CC', 'RB'])
        self.assertIsNone(spec.style, "a mixed programme has no single style")
        self.assertEqual(spec.couples_per_round, [24, 12, 6])
        self.assertEqual(spec.heats, [2, 1, 1])

    def test_jack_and_jill_without_its_dances(self):
        """'J&J 3-2-1' names neither a style nor dances, and was dropped. A mixed
        programme gets the usual LW TG CC RB, to be corrected in the table."""
        for line in ("J&J 3-2-1", "J & J 3-2-1", "Jack and Jill 3-2-1"):
            with self.subTest(line=line):
                spec, = parse_competition_schedule(line)
                self.assertEqual(spec.dances, ['LW', 'TG', 'CC', 'RB'])
                self.assertIsNone(spec.style)
                self.assertEqual(spec.heats, [3, 2, 1])
                self.assertIsNone(spec.couples_per_round)

    def test_a_line_without_style_or_dances_is_still_skipped(self):
        self.assertEqual(parse_competition_schedule("Mittagspause 12-13"), [])

    def test_couples_per_heat_is_a_parameter(self):
        spec, = parse_competition_schedule(
            "J & J (LW; TG; CC; RB) VR ZR ER 24 - 12 - 6", max_couples_per_heat=8)
        self.assertEqual(spec.heats, [3, 2, 1])

    def test_a_plain_heat_pattern_is_not_read_as_couples(self):
        spec, = parse_competition_schedule("HGR S STD 2-1")
        self.assertIsNone(spec.couples_per_round)
        self.assertEqual(spec.heats, [2, 1])

    def test_bracketed_dances_of_one_style_keep_that_style(self):
        spec, = parse_competition_schedule("Kids (SB, CC, JV) 2-1")
        self.assertEqual(spec.style, 'Latin')
        self.assertEqual(spec.dances, ['SA', 'CC', 'JI'])

    def test_the_whole_danceconvention_2026_plan(self):
        text = ("18:30  Jug A STD 2 -1\n"
                "\t   HGR S STD 2-1\n"
                "\t   SENI I S STD 2-1\n"
                "\t   SEN V S STD 2-1\n"
                "\t   J & J (LW; TG; CC; RB) VR ZR ER 24 - 12 - 6\n")
        specs = parse_competition_schedule(text)
        self.assertEqual([s.label for s in specs],
                         ['Jug A STD', 'HGR S STD', 'SENI I S STD',
                          'SEN V S STD', 'J & J'])


class CompetitionMatchesFileTest(unittest.TestCase):

    @staticmethod
    def _spec(line: str):
        specs = parse_competition_schedule(line)
        assert len(specs) == 1, specs
        return specs[0]

    def test_sen_mas_synonym(self):
        # SEN and MAS are the same (renamed) category.
        spec = self._spec("SEN I LAT 6-3-2-1")
        self.assertTrue(competition_matches_file(spec, Path("MAS_I_A_LAT.m3u")))
        self.assertTrue(competition_matches_file(spec, Path("SEN_I_LAT.m3u")))

    def test_level_is_whole_token(self):
        # 'SEN I' must never match 'SEN II'.
        spec = self._spec("SEN I LAT 6-3-2-1")
        self.assertFalse(competition_matches_file(spec, Path("SEN_II_LAT.m3u")))

    def test_style_must_match(self):
        spec = self._spec("SEN I LAT 6-3-2-1")
        self.assertFalse(competition_matches_file(spec, Path("SEN_I_STD.m3u")))

    def test_file_without_style_never_matches(self):
        spec = self._spec("SEN I LAT 6-3-2-1")
        self.assertFalse(competition_matches_file(spec, Path("LW_pre.m3u")))
        self.assertFalse(competition_matches_file(spec, Path("alle.m3u")))

    def test_a_named_class_takes_its_own_and_higher_classes(self):
        """Marcel: Jug A drew 'like last year' from Jug B/C/D lists. A class
        named in the line takes lists of that class and above (S > A > B > C > D);
        a list naming no class is open, danced at S, and WDSF counts as S."""
        spec = self._spec("Jug A STD 2-1")
        for name in ("LM_JUG_A_STD", "JUG_S_STD", "WDSF_YOUTH_STD", "Standard TEENS"):
            self.assertTrue(competition_matches_file(spec, Path(name + ".m3u")), name)
        for name in ("LM_JUG_B_STD", "LM_JUG_D_STD", "14 VR_JUG_C_B_JUNI_C_D_STD"):
            self.assertFalse(competition_matches_file(spec, Path(name + ".m3u")), name)
        hgr_s = self._spec("HGR S STD 2-1")
        self.assertFalse(competition_matches_file(hgr_s, Path("HGR_A_STD.m3u")))
        self.assertTrue(competition_matches_file(hgr_s, Path("HGR_STD.m3u")))

    def test_a_line_naming_no_class_takes_every_class(self):
        spec = self._spec("SEN I LAT 6-3-2-1")
        self.assertTrue(competition_matches_file(spec, Path("SEN_I_D_LAT.m3u")))


class KlToSimTest(unittest.TestCase):
    """Absolute KL→similarity calibration: _KL_FLOOR=5.5, _KL_SCALE=11.0."""

    def test_identical_gaussian_reads_100_percent(self):
        self.assertEqual(_kl_to_sim(0.0), 1.0)

    def test_different_recordings_capped_at_99(self):
        # At/below the floor the raw value clamps to 1.0, but any J above the
        # identical-threshold means a different recording → capped at 0.99.
        self.assertEqual(_kl_to_sim(5.5), 0.99)
        self.assertEqual(_kl_to_sim(1.0), 0.99)

    def test_monotonically_decreasing(self):
        sims = [_kl_to_sim(j) for j in (6.0, 8.0, 11.5, 20.0, 40.0)]
        self.assertEqual(sims, sorted(sims, reverse=True))

    def test_calibration_anchors(self):
        # Genuine same-dance sound-alikes (J≈6–8) should read clearly above the
        # 80% suggestion threshold; a pool-median J≈11.5 lands mid-range.
        self.assertGreater(_kl_to_sim(6.0), 0.90)
        self.assertGreater(_kl_to_sim(8.0), 0.79)
        self.assertAlmostEqual(_kl_to_sim(11.5), 0.58, delta=0.03)

    def test_large_divergence_near_zero(self):
        self.assertLess(_kl_to_sim(60.0), 0.01)
        self.assertGreaterEqual(_kl_to_sim(1000.0), 0.0)


class CleanTitleTest(unittest.TestCase):
    """_clean_title strips tempo/dance tags so display titles stay readable."""

    def test_strips_leading_tracknumber_and_code(self):
        self.assertEqual(_clean_title("01. LW Moon River"), "Moon River")

    def test_strips_parenthetical_tempo(self):
        self.assertEqual(_clean_title("Fiesta (Samba 50)"), "Fiesta")
        self.assertEqual(_clean_title("viennese waltz(58)"), "viennese waltz")

    def test_strips_pitch_suffixes(self):
        self.assertEqual(_clean_title("Besame Mucho_gepitched"), "Besame Mucho")


class VersionBaseKeysTest(unittest.TestCase):
    """A remix, cover or other version names the song it is a version of —
    only so it can be pointed out, its plays stay its own."""

    def test_a_remix_names_its_song(self):
        remix = version_base_keys(
            "Jasmine Thompson - Willow (DJ Maksy Viennese Waltz Remix) 58BPM.mp3")
        song = _song_title_keys("22-Jasmine Thompson _ Willow (Viennese Waltz 58).mp3")
        self.assertEqual(remix[0], song[0])
        self.assertIn("willow", version_base_keys("Willow [Salsa Remix]_cut.mp3"))
        self.assertIn("rolling in the deep", version_base_keys(
            "Adele - Rolling in the deep - rumba remix - (Dj Mitya)T24.mp3"))

    def test_an_ordinary_title_is_no_version(self):
        self.assertEqual(version_base_keys("2-02 Love Me Like You Do (Rb 24).mp3"), [])
        self.assertEqual(version_base_keys("Party Mix I.mp3"), [])

    def test_a_dance_word_is_no_song(self):
        self.assertNotIn("samba", version_base_keys("Samba - Danza Kuduro (New Mix).mp3"))


class CommentMarkerTest(unittest.TestCase):
    """The free markers of a COMM comment — everything that is not a class code.

    About 2800 of the 3855 library files carry one ('vocal_f' 892×, 'classic'
    651×, 'eintanzen' 102× …), so they are worth keeping; the same field also
    collects tempo digits, dance codes and converter provenance, which are not.
    """

    def test_the_markers_come_back_in_order(self):
        self.assertEqual(parse_comment_markers("B;A;S;vocal_f;classic"),
                         ["vocal_f", "classic"])

    def test_class_codes_and_instr_are_left_to_their_own_fields(self):
        self.assertEqual(parse_comment_markers("C;B;A;S;instr"), [])
        self.assertEqual(parse_comment_markers("D;instrumental"), [])

    def test_it_does_not_disturb_the_class_parse(self):
        classes, instr = _parse_class_tag("B;A;S;vocal_f;instr")
        self.assertEqual(classes, ["B", "A", "S"])
        self.assertTrue(instr)

    def test_multi_word_markers_survive_whole(self):
        self.assertEqual(
            parse_comment_markers("vocal_m;langes Vorspiel;kl break"),
            ["vocal_m", "langes vorspiel", "kl break"])

    def test_the_tempo_is_not_a_marker(self):
        # It is already in `bpm`; 'QS-50' is the same number wearing a code.
        self.assertEqual(parse_comment_markers("29;emotional"), ["emotional"])
        self.assertEqual(parse_comment_markers("QS-50;old"), ["old"])
        self.assertEqual(parse_comment_markers("30,5"), [])

    def test_a_bare_dance_code_is_not_a_marker(self):
        for code in ("rb", "WW", "Sb", "jv"):
            self.assertEqual(parse_comment_markers(code + ";classic"),
                             ["classic"])

    def test_converter_and_shop_provenance_is_dropped(self):
        for junk in ("converted by convert2mp3.net", "www.mediahuman.com",
                     "http://www.dvdvideosoft.com", "made with Suno",
                     "Erscheinungsdatum 11.2015"):
            self.assertEqual(parse_comment_markers(junk + ";practice"),
                             ["practice"])

    def test_a_release_date_or_an_artist_credit_is_dropped(self):
        """Seen in the real library (2026-08-24): the model was offered
        'erscheinungadatum 2016' and '1975 riccardo cocciante' as searchable
        tags. A typo must not smuggle a date past the filter, and a year with a
        name behind it is a credit, not a marker."""
        for junk in ("Erscheinungadatum 2016", "erscheinungsdatum 2025",
                     "1975 Riccardo Cocciante", "2016"):
            self.assertEqual(parse_comment_markers(junk + ";practice"),
                             ["practice"])

    def test_junk_that_runs_over_several_lines_is_dropped_whole(self):
        self.assertEqual(
            parse_comment_markers("erscheinungsdatum 2025\n1975 riccardo cocciante"),
            [])

    def test_the_itunes_gapless_blob_is_not_a_marker(self):
        """iTunes writes its gapless-playback data into the comment field."""
        blob = ("00000000 000002a0 00000768 00000000007eeb98 00000000"
                " 00730c38 00000000 00000000")
        self.assertEqual(parse_comment_markers(blob + ";classic"), ["classic"])

    def test_a_marker_that_only_looks_hexish_survives(self):
        # 'cafe' is all hex letters, but one word is not a blob.
        self.assertEqual(parse_comment_markers("cafe;chor"), ["cafe", "chor"])

    def test_a_repeat_is_only_listed_once(self):
        self.assertEqual(parse_comment_markers("vocal_f;vocal_f"), ["vocal_f"])

    def test_an_empty_comment_has_no_markers(self):
        self.assertEqual(parse_comment_markers(""), [])
        self.assertEqual(parse_comment_markers(";;"), [])


class _FakeScanCache:
    """A ScanCache reduced to the dict it is."""

    def __init__(self, data):
        self.data = dict(data)
        self.puts = 0

    def get(self, path):
        return dict(self.data)

    def put(self, path, data):
        self.data = dict(data)
        self.puts += 1


class CachedMarkerHealTest(unittest.TestCase):
    """Markers already in the scan cache were filtered by whatever the rules
    were on the day they were read. Re-filtering a cached list costs no ID3
    read, so a library scanned before today's rules must not keep handing the
    junk to the AI until someone rebuilds the cache."""

    def _entry(self, tags):
        from planner.library import MusicLibrary
        # Everything else already agrees with what the lazy heals would
        # derive, so any write-back is the marker one.
        cached = {"title": "Test", "dance": "WW", "bpm": None, "year": None,
                  "other_genre": None, "classes_ok": ["B", "A", "S"],
                  "comment_tags": tags, "is_instrumental": False,
                  "is_xmas": False, "tag_title": None, "tag_artist": "",
                  "tag_album": "", "duration": 180}
        cache = _FakeScanCache(cached)
        # Custom isn't mapped here, whatever the DB on this machine says, so
        # the row's missing custom value is not healed either.
        with mock.patch("planner.custom_field.source", return_value=None):
            entry = MusicLibrary()._make_entry(Path(r"C:\music\Test.mp3"), cache)
        return entry, cache

    def test_junk_left_in_the_cache_is_dropped_on_the_next_load(self):
        entry, cache = self._entry(["vocal_f", "erscheinungadatum 2016"])
        self.assertEqual(entry.comment_tags, ["vocal_f"])
        self.assertEqual(cache.data["comment_tags"], ["vocal_f"])

    def test_the_cleaned_list_is_written_back_once(self):
        _, cache = self._entry(["1975 riccardo cocciante"])
        self.assertEqual(cache.data["comment_tags"], [])
        self.assertEqual(cache.puts, 1)

    def test_a_clean_cache_is_not_rewritten(self):
        _, cache = self._entry(["vocal_f", "classic"])
        self.assertEqual(cache.puts, 0)

    def test_a_track_with_no_markers_is_left_alone(self):
        _, cache = self._entry([])
        self.assertEqual(cache.puts, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
