"""🔀 A source on one channel pair of a multichannel card.

Windows lists some cards as ONE device with four or more channels: a
Behringer UMC404HD is "Speakers (UMC404HD 192k)", its outputs 1–4 all on that
one device. Qt plays a stereo title onto the first two channels and cannot be
asked for others, so outputs 3/4 of such a card are out of reach through a
QAudioOutput. (A card whose driver lists each pair as a device of its own, the
MAYA44's "Ch12" and "Ch34", never needs this.)

So for a pair past the first, the player's decoded audio is taken off before
Qt's output (a QAudioBufferOutput, which Qt hands over in real time), laid
onto the two channels asked for with the others silent, and written to a
QAudioSink as wide as the card. Windows mixes it with whatever else plays on
the card, the music on its outputs 1/2 included.

The tempo fader is the one thing that changes on the way: Qt's pitch-kept
time stretch lives in its output, so what comes off before it is the title
at its own pitch, `rate` seconds of it per second. The route plays that
faster or slower, the way a turntable does: on a pair the music's pitch
moves with its tempo. Settings say so, and ask before the music is put on
a pair. Filler, cartwall, announcements and pre-listen have no tempo fader.
"""
import logging

import numpy as np
from PySide6.QtCore import QObject, QTimer, Slot
from PySide6.QtMultimedia import QAudioBuffer, QAudioBufferOutput, QAudioFormat, QAudioSink, QMediaPlayer, QtAudio

from shared.audio.playback import channel_pairs, device_id, pair_label

log = logging.getLogger("dancesport.gui.audio")

# Qt hands the decoded audio over about 93 ms at a time, each piece just as it
# is due. The card starts once this much is in hand, so the next piece is
# there before the last one has played out.
_PREBUFFER_MS = 150
# The sink's own buffer: room for the prebuffer and a piece on top of it.
_SINK_MS = 300
# The player runs on the computer's clock, the card on its own; the two drift
# apart by a few seconds a day. What is queued when a piece arrives is held in
# this band by playing one frame of a piece twice, or leaving one out: one
# sample in 4400, nobody hears it.
_LOW_MS = 80
_BAND_MS = 30
# A queue past this (the event loop stalled) is cut back to the prebuffer.
_MAX_QUEUED_MS = 600
# A piece that does not start where the last one ended: a seek, or a new title
# without a stop in between. What is queued belongs elsewhere then.
_JUMP_US = 50_000
_FLUSH_MS = 10


class PairRoute(QObject):
    """One player's way to its output: its QAudioOutput on a whole device
    (pair 0, Qt's own path, as it always was), or channel pair `pair` of a
    wider card. The QAudioOutput stays the source's level either way: the
    owner fades it as before, and a routed player's sink follows it.

    Nothing of the player is touched until a pair is first asked for, so a
    source on a whole device runs exactly the code it did."""

    def __init__(self, player, out, parent=None):
        super().__init__(parent)
        self._player = player
        self._out = out
        self.pair = 0
        self._device = None
        self._released = False
        self._wired = False
        self._tap: QAudioBufferOutput | None = None
        self._sink: QAudioSink | None = None
        self._io = None
        self._fmt: QAudioFormat | None = None
        self._pending = bytearray()
        self._next_us: int | None = None
        # Off normal tempo: the last frame of the piece before, and where in
        # the next piece the next frame heard is read (see _at_tempo).
        self._last: np.ndarray | None = None
        self._phase = 0.0
        self._draining = False
        self._low: float | None = None
        self._flusher = QTimer(self)
        self._flusher.setInterval(_FLUSH_MS)
        self._flusher.timeout.connect(self._flush)

    def set_device(self, device, pair: int = 0) -> None:
        """Play on `device`: the whole of it, or its channels 2·pair+1 and
        2·pair+2. A pair the card does not have is the whole card."""
        if pair and channel_pairs(device) <= pair:
            log.warning("🔀 Channel pair not on this card\n"
                        "output: %s\n"
                        "asked for: %s\n"
                        "playing on: the whole device",
                        device.description(), pair_label(pair))
            pair = 0
        if pair == self.pair == 0:
            self._device = device
            self._out.setDevice(device)
            return
        if (pair == self.pair and self._device is not None
                and device_id(self._device) == device_id(device)):
            return
        self._out.setDevice(device)   # so out.device() still says where
        self._drop()
        self._device = device
        self.pair = pair
        if not self._released:
            self._attach()
        log.info("🔀 Output on a channel pair\n"
                 "output: %s\n"
                 "channels: %s", device.description(),
                 pair_label(pair) if pair else "the whole device")

    def release(self) -> None:
        """🔇 Let go of the card (see AudioDevice.release)."""
        self._released = True
        self._player.setAudioOutput(None)
        if self._wired:
            self._player.setAudioBufferOutput(None)
        self._drop()

    def restore(self) -> None:
        """Take the card back before anything is heard."""
        if self._released:
            self._released = False
            self._attach()
        elif not self.pair and self._player.audioOutput() is None:
            self._player.setAudioOutput(self._out)

    def _attach(self):
        if not self.pair:
            if self._wired:
                self._player.setAudioBufferOutput(None)
            self._player.setAudioOutput(self._out)
            return
        self._wire()
        self._fmt = self._sink_format(self._device)
        tap_fmt = QAudioFormat()
        tap_fmt.setSampleRate(self._fmt.sampleRate())
        tap_fmt.setChannelCount(2)
        tap_fmt.setSampleFormat(QAudioFormat.SampleFormat.Float)
        old, self._tap = self._tap, QAudioBufferOutput(tap_fmt, self)
        self._tap.audioBufferReceived.connect(self._on_buffer)
        self._player.setAudioOutput(None)
        self._player.setAudioBufferOutput(self._tap)
        if old is not None:
            old.deleteLater()

    def _wire(self):
        if self._wired:
            return
        self._wired = True
        self._player.playbackStateChanged.connect(self._on_state)
        self._player.mediaStatusChanged.connect(self._on_status)
        self._out.volumeChanged.connect(self._apply_volume)
        self._out.mutedChanged.connect(self._apply_volume)

    @staticmethod
    def _sink_format(device) -> QAudioFormat:
        """As wide as the card, at its own rate: nothing for Windows to mix
        down or resample."""
        fmt = QAudioFormat()
        fmt.setSampleRate(device.preferredFormat().sampleRate() or 48000)
        fmt.setChannelCount(2 * channel_pairs(device))
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Float)
        return fmt

    # ── the audio on its way ─────────────────────────────────────────────────

    @Slot(QAudioBuffer)
    def _on_buffer(self, buf: QAudioBuffer):
        if (not self.pair or self._released or self._fmt is None
                or not buf.isValid() or not buf.byteCount()):
            return   # Qt closes a title with an empty piece
        start = buf.startTime()
        if self._draining:
            # A title ran out and the next follows: after its tail, not over it.
            self._draining = False
        elif self._next_us is not None and abs(start - self._next_us) > _JUMP_US:
            self._drop()
        self._next_us = start + buf.duration()
        stereo = np.frombuffer(buf.constData(), dtype=np.float32)
        frames = len(stereo) // 2
        if not frames:
            return
        stereo = self._at_tempo(stereo[:2 * frames].reshape(frames, 2))
        frames = len(stereo)
        if not frames:
            return
        wide = np.zeros((frames, self._fmt.channelCount()), dtype=np.float32)
        first = 2 * self.pair
        wide[:, first:first + 2] = stereo
        self._pending += self._keep_pace(wide).tobytes()
        self._flush()
        if not self._flusher.isActive():
            self._flusher.start()

    def _at_tempo(self, stereo):
        """The piece at the player's tempo: every frame heard is read `rate`
        frames further into the title, between two frames where it falls on
        none (a straight line between them), so the pitch moves with the
        speed. Where the reading stands carries over to the next piece: the
        join is not heard."""
        rate = self._player.playbackRate() or 1.0
        # A copy: the piece's memory is Qt's, gone with the buffer.
        last, self._last = self._last, stereo[-1:].copy()
        if rate == 1.0 and not self._phase:
            return stereo
        # The frame before this piece leads it, so a reading between the
        # two pieces has both of its ends.
        src = np.vstack([stereo[:1] if last is None else last, stereo])
        start = self._phase + 1
        n = max(0, int((len(src) - 1 - start) // rate) + 1)
        self._phase = start + n * rate - len(src)
        at = start + np.arange(n) * rate
        idx = np.arange(len(src))
        return np.column_stack([np.interp(at, idx, src[:, 0]),
                                np.interp(at, idx, src[:, 1])]).astype(np.float32)

    def _keep_pace(self, wide):
        """One frame more or less while the queue strays from its band: the
        two clocks' drift (see _LOW_MS). Measured as a piece arrives, when
        the queue is at its lowest."""
        if self._sink is None or self._fmt is None:
            return wide
        low = self._queued_ms(self._fmt)
        if low <= 0:
            # Ran dry: start over with a full prebuffer rather than limp on.
            self._close()
            return wide
        self._low = low if self._low is None else self._low + 0.05 * (low - self._low)
        if self._low < _LOW_MS - _BAND_MS:
            return np.vstack([wide, wide[-1:]])
        if self._low > _LOW_MS + _BAND_MS and len(wide) > 1:
            return wide[:-1]
        return wide

    def _queued_ms(self, fmt: QAudioFormat) -> float:
        queued = len(self._pending)
        if self._sink is not None:
            queued += self._sink.bufferSize() - self._sink.bytesFree()
        return fmt.durationForBytes(queued) / 1000

    def _flush(self):
        fmt = self._fmt
        if fmt is None:
            return
        if self._io is None:
            if not self._pending:
                self._flusher.stop()
                return
            if (fmt.durationForBytes(len(self._pending)) < _PREBUFFER_MS * 1000
                    and not self._draining):
                return
            if not self._open(fmt):
                return
        sink, io = self._sink, self._io
        if sink is None or io is None:
            return
        if self._queued_ms(fmt) > _MAX_QUEUED_MS:
            cut = len(self._pending) - fmt.bytesForDuration(_PREBUFFER_MS * 1000)
            cut -= cut % fmt.bytesPerFrame()
            if cut > 0:
                del self._pending[:cut]
                log.info("🔀 Channel pair queue cut back\n"
                         "dropped: %d ms", fmt.durationForBytes(cut) // 1000)
        n = min(len(self._pending), sink.bytesFree())
        n -= n % fmt.bytesPerFrame()
        if n > 0:
            written = io.write(bytes(self._pending[:n]))
            if written > 0:
                del self._pending[:written]
        if (self._draining and not self._pending
                and sink.state() == QtAudio.State.IdleState):
            self._close()   # the tail has played out: the card is free again

    def _open(self, fmt: QAudioFormat) -> bool:
        device = self._device
        if device is None:
            return False
        if not device.isFormatSupported(fmt):
            self._give_up(device, "the card refuses %d channels" % fmt.channelCount())
            return False
        sink = QAudioSink(device, fmt, self)
        sink.setBufferSize(fmt.bytesForDuration(_SINK_MS * 1000))
        sink.setVolume(self._level())
        io = sink.start()
        if io is None or sink.error() != QtAudio.Error.NoError:
            sink.deleteLater()
            self._give_up(device, "the card did not open (%s)" % sink.error())
            return False
        self._sink, self._io, self._low = sink, io, None
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            sink.suspend()
        return True

    def _give_up(self, device, why: str):
        """The pair cannot be played: the whole card rather than silence."""
        log.warning("🔀 Channel pair unavailable\n"
                    "output: %s\n"
                    "reason: %s\n"
                    "playing on: the whole device", device.description(), why)
        self._drop()
        self.pair = 0
        if not self._released:
            self._attach()

    def _close(self):
        if self._sink is not None:
            self._sink.stop()
            self._sink.deleteLater()
        self._sink = self._io = None
        self._low = None

    def _drop(self):
        """Nothing queued is to be heard any more: a stop, a seek, a move."""
        self._pending.clear()
        self._next_us = None
        self._last, self._phase = None, 0.0
        self._draining = False
        self._close()
        self._flusher.stop()

    # ── following the player ─────────────────────────────────────────────────

    def _level(self) -> float:
        return 0.0 if self._out.isMuted() else self._out.volume()

    def _apply_volume(self, *_):
        if self._sink is not None:
            self._sink.setVolume(self._level())

    def _on_state(self, state):
        if not self.pair:
            return
        if state == QMediaPlayer.PlaybackState.PausedState:
            if self._sink is not None:
                self._sink.suspend()
        elif state == QMediaPlayer.PlaybackState.PlayingState:
            if (self._sink is not None
                    and self._sink.state() == QtAudio.State.SuspendedState):
                self._sink.resume()
        else:
            # Qt reports Stopped before EndOfMedia, so only after both have
            # landed can a stop be told apart from the title running out.
            QTimer.singleShot(0, self._after_stop)

    def _after_stop(self):
        if self._draining or (self._player.mediaStatus()
                              == QMediaPlayer.MediaStatus.EndOfMedia):
            self._end()
        elif (self._player.playbackState()
                == QMediaPlayer.PlaybackState.StoppedState):
            self._drop()

    def _on_status(self, status):
        if self.pair and status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._end()

    def _end(self):
        """The title ran out: what is queued is its last bit, to be heard."""
        self._draining = True
        self._flush()
        if self._pending or self._sink is not None:
            self._flusher.start()
