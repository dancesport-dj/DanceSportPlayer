"""Tests for the pure helpers behind the playing-mode desk features: the
audible-play-length arithmetic, the spoken next-dance announcement and the
recorded clips it is made from."""
import random
import tempfile
import unittest
from pathlib import Path

from player import announce
from shared.playback import audible_played_secs
from player.announce import (DanceAnnouncer, announce_clips, announce_parts,
                          announce_text, clip_bounds, clip_genders,
                          clip_language, parse_bounds, pick_clip_gender)
from planner import i18n, terms
from player.main_pause import PauseMusicMixin
from gui.running_order import Row, RunningOrder


class AudiblePlayedSecsTest(unittest.TestCase):

    def test_plain_position_is_identity(self):
        self.assertAlmostEqual(audible_played_secs(45_000, 0, 1.0), 45.0)

    def test_skipped_intro_does_not_count_as_played(self):
        # 8 s of leading silence were jumped over: at file position 1:53 the
        # floor has heard exactly the 1:45 of music the play length promises.
        self.assertAlmostEqual(audible_played_secs(113_000, 8_000, 1.0), 105.0)

    def test_tempo_rate_stretches_file_time(self):
        # At +16 % the file runs faster than the clock, so 105 wall-clock
        # seconds of dancing cost 121.8 s of track.
        self.assertAlmostEqual(audible_played_secs(121_800, 0, 1.16), 105.0,
                               places=3)

    def test_offset_and_rate_combine(self):
        self.assertAlmostEqual(
            audible_played_secs(121_800 + 8_000, 8_000, 1.16), 105.0, places=3)

    def test_position_before_offset_is_zero_not_negative(self):
        self.assertEqual(audible_played_secs(3_000, 8_000, 1.0), 0.0)

    def test_zero_rate_does_not_divide_by_zero(self):
        # A rate of 0 is never a real playback rate — treat it as normal speed
        # rather than blowing up or returning an absurd number.
        self.assertAlmostEqual(audible_played_secs(1_000, 0, 0.0), 1.0)

    def test_none_rate_is_treated_as_normal_speed(self):
        self.assertAlmostEqual(audible_played_secs(30_000, 0, None), 30.0)


class _HallLanguage(unittest.TestCase):
    """Restores the screen language and the German-terms switch."""

    def setUp(self):
        real_lang, real_terms = i18n.active_language(), terms._english_terms
        self.addCleanup(i18n.set_active, real_lang)
        self.addCleanup(setattr, terms, "_english_terms", real_terms)
        self.addCleanup(setattr, terms, "_german_kept", terms._german_kept)

    def hall(self, lang, german_terms=False):
        i18n.set_active(lang)
        terms.apply_settings({"german_dance_terms": german_terms})


class AnnounceTextTest(_HallLanguage):

    def setUp(self):
        super().setUp()
        self.hall("de")

    def test_german_dance_name(self):
        self.assertEqual(announce_text("LW"), "Nächster Tanz: Langsamer Walzer")

    def test_lowercase_code_is_accepted(self):
        self.assertEqual(announce_text("rb"), "Nächster Tanz: Ruhmba")

    def test_names_are_spelled_the_way_a_german_voice_reads_them(self):
        # Not how the dance is written — how it has to be written to come out
        # right. The voice spelled 'Chachacha' letter by letter.
        self.assertEqual(announce_text("SF"), "Nächster Tanz: Slowfox")
        self.assertEqual(announce_text("QS"), "Nächster Tanz: Quickstep")
        self.assertEqual(announce_text("JI"), "Nächster Tanz: Jive")
        self.assertEqual(announce_text("CC"), "Nächster Tanz: Tscha Tscha")

    def test_every_fragment_is_spoken_german(self):
        # One voice on the microphone, foreign dance names included.
        self.assertEqual(announce_parts("JI"),
                         [("Nächster Tanz:", "de"), ("Jive", "de")])
        self.assertEqual(announce_parts("LW"),
                         [("Nächster Tanz:", "de"), ("Langsamer Walzer", "de")])

    def test_the_takt_is_a_fragment_of_its_own(self):
        self.assertEqual(announce_parts("PD", 60),
                         [("Nächster Tanz:", "de"), ("Paso doble", "de"),
                          ("60 Takte", "de")])

    def test_over_the_music_drops_the_framing(self):
        self.assertEqual(announce_parts("WW", now=True),
                         [("Wiener Walzer", "de")])

    def test_takt_suffix_only_when_asked(self):
        self.assertEqual(announce_text("WW", 60), "Nächster Tanz: Wiener Walzer, 60 Takte")
        self.assertEqual(announce_text("WW"), "Nächster Tanz: Wiener Walzer")
        self.assertEqual(announce_text("WW", 0), "Nächster Tanz: Wiener Walzer")

    def test_the_heat_is_a_fragment_of_its_own(self):
        self.assertEqual(announce_parts("LW", heat=3),
                         [("Nächster Tanz:", "de"), ("Langsamer Walzer", "de"),
                          ("Heat 3", "de")])

    def test_the_heat_comes_before_the_takt(self):
        # The floor is waiting for the heat; the takt is the trailing extra.
        self.assertEqual(announce_text("LW", 29, heat=2),
                         "Nächster Tanz: Langsamer Walzer, Heat 2, 29 Takte")

    def test_heat_suffix_only_when_asked(self):
        self.assertEqual(announce_text("WW"), "Nächster Tanz: Wiener Walzer")
        self.assertEqual(announce_text("WW", heat=0), "Nächster Tanz: Wiener Walzer")

    def test_unknown_code_falls_back_to_the_code(self):
        self.assertEqual(announce_text("XX"), "Nächster Tanz: XX")

    def test_missing_code_still_says_something(self):
        self.assertEqual(announce_text(""), "Nächster Tanz: Tanz")


class EnglishAnnounceTextTest(_HallLanguage):
    """An English hall hears the synthesiser in English, as long as nobody
    asked for the German dance terms."""

    def test_an_english_hall_hears_an_english_sentence(self):
        self.hall("en")
        self.assertEqual(announce_text("LW", 29, heat=2),
                         "Next dance: Slow Waltz, Heat 2, 29 bars")

    def test_every_fragment_is_spoken_english(self):
        self.hall("en")
        self.assertEqual(announce_parts("JI", heat=3),
                         [("Next dance:", "en"), ("Jive", "en"), ("Heat 3", "en")])

    def test_english_names_are_written_plainly(self):
        # The German respellings ("Tscha Tscha", "Ruhmba") are for a German voice.
        self.hall("en")
        self.assertEqual(announce_parts("CC", now=True), [("ChaCha", "en")])
        self.assertEqual(announce_parts("RB", now=True), [("Rumba", "en")])
        self.assertEqual(announce_parts("FORRO", now=True), [("Forro", "en")])

    def test_missing_code_still_says_something_in_english(self):
        self.hall("en")
        self.assertEqual(announce_text(""), "Next dance: Dance")

    def test_the_german_dance_terms_keep_the_synthesiser_german(self):
        self.hall("en", german_terms=True)
        self.assertEqual(announce_text("LW"), "Nächster Tanz: Langsamer Walzer")


class AnnounceClipsTest(_HallLanguage):
    """The recorded announcement: which voice reads it and which files play."""

    def setUp(self):
        super().setUp()
        self.hall("de")
        self.root = Path(tempfile.mkdtemp(prefix="dp_announcements_"))
        for gender in ("female", "male"):
            folder = self.root / "german" / gender
            folder.mkdir(parents=True)
            for name in ("next_dance", "LW", "SL", "SB", "JV",
                         "heat", "1", "2", "3"):
                (folder / f"{name}.mp3").write_bytes(b"")

    def names(self, *args, **kw):
        return [p.name for p in announce_clips(*args, root=self.root, **kw)]

    def test_the_lead_in_plays_before_the_dance(self):
        self.assertEqual(self.names("LW", "female"),
                         ["next_dance.mp3", "LW.mp3"])

    def test_over_the_music_the_dance_is_already_running(self):
        # "Nächster Tanz" would be a lie over the first bars — same rule the
        # spoken sentence follows.
        self.assertEqual(self.names("LW", "female", now=True), ["LW.mp3"])

    def test_the_voice_picks_the_folder(self):
        self.assertEqual(announce_clips("LW", "male", root=self.root)[0].parent.name,
                         "male")

    def test_a_spelled_out_social_dance_finds_its_short_clip(self):
        self.assertEqual(self.names("SALSA", "female")[-1], "SL.mp3")

    def test_samba_and_jive_play_the_clips_named_like_the_desk(self):
        # The planner's codes are SA and JI, the desk shows SB and JV.
        self.assertEqual(self.names("SA", "female")[-1], "SB.mp3")
        self.assertEqual(self.names("JI", "male")[-1], "JV.mp3")

    def test_lowercase_code_is_accepted(self):
        self.assertEqual(self.names("lw", "female")[-1], "LW.mp3")

    def test_a_dance_never_recorded_leaves_it_to_the_synthesiser(self):
        self.assertEqual(self.names("QS", "female"), [])

    def test_a_voice_never_recorded_leaves_it_to_the_synthesiser(self):
        self.assertEqual(self.names("LW", "child"), [])

    def test_without_a_lead_in_the_dance_is_named_alone(self):
        (self.root / "german" / "female" / "next_dance.mp3").unlink()
        self.assertEqual(self.names("LW", "female"), ["LW.mp3"])

    def test_the_heat_is_called_after_the_dance(self):
        self.assertEqual(self.names("LW", "female", heat=3),
                         ["next_dance.mp3", "LW.mp3", "heat.mp3", "3.mp3"])

    def test_over_the_music_the_heat_still_follows_the_dance(self):
        self.assertEqual(self.names("LW", "female", now=True, heat=2),
                         ["LW.mp3", "heat.mp3", "2.mp3"])

    def test_no_heat_asked_for_means_no_heat_called(self):
        self.assertEqual(self.names("LW", "female"),
                         ["next_dance.mp3", "LW.mp3"])

    def test_a_heat_beyond_the_recorded_numbers_keeps_the_dance(self):
        # Only 1-8 were recorded. Calling "Heat" into nothing would be worse
        # than leaving the number out.
        self.assertEqual(self.names("LW", "female", heat=9),
                         ["next_dance.mp3", "LW.mp3"])

    def test_without_a_heat_clip_the_number_is_dropped_too(self):
        (self.root / "german" / "female" / "heat.mp3").unlink()
        self.assertEqual(self.names("LW", "female", heat=3),
                         ["next_dance.mp3", "LW.mp3"])

    def test_installed_voices_are_the_folders_that_are_there(self):
        self.assertEqual(clip_genders(self.root), ("female", "male"))
        (self.root / "german" / "male").rename(self.root / "german" / "kid")
        self.assertEqual(clip_genders(self.root), ("female",))

    def test_nothing_installed_at_all(self):
        self.assertEqual(clip_genders(self.root / "nope"), ())


class BilingualClipsTest(unittest.TestCase):
    """One clip folder per language. German was recorded first and stands in
    for every clip another language does not have yet."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dp_announcements_"))
        for name in ("next_dance", "LW", "TG", "heat", "3"):
            self.clip("german", name)
        for name in ("LW", "heat"):
            self.clip("english", name)

    def clip(self, language, name, gender="female"):
        folder = self.root / language / gender
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{name}.mp3").write_bytes(b"")

    def played(self, *args, **kw):
        return [f"{p.parent.parent.name}/{p.name}"
                for p in announce_clips(*args, root=self.root, **kw)]

    def test_an_english_clip_wins_over_the_german_one(self):
        self.assertEqual(self.played("LW", "female", now=True, language="english"),
                         ["english/LW.mp3"])

    def test_a_clip_english_lacks_comes_from_german(self):
        self.assertEqual(self.played("TG", "female", language="english"),
                         ["german/next_dance.mp3", "german/TG.mp3"])

    def test_the_fallback_is_per_clip(self):
        self.assertEqual(self.played("LW", "female", heat=3, language="english"),
                         ["german/next_dance.mp3", "english/LW.mp3",
                          "english/heat.mp3", "german/3.mp3"])

    def test_german_never_reaches_into_the_english_folder(self):
        self.assertEqual(self.played("LW", "female", now=True, language="german"),
                         ["german/LW.mp3"])

    def test_a_voice_recorded_in_english_only_is_installed_for_english(self):
        self.clip("english", "LW", gender="male")
        self.assertEqual(clip_genders(self.root, language="english"),
                         ("female", "male"))
        self.assertEqual(clip_genders(self.root, language="german"), ("female",))

    def test_a_voice_with_no_english_clips_speaks_its_german_ones(self):
        # The Windows voice is no stand-in any more (Marcel: "it is really
        # bad"): a recorded German clip beats a synthesised English one.
        self.clip("german", "LW", gender="male")
        self.assertEqual(clip_genders(self.root, language="english"),
                         ("female", "male"))
        self.assertEqual(self.played("LW", "male", now=True, language="english"),
                         ["german/LW.mp3"])

    def test_no_english_clips_at_all_play_the_german_set(self):
        root = Path(tempfile.mkdtemp(prefix="dp_announcements_"))
        (root / "german" / "female").mkdir(parents=True)
        (root / "german" / "female" / "LW.mp3").write_bytes(b"")
        (root / "english").mkdir()
        (root / "english" / "README.md").write_text("no clips yet")
        self.assertEqual(clip_genders(root, language="english"), ("female",))
        self.assertEqual([p.parent.parent.name for p in
                          announce_clips("LW", "female", root=root,
                                         language="english")], ["german"])


class ClipLanguageTest(unittest.TestCase):
    """Which language the clips are taken from: the one the screen names the
    dances in (planner.terms)."""

    def setUp(self):
        real_lang, real_terms = i18n.active_language(), terms._english_terms
        self.addCleanup(i18n.set_active, real_lang)
        self.addCleanup(setattr, terms, "_english_terms", real_terms)
        self.addCleanup(setattr, terms, "_german_kept", terms._german_kept)

    def test_an_english_screen_announces_in_english(self):
        i18n.set_active("en")
        terms.apply_settings({})
        self.assertEqual(clip_language(), "english")

    def test_the_german_dance_terms_switch_keeps_the_announcement_german(self):
        i18n.set_active("en")
        terms.apply_settings({"german_dance_terms": True})
        self.assertEqual(clip_language(), "german")

    def test_a_german_screen_announces_in_german(self):
        i18n.set_active("de")
        terms.apply_settings({})
        self.assertEqual(clip_language(), "german")


class _Deck:
    """Just enough of a PlaylistTable for the heat lookup: the row metas and
    which ─── strip each row hangs under."""

    def __init__(self, metas, headers=None):
        self._row_meta = RunningOrder(metas)
        self._row_round_hdr = dict(headers or {})
        self._current_play_row = -1


class _Panel:
    def __init__(self, on=True):
        self._on = on

    def announce_heat(self):
        return self._on


class HeatOfRowTest(unittest.TestCase):
    """Which heat the announcement calls. A generated grid states it; every
    other list — a running order, a party set, an imported .m3u — has it read
    off the order of the rows."""

    def setUp(self):
        self.win = PauseMusicMixin()
        self.win._play_panel = _Panel()

    def flat(self, dances, headers=None):
        return _Deck([Row(dance=d) for d in dances], headers)

    def test_a_generated_grid_states_its_own_heat(self):
        deck = _Deck([Row(dance="SA", round_name="Vorrunde", h_idx=2)])
        self.assertEqual(self.win._heat_of(deck, 0), 3)

    def test_three_sambas_in_a_row_are_heats_one_two_three(self):
        deck = self.flat(["SA", "SA", "SA"])
        self.assertEqual([self.win._heat_of(deck, r) for r in range(3)],
                         [1, 2, 3])

    def test_each_dance_counts_its_own_heats(self):
        # A Vorrunde runs LW SA LW SA — two heats of each, not four of one.
        deck = self.flat(["LW", "SA", "LW", "SA"])
        self.assertEqual([self.win._heat_of(deck, r) for r in range(4)],
                         [1, 1, 2, 2])

    def test_the_next_round_starts_counting_again(self):
        # Rows 0-1 hang under the Vorrunde strip, rows 2-3 under the Finale's.
        deck = self.flat(["SA", "SA", "SA", "SA"],
                         {0: 0, 1: 0, 2: 5, 3: 5})
        self.assertEqual([self.win._heat_of(deck, r) for r in range(4)],
                         [1, 2, 1, 2])

    def test_a_row_with_no_dance_has_no_heat(self):
        self.assertIsNone(self.win._heat_of(self.flat([""]), 0))

    def test_a_strip_row_has_no_heat(self):
        self.assertIsNone(self.win._heat_of(_Deck([None]), 0))

    def test_nothing_is_called_when_the_operator_didnt_ask(self):
        self.win._play_panel = _Panel(on=False)
        self.assertIsNone(self.win._heat_of(self.flat(["SA"]), 0))

    def test_no_deck_and_no_row_are_survived(self):
        self.assertIsNone(self.win._heat_of(None, -1))
        self.assertIsNone(self.win._heat_of(self.flat(["SA"]), 7))


class ClipTrimTest(unittest.TestCase):
    """Where a clip's spoken word really starts and ends (parse_bounds), so the
    announcement doesn't sit through the studio silence around every fragment."""

    def bounds(self, duration: str, *spans):
        text = f"  Duration: {duration}\n" + "".join(
            f"[silencedetect] silence_start: {s}\n"
            + (f"[silencedetect] silence_end: {e} | silence_duration: 1\n"
               if e is not None else "")
            for s, e in spans)
        return parse_bounds(text)

    def test_the_silence_around_the_word_is_cut_off(self):
        # 0.0-0.4 silence, word, 1.5-2.0 silence. ±30 ms of padding kept.
        self.assertEqual(self.bounds("00:00:02.00", (0.0, 0.4), (1.5, 2.0)),
                         (370, 1530))

    def test_a_clip_that_ends_silent_is_still_cut(self):
        # ffmpeg leaves the last silence_start unclosed on such a file.
        self.assertEqual(self.bounds("00:00:02.00", (1.5, None)), (0, 1530))

    def test_a_pause_inside_the_word_is_left_alone(self):
        # "West Coast Swing" breathes in the middle — that is the announcement.
        self.assertEqual(self.bounds("00:00:02.00", (0.8, 0.9)), (0, 2000))

    def test_a_clip_with_no_silence_plays_whole(self):
        self.assertEqual(self.bounds("00:00:01.00"), (0, 1000))

    def test_a_probe_that_found_only_silence_plays_the_clip_whole(self):
        # Better a slow announcement than a clipped one.
        self.assertEqual(self.bounds("00:00:02.00", (0.0, 1.95)), (0, 2000))

    def test_output_without_a_duration_is_no_answer_at_all(self):
        self.assertIsNone(parse_bounds("[silencedetect] silence_start: 0.0\n"))
        self.assertIsNone(parse_bounds(""))

    def test_an_unprobed_clip_plays_whole(self):
        self.assertEqual(clip_bounds(Path("never-measured.mp3")), (0, None))


class PickClipGenderTest(unittest.TestCase):

    def test_the_asked_for_voice_wins(self):
        self.assertEqual(pick_clip_gender("male", ("female", "male")), "male")

    def test_mixed_draws_one_of_them_to_start_with(self):
        random.seed(0)
        drawn = {pick_clip_gender("random", ("female", "male"))
                 for _ in range(30)}
        self.assertEqual(drawn, {"female", "male"})

    def test_mixed_takes_the_other_voice_next(self):
        self.assertEqual(
            pick_clip_gender("random", ("female", "male"), "female"), "male")
        self.assertEqual(
            pick_clip_gender("random", ("female", "male"), "male"), "female")

    def test_mixed_with_one_voice_installed_keeps_using_it(self):
        self.assertEqual(
            pick_clip_gender("random", ("female",), "female"), "female")

    def test_a_voice_that_was_never_recorded_takes_what_is_there(self):
        # The wrong gender still beats the robot.
        self.assertEqual(pick_clip_gender("male", ("female",)), "female")

    def test_nothing_recorded_means_nothing_to_pick(self):
        self.assertIsNone(pick_clip_gender("female", ()))
        self.assertIsNone(pick_clip_gender("female", None))


class _ClipRunBase(_HallLanguage):
    """An announcer with two recorded clips and no Qt player behind it."""

    def setUp(self):
        super().setUp()
        self.hall("de")
        root = Path(tempfile.mkdtemp(prefix="dp_announcements_"))
        (root / "german" / "female").mkdir(parents=True)
        for name in ("next_dance", "LW"):
            (root / "german" / "female" / f"{name}.mp3").write_bytes(b"")
        self._real_dir = announce._CLIP_DIR
        announce._CLIP_DIR = root
        self.addCleanup(setattr, announce, "_CLIP_DIR", self._real_dir)

        self.ducked = []
        self.played = []
        self.ann = DanceAnnouncer(on_speaking=self.ducked.append)
        self.ann._clip_engine = lambda: object()   # no real player in a test
        self.ann._start_clip = self._start_clip
        # The media statuses, standing in for QMediaPlayer.MediaStatus.
        self.ann._clip_end = "end"
        self.ann._clip_loaded = "loaded"
        self.ann._clip_ready = ("loaded", "buffered")

    def _start_clip(self, path):
        """What the real one does, minus the Qt player: a fresh token and a
        fragment that has not ended yet."""
        self.played.append(path.name)
        self.ann._token += 1
        self.ann._clip_seeked = False
        self.ann._clip_over = False
        self.ann._clip_playing = False

class AnnouncerClipRunTest(_ClipRunBase):
    """How the clips are played one after another, and what the music does
    around them — what matters here is that the duck spans the WHOLE
    announcement, gap included."""

    def test_the_lead_in_plays_first_and_the_music_ducks_with_it(self):
        self.assertTrue(self.ann.speak("LW"))
        self.assertEqual(self.played, ["next_dance.mp3"])
        self.assertEqual(self.ducked, [True])

    def test_the_dance_follows_and_only_then_does_the_music_come_back(self):
        self.ann.speak("LW")
        self.ann._on_clip_status("end")          # lead-in over
        self.assertEqual(self.ducked, [True])    # the gap is not a way out
        self.ann._next_clip(self.ann._token)     # …after the gap
        self.assertEqual(self.played, ["next_dance.mp3", "LW.mp3"])
        self.ann._on_clip_status("end")          # dance over
        self.assertEqual(self.ducked, [True, False])

    def test_a_repeated_end_does_not_eat_the_next_fragment(self):
        # The backend reports the end twice (a stray status, or the end of a
        # clip that was already cut short). Acting on the repeat would pull the
        # dance out of the queue unheard and leave "Nächster Tanz…" alone.
        self.ann.speak("LW")
        self.ann._on_clip_status("end")
        self.ann._on_clip_status("end")
        self.ann._next_clip(self.ann._token)
        self.assertEqual(self.played, ["next_dance.mp3", "LW.mp3"])

    def test_a_tail_cut_left_over_from_the_last_fragment_is_ignored(self):
        # The cut is armed per fragment; one arriving late must not end the one
        # that is playing NOW.
        self.ann.speak("LW")
        stale = self.ann._token
        self.ann._on_clip_status("end")
        self.ann._next_clip(self.ann._token)
        self.ann._cut_tail(stale, True)
        self.assertEqual(self.ducked, [True])

    def test_a_dance_never_recorded_is_not_read_by_the_synthesiser(self):
        # Only the takt still goes to the Windows voice; a dance without a
        # clip is left unannounced rather than read by it.
        said = []

        class _Tts:
            def say(self, text):
                said.append(text)

            def setLocale(self, _loc):
                pass

            def setVoice(self, _voice):
                pass

        self.ann._engine = lambda: _Tts()
        self.ann._tts = _Tts()
        self.assertFalse(self.ann.speak("QS"))
        self.assertEqual((said, self.played, self.ducked), ([], [], []))

    def test_a_stop_mid_announcement_drops_what_is_left(self):
        self.ann.speak("LW")
        token = self.ann._token
        self.ann.stop()
        self.assertEqual(self.ducked, [True, False])
        self.ann._next_clip(token)               # the gap timer, arriving late
        self.assertEqual(self.played, ["next_dance.mp3"])

    def test_the_watchdog_silences_what_it_gives_up_on(self):
        """A voice the engine never reported finished may still come — late,
        over the music that has just come back up. Giving up stops it."""
        stopped = []

        class _Engine:
            def __init__(self, name):
                self.name = name

            def stop(self):
                stopped.append(self.name)
        self.ann._clip_player = _Engine("clip")
        self.ann._tts = _Engine("tts")
        self.ann.speak("LW")
        token = self.ann._token
        self.ann._give_up(token)
        self.assertEqual(self.ducked, [True, False])
        self.assertEqual(sorted(stopped), ["clip", "tts"])
        self.assertNotEqual(self.ann._token, token,
                            "a gap or tail-cut timer still out is void")

    def test_a_clip_that_never_plays_lets_the_music_back_up(self):
        self.ann.speak("LW")
        self.ann._on_clip_error("ResourceError", "no such file")
        self.assertEqual(self.ducked, [True, False])

    def test_over_the_music_there_is_only_the_dance(self):
        self.ann.speak("LW", now=True)
        self.ann._on_clip_status("end")
        self.assertEqual(self.played, ["LW.mp3"])
        self.assertEqual(self.ducked, [True, False])

    def test_a_mixed_evening_alternates_the_voices(self):
        male = announce._CLIP_DIR / "german" / "male"
        male.mkdir()
        for name in ("next_dance", "LW"):
            (male / f"{name}.mp3").write_bytes(b"")
        self.ann.set_voice("random")
        voices = [self.ann._clips_for("LW", False)[0].parent.name
                  for _ in range(4)]
        self.assertEqual(voices[0::2], [voices[0]] * 2)   # she, he, she, he
        self.assertNotEqual(voices[0], voices[1])
        self.assertEqual(set(voices), {"female", "male"})

    def test_the_voice_can_be_changed_while_the_app_runs(self):
        self.ann.set_voice("male")               # nothing recorded for him
        self.assertEqual(self.ann._voice_mode, "male")
        self.ann.speak("LW")                     # falls back to the female clips
        self.assertEqual(self.played, ["next_dance.mp3"])


class AnnouncerClipEndTest(_ClipRunBase):
    """When a fragment counts as over.

    EndOfMedia is not the only way a clip ends. The Windows backend the app
    runs on never sends it for a clip that plays to its own end: it drops back
    to LoadedMedia instead. Measured on the real thing, an unmeasured clip left
    the music ducked for the full 8 s watchdog and swallowed every fragment
    after it — the first announcement of each voice in a session, every one of
    them where there is no ffmpeg to measure with.
    """

    def _play_through(self):
        """Load, buffer, and reach the end of the file the Windows way."""
        self.ann._on_clip_status("loaded")
        self.ann._on_clip_status("buffered")
        self.ann._on_clip_status("loaded")

    def test_falling_back_to_loaded_ends_the_fragment(self):
        self.ann.speak("LW", now=True)
        self._play_through()
        self.assertEqual(self.ducked, [True, False])

    def test_the_fragments_after_it_are_still_spoken(self):
        self.ann.speak("LW")                     # lead-in + dance
        self._play_through()
        self.assertEqual(self.ducked, [True])    # the gap is not a way out
        self.ann._next_clip(self.ann._token)
        self.assertEqual(self.played, ["next_dance.mp3", "LW.mp3"])
        self._play_through()
        self.assertEqual(self.ducked, [True, False])

    def test_the_loaded_a_clip_STARTS_in_is_not_an_end(self):
        # Every clip reports LoadedMedia on the way in, and some backends
        # report it twice (source set, then media opened). Ending there would
        # cut the word before it was ever heard.
        self.ann.speak("LW", now=True)
        self.ann._on_clip_status("loaded")
        self.ann._on_clip_status("loaded")
        self.assertEqual(self.ducked, [True])

    def test_end_of_media_still_ends_it(self):
        # The other backends (ffmpeg, macOS, Linux) do send it.
        self.ann.speak("LW", now=True)
        self.ann._on_clip_status("loaded")
        self.ann._on_clip_status("buffered")
        self.ann._on_clip_status("end")
        self.assertEqual(self.ducked, [True, False])

    def test_a_late_loaded_after_a_cut_tail_changes_nothing(self):
        # A measured clip is stopped by the tail cut; the LoadedMedia that the
        # stop itself produces must not pull the NEXT fragment out unheard.
        self.ann.speak("LW")
        self.ann._on_clip_status("loaded")
        self.ann._on_clip_status("buffered")
        self.ann._clip_done(self.ann._token)     # the tail cut
        self.ann._on_clip_status("loaded")
        self.ann._next_clip(self.ann._token)
        self.assertEqual(self.played, ["next_dance.mp3", "LW.mp3"])


if __name__ == "__main__":
    unittest.main()
