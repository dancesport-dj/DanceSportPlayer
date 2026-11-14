#!/usr/bin/env python3
"""✂️ A title whose file cuts off at full level gets a short fade.

Run:  .venv\\Scripts\\python.exe -m unittest tests.player.test_hard_end -v

"Warum hast du nicht nein gesagt" stops at +2.4 dB in its last 2 ms: the cut is
in the file, not in the player. The last 20 ms of a title tell such an end from
a natural one, and the play tick then takes the level down before the file runs
out.
"""

import math
import os
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_hard_end_"))

from PySide6.QtCore import QThread
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication, QWidget

from player.audio.between_dances import BetweenDances
from player.audio.fade_now import FadeNow
from player.audio.mix import OutputMix
from player.audio.playback_state import PlaybackState
from player.window import main_audio
from player.window.main_player import PlayerControlMixin
from shared.audio import audio_probes
from shared.audio.audio_probes import (
    HardEndWorker,
    LoudnessWorker,
    PdHighlightWorker,
    detect_hard_end,
    find_ffmpeg,
    parse_hard_end,
)
from tests.qt_test_support import reap_widget

TRACK = Path(r"C:\music\Warum.mp3")
RATE = 44100


def write_wav(path: Path, levels: list):
    """A 440 Hz tone, `levels` giving (seconds, amplitude) stretches of it."""
    frames = bytearray()
    n = 0
    for secs, amp in levels:
        for _ in range(int(secs * RATE)):
            v = amp * math.sin(2 * math.pi * 440 * n / RATE)
            frames += struct.pack("<h", int(v * 32767))
            n += 1
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(frames))


class ParseHardEndTest(unittest.TestCase):

    def test_the_level_still_up_at_the_end_is_a_hard_end(self):
        self.assertTrue(parse_hard_end("[Parsed_volumedetect_0] max_volume: 0.0 dB"))
        self.assertTrue(parse_hard_end("[Parsed_volumedetect_0] max_volume: -29.9 dB"))

    def test_the_loudest_natural_ending_in_the_library_is_none(self):
        self.assertFalse(parse_hard_end("[Parsed_volumedetect_0] max_volume: -36.3 dB"))

    def test_digital_silence_is_none(self):
        self.assertFalse(parse_hard_end("[Parsed_volumedetect_0] max_volume: -91.0 dB"))

    def test_no_measure_says_nothing(self):
        self.assertIsNone(parse_hard_end("Output file is empty"))
        self.assertIsNone(parse_hard_end(None))


@unittest.skipUnless(find_ffmpeg(), "needs ffmpeg")
class DetectHardEndTest(unittest.TestCase):
    """The real probe on real files."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def probe(self, levels):
        path = self.dir / "t.wav"
        write_wav(path, levels)
        return detect_hard_end(find_ffmpeg(), path)

    def test_a_tone_up_to_the_last_sample(self):
        self.assertTrue(self.probe([(0.5, 0.5)]))

    def test_a_tone_cut_a_moment_before_the_file_stops(self):
        # Loud until 50 ms before the end, quiet in the last 20: the hall
        # still hears a cut ("anonimo veneziano rumba", "saboreando").
        self.assertTrue(self.probe([(0.5, 0.5), (0.05, 0.0)]))

    def test_a_tone_with_a_long_silence_behind_it(self):
        self.assertFalse(self.probe([(0.5, 0.5), (0.3, 0.0)]))

    def test_a_tone_that_has_decayed_at_the_end(self):
        self.assertFalse(self.probe([(0.5, 0.5), (0.2, 0.05), (0.1, 0.005)]))

    def test_a_missing_file_says_nothing(self):
        self.assertIsNone(detect_hard_end(find_ffmpeg(), self.dir / "gone.mp3"))

    def test_the_worker_reports_the_path(self):
        path = self.dir / "t.wav"
        write_wav(path, [(0.5, 0.5)])
        heard = []
        w = HardEndWorker(path, find_ffmpeg())
        w.done.connect(lambda p, hard: heard.append((p, hard)))
        w.run()
        self.assertEqual(heard, [(str(path), True)])

    def test_the_worker_can_report_under_the_stored_path(self):
        path = self.dir / "t.wav"
        write_wav(path, [(0.5, 0.5)])
        heard = []
        w = HardEndWorker(path, find_ffmpeg(), key="G:/stick/t.wav")
        w.done.connect(lambda p, hard: heard.append((p, hard)))
        w.run()
        self.assertEqual(heard, [("G:/stick/t.wav", True)])

    def test_the_worker_stays_quiet_when_nothing_was_measured(self):
        heard = []
        w = HardEndWorker(self.dir / "gone.mp3", find_ffmpeg())
        w.done.connect(lambda p, hard: heard.append((p, hard)))
        w.run()
        self.assertEqual(heard, [])


class _Media:
    def __init__(self, dur_ms=200_000):
        self.pos = 0
        self.dur = dur_ms

    def playbackState(self):
        return QMediaPlayer.PlaybackState.PlayingState

    def position(self):
        return self.pos

    def duration(self):
        return self.dur

    def playbackRate(self):
        return 1.0


class _Panel:
    def stop_fade_due(self, *_a):
        return False


class _Desk(PlayerControlMixin, QWidget):
    """The play tick on its own: the rest of the evening has tests of its own."""

    def __init__(self, limit=0.0, fade=3.0, looping=False):
        QWidget.__init__(self)
        self.media = _Media()
        self._player = cast(Any, self.media)
        self._play_panel = cast(Any, _Panel())
        self._playback = PlaybackState()
        self._playback.path = TRACK
        # These tests describe a one second fade; 2 s is the app's default.
        self._settings = {"hard_end_fade_secs": 1.0}
        self._mix = OutputMix()
        self._fade_now = FadeNow()
        self._between = BetweenDances()
        self._between.pending = None
        self._played_marked = True
        self.limit = limit
        self.fade = fade
        self.looping = looping
        self.ended = []

    def _is_playing_mode(self):
        return True

    def _maybe_skip_silence(self):
        return False

    def _watch_stall(self):
        return False

    def _closing_tick(self):
        return False

    def _note_on_air(self):
        pass

    def _celebration_tick(self):
        return False

    def _maybe_crossfade(self):
        pass

    def _pd_runs_to_its_highlight(self):
        return False

    def _looping(self):
        return self.looping

    def _play_limit_secs(self):
        return self.limit

    def _play_end_secs(self):
        return self.limit

    def _pv(self, _key):
        return self.fade

    def _cut_fade_floor(self):
        return 0.0

    def _begin_celebration(self):
        return False

    def _on_timed_end(self, why):
        self.ended.append(why)

    def _set_countdown(self, _text):
        pass

    def _apply_volume(self):
        pass


class HardEndFadeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def desk(self, hard=True, **kw):
        d = _Desk(**kw)
        self.addCleanup(reap_widget, d)
        if hard is not None:
            d._playback.hard_ends[str(TRACK)] = hard
        return d

    def level(self, d, left_ms):
        d.media.pos = d.media.dur - left_ms
        d._on_play_tick()
        return d._mix.fade

    def test_a_title_with_a_natural_end_stays_up(self):
        self.assertEqual(self.level(self.desk(hard=False), 100), 1.0)

    def test_off_leaves_even_a_cut_title_at_full_level(self):
        # ⚙ Settings ▸ "Fade a title that ends abruptly over: off" stores 0.0.
        d = self.desk()
        d._settings = {"hard_end_fade_secs": 0.0}
        self.assertEqual(self.level(d, 100), 1.0)
        self.assertEqual(self.level(d, 1), 1.0)

    def test_a_title_not_probed_yet_stays_up(self):
        self.assertEqual(self.level(self.desk(hard=None), 100), 1.0)

    def test_full_level_until_the_last_stretch(self):
        self.assertEqual(self.level(self.desk(), 1500), 1.0)

    def test_it_ramps_down_over_the_last_second(self):
        d = self.desk()
        self.assertAlmostEqual(self.level(d, 700), 0.5)
        self.assertAlmostEqual(self.level(d, 400), 0.2)

    def test_it_is_gone_one_tick_before_the_file_stops(self):
        # The tick is 200 ms: aimed at the very end, the cut would still be
        # there at up to a fifth of the level.
        d = self.desk()
        self.assertEqual(self.level(d, 200), 0.0)
        self.assertEqual(self.level(d, 50), 0.0)

    def test_a_seek_back_brings_it_up_again(self):
        d = self.desk()
        self.assertEqual(self.level(d, 100), 0.0)
        self.assertEqual(self.level(d, 60_000), 1.0)

    def test_a_length_the_file_does_not_reach_still_fades(self):
        d = self.desk(limit=600.0)
        self.assertAlmostEqual(self.level(d, 700), 0.5)

    def test_the_timed_fade_wins_where_it_is_lower(self):
        # 2 s of music left of a 4 s fade: 0.5, the end of the file is far off.
        d = self.desk(limit=100.0, fade=4.0)
        d.media.pos = 98_000
        d._on_play_tick()
        self.assertAlmostEqual(d._mix.fade, 0.5)

    def test_the_end_of_the_file_wins_where_it_is_lower(self):
        # A timed fade aimed past the end of the file has barely started.
        d = self.desk(limit=205.0, fade=10.0)
        self.assertAlmostEqual(self.level(d, 500), 0.3)

    def test_a_loop_plays_through(self):
        self.assertEqual(self.level(self.desk(looping=True), 100), 1.0)

    def test_a_length_the_backend_does_not_know_stays_up(self):
        d = self.desk()
        d.media.dur = 0
        d._on_play_tick()
        self.assertEqual(d._mix.fade, 1.0)


class HardEndArmingTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.d = _Desk()
        self.addCleanup(reap_widget, self.d)
        self.d._silences = {str(TRACK): []}

    def test_loading_a_title_asks_how_it_ends(self):
        with mock.patch.object(main_audio, "find_ffmpeg", return_value="ffmpeg"), \
                mock.patch.object(main_audio, "HardEndWorker") as worker:
            self.d._ensure_silences(TRACK)
        worker.assert_called_once_with(TRACK, "ffmpeg", key=str(TRACK), parent=self.d)
        worker.return_value.start.assert_called_once_with()

    def test_a_title_found_elsewhere_is_probed_where_it_is(self):
        """Marcel: the fade seemed to work on wishlists only. A playlist line whose
        stored path is not there (the stick came back as G:, a 🧭 copy) was probed
        at that path, got no answer, and so never faded. The probe reads the file
        the deck plays; the answer is still filed under the stored path."""
        found = TRACK.with_name("elsewhere.mp3")
        with mock.patch.object(main_audio, "find_ffmpeg", return_value="ffmpeg"), \
                mock.patch.object(main_audio, "resolve_file", create=True,
                                  return_value=found), \
                mock.patch.object(main_audio, "HardEndWorker") as worker:
            self.d._ensure_silences(TRACK)
        worker.assert_called_once_with(found, "ffmpeg", key=str(TRACK), parent=self.d)

    def test_a_title_is_asked_once_a_session(self):
        self.d._playback.hard_ends[str(TRACK)] = False
        with mock.patch.object(main_audio, "HardEndWorker") as worker:
            self.d._ensure_silences(TRACK)
        worker.assert_not_called()

    def test_without_ffmpeg_nothing_is_started(self):
        with mock.patch.object(main_audio, "find_ffmpeg", return_value=None), \
                mock.patch.object(main_audio, "HardEndWorker") as worker:
            self.d._ensure_silences(TRACK)
        worker.assert_not_called()

    def test_the_answer_lands_on_the_deck(self):
        self.d._on_hard_end(str(TRACK), True)
        self.assertTrue(self.d._playback.hard_ends[str(TRACK)])


class _ProbeDesk(_Desk):
    """The arming path with nothing but the probes real: no cache, workers run
    inline, the answers recorded where the deck would file them."""

    def __init__(self):
        super().__init__()
        self._library = SimpleNamespace(cache=None)
        self._silence_worker = None
        self._silences = {}
        self.silence_answers, self.silence_errors = [], []

    def _on_silences(self, path_str, spans):
        self.silence_answers.append((path_str, spans))
        self._silences[path_str] = spans

    def _on_silence_error(self, path_str, msg):
        self.silence_errors.append((path_str, msg))


@unittest.skipUnless(find_ffmpeg(), "needs ffmpeg")
class ProbesReadTheFileTheDeckPlaysTest(unittest.TestCase):
    """Marcel: a playlist line whose file is found elsewhere (the stick came back
    as another drive, a copy under a search root) got no hard-end fade and no
    silence skip. Real ffmpeg on a real file, the stored path pointing nowhere."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.stored = self.dir / "stick-gone" / "t.wav"       # the stored path: not there
        self.found = self.dir / "t.wav"                        # where the deck finds it
        self.d = _ProbeDesk()
        self.addCleanup(reap_widget, self.d)
        self.d._playback.path = self.stored
        for patch in (mock.patch.object(main_audio, "resolve_file",
                                        return_value=self.found),
                      mock.patch.object(QThread, "start", lambda w: w.run())):
            patch.start()
            self.addCleanup(patch.stop)

    def test_a_cut_title_found_elsewhere_gets_its_hard_end_under_the_stored_path(self):
        write_wav(self.found, [(0.5, 0.5)])                    # stops in full sound
        self.d._ensure_silences(self.stored)
        self.assertIs(self.d._playback.hard_ends.get(str(self.stored)), True)

    def test_a_silence_found_elsewhere_is_probed_and_filed_under_the_stored_path(self):
        write_wav(self.found, [(1.0, 0.5), (3.0, 0.0), (1.0, 0.5)])
        self.d._ensure_silences(self.stored)
        self.assertEqual(self.d.silence_errors, [])
        self.assertEqual([p for p, _spans in self.d.silence_answers], [str(self.stored)])
        self.assertTrue(self.d.silence_answers[0][1])

    def test_a_probe_still_running_for_the_stored_path_is_recognised(self):
        """The one-probe-at-a-time guard compares the title, not the file read."""
        write_wav(self.found, [(1.0, 0.5), (3.0, 0.0), (1.0, 0.5)])
        self.d._ensure_silences(self.stored)
        worker = mock.Mock()
        worker.isRunning.return_value = True
        worker.key = str(self.stored)
        self.d._silence_worker = worker
        self.d._silences.clear()
        self.d._ensure_silences(self.stored)
        worker.cancel.assert_not_called()


class WorkersReportUnderTheirKeyTest(unittest.TestCase):
    """The loudness and Paso Doble workers read the file they are given and
    report under the stored path the deck knows the title by."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @unittest.skipUnless(find_ffmpeg(), "needs ffmpeg")
    def test_loudness_is_measured_in_the_found_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            found = Path(tmp) / "t.wav"
            write_wav(found, [(2.0, 0.5)])
            stored = Path(tmp) / "stick-gone" / "t.wav"
            w = LoudnessWorker(found, find_ffmpeg(), key=str(stored))
            done, errors = [], []
            w.done.connect(lambda *a: done.append(a))
            w.error.connect(lambda *a: errors.append(a))
            w.run()
        self.assertEqual(errors, [])
        self.assertEqual([a[0] for a in done], [str(stored)])
        self.assertEqual(w.key, str(stored))

    def test_pd_highlights_are_detected_in_the_found_file(self):
        found, stored = Path("found/pd.mp3"), Path("gone/pd.mp3")
        with mock.patch.object(audio_probes, "detect_pd_highlights",
                               return_value=[30.0]) as detect:
            w = PdHighlightWorker(found, key=str(stored))
            done = []
            w.done.connect(lambda *a: done.append(a))
            w.run()
        self.assertEqual(detect.call_args.args[0], found)
        self.assertEqual(done, [(str(stored), [30.0])])
        self.assertEqual(w.key, str(stored))


if __name__ == "__main__":
    unittest.main()
