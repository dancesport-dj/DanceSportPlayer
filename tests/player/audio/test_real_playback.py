#!/usr/bin/env python3
"""🔊 A title really played, on this PC's sound card, at volume 0.

Run:  .venv/Scripts/python.exe -m unittest tests.player.audio.test_real_playback -v

Everything else stubs the card; this plays a short generated title through
a real QMediaPlayer, start to end: on Qt's own output (main's way), through
the EQ path, and at a tempo on each of the app's engines. It must start,
advance, end, take its length over the tempo in wall time, and never run the
card dry ("Tapped audio ran dry" is a dropout the hall hears).

Needs a sound card, so it is skipped where there is none. Nothing is heard:
the output's volume is 0 (the tapped path's sink takes the same level).
"""
import logging
import math
import os
import struct
import tempfile
import time
import unittest
import wave
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_MEDIA_BACKEND", "ffmpeg")   # as the app (taps need it)

import shiboken6
from PySide6.QtCore import QEventLoop, QTimer, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer
from PySide6.QtWidgets import QApplication

from player.audio import pair_route, stretch_engines
from player.audio.eq import Band
from player.audio.pair_route import PairRoute

_SECONDS = 3.0
_RATE = 44100
# Startup (opening the card, the first pieces) plus the timer's grain.
_SLACK_S = 0.6
_SLACK_PART = 0.08


def _write_title(path: Path):
    """A 440 Hz tone with a click on every beat: something to stretch."""
    frames = int(_SECONDS * _RATE)
    data = bytearray()
    for i in range(frames):
        t = i / _RATE
        v = 0.3 * math.sin(2 * math.pi * 440 * t)
        if (i % (_RATE // 2)) < 200:
            v += 0.4
        s = int(max(-1.0, min(1.0, v)) * 32767)
        data += struct.pack("<hh", s, s)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(_RATE)
        w.writeframes(bytes(data))


class _Lines(logging.Handler):
    def __init__(self):
        super().__init__(logging.INFO)
        self.lines: list[str] = []

    def emit(self, record):
        self.lines.append(record.getMessage())


def _card():
    if os.environ.get("CI"):
        return None
    dev = QMediaDevices.defaultAudioOutput()
    return None if dev.isNull() else dev


class RealPlaybackTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.card = _card()
        if cls.card is None:
            raise unittest.SkipTest("no sound card")
        cls.dir = tempfile.TemporaryDirectory(prefix="dp_real_play_")
        cls.title = Path(cls.dir.name) / "tone.wav"
        _write_title(cls.title)

    @classmethod
    def tearDownClass(cls):
        cls.dir.cleanup()

    def setUp(self):
        self.addCleanup(stretch_engines.set_engine, stretch_engines.chosen())
        self.warnings = _Lines()
        audio_log = logging.getLogger("dancesport.gui.audio")
        audio_log.addHandler(self.warnings)
        self.addCleanup(audio_log.removeHandler, self.warnings)

    def play(self, *, rate=1.0, eq=None, engine=stretch_engines.QT, change_ms=0):
        """Plays the title through; (wall seconds, positions seen, ended).
        With `change_ms` it starts at 1.0 and takes `rate` that far in, as a
        DJ's first nudge of a playing title."""
        stretch_engines.set_engine(engine)
        player, out = QMediaPlayer(), QAudioOutput(self.card)
        out.setVolume(0.0)
        player.setAudioOutput(out)
        route = None
        if eq is not None:
            route = PairRoute(player, out)
            route.set_device(self.card)
            route.set_eq(eq)

        def reap():
            player.stop()
            self.app.processEvents()   # the stop's own singleShot, while the route lives
            if route is not None:
                shiboken6.delete(route)
            shiboken6.delete(player)
            shiboken6.delete(out)
        self.addCleanup(reap)
        # As on quit (aboutToQuit): the audio thread ends before the players go.
        self.addCleanup(pair_route.stop_audio_thread)

        loop = QEventLoop()
        positions: list[int] = []
        ended = []

        def on_status(status):
            if status == QMediaPlayer.MediaStatus.LoadedMedia and not positions:
                positions.append(0)
                player.setPlaybackRate(1.0 if change_ms else rate)
                start[0] = time.monotonic()
                player.play()
                if change_ms:
                    QTimer.singleShot(change_ms, lambda: player.setPlaybackRate(rate))
            elif status == QMediaPlayer.MediaStatus.EndOfMedia:
                ended.append(time.monotonic())
                loop.quit()
        start = [0.0]
        player.mediaStatusChanged.connect(on_status)
        player.positionChanged.connect(positions.append)
        QTimer.singleShot(int(3000 * _SECONDS), loop.quit)
        player.setSource(QUrl.fromLocalFile(str(self.title)))
        loop.exec()
        if route is not None:
            self.assertTrue(route.tapped, "the route left the EQ path")
        wall = (ended[0] - start[0]) if ended else float("nan")
        return wall, positions, bool(ended)

    def assert_played(self, wall, positions, ended, rate=1.0):
        self.assertTrue(ended, "no EndOfMedia")
        self.assertGreater(max(positions), 0.8 * _SECONDS * 1000, "it never advanced")
        self.assertEqual(positions, sorted(positions), "the position went back")
        want = _SECONDS / rate
        self.assertLess(abs(wall - want), _SLACK_S + _SLACK_PART * want,
                        "took %.2f s for %.2f s of music" % (wall, want))
        # Both are music the hall did not hear as it was.
        lost = [w for w in self.warnings.lines if "ran dry" in w or "cut back" in w]
        self.assertEqual(lost, [], "audio lost on the way to the card")

    # ===== Acceptance criteria =====

    def test_qts_own_output_plays_it_through(self):
        self.assert_played(*self.play())

    def test_the_eq_path_plays_it_through(self):
        self.assert_played(*self.play(eq=(Band("peak", 1000.0, 4.0, 1.0),)))

    def test_qts_own_tempo_plays_it_faster(self):
        self.assert_played(*self.play(rate=1.08), rate=1.08)

    def test_signalsmith_tempo_plays_it_faster(self):
        self.assert_played(*self.play(rate=1.08, eq=(), engine="signalsmith"), rate=1.08)

    def test_rubber_band_tempo_plays_it_slower(self):
        self.assert_played(*self.play(rate=0.92, eq=(), engine="rubberband"), rate=0.92)

    # ===== Core behavior =====

    def test_the_eq_path_at_qts_tempo_plays_it_faster(self):
        """The EQ on with ⏩ Tempo on Qt's: the app's stretch takes over."""
        self.assert_played(*self.play(rate=1.08, eq=()), rate=1.08)

    # The first ⏩ nudge of a playing title starts the app's stretch, which
    # holds back ~120 ms of audio; at the old 80 ms queue the card ran dry (a
    # dropout). The pump's depths in pair_route carry it.

    def assert_fed(self, wall, positions, ended):
        self.assertTrue(ended, "no EndOfMedia")
        lost = [w for w in self.warnings.lines if "ran dry" in w or "cut back" in w]
        self.assertEqual(lost, [], "audio lost on the way to the card")

    def test_signalsmith_first_change_faster_keeps_the_card_fed(self):
        self.assert_fed(*self.play(rate=1.08, eq=(), engine="signalsmith", change_ms=1500))

    def test_signalsmith_first_change_slower_keeps_the_card_fed(self):
        self.assert_fed(*self.play(rate=0.92, eq=(), engine="signalsmith", change_ms=1500))

    def test_rubber_band_first_change_faster_keeps_the_card_fed(self):
        self.assert_fed(*self.play(rate=1.08, eq=(), engine="rubberband", change_ms=1500))

    def test_rubber_band_first_change_slower_keeps_the_card_fed(self):
        self.assert_fed(*self.play(rate=0.92, eq=(), engine="rubberband", change_ms=1500))


if __name__ == "__main__":
    unittest.main()
