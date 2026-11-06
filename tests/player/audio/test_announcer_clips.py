#!/usr/bin/env python3
"""🔈 The announcer's clip run, driven by hand: no sound card, no ffmpeg.

Run:  py -m unittest tests.player.audio.test_announcer_clips -v

The player, the timer and the text-to-speech engine are fakes, so each status
the media backend can report, each timer that can fire late and each way the
engine can fail is a plain call here.
"""
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtCore import QLocale, QUrl

from player.audio import announce
from player.audio.announce import DanceAnnouncer

LOADED, BUFFERED, END, OTHER = "loaded", "buffered", "end", "stalled"


class FakeTimer:
    calls = []

    @staticmethod
    def singleShot(ms, fn):
        FakeTimer.calls.append((ms, fn))


class FakePlayer:
    def __init__(self):
        self.pos = 0
        self.sources = []
        self.played = 0
        self.stopped = 0
        self.seeks = []

    def position(self):
        return self.pos

    def setPosition(self, ms):
        self.seeks.append(ms)

    def setSource(self, url):
        self.sources.append(url.toLocalFile())

    def play(self):
        self.played += 1

    def stop(self):
        self.stopped += 1


class ClipRunTest(unittest.TestCase):
    def setUp(self):
        FakeTimer.calls = []
        patcher = mock.patch.object(announce, "QTimer", FakeTimer)
        patcher.start()
        self.addCleanup(patcher.stop)
        bounds = mock.patch.dict(announce._BOUNDS, clear=True)
        bounds.start()
        self.addCleanup(bounds.stop)
        self.ducks = []
        self.a = DanceAnnouncer(on_speaking=self.ducks.append)
        self.player = FakePlayer()
        self.a._clip_player = self.player
        self.a._clip_end, self.a._clip_loaded = END, LOADED
        self.a._clip_ready = (LOADED, BUFFERED)

    def fire(self, index=-1):
        FakeTimer.calls[index][1]()

    def startClip(self, name="a.mp3", start=0, stop=None):
        path = Path("C:/clips") / name
        if start or stop:
            announce._BOUNDS[str(path)] = (start, stop)
        self.a._start_clip(path)
        return path

    # ── starting a clip ──────────────────────────────────────────────────────
    def test_a_clip_is_loaded_played_and_watched(self):
        path = self.startClip()
        self.assertEqual(self.player.sources, [QUrl.fromLocalFile(str(path)).toLocalFile()])
        self.assertEqual(self.player.played, 1)
        self.assertEqual(FakeTimer.calls[0][0], announce._WATCHDOG_MS)

    def test_without_a_player_the_watchdog_is_left_to_give_up(self):
        self.a._clip_player = None
        self.startClip()
        self.assertEqual(len(FakeTimer.calls), 1)
        self.assertEqual(self.player.played, 0)

    def test_a_measured_clip_remembers_where_its_word_is(self):
        self.startClip(start=120, stop=900)
        self.assertEqual((self.a._clip_start_ms, self.a._clip_stop_ms), (120, 900))
        self.assertFalse(self.a._clip_seeked or self.a._clip_over or self.a._clip_playing)

    # ── what the media backend reports ───────────────────────────────────────
    def test_the_first_ready_status_skips_the_silence_and_arms_the_tail_cut(self):
        self.startClip(start=120, stop=900)
        self.a._on_clip_status(LOADED)
        self.assertEqual(self.player.seeks, [120])
        self.assertEqual(FakeTimer.calls[-1][0], 780)
        self.assertFalse(self.a._clip_playing)

    def test_a_buffered_first_status_means_the_word_is_running(self):
        self.startClip()
        self.a._on_clip_status(BUFFERED)
        self.assertTrue(self.a._clip_playing)
        self.assertEqual(self.player.seeks, [])

    def test_a_repeated_ready_status_does_not_seek_again(self):
        self.startClip(start=120, stop=900)
        self.a._on_clip_status(LOADED)
        self.a._on_clip_status(LOADED)
        self.assertEqual(self.player.seeks, [120])

    def test_loaded_after_playing_is_the_end_of_an_unmeasured_clip(self):
        """WMF falls back to LoadedMedia instead of EndOfMedia at a clip's end."""
        self.a._set_speaking(True)
        self.startClip()
        self.a._on_clip_status(BUFFERED)
        self.a._on_clip_status(BUFFERED)
        self.assertTrue(self.a.speaking)
        self.a._on_clip_status(LOADED)
        self.assertTrue(self.a._clip_over)
        self.assertFalse(self.a.speaking)

    def test_loaded_again_before_playing_is_ignored(self):
        self.a._set_speaking(True)
        self.startClip()
        self.a._on_clip_status(LOADED)
        self.a._on_clip_status(LOADED)
        self.assertFalse(self.a._clip_over)

    def test_end_of_media_finishes_the_clip_once(self):
        self.a._set_speaking(True)
        self.startClip()
        self.a._on_clip_status(END)
        self.a._on_clip_status(END)
        self.assertEqual(self.ducks, [True, False])

    def test_another_status_is_not_acted_on(self):
        self.startClip()
        self.a._on_clip_status(OTHER)
        self.assertFalse(self.a._clip_over or self.a._clip_seeked)

    # ── cutting the tail ─────────────────────────────────────────────────────
    def test_the_tail_cut_stops_the_player_at_the_end_of_the_word(self):
        self.a._set_speaking(True)
        self.startClip(start=0, stop=900)
        self.a._on_clip_status(BUFFERED)
        self.player.pos = 890
        self.fire()
        self.assertEqual(self.player.stopped, 1)
        self.assertFalse(self.a.speaking)

    def test_a_slow_start_gets_one_more_look_at_where_the_player_is(self):
        self.startClip(start=0, stop=900)
        self.a._on_clip_status(BUFFERED)
        self.player.pos = 100
        before = len(FakeTimer.calls)
        self.fire()
        self.assertEqual(len(FakeTimer.calls), before + 1)
        self.assertEqual(FakeTimer.calls[-1][0], 800)
        self.assertEqual(self.player.stopped, 0)
        self.fire()      # the re-check cuts whatever the position says
        self.assertEqual(self.player.stopped, 1)

    def test_a_tail_cut_of_an_older_clip_does_nothing(self):
        self.startClip(start=0, stop=900)
        self.a._on_clip_status(BUFFERED)
        self.a._token += 1
        self.fire()
        self.assertEqual(self.player.stopped, 0)

    def test_a_tail_cut_after_the_clip_is_over_does_nothing(self):
        self.startClip(start=0, stop=900)
        self.a._on_clip_status(BUFFERED)
        self.a._clip_over = True
        self.fire()
        self.assertEqual(self.player.stopped, 0)

    def test_a_tail_cut_without_a_player_does_nothing(self):
        self.startClip(start=0, stop=900)
        self.a._on_clip_status(BUFFERED)
        self.a._clip_player = None
        self.fire()
        self.assertEqual(self.player.stopped, 0)

    # ── the queue ────────────────────────────────────────────────────────────
    def test_the_next_fragment_follows_after_the_gap(self):
        self.a._clip_queue = [Path("C:/clips/b.mp3")]
        self.startClip()
        self.a._on_clip_status(END)
        ms, _fn = FakeTimer.calls[-1]
        self.assertEqual(ms, announce._CLIP_GAP_MS)
        self.fire()
        self.assertEqual(self.player.played, 2)
        self.assertEqual(self.a._clip_queue, [])

    def test_a_queue_for_an_older_token_is_not_played(self):
        self.a._clip_queue = [Path("C:/clips/b.mp3")]
        self.startClip()
        self.a._next_clip(self.a._token - 1)
        self.assertEqual(self.player.played, 1)
        self.a._clip_queue = []
        self.a._next_clip(self.a._token)
        self.assertEqual(self.player.played, 1)

    def test_a_done_call_of_an_older_clip_is_ignored(self):
        self.a._set_speaking(True)
        self.startClip()
        self.a._clip_done(self.a._token - 1)
        self.assertTrue(self.a.speaking)

    def test_a_failing_clip_gives_the_music_back(self):
        self.a._set_speaking(True)
        self.a._clip_queue = [Path("C:/clips/b.mp3")]
        self.a._on_clip_error(1, "no codec")
        self.assertEqual(self.a._clip_queue, [])
        self.assertFalse(self.a.speaking)

    # ── ducking ──────────────────────────────────────────────────────────────
    def test_the_duck_is_only_reported_when_it_changes(self):
        self.a._set_speaking(True)
        self.a._set_speaking(True)
        self.a._set_speaking(False)
        self.assertEqual(self.ducks, [True, False])

    def test_a_listener_whose_objects_are_gone_is_dropped(self):
        def gone(_on):
            raise RuntimeError("Internal C++ object already deleted")
        self.a._on_speaking = gone
        self.a._set_speaking(True)
        self.assertIsNone(self.a._on_speaking)
        self.a._set_speaking(False)      # nobody left to tell

    def test_the_engine_state_drives_the_duck(self):
        states = types.SimpleNamespace(Speaking=1, Ready=2, Error=3, Paused=4)
        self.a._on_state(1)              # no engine yet: ignored
        self.assertFalse(self.a.speaking)
        self.a._state = states
        self.a._on_state(states.Speaking)
        self.assertTrue(self.a.speaking)
        self.a._on_state(states.Paused)
        self.assertTrue(self.a.speaking)
        self.a._on_state(states.Ready)
        self.assertFalse(self.a.speaking)
        self.a._on_state(states.Speaking)
        self.a._on_state(states.Error)
        self.assertFalse(self.a.speaking)

    def test_the_watchdog_lets_the_music_back_up(self):
        self.a._give_up(self.a._token)       # not speaking: nothing to undo
        self.assertEqual(self.player.stopped, 0)
        self.a._set_speaking(True)
        self.a._give_up(self.a._token + 5)   # an older announcement's watchdog
        self.assertTrue(self.a.speaking)
        self.a._give_up(self.a._token)
        self.assertFalse(self.a.speaking)
        self.assertEqual(self.player.stopped, 1)

    # ── speak / stop / shutdown ──────────────────────────────────────────────
    def test_a_dance_without_recordings_is_not_spoken(self):
        with mock.patch.object(self.a, "_clips_for", return_value=[]):
            self.assertFalse(self.a.speak("LW"))

    def test_a_dance_with_recordings_plays_them(self):
        clips = [Path("C:/clips/a.mp3"), Path("C:/clips/b.mp3")]
        with mock.patch.object(self.a, "_clips_for", return_value=clips):
            self.assertTrue(self.a.speak("LW", now=True, heat=2))
        self.assertTrue(self.a.speaking)
        self.assertEqual(self.a._clip_queue, [clips[1]])
        self.assertEqual(self.player.played, 1)

    def test_no_clip_engine_means_nothing_is_played(self):
        with mock.patch.object(self.a, "_clip_engine", return_value=None):
            self.assertFalse(self.a._play_clips([Path("C:/clips/a.mp3")]))
        self.assertFalse(self.a.speaking)

    def test_stop_silences_both_engines_and_empties_the_queue(self):
        tts = mock.Mock()
        self.a._tts = tts
        self.a._clip_queue = [Path("C:/clips/b.mp3")]
        self.a._set_speaking(True)
        token = self.a._token
        self.a.stop()
        tts.stop.assert_called_once()
        self.assertEqual(self.player.stopped, 1)
        self.assertEqual(self.a._clip_queue, [])
        self.assertEqual(self.a._token, token + 1)
        self.assertFalse(self.a.speaking)

    def test_shutdown_forgets_the_duck_and_tolerates_dead_engines(self):
        self.a._tts = mock.Mock()
        self.a._tts.stop.side_effect = RuntimeError("deleted")
        self.a._set_speaking(True)
        self.a.shutdown()
        self.assertIsNone(self.a._on_speaking)
        self.assertFalse(self.a.speaking)
        self.assertEqual(self.player.stopped, 1)

    # ── the output the clips play on ─────────────────────────────────────────
    def test_the_device_is_kept_for_a_player_not_built_yet(self):
        self.a.set_device("hall", 2)
        self.assertEqual((self.a._device, self.a._pair), ("hall", 2))

    def test_a_built_route_follows_the_device_and_the_idle_release(self):
        route = mock.Mock()
        self.a._clip_route = route
        self.a.set_device("hall", 1)
        self.a.release_outputs()
        self.a.restore_outputs()
        route.set_device.assert_called_once_with("hall", 1)
        route.release.assert_called_once()
        route.restore.assert_called_once()

    def test_without_a_route_release_and_restore_are_no_ops(self):
        self.a.release_outputs()
        self.a.restore_outputs()


class ClipsForTest(unittest.TestCase):
    def setUp(self):
        self.a = DanceAnnouncer()
        for name, value in (("clip_language", "german"),
                            ("clip_genders", ["female", "male"]),
                            ("clip_folders", [Path("C:/clips/f")]),
                            ("prime_clip_bounds", None),
                            ("announce_clips", [Path("C:/clips/f/LW.mp3")])):
            patcher = mock.patch.object(announce, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_the_voice_of_the_evening_is_chosen_and_remembered(self):
        with mock.patch.object(announce, "pick_clip_gender", return_value="male"):
            clips = self.a._clips_for("LW", True)
        self.assertEqual(clips, [Path("C:/clips/f/LW.mp3")])
        self.assertEqual(self.a._last_gender, "male")
        announce.prime_clip_bounds.assert_called_once_with(Path("C:/clips/f"))

    def test_no_voice_means_no_clips(self):
        with mock.patch.object(announce, "pick_clip_gender", return_value=None):
            self.assertEqual(self.a._clips_for("LW", False), [])
        self.assertIsNone(self.a._last_gender)

    def test_a_failed_player_means_no_clips(self):
        self.a._clips_failed = True
        self.assertEqual(self.a._clips_for("LW", False), [])

    def test_without_multimedia_the_clip_player_gives_up_for_good(self):
        with mock.patch.dict(sys.modules, {"PySide6.QtMultimedia": None}):
            self.assertIsNone(self.a._clip_engine())
        self.assertTrue(self.a._clips_failed)
        self.assertIsNone(self.a._clip_engine())      # does not try again


class ProbeTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.folder = Path(self.dir.name)
        for name in ("a.mp3", "b.mp3", "notes.txt"):
            (self.folder / name).write_bytes(b"")
        bounds = mock.patch.dict(announce._BOUNDS, clear=True)
        bounds.start()
        self.addCleanup(bounds.stop)

    def test_a_folder_is_probed_in_the_background_once(self):
        started = []
        fake = mock.Mock(side_effect=lambda **kw: mock.Mock(start=lambda: started.append(kw)))
        with mock.patch.object(announce, "_BOUNDS_PROBED", set()), \
                mock.patch.object(announce.threading, "Thread", fake):
            announce.prime_clip_bounds(self.folder)
            announce.prime_clip_bounds(self.folder)
            announce.prime_clip_bounds(self.folder / "missing")
        self.assertEqual(len(started), 1)
        self.assertEqual(started[0]["args"], (self.folder,))

    def test_every_measurable_clip_gets_its_bounds(self):
        def silence(_ffmpeg, clip):
            return None if clip.name == "b.mp3" else "stderr of " + clip.name
        with mock.patch("shared.audio.audio_probes.find_ffmpeg", return_value="ffmpeg"), \
                mock.patch.object(announce, "_silencedetect", side_effect=silence), \
                mock.patch.object(announce, "parse_bounds", return_value=(10, 500)):
            announce._prime_clip_bounds(self.folder)
        self.assertEqual(announce._BOUNDS, {str(self.folder / "a.mp3"): (10, 500)})

    def test_a_probe_without_a_duration_leaves_the_clip_whole(self):
        with mock.patch("shared.audio.audio_probes.find_ffmpeg", return_value="ffmpeg"), \
                mock.patch.object(announce, "_silencedetect", return_value="junk"), \
                mock.patch.object(announce, "parse_bounds", return_value=None):
            announce._prime_clip_bounds(self.folder)
        self.assertEqual(announce._BOUNDS, {})

    def test_without_ffmpeg_nothing_is_measured(self):
        with mock.patch("shared.audio.audio_probes.find_ffmpeg", return_value=None), \
                mock.patch.object(announce, "_silencedetect") as probe:
            announce._prime_clip_bounds(self.folder)
        probe.assert_not_called()
        self.assertEqual(announce._BOUNDS, {})


class SilenceDetectTest(unittest.TestCase):
    def run_with(self, **result):
        with mock.patch.object(announce.subprocess, "run", **result):
            return announce._silencedetect("ffmpeg", Path("C:/clips/a.mp3"))

    def test_the_stderr_of_a_finished_probe_is_returned(self):
        done = subprocess.CompletedProcess([], 0, stdout="", stderr="Duration: 00:00:01.00")
        self.assertEqual(self.run_with(return_value=done), "Duration: 00:00:01.00")

    def test_a_probe_that_died_halfway_says_nothing(self):
        done = subprocess.CompletedProcess([], 1, stdout="", stderr="partial")
        self.assertIsNone(self.run_with(return_value=done))

    def test_a_missing_or_stuck_ffmpeg_says_nothing(self):
        self.assertIsNone(self.run_with(side_effect=OSError("gone")))
        self.assertIsNone(self.run_with(
            side_effect=subprocess.TimeoutExpired("ffmpeg", 20)))


class SpokenFragmentTest(unittest.TestCase):
    def test_a_word_gets_a_full_stop_to_cut_into(self):
        self.assertEqual(announce.spoken_fragment("Jive"), "Jive.")
        self.assertEqual(announce.spoken_fragment("Heat 5!"), "Heat 5!")
        self.assertEqual(announce.spoken_fragment(""), "")


# ── the synthesiser, which only the audition tool still uses ─────────────────
def fakeSpeechModule(engines):
    """PySide6.QtTextToSpeech with `engines`: {name: [(language, female, name)]}."""
    class Gender:
        Female = "female"
        Male = "male"

    genderEnum = Gender

    class Voice:
        Gender = genderEnum

        def __init__(self, language, gender, name):
            self._language, self._gender, self._name = language, gender, name

        def locale(self):
            return types.SimpleNamespace(language=lambda: self._language)

        def gender(self):
            return self._gender

        def name(self):
            return self._name

    class Signal:
        def __init__(self):
            self.slots = []

        def connect(self, fn):
            self.slots.append(fn)

    class Engine:
        State = types.SimpleNamespace(Speaking=1, Ready=2, Error=3)
        built = []

        def __init__(self, *args):
            self.name = args[0] if isinstance(args[0], str) else "default"
            self.stateChanged = Signal()
            self.locale = self.voice = None
            self.deleted = self.stopped = False
            self.cursor = None
            Engine.built.append(self)

        @staticmethod
        def availableEngines():
            return list(engines) + ["mock"]

        def _voices(self):
            return [Voice(lang, Gender.Female if female else Gender.Male, nm)
                    for lang, female, nm in engines.get(self.name, [])]

        def availableLocales(self):
            return [types.SimpleNamespace(language=lambda lang=v._language: lang,
                                          tag=v._language) for v in self._voices()]

        def setLocale(self, loc):
            self.locale = loc

        def availableVoices(self):
            return [v for v in self._voices()
                    if self.locale is None or v._language == self.locale.language()]

        def setVoice(self, voice):
            self.voice = voice

        def engine(self):
            return self.name

        def deleteLater(self):
            self.deleted = True

        def stop(self):
            self.stopped = True

    Engine.built = []
    return types.SimpleNamespace(QTextToSpeech=Engine, QVoice=Voice)


class PickVoiceTest(unittest.TestCase):
    def voices(self):
        module = fakeSpeechModule({})
        voice = module.QVoice
        return module, [voice(QLocale.Language.English, "female", "Zira"),
                        voice(QLocale.Language.German, "male", "Stefan"),
                        voice(QLocale.Language.German, "male", "Conrad")]

    def test_a_voice_of_the_wanted_language_beats_a_female_one_of_another(self):
        module, voices = self.voices()
        got = announce.pick_voice(voices, QLocale, module.QVoice)
        self.assertEqual(got.name(), "Stefan")

    def test_a_female_voice_wins_inside_the_language(self):
        module, voices = self.voices()
        voices.append(module.QVoice(QLocale.Language.German, "female", "Katja"))
        self.assertEqual(announce.pick_voice(voices, QLocale, module.QVoice).name(), "Katja")

    def test_without_the_language_any_female_voice_will_do(self):
        module, voices = self.voices()
        got = announce.pick_voice(voices, QLocale, module.QVoice,
                                  language=QLocale.Language.French)
        self.assertEqual(got.name(), "Zira")

    def test_nothing_to_choose_from_is_none(self):
        module, _voices = self.voices()
        self.assertIsNone(announce.pick_voice([], QLocale, module.QVoice))


class SynthesiserTest(unittest.TestCase):
    GERMAN, ENGLISH = QLocale.Language.German, QLocale.Language.English

    def engine(self, engines, **kw):
        module = fakeSpeechModule(engines)
        a = DanceAnnouncer(**kw)
        with mock.patch.dict(sys.modules, {"PySide6.QtTextToSpeech": module}):
            return a, a._engine(), module

    def test_a_german_and_an_english_voice_are_found(self):
        a, tts, _m = self.engine({"sapi": [(self.GERMAN, True, "Katja"),
                                           (self.GERMAN, False, "Stefan"),
                                           (self.ENGLISH, True, "Zira")]})
        self.assertIs(tts, a._tts)
        self.assertEqual(a._voices["de"][1].name(), "Katja")
        self.assertEqual(a._voices["en"][1].name(), "Zira")
        self.assertEqual(tts.voice.name(), "Katja")
        self.assertEqual(len(tts.stateChanged.slots), 1)
        self.assertIs(a._engine(), tts)       # built once

    def test_the_first_engine_with_a_german_voice_wins(self):
        a, tts, module = self.engine({"one": [(self.ENGLISH, True, "Zira")],
                                      "two": [(self.GERMAN, True, "Hedda")]})
        self.assertEqual(tts.name, "two")
        self.assertEqual(a._voices["de"][1].name(), "Hedda")
        first = module.QTextToSpeech.built[0]
        self.assertTrue(first.deleted)

    def test_a_second_engine_is_dropped_when_the_first_already_speaks_german(self):
        a, tts, module = self.engine({"one": [(self.GERMAN, True, "Katja")],
                                      "two": [(self.GERMAN, True, "Hedda")]})
        self.assertEqual(tts.name, "one")
        self.assertEqual(len(module.QTextToSpeech.built), 1)

    def test_without_a_german_voice_the_engine_is_left_on_german_anyway(self):
        a, tts, _m = self.engine({"sapi": [(self.ENGLISH, True, "Zira")]})
        self.assertIsNone(a._voices["de"])
        self.assertEqual(tts.locale.language(), self.GERMAN)
        self.assertIsNone(tts.voice)

    def test_an_engine_list_of_only_the_mock_uses_the_default_engine(self):
        a, tts, _m = self.engine({})
        self.assertEqual(tts.name, "default")

    def test_an_engine_that_cannot_start_is_given_up_for_good(self):
        module = fakeSpeechModule({"sapi": []})
        module.QTextToSpeech.availableEngines = staticmethod(
            lambda: (_ for _ in ()).throw(RuntimeError("no audio service")))
        a = DanceAnnouncer()
        with mock.patch.dict(sys.modules, {"PySide6.QtTextToSpeech": module}):
            self.assertIsNone(a._engine())
            self.assertTrue(a._failed)
            self.assertIsNone(a._engine())

    def test_a_later_engine_without_german_either_is_dropped(self):
        a, tts, module = self.engine({"one": [(self.ENGLISH, True, "Zira")],
                                      "two": [(self.ENGLISH, True, "David")]})
        self.assertEqual(tts.name, "one")
        self.assertIsNone(a._voices["de"])
        self.assertTrue(module.QTextToSpeech.built[1].deleted)

    def test_without_the_module_there_is_no_engine(self):
        a = DanceAnnouncer()
        with mock.patch.dict(sys.modules, {"PySide6.QtTextToSpeech": None}):
            self.assertIsNone(a._engine())
        self.assertTrue(a._failed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
