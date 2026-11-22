#!/usr/bin/env python3
"""⏩ Every way the music's tempo is made, held against how it was before the
equalizer branch (main at 669ebbe2, merge base 652532f1).

Run:  .venv/Scripts/python.exe -m unittest tests.player.audio.test_tempo_all_ways -v

The ways in: the fader's target (🎚 TSO, set_tempo_to_target), the ♪ takt
correction, a controller knob, the desk's − / + steps and the reset all end in
BigPlayerWidget.apply_tempo → setPlaybackRate. The rates they set were
measured on main and must not move.

The ways out, one per ⏩ Tempo choice:
- "qt" with every EQ off: untapped, Qt's own stretch, exactly as on main.
- "qt" with an EQ on, and "signalsmith": sstretch.dll makes the tempo.
- "rubberband": ffmpeg's rubberband filter. On a bare sine Rubber Band itself
  wobbles at some tempi (0.92, 1.08: dips and a pitch off by a few Hz, the
  same from a plain `ffmpeg -af rubberband`), so it is held to ffmpeg's own
  output: the app must add nothing. A tempo change reaches it as a command
  beside the audio, so that one is checked in real time; ffmpeg's own
  crossover dips to ~0.33 of the level there (measured with asendcmd).
- "numpy": the stand-in where the others are missing.
The engines' own files (test_stretch*.py) go deeper into each; this one holds
them all to one bar over the fader's whole range.

Deliberate differences from main, not regressions:
- A channel pair played the tempo like a turntable, the pitch moving with it;
  since 17053c0c every tapped stream keeps its pitch.
- A tempo change mid-title repriced the music already danced (a late −16 %
  ended the title at once); since 8c8d037b what was danced stays danced.
"""
import os
import tempfile
import time
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_tempo_all_ways_"))

import subprocess

import numpy as np
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QApplication

from planner.playing import equalizer as eqs
from player.audio import pair_route, stretch_engines, stretch_ffmpeg, stretch_signalsmith
from player.widgets.player import BigPlayerWidget
from shared.audio.playback import audible_played_secs, tempo_shift_secs
from tests.player.audio.test_pair_route import _PIECE, _RouteCase
from tests.player.test_audio_idle import _Desk
from tests.qt_test_support import reap_widget

_RATE = 48000
_AMP = 0.3
# The fader's range (±16 %) and two steps inside it.
_FADER = (0.84, 0.92, 1.08, 1.16)


def _engines() -> list[str]:
    """The tapped engines this machine has; numpy is always there."""
    have = ["numpy"]
    if stretch_signalsmith.available():
        have.append("signalsmith")
    if stretch_ffmpeg.available():
        have.append("rubberband")
    return have


def _tone(seconds: float, freq: float = 440.0) -> np.ndarray:
    t = np.arange(int(_RATE * seconds)) / _RATE
    mono = (_AMP * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    return np.column_stack([mono, mono])


def _beats(seconds: float, period: float = 0.5, on: float = 0.2) -> np.ndarray:
    """A 440 Hz beep every `period` seconds: a beat at 120 per minute."""
    frames = _tone(seconds)
    t = np.arange(len(frames)) / _RATE
    frames[(t % period) >= on] = 0
    return frames


def _stream(engine: str, frames: np.ndarray, rates: list[float],
            real_time: bool = False) -> np.ndarray:
    """`frames` through a stretch built the way the route builds one, in the
    pieces Qt hands over (~26 ms). `rates`: the tempo for each equal part of
    the title (one entry: the whole title at that tempo). `real_time`: the
    pieces come as fast as Qt hands them over at that tempo."""
    stretch = stretch_engines.make(_RATE, engine)
    try:
        stretch.set_rate(rates[0])
        if hasattr(stretch, "ready"):
            stretch.ready(5.0)
        part = -(-len(frames) // len(rates))
        out = []
        due = time.perf_counter()
        for i in range(0, len(frames), _PIECE):
            rate = rates[min(i // part, len(rates) - 1)]
            stretch.set_rate(rate)
            out.append(stretch.process(frames[i:i + _PIECE]))
            if real_time:
                due += _PIECE / _RATE / rate
                time.sleep(max(0.0, due - time.perf_counter()))
        out.append(stretch.flush())
    finally:
        if hasattr(stretch, "close"):
            stretch.close()
    return np.vstack(out)


def _ffmpeg_rubberband(frames: np.ndarray, rate: float) -> np.ndarray:
    """The same frames through a plain `ffmpeg -af rubberband`, no app code."""
    raw = ["-f", "f32le", "-ar", str(_RATE), "-ac", "2"]
    cmd = [stretch_ffmpeg._ffmpeg(), "-hide_banner", "-loglevel", "error",
           *raw, "-i", "pipe:0", "-af", "rubberband=tempo=%.6f" % rate, *raw, "pipe:1"]
    out = subprocess.run(cmd, input=frames.astype(np.float32).tobytes(),
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32).reshape(-1, 2)


def _length_at(frames: np.ndarray, rates: list[float]) -> float:
    """Frames heard when each equal part of `frames` plays at its rate."""
    part = len(frames) / len(rates)
    return sum(part / rate for rate in rates)


def _middle(mono: np.ndarray) -> np.ndarray:
    """Without the first and last 0.3 s, where a stretch ramps in and out."""
    edge = int(0.3 * _RATE)
    return mono[edge:len(mono) - edge]


def _envelope(mono: np.ndarray, window: int = 240) -> np.ndarray:
    """RMS per 5 ms (window 240) — a dropout shows as a dip."""
    n = len(mono) // window
    return np.sqrt((mono[:n * window].reshape(n, window) ** 2).mean(axis=1))


def _peak_hz(mono: np.ndarray) -> float:
    spectrum = np.abs(np.fft.rfft(mono * np.hanning(len(mono))))
    return float(np.fft.rfftfreq(len(mono), 1 / _RATE)[np.argmax(spectrum)])


def _level_db(mono: np.ndarray) -> float:
    """Against the input tone's own RMS."""
    return float(20 * np.log10(np.sqrt((mono ** 2).mean()) / (_AMP / np.sqrt(2))))


def _beat_ratio(mono: np.ndarray, rate: float, period: float = 0.5) -> float:
    """The beat spacing heard, over the one the tempo asks for (1.0 = right):
    the strongest repeat of the 1 ms envelope near period/rate."""
    env = _envelope(mono, 48)
    env = env - env.mean()
    ac = np.correlate(env, env, "full")[len(env) - 1:]
    want = period * 1000 / rate
    lo, hi = int(want * 0.7), int(want * 1.3)
    return (lo + int(np.argmax(ac[lo:hi]))) / want


class _AppCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])


class EnginesTest(unittest.TestCase):
    """Every tapped engine over the fader's range, in Qt-sized pieces."""

    def each(self, engines=None, rates=_FADER):
        """(engine, rate) for every engine this machine has, as subtests."""
        for engine in engines or _engines():
            for rate in rates:
                with self.subTest(engine=engine, rate=rate):
                    yield engine, rate

    # ===== Acceptance criteria =====

    def test_every_engine_plays_the_beat_at_the_new_tempo(self):
        """What the couples dance to: at +16 % a beat every 0.431 s, not 0.5."""
        for engine, rate in self.each():
            out = _stream(engine, _beats(6.0), [rate])
            self.assertAlmostEqual(_beat_ratio(out[:, 0], rate), 1.0, delta=0.01)

    def test_every_engine_keeps_the_pitch(self):
        # Rubber Band: held to ffmpeg's own output below (see the docstring).
        for engine, rate in self.each(["numpy", "signalsmith"]):
            if engine not in _engines():
                self.skipTest(f"{engine} not on this machine")
            out = _stream(engine, _tone(4.0), [rate])
            self.assertAlmostEqual(_peak_hz(_middle(out[:, 0])), 440, delta=1)

    def test_every_engine_plays_the_title_for_its_length_over_the_tempo(self):
        """A 4 s title at 0.84 lasts 4.76 s: nothing lost at the start or end."""
        for engine, rate in self.each():
            source = _tone(4.0)
            out = _stream(engine, source, [rate])
            self.assertAlmostEqual(len(out) / (len(source) / rate), 1.0, delta=0.01)

    @unittest.skipUnless(stretch_ffmpeg.available(), "no ffmpeg with rubberband")
    def test_rubberband_in_the_app_sounds_as_ffmpeg_makes_it(self):
        """The pipe, the pieces and the spare process add nothing."""
        for rate in _FADER:
            with self.subTest(rate=rate):
                source = _tone(4.0)
                ours = _stream("rubberband", source, [rate])
                theirs = _ffmpeg_rubberband(source, rate)
                self.assertEqual(len(ours), len(theirs))
                diff = np.sqrt(((ours - theirs) ** 2).mean() / (theirs ** 2).mean())
                self.assertLess(diff, 1e-4)

    # ===== Core behavior =====

    def test_every_engine_keeps_the_level(self):
        for engine, rate in self.each(["numpy", "signalsmith"]):
            if engine not in _engines():
                self.skipTest(f"{engine} not on this machine")
            out = _stream(engine, _tone(4.0), [rate])
            self.assertAlmostEqual(_level_db(_middle(out[:, 0])), 0.0, delta=0.5)

    def test_a_steady_tone_has_no_dropout(self):
        for engine, rate in self.each(["numpy", "signalsmith"]):
            if engine not in _engines():
                self.skipTest(f"{engine} not on this machine")
            env = _envelope(_middle(_stream(engine, _tone(4.0), [rate])[:, 0]))
            self.assertGreater(env.min() / env.mean(), 0.9)

    def test_a_tempo_change_mid_title_has_no_gap(self):
        """The fader moved while the title plays: 1.0 → +16 % → −16 %."""
        for engine in ("numpy", "signalsmith"):
            if engine not in _engines():
                continue
            with self.subTest(engine=engine):
                source = _tone(6.0)
                out = _stream(engine, source, [1.0, 1.16, 0.84])
                env = _envelope(_middle(out[:, 0]))
                self.assertGreater(env.min() / env.mean(), 0.9)
                self.assertAlmostEqual(len(out) / _length_at(source, [1.0, 1.16, 0.84]),
                                       1.0, delta=0.02)

    @unittest.skipUnless(stretch_ffmpeg.available(), "no ffmpeg with rubberband")
    def test_rubberband_takes_a_tempo_change_mid_title(self):
        """In real time, as the app feeds it (~5 s). Its own crossover dips
        to ~0.33 (see the docstring); a gap would go to 0."""
        source = _tone(4.5)
        rates = [1.0, 1.16, 0.84]
        out = _stream("rubberband", source, rates, real_time=True)
        env = _envelope(_middle(out[:, 0]))
        self.assertGreater(env.min() / env.mean(), 0.2)
        self.assertAlmostEqual(len(out) / _length_at(source, rates), 1.0, delta=0.04)

    def test_at_tempo_1_every_engine_leaves_the_title_as_it_is(self):
        for engine in _engines():
            with self.subTest(engine=engine):
                source = _tone(3.0)
                out = _stream(engine, source, [1.0])
                self.assertEqual(len(out), len(source))
                self.assertAlmostEqual(_peak_hz(_middle(out[:, 0])), 440, delta=1)
                self.assertAlmostEqual(_level_db(_middle(out[:, 0])), 0.0, delta=0.1)


class EntryPointsTest(_AppCase):
    """Every way in sets the rate main set. Measured on main (669ebbe2) with
    the same calls; unchanged on this branch."""

    def card(self) -> BigPlayerWidget:
        w = BigPlayerWidget(QMediaPlayer(), QAudioOutput())
        self.addCleanup(reap_widget, w)
        return w

    def rate(self, w) -> float:
        return round(w._tempo_player.playbackRate(), 6)

    # ===== Acceptance criteria =====

    def test_the_tso_target_pitches_as_on_main(self):
        # (takt, target BPM) → (rate, takt the title now plays at)
        main = {(29, 28.0): (0.966, 28.014), (29, 30.0): (1.034, 29.986),
                (50, 52.0): (1.04, 52.0), (25, 30.0): (1.16, 29.0),
                (60, 50.0): (0.84, 50.4)}
        for (takt, target), (rate, plays) in main.items():
            with self.subTest(takt=takt, target=target):
                w = self.card()
                w._takt = takt
                got = w.set_tempo_to_target(target)
                self.assertEqual(self.rate(w), rate)
                self.assertAlmostEqual(got, plays, places=6)

    def test_the_takt_correction_pitches_as_on_main(self):
        # (fader before, ♪ correction %) → rate
        main = {(0, 3.5): 1.035, (0, -2.0): 0.98, (100, 5.0): 1.155,
                (-150, -5.0): 0.84, (150, 10.0): 1.16}
        for (start, pct), rate in main.items():
            with self.subTest(start=start, pct=pct):
                w = self.card()
                w._tempo.setValue(start)
                w.apply_tempo()
                w.apply_takt_correction(pct)
                self.assertEqual(self.rate(w), rate)

    def test_a_controller_knob_pitches_as_on_main(self):
        main = {-1.0: 0.84, -0.5: 0.92, 0.0: 1.0, 0.33: 1.053, 1.0: 1.16}
        for knob, rate in main.items():
            with self.subTest(knob=knob):
                w = self.card()
                w.set_tempo_from_knob(knob)
                w.apply_tempo()
                self.assertEqual(self.rate(w), rate)

    def test_the_desk_steps_pitch_as_on_main(self):
        # Steps (− negative) → rate; 40 steps stop nowhere near the end.
        main = {1: 1.001, 3: 1.003, -2: 0.998, 40: 1.04}
        for steps, rate in main.items():
            with self.subTest(steps=steps):
                w = self.card()
                for _ in range(abs(steps)):
                    w.step_tempo(steps > 0)
                w.apply_tempo()
                self.assertEqual(self.rate(w), rate)

    # ===== Core behavior =====

    def test_the_reset_brings_the_title_back_to_its_own_tempo(self):
        w = self.card()
        w._tempo.setValue(120)
        w.apply_tempo()
        w.reset_tempo()
        self.assertEqual(self.rate(w), 1.0)

    def test_every_rate_change_is_announced_before_it_lands(self):
        """The timed cut books the tempo's history from it (tempoChanging)."""
        w = self.card()
        seen = []
        w.tempoChanging.connect(lambda old, new, pos: seen.append((old, new)))
        w._tempo.setValue(80)
        w.apply_tempo()
        self.assertEqual(len(seen), 1)
        self.assertAlmostEqual(seen[0][0], 1.0)
        self.assertAlmostEqual(seen[0][1], 1.08)


class FloorTimeTest(unittest.TestCase):
    """The play length is floor time: how long the couples dance."""

    # ===== Acceptance criteria =====

    def test_at_one_tempo_the_floor_time_is_mains(self):
        # (position ms, silence skipped ms, rate) → seconds, measured on main.
        main = {(105000, 0, 1.16): 90.51724137931035, (105000, 0, 0.84): 125.0,
                (60000, 8000, 1.0): 52.0, (90000, 2500, 1.08): 81.01851851851852,
                (5000, 8000, 0.92): 0.0, (0, 0, 0.0): 0.0}
        for args, secs in main.items():
            with self.subTest(args=args):
                self.assertAlmostEqual(audible_played_secs(*args), secs, places=9)

    # ===== Core behavior =====

    def test_a_late_tempo_change_keeps_what_was_danced(self):
        """Log 2026-11-21 12:56, "Fragil": 79.83 s at 1.0, then −16 % to the
        cut at 92290 ms is 94.7 s, as long as it played at 1.0 the time
        before. Main read all of it at 0.84 (109.9 s) and cut at once."""
        shift = tempo_shift_secs(79830, 0, 1.0, 0.84)
        self.assertAlmostEqual(audible_played_secs(92290, 0, 0.84, shift),
                               79.83 + 12.46 / 0.84, places=6)

    # ===== Coverage and null checks =====

    def test_a_change_to_the_same_tempo_shifts_nothing(self):
        self.assertEqual(tempo_shift_secs(60000, 4000, 1.08, 1.08), 0.0)


class TapsTest(_AppCase):
    """Which tempo the music gets per ⏩ Tempo choice and EQ: untapped is Qt's
    own (the path main had for every title)."""

    def setUp(self):
        self.addCleanup(stretch_engines.set_engine, stretch_engines.chosen())
        # A tapped music stream starts the audio thread; left running, the
        # process aborts at exit (exit 127 after "OK").
        self.addCleanup(pair_route.stop_audio_thread)
        self.desk = _Desk()
        patcher = mock.patch("player.audio.eq.available", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def music(self, engine: str, eq_on: bool):
        stretch_engines.set_engine(engine)
        cfg = eqs.default_eq("music")
        cfg["on"] = eq_on
        self.desk.settings["equalizer"] = {"music": cfg}
        self.desk.device.sync_eq()
        return self.desk.device._music_eq

    # ===== Acceptance criteria =====

    def test_qt_with_the_eq_off_stays_untapped_as_on_main(self):
        self.assertIsNone(self.music("qt", eq_on=False))

    def test_the_apps_own_engines_tap_the_music_without_an_eq(self):
        for engine in ("signalsmith", "rubberband"):
            with self.subTest(engine=engine):
                self.assertEqual(self.music(engine, eq_on=False), ())

    # ===== Core behavior =====

    def test_qt_with_the_eq_on_taps_the_music(self):
        self.assertTrue(self.music("qt", eq_on=True))


class RouteTest(_RouteCase):
    """A tapped title through the route, per ⏩ Tempo choice: the engine it
    gets, and the tempo and pitch that come out."""

    # The engine a tapped title gets per choice (Qt's own is Signalsmith).
    WANT = {"qt": "signalsmith", "signalsmith": "signalsmith", "rubberband": "rubberband"}

    def setUp(self):
        self.addCleanup(stretch_engines.set_engine, stretch_engines.chosen())
        super().setUp()

    def check(self, choice: str, rate: float = 1.08):
        """A 3 s tone through the route under `choice` at `rate`."""
        engine = self.WANT[choice]
        if engine not in _engines():
            self.skipTest(f"{engine} not on this machine")
        stretch_engines.set_engine(choice)
        self.route.set_device(self.card, 1)
        self.player.go(QMediaPlayer.PlaybackState.PlayingState)
        self.player.setPlaybackRate(rate)
        pump = self.route._pump
        if hasattr(pump._stretch, "ready"):
            pump._stretch.ready(5.0)
        source = _tone(3.0)
        out = [pump._at_tempo(source[i:i + _PIECE]) for i in range(0, len(source), _PIECE)]
        out.append(pump._stretch.flush())
        mono = np.vstack(out)[:, 0]
        self.assertEqual(pump._stretch.engine, engine)
        self.assertAlmostEqual(len(mono) / (len(source) / rate), 1.0, delta=0.01)
        if engine != "rubberband":   # see the module docstring
            self.assertAlmostEqual(_peak_hz(_middle(mono)), 440, delta=1)

    # ===== Acceptance criteria =====

    def test_qt_with_the_eq_on_keeps_the_pitch_on_a_tapped_title(self):
        self.check("qt")

    def test_signalsmith_keeps_the_pitch_on_a_tapped_title(self):
        self.check("signalsmith")

    def test_rubberband_plays_a_tapped_title_at_its_tempo(self):
        self.check("rubberband")


if __name__ == "__main__":
    unittest.main()
