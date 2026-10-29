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
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtCore import QByteArray, QObject, Signal
from PySide6.QtMultimedia import QAudioBuffer, QAudioFormat, QMediaPlayer, QtAudio
from PySide6.QtWidgets import QApplication

from player.audio import pair_route
from player.audio.pair_route import PairRoute
from shared.audio.playback import choice_pair, output_key, pair_label, split_output_key

_RATE = 48000
_PIECE = 4458   # frames Qt hands over at a time, about 93 ms


def _fmt(channels: int) -> QAudioFormat:
    fmt = QAudioFormat()
    fmt.setSampleRate(_RATE)
    fmt.setChannelCount(channels)
    fmt.setSampleFormat(QAudioFormat.SampleFormat.Float)
    return fmt


class _Card:
    """Stands in for a QAudioDevice of `channels` channels."""

    def __init__(self, key: str, channels: int):
        self._id = key.encode()
        self._fmt = _fmt(channels)

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

    def __init__(self):
        super().__init__()
        self.out = None
        self.tap = None
        self.state = QMediaPlayer.PlaybackState.StoppedState
        self.status = QMediaPlayer.MediaStatus.LoadedMedia
        self.rate = 1.0

    def playbackRate(self):
        return self.rate

    def setAudioOutput(self, out):
        self.out = out

    def audioOutput(self):
        return self.out

    def setAudioBufferOutput(self, tap):
        self.tap = tap

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
        self.player, self.out = _Player(), _Out()
        self.route = PairRoute(self.player, self.out)
        self.card = _Card("umc404hd", 4)

    def feed(self, n: int, first_us: int = 0):
        """`n` pieces in a row, from `first_us` on."""
        for i in range(n):
            self.route._on_buffer(_piece(first_us + i * _us(_PIECE)))

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
        self.route._on_buffer(_piece(30_000_000))
        self.assertTrue(first.stopped)
        self.assertEqual(len(self.route._pending), _PIECE * 16, "only the new piece")

    def test_a_stop_is_silent_at_once(self):
        self.feed(2)
        self.player.go(QMediaPlayer.PlaybackState.StoppedState)
        self.settle()
        self.assertTrue(self.sink.stopped)
        self.assertEqual(self.route._pending, bytearray())

    def test_a_stop_while_still_buffered_is_a_stop(self):
        # Qt's real order: Stopped arrives while the status is still Buffered
        self.player.status = QMediaPlayer.MediaStatus.BufferedMedia
        self.feed(2)
        self.player.go(QMediaPlayer.PlaybackState.StoppedState)
        self.assertFalse(self.sink.stopped, "not before the status had its say")
        self.settle()
        self.assertTrue(self.sink.stopped)

    def test_a_play_right_after_a_stop_keeps_the_card(self):
        self.feed(2)
        self.player.go(QMediaPlayer.PlaybackState.StoppedState)
        self.player.go(QMediaPlayer.PlaybackState.PlayingState)
        self.settle()
        self.assertFalse(self.sink.stopped)

    def test_an_empty_closing_piece_is_ignored(self):
        self.feed(2)
        queued = len(self.route._pending) + len(self.sink.data)
        self.route._on_buffer(QAudioBuffer())
        self.assertEqual(len(self.route._pending) + len(self.sink.data), queued)

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
        self.route._flush()
        self.assertTrue(self.sink.stopped, "played out: the card is let go")

    def test_the_next_title_follows_the_tail(self):
        self.feed(2)
        self.player.go(QMediaPlayer.PlaybackState.StoppedState,
                       QMediaPlayer.MediaStatus.EndOfMedia)
        sink = self.sink
        self.player.go(QMediaPlayer.PlaybackState.PlayingState)
        self.route._on_buffer(_piece(0))   # the next title from its top
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
        before = len(self.route._pending) + len(self.sink.data)
        self.route._on_buffer(_piece((2 + i) * _us(_PIECE)))
        return (len(self.route._pending) + len(self.sink.data) - before) // 16

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
    the route plays it faster or slower, the pitch moving with it."""

    def setUp(self):
        super().setUp()
        self.route.set_device(self.card, 1)
        self.player.go(QMediaPlayer.PlaybackState.PlayingState)

    def ramp(self, first: int, frames: int = _PIECE) -> np.ndarray:
        """Stereo frames whose value is their frame number in the title."""
        n = np.arange(first, first + frames, dtype=np.float32)
        return np.column_stack([n, -n])

    def test_at_normal_tempo_nothing_is_touched(self):
        out = self.route._at_tempo(self.ramp(0))
        np.testing.assert_array_equal(out, self.ramp(0))

    def test_a_faster_tempo_plays_fewer_frames(self):
        self.player.rate = 1.25
        total = sum(len(self.route._at_tempo(self.ramp(i * _PIECE)))
                    for i in range(40))
        self.assertAlmostEqual(total, 40 * _PIECE / 1.25, delta=1)

    def test_a_slower_tempo_plays_more_frames(self):
        self.player.rate = 0.8
        total = sum(len(self.route._at_tempo(self.ramp(i * _PIECE)))
                    for i in range(40))
        self.assertAlmostEqual(total, 40 * _PIECE / 0.8, delta=1)

    def test_no_seam_between_pieces(self):
        # Every output frame steps `rate` frames into the title, across
        # the joins between pieces too: no click where a piece ends.
        for rate in (0.93, 1.1, 1.25):
            with self.subTest(rate=rate):
                self.route._drop()
                self.player.rate = rate
                out = np.vstack([self.route._at_tempo(self.ramp(i * _PIECE))
                                 for i in range(5)])
                steps = np.diff(out[:, 0].astype(np.float64))
                np.testing.assert_allclose(steps, rate, atol=1e-2)
                np.testing.assert_allclose(out[:, 1], -out[:, 0])

    def test_the_card_gets_the_title_at_its_tempo(self):
        self.player.rate = 2.0
        self.feed(4)                       # 372 ms of the title, 186 ms heard
        self.assertEqual(len(self.sink.frames()), 2 * _PIECE)

    def test_a_seek_starts_afresh(self):
        self.player.rate = 1.1
        self.route._at_tempo(self.ramp(0))
        self.route._drop()
        out = self.route._at_tempo(self.ramp(1000))
        self.assertEqual(out[0, 0], 1000.0, "not bent towards the old place")


if __name__ == "__main__":
    unittest.main()
