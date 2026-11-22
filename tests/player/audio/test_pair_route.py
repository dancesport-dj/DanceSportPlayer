#!/usr/bin/env python3
"""🔀 A source on one channel pair of a multichannel card.

Run:  .venv/Scripts/python.exe -m unittest tests.player.audio.test_pair_route -v

A tester's Behringer UMC404HD shows up in Windows as ONE device with four
channels, so its outputs 3/4 could not be chosen for anything: Qt plays a
stereo title onto channels 1/2 and nowhere else. A source put on "Out 3/4"
now has its decoded audio laid onto channels 3/4 of a four-channel stream.
Runs against a stub player, a stub card and a stub sink: nothing here opens a
real sound device.
"""
import os
import threading
import time
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtCore import QByteArray, QEvent, QObject, QThread, Signal
from PySide6.QtMultimedia import QAudioBuffer, QAudioFormat, QMediaPlayer, QtAudio
from PySide6.QtWidgets import QApplication

from player.audio import pair_route
from player.audio.eq import Band
from player.audio.pair_route import PairRoute
from shared.audio.playback import choice_pair, output_key, pair_label, split_output_key

_RATE = 48000
_PIECE = 4458   # frames Qt hands over at a time, about 93 ms


def _fmt(channels: int, rate: int = _RATE) -> QAudioFormat:
    fmt = QAudioFormat()
    fmt.setSampleRate(rate)
    fmt.setChannelCount(channels)
    fmt.setSampleFormat(QAudioFormat.SampleFormat.Float)
    return fmt


class _Card:
    """Stands in for a QAudioDevice of `channels` channels."""

    def __init__(self, key: str, channels: int, rate: int = _RATE):
        self._id = key.encode()
        self._fmt = _fmt(channels, rate)

    def id(self):
        return self._id

    def description(self):
        return "Speakers (%s)" % self._id.decode()

    def preferredFormat(self):
        return self._fmt

    def isFormatSupported(self, fmt):
        return fmt.channelCount() <= self._fmt.channelCount()


class _Player(QObject):
    """A QMediaPlayer: what it is attached to, and its state."""

    playbackStateChanged = Signal(object)
    mediaStatusChanged = Signal(object)
    playbackRateChanged = Signal(float)

    def __init__(self):
        super().__init__()
        self.out = None
        self.tap = None
        self.state = QMediaPlayer.PlaybackState.StoppedState
        self.status = QMediaPlayer.MediaStatus.LoadedMedia
        self.rate = 1.0
        # Measured on Qt 6.12's FFmpeg backend: a playing player left with
        # neither output for a moment loses its renderer, and a tap attached
        # after that gets nothing for the rest of the title.
        self.went_bare = False

    def _check_bare(self):
        if (self.out is None and self.tap is None
                and self.state != QMediaPlayer.PlaybackState.StoppedState):
            self.went_bare = True

    def playbackRate(self):
        return self.rate

    def setPlaybackRate(self, rate):
        self.rate = rate
        self.playbackRateChanged.emit(rate)

    def setAudioOutput(self, out):
        self.out = out
        self._check_bare()

    def audioOutput(self):
        return self.out

    def setAudioBufferOutput(self, tap):
        self.tap = tap
        if tap is not None:
            # Measured on Qt 6.12: ANY tap it was once given, deleted, clears
            # the one it has now, and the title goes silent.
            tap.destroyed.connect(self._lose_tap)
        self._check_bare()

    def _lose_tap(self, *_):
        self.tap = None

    def playbackState(self):
        return self.state

    def mediaStatus(self):
        return self.status

    def go(self, state, status=None):
        """In Qt's own order: the state first, then the media status."""
        self.state = state
        self.playbackStateChanged.emit(state)
        if status is not None:
            self.status = status
            self.mediaStatusChanged.emit(status)


class _Out(QObject):
    """A QAudioOutput: the source's level and the device it was given."""

    volumeChanged = Signal(float)
    mutedChanged = Signal(bool)

    def __init__(self):
        super().__init__()
        self.dev = None
        self._vol = 1.0

    def setDevice(self, dev):
        self.dev = dev

    def device(self):
        return self.dev

    def volume(self):
        return self._vol

    def setVolume(self, v):
        self._vol = v
        self.volumeChanged.emit(v)

    def isMuted(self):
        return False


class _Io:
    def __init__(self, sink):
        self._sink = sink

    def write(self, data: bytes) -> int:
        n = min(len(data), self._sink.bytesFree())
        self._sink.data += data[:n]
        return n


class _Sink:
    """A QAudioSink: what was written to it, nothing played."""

    made: list = []

    def __init__(self, device, fmt, parent=None):
        self.device, self.fmt = device, fmt
        self.data = bytearray()
        self.size = 0
        self.vol = 1.0
        self.stopped = False
        self.status = QtAudio.State.ActiveState
        _Sink.made.append(self)

    def setBufferSize(self, n):
        self.size = n

    def bufferSize(self):
        return self.size

    def bytesFree(self):
        return max(0, self.size - len(self.data))

    def setVolume(self, v):
        self.vol = v

    def start(self):
        return _Io(self)

    def error(self):
        return QtAudio.Error.NoError

    def state(self):
        return self.status

    def suspend(self):
        self.status = QtAudio.State.SuspendedState

    def resume(self):
        self.status = QtAudio.State.ActiveState

    def stop(self):
        self.stopped = True

    def deleteLater(self):
        pass

    def frames(self) -> np.ndarray:
        return np.frombuffer(bytes(self.data), dtype=np.float32).reshape(
            -1, self.fmt.channelCount())

    def play(self, ms: int):
        """The card plays `ms` of what it holds."""
        del self.data[:self.fmt.bytesForDuration(ms * 1000)]


def _piece(start_us: int, left=0.5, right=-0.25, frames=_PIECE) -> QAudioBuffer:
    st = np.empty((frames, 2), dtype=np.float32)
    st[:, 0], st[:, 1] = left, right
    return QAudioBuffer(QByteArray(st.tobytes()), _fmt(2), start_us)


def _us(frames: int) -> int:
    return frames * 1_000_000 // _RATE


class _RouteCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        _Sink.made = []
        patcher = mock.patch.object(pair_route, "QAudioSink", _Sink)
        patcher.start()
        self.addCleanup(patcher.stop)
        # The worker's half on this thread, in order (WorkerThreadTest runs it apart).
        in_line = mock.patch.object(pair_route, "_USE_WORKER", False)
        in_line.start()
        self.addCleanup(in_line.stop)
        # The pump's mechanics in whole pieces: two pieces make the prebuffer.
        # The depths the card really gets are tuned on the card itself
        # (test_real_playback, the *_first_change_* tests).
        for name, ms in (("_PREBUFFER_MS", 150), ("_SINK_MS", 300), ("_LOW_MS", 80)):
            depth = mock.patch.object(pair_route, name, ms)
            depth.start()
            self.addCleanup(depth.stop)
        self.player, self.out = _Player(), _Out()
        self.route = PairRoute(self.player, self.out)
        self.card = _Card("umc404hd", 4)

    def feed(self, n: int, first_us: int = 0):
        """`n` pieces in a row, from `first_us` on."""
        for i in range(n):
            self.route._pump.on_buffer(_piece(first_us + i * _us(_PIECE)))

    def settle(self):
        """Lets the calls the route deferred run."""
        QApplication.processEvents()

    @property
    def sink(self) -> _Sink:
        return _Sink.made[-1]


class HelperTest(unittest.TestCase):

    def test_a_pair_is_named_the_way_the_card_names_it(self):
        self.assertEqual(pair_label(1), "Out 3/4")
        self.assertEqual(pair_label(2), "Out 5/6")

    def test_picker_key_carries_the_pair(self):
        self.assertEqual(output_key("ab12", 0), "ab12")
        self.assertEqual(split_output_key(output_key("ab12", 1)), ("ab12", 1))
        self.assertEqual(split_output_key("ab12"), ("ab12", 0))

    def test_a_choice_without_a_pair_is_the_whole_device(self):
        self.assertEqual(choice_pair({"id": "ab"}), 0)
        self.assertEqual(choice_pair({"id": "ab", "pair": 1}), 1)
        self.assertEqual(choice_pair({"id": "ab", "pair": "3"}), 0)
        self.assertEqual(choice_pair({"id": "ab", "pair": -1}), 0)


class WholeDeviceTest(_RouteCase):
    """Pair 0 is Qt's own path, exactly as before."""

    def test_the_whole_device_goes_to_the_audio_output(self):
        self.player.setAudioOutput(self.out)
        self.route.set_device(self.card)
        self.assertIs(self.out.dev, self.card)
        self.assertIs(self.player.out, self.out)
        self.assertIsNone(self.player.tap)
        self.assertFalse(self.route._wired)

    def test_release_and_restore(self):
        self.player.setAudioOutput(self.out)
        self.route.release()
        self.assertIsNone(self.player.out)
        self.route.restore()
        self.assertIs(self.player.out, self.out)

    def test_a_pair_the_card_lacks_is_the_whole_card(self):
        stereo = _Card("speakers", 2)
        self.player.setAudioOutput(self.out)
        with self.assertLogs("dancesport.gui.audio", "WARNING"):
            self.route.set_device(stereo, 1)
        self.assertEqual(self.route.pair, 0)
        self.assertIs(self.player.out, self.out)


class PairTest(_RouteCase):

    def setUp(self):
        super().setUp()
        self.route.set_device(self.card, 1)
        self.player.go(QMediaPlayer.PlaybackState.PlayingState)

    def test_the_player_feeds_the_tap_not_its_output(self):
        self.assertIsNone(self.player.out)
        self.assertIs(self.player.tap, self.route._tap)
        self.assertIs(self.out.dev, self.card)

    def test_the_audio_lands_on_channels_3_and_4_only(self):
        self.feed(2)
        frames = self.sink.frames()
        self.assertEqual(self.sink.fmt.channelCount(), 4)
        self.assertTrue(np.all(frames[:, 0:2] == 0.0))
        self.assertTrue(np.all(frames[:, 2] == 0.5))
        self.assertTrue(np.all(frames[:, 3] == -0.25))

    def test_the_card_waits_for_a_prebuffer(self):
        self.feed(1)                       # 93 ms: not yet
        self.assertEqual(_Sink.made, [])
        self.feed(1, first_us=_us(_PIECE))  # 186 ms: start
        self.assertEqual(len(_Sink.made), 1)
        self.assertEqual(len(self.sink.frames()), 2 * _PIECE)

    def test_the_level_follows_the_audio_output(self):
        self.out.setVolume(0.3)
        self.feed(2)
        self.assertAlmostEqual(self.sink.vol, 0.3)
        self.out.setVolume(0.1)            # the owner's fade
        self.assertAlmostEqual(self.sink.vol, 0.1)

    def test_a_seek_drops_what_was_queued(self):
        self.feed(2)
        first = self.sink
        self.route._pump.on_buffer(_piece(30_000_000))
        self.assertTrue(first.stopped)
        self.assertEqual(len(self.route._pump._pending), _PIECE * 16, "only the new piece")

    def test_a_stop_is_silent_at_once(self):
        self.feed(2)
        self.player.go(QMediaPlayer.PlaybackState.StoppedState)
        self.settle()
        self.assertTrue(self.sink.stopped)
        self.assertEqual(self.route._pump._pending, bytearray())

    def test_a_stop_while_still_buffered_is_a_stop(self):
        # Qt's real order: Stopped arrives while the status is still Buffered
        self.player.status = QMediaPlayer.MediaStatus.BufferedMedia
        self.feed(2)
        self.player.go(QMediaPlayer.PlaybackState.StoppedState)
        self.assertFalse(self.sink.stopped, "not before the status had its say")
        self.settle()
        self.assertTrue(self.sink.stopped)

    def test_a_play_right_after_a_stop_cuts_off_the_old_queue(self):
        """The same title stopped and played again, no reload: what the stop
        left queued would play on at the level the play brings back."""
        self.feed(2)
        first = self.sink
        self.player.go(QMediaPlayer.PlaybackState.StoppedState)
        self.player.go(QMediaPlayer.PlaybackState.PlayingState)
        self.assertTrue(first.stopped)
        self.assertEqual(self.route._pump._pending, bytearray())

    def test_a_play_right_after_a_stop_keeps_what_it_plays(self):
        self.feed(2)
        self.player.go(QMediaPlayer.PlaybackState.StoppedState)
        self.player.go(QMediaPlayer.PlaybackState.PlayingState)
        self.feed(2)                       # the replay, from the start
        self.settle()
        self.assertFalse(self.sink.stopped)
        self.assertEqual(len(self.sink.frames()), 2 * _PIECE)

    def test_a_replay_after_a_natural_end_keeps_the_tail(self):
        self.feed(1)
        self.player.go(QMediaPlayer.PlaybackState.StoppedState,
                       QMediaPlayer.MediaStatus.EndOfMedia)
        self.player.go(QMediaPlayer.PlaybackState.PlayingState)
        self.settle()
        self.assertFalse(self.sink.stopped, "the last bit is still heard")

    def test_the_next_title_cuts_off_what_the_last_one_still_queued(self):
        """Marcel: "a short loud bit of the old title" after a fade. ⏭ loads
        and plays the next title before the deferred drop runs, so the old
        queue played on at the level the new title brings back."""
        self.feed(2)
        first = self.sink
        self.player.go(QMediaPlayer.PlaybackState.StoppedState,
                       QMediaPlayer.MediaStatus.LoadingMedia)
        self.player.go(QMediaPlayer.PlaybackState.PlayingState)
        self.assertTrue(first.stopped)
        self.assertEqual(self.route._pump._pending, bytearray())

    def test_a_title_loaded_over_a_playing_one_cuts_off_its_queue(self):
        """A new source with no stop reported first: the load itself drops
        what the old title queued (the test above is also caught by the
        drop on Playing, which this case never reaches)."""
        self.feed(2)
        first = self.sink
        self.player.status = QMediaPlayer.MediaStatus.LoadingMedia
        self.player.mediaStatusChanged.emit(QMediaPlayer.MediaStatus.LoadingMedia)
        self.assertTrue(first.stopped)
        self.assertEqual(self.route._pump._pending, bytearray())

    def test_the_next_title_after_a_natural_end_keeps_the_tail(self):
        self.feed(1)
        self.player.go(QMediaPlayer.PlaybackState.StoppedState,
                       QMediaPlayer.MediaStatus.EndOfMedia)
        self.player.go(QMediaPlayer.PlaybackState.StoppedState,
                       QMediaPlayer.MediaStatus.LoadingMedia)
        self.settle()
        self.assertFalse(self.sink.stopped, "the last title's tail is still heard")

    def test_a_level_pushed_after_a_stop_waits_for_the_next_play(self):
        """Marcel: still "a short bit of the old title" at a fade's end, only
        with the music tapped. The queue goes a moment after the stop; a
        level the app pushes in between played the old tail loud."""
        self.out.setVolume(0.05)
        self.feed(2)
        self.player.go(QMediaPlayer.PlaybackState.StoppedState)
        self.out.setVolume(0.8)
        self.assertAlmostEqual(self.sink.vol, 0.05)
        self.player.go(QMediaPlayer.PlaybackState.PlayingState)
        self.feed(2)
        self.assertAlmostEqual(self.sink.vol, 0.8)

    def test_a_level_raised_over_queued_audio_is_logged(self):
        """Marcel still hears a loud bit at a fade's end: the log must say
        whether a level push met audio still queued (the old title's tail)."""
        self.out.setVolume(0.05)
        self.feed(2)
        with self.assertLogs("dancesport.gui.audio", "INFO") as logs:
            self.out.setVolume(0.8)
        self.assertTrue(any("Level raised over queued audio" in line
                            for line in logs.output), logs.output)

    def test_a_piece_over_full_scale_is_logged_once_per_title(self):
        with self.assertLogs("dancesport.gui.audio", "INFO") as logs:
            for i in range(3):
                self.route._pump.on_buffer(_piece(i * _us(_PIECE), left=1.4))
        self.assertEqual(sum("over full scale" in line for line in logs.output), 1)

    def test_an_empty_closing_piece_is_ignored(self):
        self.feed(2)
        queued = len(self.route._pump._pending) + len(self.sink.data)
        self.route._pump.on_buffer(QAudioBuffer())
        self.assertEqual(len(self.route._pump._pending) + len(self.sink.data), queued)

    def test_the_end_of_a_title_plays_its_tail(self):
        self.feed(1)                       # below the prebuffer
        self.player.status = QMediaPlayer.MediaStatus.BufferedMedia
        self.player.go(QMediaPlayer.PlaybackState.StoppedState,
                       QMediaPlayer.MediaStatus.EndOfMedia)
        self.settle()
        self.assertEqual(len(_Sink.made), 1, "the short tail is still heard")
        self.assertEqual(len(self.sink.frames()), _PIECE)
        self.assertFalse(self.sink.stopped)
        self.sink.data.clear()
        self.sink.status = QtAudio.State.IdleState
        self.route._pump._flush()
        self.assertTrue(self.sink.stopped, "played out: the card is let go")

    def test_the_next_title_follows_the_tail(self):
        self.feed(2)
        self.player.go(QMediaPlayer.PlaybackState.StoppedState,
                       QMediaPlayer.MediaStatus.EndOfMedia)
        sink = self.sink
        self.player.go(QMediaPlayer.PlaybackState.PlayingState)
        self.route._pump.on_buffer(_piece(0))   # the next title from its top
        self.assertFalse(sink.stopped)

    def test_pause_holds_the_card_and_play_resumes_it(self):
        self.feed(2)
        self.player.go(QMediaPlayer.PlaybackState.PausedState)
        self.assertEqual(self.sink.status, QtAudio.State.SuspendedState)
        self.player.go(QMediaPlayer.PlaybackState.PlayingState)
        self.assertEqual(self.sink.status, QtAudio.State.ActiveState)

    def test_release_lets_go_of_tap_and_card(self):
        self.feed(2)
        self.route.release()
        self.assertTrue(self.sink.stopped)
        self.assertIsNone(self.player.tap)
        self.assertIsNone(self.player.out)
        self.route.restore()
        self.assertIs(self.player.tap, self.route._tap)
        self.assertIsNone(self.player.out)

    def test_back_to_the_whole_device(self):
        self.feed(2)
        self.route.set_device(self.card, 0)
        self.assertTrue(self.sink.stopped)
        self.assertIsNone(self.player.tap)
        self.assertIs(self.player.out, self.out)

    def test_the_same_choice_again_moves_nothing(self):
        self.feed(2)
        self.route.set_device(_Card("umc404hd", 4), 1)
        self.assertFalse(self.sink.stopped)

    def test_a_card_that_refuses_falls_back_to_the_whole_device(self):
        self.card.isFormatSupported = lambda fmt: False
        with self.assertLogs("dancesport.gui.audio", "WARNING"):
            self.feed(2)
        self.assertEqual(self.route.pair, 0)
        self.assertIs(self.player.out, self.out)


class DriftTest(_RouteCase):
    """The card's clock and the player's drift apart: one frame in a piece
    is added or left out to hold the queue in its band."""

    def setUp(self):
        super().setUp()
        self.route.set_device(self.card, 1)
        self.player.go(QMediaPlayer.PlaybackState.PlayingState)
        self.feed(2)

    def _next(self, i: int) -> int:
        """One more piece; how many frames it added."""
        before = len(self.route._pump._pending) + len(self.sink.data)
        self.route._pump.on_buffer(_piece((2 + i) * _us(_PIECE)))
        return (len(self.route._pump._pending) + len(self.sink.data) - before) // 16

    def test_a_card_running_fast_gets_a_frame_more(self):
        for i in range(60):
            self.sink.play(165)           # drains more than a piece holds
            self.sink.data += bytes(16 * 1000)   # …but not dry
            added = self._next(i)
        self.assertEqual(added, _PIECE + 1)

    def test_a_card_running_slow_gets_a_frame_less(self):
        for i in range(60):
            added = self._next(i)          # nothing played: the queue only grows
            self.sink.play(93)
        self.assertEqual(added, _PIECE - 1)


class TempoTest(_RouteCase):
    """The tempo fader on a routed title: Qt hands over `rate` seconds of
    the title per second, unstretched (measured: 1.2 s per s at 1.2), so
    the route makes the tempo, the pitch kept (player.audio.stretch)."""

    def setUp(self):
        super().setUp()
        self.route.set_device(self.card, 1)
        self.player.go(QMediaPlayer.PlaybackState.PlayingState)

    def ramp(self, first: int, frames: int = _PIECE) -> np.ndarray:
        """Stereo frames whose value is their frame number in the title."""
        n = np.arange(first, first + frames, dtype=np.float32)
        return np.column_stack([n, -n])

    def test_at_normal_tempo_nothing_is_touched(self):
        out = self.route._pump._at_tempo(self.ramp(0))
        np.testing.assert_array_equal(out, self.ramp(0))

    def sine(self, first: int, freq: float = 440.0) -> np.ndarray:
        t = np.arange(first, first + _PIECE) / _RATE
        mono = (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
        return np.column_stack([mono, mono])

    def test_the_pitch_stays_where_it_was(self):
        for rate in (0.95, 1.05):
            with self.subTest(rate=rate):
                self.route._pump.drop()
                self.player.setPlaybackRate(rate)
                out = np.vstack([self.route._pump._at_tempo(self.sine(i * _PIECE))
                                 for i in range(20)])[:, 0]
                spectrum = np.abs(np.fft.rfft(out * np.hanning(len(out))))
                peak = np.fft.rfftfreq(len(out), 1 / _RATE)[np.argmax(spectrum)]
                self.assertAlmostEqual(peak, 440, delta=3)

    def test_a_faster_tempo_plays_fewer_frames(self):
        self.player.setPlaybackRate(1.25)
        total = sum(len(self.route._pump._at_tempo(self.ramp(i * _PIECE)))
                    for i in range(40))
        self.assertAlmostEqual(total, 40 * _PIECE / 1.25, delta=self.held() / 1.25)

    def test_a_slower_tempo_plays_more_frames(self):
        self.player.setPlaybackRate(0.8)
        total = sum(len(self.route._pump._at_tempo(self.ramp(i * _PIECE)))
                    for i in range(40))
        self.assertAlmostEqual(total, 40 * _PIECE / 0.8, delta=self.held() / 0.8)

    def test_the_card_gets_the_title_at_its_tempo(self):
        self.player.setPlaybackRate(2.0)
        self.feed(6)                       # 557 ms of the title, 279 ms heard
        heard = len(self.sink.frames())
        self.assertLessEqual(heard, 3 * _PIECE)
        self.assertGreater(heard, 3 * _PIECE - self.held() / 2.0)

    def test_the_end_of_the_title_lets_out_what_the_stretch_holds(self):
        self.player.setPlaybackRate(1.05)
        self.feed(4)
        pump = self.route._pump
        queued = lambda: len(self.sink.data) + len(pump._pending)   # noqa: E731
        held = queued()
        pump.end()
        self.assertGreater(queued(), held)
        self.assertFalse(self.route._pump._stretch.holding)

    def test_a_seek_starts_afresh(self):
        self.player.setPlaybackRate(1.1)
        for i in range(8):
            self.route._pump._at_tempo(self.ramp(i * _PIECE))
        self.route._pump.drop()
        self.assertFalse(self.route._pump._stretch.holding)

    def held(self) -> int:
        """Title frames the stretch holds back at most (heard: ÷ tempo)."""
        return self.route._pump._stretch.lookahead


class EqRouteTest(_RouteCase):
    """🎚 The EQ taps the player on the whole device too: a stereo sink at
    the card's rate, the pieces filtered on the way."""

    # A low shelf far above anything in a constant piece: −12 dB on all of it,
    # once the switch-on fade (one piece) is past.
    _CUT = (Band("lowshelf", 1000, -12.0),)

    def setUp(self):
        super().setUp()
        self.stereo = _Card("speakers", 2)
        self.player.setAudioOutput(self.out)
        self.route.set_device(self.stereo)
        self.player.go(QMediaPlayer.PlaybackState.PlayingState)

    def eq(self, bands):
        self.route.set_eq(bands)

    # ===== Acceptance criteria =====

    def test_on_while_playing_is_heard_on_this_title(self):
        """Marcel: on/off must apply to the title playing, not the next one,
        or the adjustment can't be heard."""
        self.route.set_eq(self._CUT)
        self.assertTrue(self.route.tapped)
        self.assertIs(self.player.tap, self.route._tap)
        self.assertIsNone(self.player.out)

    def test_the_player_is_never_left_without_an_output_while_playing(self):
        """Marcel: "music is still when equalizer on". Qt drops the renderer
        of a playing player that goes without both outputs; the tap attached
        after it then stays silent."""
        self.route.set_eq(self._CUT)
        self.route.set_device(_Card("headphones", 2))
        self.route.set_eq(None)
        self.assertFalse(self.player.went_bare)

    def test_on_again_after_off_keeps_the_tap(self):
        """Marcel: from Qt's own tempo to another, OK, and no music any more.
        Qt clears the player's tap when an earlier one is deleted."""
        self.route.set_eq(self._CUT)
        self.route.set_eq(None)
        self.route.set_eq(self._CUT)
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.assertIsNotNone(self.player.tap)
        self.assertIs(self.player.tap, self.route._tap)

    def test_off_while_playing_hands_back_to_qt_on_this_title(self):
        self.eq(self._CUT)
        self.route.set_eq(None)
        self.assertFalse(self.route.tapped)
        self.assertIs(self.player.out, self.out)
        self.assertIsNone(self.player.tap)

    def test_the_eq_takes_the_player_off_qts_output(self):
        self.eq(self._CUT)
        self.assertTrue(self.route.tapped)
        self.assertIsNone(self.player.out)
        self.assertIs(self.player.tap, self.route._tap)

    def test_the_card_hears_the_filtered_audio_in_stereo(self):
        self.eq(self._CUT)
        self.feed(4)
        frames = self.sink.frames()
        self.assertEqual(self.sink.fmt.channelCount(), 2)
        settled = frames[-500:]
        np.testing.assert_allclose(settled[:, 0], 0.5 * 10 ** (-12 / 20), rtol=0.02)
        np.testing.assert_allclose(settled[:, 1], -0.25 * 10 ** (-12 / 20), rtol=0.02)

    def test_off_hands_the_player_back_to_qt(self):
        self.eq(self._CUT)
        self.feed(2)
        sink = self.sink
        self.eq(None)
        self.assertFalse(self.route.tapped)
        self.assertTrue(sink.stopped)
        self.assertIsNone(self.player.tap)
        self.assertIs(self.player.out, self.out)

    def test_bypass_stays_tapped_and_passes_the_sound(self):
        self.eq(())
        self.feed(2)
        self.assertTrue(self.route.tapped)
        self.assertTrue(np.all(self.sink.frames()[:, 0] == 0.5))

    def test_new_bands_are_heard_without_reopening_the_card(self):
        self.eq(())
        self.feed(2)
        sink = self.sink
        self.eq(self._CUT)
        self.feed(3, first_us=2 * _us(_PIECE))
        self.assertIs(self.sink, sink)
        self.assertFalse(sink.stopped)
        self.assertLess(float(sink.frames()[-1, 0]), 0.2)

    # ===== Core behavior =====

    def test_another_card_moves_the_tapped_whole_device(self):
        """Not the early return of an untapped whole device: the sink moves."""
        self.eq(self._CUT)
        self.feed(2)
        sink = self.sink
        other = _Card("headphones", 2)
        self.route.set_device(other)
        self.assertTrue(sink.stopped)
        self.feed(2, first_us=2 * _us(_PIECE))
        self.assertIs(self.sink.device, other)

    def test_release_and_restore_keep_the_eq_path(self):
        self.eq(self._CUT)
        self.feed(2)
        self.route.release()
        self.assertTrue(self.sink.stopped)
        self.assertIsNone(self.player.tap)
        self.route.restore()
        self.assertIs(self.player.tap, self.route._tap)
        self.assertIsNone(self.player.out)

    def test_pause_and_end_of_title_work_on_the_whole_device(self):
        self.eq(())
        self.feed(2)
        self.player.go(QMediaPlayer.PlaybackState.PausedState)
        self.assertEqual(self.sink.status, QtAudio.State.SuspendedState)
        self.player.go(QMediaPlayer.PlaybackState.PlayingState)
        self.player.go(QMediaPlayer.PlaybackState.StoppedState,
                       QMediaPlayer.MediaStatus.EndOfMedia)
        self.settle()
        self.assertFalse(self.sink.stopped, "the tail is still heard")

    def test_the_level_and_tempo_reach_the_tapped_whole_device(self):
        self.eq(())
        self.out.setVolume(0.4)
        self.player.setPlaybackRate(2.0)
        self.feed(6)
        self.assertAlmostEqual(self.sink.vol, 0.4)
        self.assertEqual(self.route._pump._stretch.rate, 2.0)
        self.assertLessEqual(len(self.sink.frames()), 3 * _PIECE)

    def test_the_filter_is_built_for_the_cards_own_rate(self):
        slow = _Card("cd-rate", 2, rate=44100)
        self.route.set_device(slow)
        self.eq(self._CUT)
        self.assertEqual(self.route._pump._fmt.sampleRate(), 44100)
        self.assertEqual(self.route._pump._eq._rate, 44100)

    # ===== Coverage and null checks =====

    def test_a_card_that_refuses_drops_the_eq_for_qts_output(self):
        self.stereo.isFormatSupported = lambda fmt: False
        self.eq(self._CUT)
        with self.assertLogs("dancesport.gui.audio", "WARNING"):
            self.feed(2)
        self.assertFalse(self.route.tapped)
        self.assertIs(self.player.out, self.out)

    def test_an_untapped_route_never_builds_the_worker_half(self):
        self.assertIsNone(self.route._pump)
        self.eq(None)
        self.assertIsNone(self.route._pump)


class _Feeder(QObject):
    """Hands pieces over from a thread of its own, as Qt's renderer does."""
    piece = Signal(QAudioBuffer)


class WorkerThreadTest(unittest.TestCase):
    """The tapped audio on its own thread: the card keeps getting pieces
    while the GUI thread is busy, and quitting closes it cleanly."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        _Sink.made = []
        patcher = mock.patch.object(pair_route, "QAudioSink", _Sink)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(pair_route.stop_audio_thread)
        self.player, self.out = _Player(), _Out()
        self.route = PairRoute(self.player, self.out)
        self.route.set_device(_Card("speakers", 2))
        self.route.set_eq(())
        self.player.go(QMediaPlayer.PlaybackState.PlayingState)
        self.feeder = _Feeder()
        self.feeder.piece.connect(self.route._pump.on_buffer)

    def _feed_from_a_thread(self, seconds: float, piece_frames: int = 1250):
        """Pieces at their real pace from a Python thread, like the renderer."""
        def run():
            step = piece_frames / _RATE
            t0, i = time.perf_counter(), 0
            while time.perf_counter() - t0 < seconds:
                self.feeder.piece.emit(_piece(i * _us(piece_frames), frames=piece_frames))
                i += 1
                time.sleep(step)
        worker = threading.Thread(target=run)
        worker.start()
        return worker

    def test_the_card_is_fed_while_the_gui_thread_is_busy(self):
        self.assertIsNot(self.route._pump.thread(), QThread.currentThread())
        feeder = self._feed_from_a_thread(1.2)
        time.sleep(0.4)                    # past the prebuffer: the card is open
        # Where in the title the worker stands: it moves with every piece it
        # handled. (The stub card never plays, so its fill says nothing.)
        before = self.route._pump._next_us or 0
        end = time.perf_counter() + 0.6    # busy in Python, no event loop
        while time.perf_counter() < end:
            pass
        handled_ms = ((self.route._pump._next_us or 0) - before) / 1000
        feeder.join()
        self.assertTrue(_Sink.made, "the card opened on the audio thread")
        # On the GUI thread this was 0. The feeder's sleeps run long on
        # Windows (~15 ms steps), so it hands over less than real time itself,
        # and less again with the whole suite on every core (234 ms seen).
        # Anything clearly above 0 shows the stall did not stop the worker.
        self.assertGreater(handled_ms, 100, "the pieces kept coming through the stall")

    def test_quitting_while_playing_closes_the_card_and_the_thread(self):
        feeder = self._feed_from_a_thread(0.5)
        feeder.join()
        thread = pair_route._thread
        pair_route.stop_audio_thread()
        self.assertTrue(thread.isFinished())
        self.assertTrue(all(s.stopped for s in _Sink.made))
        self.assertIsNone(pair_route._thread)


# A real QMediaPlayer: the stub above cannot show what Qt does with a tap.
_TAP_OUTLIVES_PLAYER = """
import shiboken6
from unittest import mock
from PySide6.QtCore import QCoreApplication
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from player.audio import pair_route
app = QCoreApplication([])
with mock.patch.object(pair_route, "_USE_WORKER", False):
    routes = []
    for _ in range(4):
        player, out = QMediaPlayer(), QAudioOutput()
        player.setAudioOutput(out)
        route = pair_route.PairRoute(player, out)
        route.set_eq(())     # tapped
        route.set_eq(None)   # back on Qt's output: the tap is kept
        routes.append(route)
        shiboken6.delete(player)
        for spare in [QMediaPlayer() for _ in range(20)]:   # reuse its memory
            shiboken6.delete(spare)
    for route in routes:
        shiboken6.delete(route)
print("survived")
"""


class TapLifetimeTest(unittest.TestCase):
    """The EQ switched off keeps the tap (a destroyed one silences Qt 6.12's
    player). A tap that outlived its player then pointed into freed memory,
    and destroying its route, at the latest when the process ended, crashed
    (exit 139 after the window had gone)."""

    # ===== Acceptance criteria =====

    def test_a_route_outliving_its_player_goes_without_a_crash(self):
        import subprocess
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parents[3]
        env = dict(os.environ, PYTHONPATH=str(root), QT_QPA_PLATFORM="offscreen")
        done = subprocess.run([sys.executable, "-c", _TAP_OUTLIVES_PLAYER], cwd=root,
                              env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr[-2000:])
        self.assertIn("survived", done.stdout)


if __name__ == "__main__":
    unittest.main()
