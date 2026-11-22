"""🔀 A source on one channel pair of a multichannel card, or through the 🎚 EQ.

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

The 🎚 equalizer (player.audio.eq) needs the same way round, on the whole
device too: QMediaPlayer has no equalizer, so with the EQ on the audio is
taken off, filtered, and written to a stereo sink. Either way the player is
"tapped". QAudioBufferOutput exists on the FFmpeg backend only.

The tapped audio runs on a thread of its own (one for every route), not the
GUI thread: the tap, the EQ, the drift keeping and the card's sink. A GUI busy
for half a second (a rescan, a big dialog) would otherwise starve the card of
its next piece while the hall listens. Measured before it was built: with the
receiver on a worker thread, the pieces kept coming through a 1.5 s busy loop
on the GUI thread, 32 ms the longest gap. The worker never touches the player
or its QAudioOutput; what it needs of them (rate, level, paused) is pushed to
it. GUI → worker goes by signal: queued across the threads, direct in the
tests, which run the worker's half on the GUI thread (`_USE_WORKER`).

The tempo fader is the one thing that changes on the way: Qt's pitch-kept
time stretch lives in its output, so what comes off before it is the title
at its own pitch, `rate` seconds of it per second. The route makes the
tempo itself, the pitch kept (player.audio.stretch_engines picks how; by
default the same Signalsmith Stretch Qt uses): on a pair or through the EQ.
Settings say so, and ask first.
Filler, cartwall, announcements and pre-listen have no tempo fader.
"""
import logging
import weakref

import numpy as np
from PySide6.QtCore import QCoreApplication, QObject, QThread, QTimer, Signal, Slot
from PySide6.QtMultimedia import QAudioBuffer, QAudioBufferOutput, QAudioFormat, QAudioSink, QMediaPlayer, QtAudio

from player.audio import stretch_engines
from player.audio.eq import Band, EqFilter
from shared.audio.playback import channel_pairs, device_id, pair_label

log = logging.getLogger("dancesport.gui.audio")

# Qt hands the decoded audio over in pieces, each just as it is due. The card
# starts once this much is in hand, so the next piece is there before the
# last one has played out.
# Deep enough for a tempo engine's first change: the stretch holds back about
# 120 ms when it starts, and at 80 ms the card ran dry (measured on the card).
_PREBUFFER_MS = 200
# The sink's own buffer: room for the prebuffer and a piece on top of it.
_SINK_MS = 400
# The player runs on the computer's clock, the card on its own; the two drift
# apart by a few seconds a day. What is queued when a piece arrives is held in
# this band by playing one frame of a piece twice, or leaving one out: one
# sample in 4400, nobody hears it. Its floor carries the stretch's hold-back
# too, all evening long, with ~80 ms to spare.
_LOW_MS = 200
_BAND_MS = 30
# A queue past this (the event loop stalled) is cut back to the prebuffer.
_MAX_QUEUED_MS = 600
# A piece that does not start where the last one ended: a seek, or a new title
# without a stop in between. What is queued belongs elsewhere then.
_JUMP_US = 50_000
_FLUSH_MS = 10
# How long quitting waits for the audio thread to close its cards.
_QUIT_WAIT_MS = 2000

# Off in the tests: the worker's half runs on the calling thread, in order.
_USE_WORKER = True


# ── the audio thread ─────────────────────────────────────────────────────────

class _Closer(QObject):
    """Lives on the audio thread: closes every route's card there, then ends
    the thread, so no sink is left open for the process's teardown."""

    def __init__(self):
        super().__init__()
        self.pumps: weakref.WeakSet[_Pump] = weakref.WeakSet()

    @Slot()
    def close_all(self):
        for pump in list(self.pumps):
            pump.drop()
        QThread.currentThread().quit()


_thread: QThread | None = None
_closer: _Closer | None = None


class _Signals(QObject):
    close = Signal()


_signals: _Signals | None = None


def _audio_thread() -> tuple[QThread, _Closer]:
    """The one thread every tapped route's audio runs on, started on first use
    and ended when the application quits."""
    global _thread, _closer, _signals
    if _thread is None:
        _thread = QThread()
        _thread.setObjectName("audio-tap")
        _closer = _Closer()
        _closer.moveToThread(_thread)
        _signals = _Signals()
        _signals.close.connect(_closer.close_all)
        _thread.start(QThread.Priority.TimeCriticalPriority)
        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(stop_audio_thread)
        log.info("🔀 Audio tap thread started")
    closer = _closer
    if closer is None:   # made together with _thread above
        raise RuntimeError("the audio tap thread has no closer")
    return _thread, closer


def stop_audio_thread() -> None:
    """Close every tapped card and end the audio thread (on quit). A running
    QThread destroyed at exit aborts the process."""
    global _thread, _closer, _signals
    thread, signals = _thread, _signals
    if thread is None or signals is None:
        return
    signals.close.emit()   # queued: the closer runs on the audio thread
    if not thread.wait(_QUIT_WAIT_MS):
        log.warning("🔀 Audio tap thread did not stop\n"
                    "waited: %d ms", _QUIT_WAIT_MS)
        thread.terminate()
        thread.wait(_QUIT_WAIT_MS)
    _thread = _closer = _signals = None


# ── the worker's half: the audio on its way ─────────────────────────────────

class _Pump(QObject):
    """The tapped audio of one route, from Qt's pieces to the card. Lives on
    the audio thread; everything it is told arrives through its slots."""

    gaveUp = Signal(str)

    def __init__(self):
        super().__init__()
        self._device = None
        self._pair = 0
        self._fmt: QAudioFormat | None = None
        self._sink: QAudioSink | None = None
        self._io = None
        self._pending = bytearray()
        self._next_us: int | None = None
        self._draining = False
        self._low: float | None = None
        self._rate = 1.0
        self._level = 1.0
        self._paused = False
        self._clip_said = False   # 📝 "over full scale" said for this title
        self._eq = EqFilter()
        self._bands: tuple[Band, ...] = ()
        # A tempo other than 1, its pitch kept: built for the card's rate.
        self._stretch = None
        self._flusher = QTimer(self)
        self._flusher.setInterval(_FLUSH_MS)
        self._flusher.timeout.connect(self._flush)

    # ── told by the route ────────────────────────────────────────────────────

    @Slot(object, int, object)
    def configure(self, device, pair: int, fmt):
        """Play on `device` (channel pair `pair`, 0 = the first two) in `fmt`;
        None = nowhere (untapped)."""
        self.drop()
        self._device, self._pair, self._fmt = device, pair, fmt
        if fmt is not None:
            self._eq.set_bands(self._bands, fmt.sampleRate())
            self._stretch = stretch_engines.make(fmt.sampleRate())
            self._stretch.set_rate(self._rate)

    @Slot(object)
    def set_bands(self, bands):
        """The EQ's bands, a tuple of player.audio.eq.Band ((): as it is)."""
        self._bands = tuple(bands)
        if self._fmt is not None:
            self._eq.set_bands(self._bands, self._fmt.sampleRate())

    @Slot(float)
    def set_rate(self, rate: float):
        """The player's tempo. Told to an idle stretch too: Rubber Band
        starts its next title's process at it."""
        self._rate = rate or 1.0
        if self._stretch is not None:
            self._stretch.set_rate(self._rate)

    @Slot(float)
    def set_level(self, level: float):
        if self._fmt is not None and level - self._level > 0.2:
            queued = self._queued_ms(self._fmt)
            if queued > 20:
                # 📝 A loud bit at a fade's end: the level came back while
                # what was queued (the last title's tail?) still plays.
                log.info("🔀 Level raised over queued audio\n"
                         "from: %.2f\n"
                         "to: %.2f\n"
                         "queued: %.0f ms", self._level, level, queued)
        self._level = level
        if self._sink is not None:
            self._sink.setVolume(level)

    @Slot(bool)
    def set_paused(self, paused: bool):
        self._paused = paused
        if self._sink is None:
            return
        if paused:
            self._sink.suspend()
        elif self._sink.state() == QtAudio.State.SuspendedState:
            self._sink.resume()

    @Slot()
    def drop(self):
        """Nothing queued is to be heard any more: a stop, a seek, a move."""
        self._clip_said = False
        self._pending.clear()
        self._next_us = None
        self._draining = False
        self._eq.reset()
        if self._stretch is not None:
            self._stretch.reset()
        self._close()
        self._flusher.stop()

    @Slot()
    def end(self):
        """The title ran out: what is queued is its last bit, to be heard."""
        self._draining = True
        if self._stretch is not None and self._stretch.holding:
            # The stretch's lookahead is the title's last bit: heard as it is.
            self._queue(self._stretch.flush())
        self._flush()
        if self._pending or self._sink is not None:
            self._flusher.start()

    # ── the pieces ───────────────────────────────────────────────────────────

    @Slot(QAudioBuffer)
    def on_buffer(self, buf: QAudioBuffer):
        if self._fmt is None or not buf.isValid() or not buf.byteCount():
            return   # Qt closes a title with an empty piece
        start = buf.startTime()
        if self._draining:
            # A title ran out and the next follows: after its tail, not over it.
            self._draining = False
        elif self._next_us is not None and abs(start - self._next_us) > _JUMP_US:
            self.drop()
        self._next_us = start + buf.duration()
        stereo = np.frombuffer(buf.constData(), dtype=np.float32)
        frames = len(stereo) // 2
        if not frames:
            return
        self._queue(self._at_tempo(stereo[:2 * frames].reshape(frames, 2)))

    def _queue(self, stereo):
        """Stereo frames at the heard tempo: through the EQ, onto the card."""
        fmt = self._fmt
        if fmt is None or not len(stereo):
            return
        stereo = self._eq.process(stereo)
        if not self._clip_said and len(stereo):
            peak = float(np.abs(stereo).max())
            if peak > 1.0:
                # 📝 Distortion the card makes of it: a stretch or an EQ
                # boost took a loud master past full scale.
                self._clip_said = True
                log.info("🔀 Tapped audio over full scale\n"
                         "peak: %.2f\n"
                         "engine: %s", peak, getattr(self._stretch, "engine", "-"))
        channels = fmt.channelCount()
        if channels == 2:
            wide = np.ascontiguousarray(stereo, dtype=np.float32)
        else:
            wide = np.zeros((len(stereo), channels), dtype=np.float32)
            first = 2 * self._pair
            wide[:, first:first + 2] = stereo
        self._pending += self._keep_pace(wide).tobytes()
        self._flush()
        if not self._flusher.isActive():
            self._flusher.start()

    def _at_tempo(self, stereo):
        """The piece at the player's tempo, its pitch kept (Qt's own stretch
        is past the tap). At tempo 1 nothing is held back, until the stretch
        has started on the title: then it carries on to the next drop, as
        leaving it mid-title would skip its lookahead. An idle stretch takes
        up a newly chosen engine."""
        stretch = self._stretch
        if stretch is None:
            return stereo
        if getattr(stretch, "failed", False):
            stretch_engines.note_broken(stretch.engine)
        if (not stretch.holding and stretch.engine != stretch_engines.current()
                and self._fmt is not None):
            stretch = self._stretch = stretch_engines.make(self._fmt.sampleRate())
            stretch.set_rate(self._rate)
        if self._rate == 1.0 and not stretch.holding:
            return stereo
        stretch.set_rate(self._rate)
        return stretch.process(stereo)

    def _keep_pace(self, wide):
        """One frame more or less while the queue strays from its band: the
        two clocks' drift (see _LOW_MS). Measured as a piece arrives, when
        the queue is at its lowest."""
        if self._sink is None or self._fmt is None:
            return wide
        low = self._queued_ms(self._fmt)
        if low <= 0:
            # Ran dry: start over with a full prebuffer rather than limp on.
            # Said every time: a dry card is a dropout the hall heard.
            channels = pair_label(self._pair) if self._pair else "the whole device"
            log.warning("🔀 Tapped audio ran dry\n"
                        "output: %s\n"
                        "channels: %s",
                        self._device.description() if self._device is not None else "-",
                        channels)
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

    @Slot()
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
                log.info("🔀 Tapped audio queue cut back\n"
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
            self._give_up("the card refuses %d channels" % fmt.channelCount())
            return False
        sink = QAudioSink(device, fmt, self)
        sink.setBufferSize(fmt.bytesForDuration(_SINK_MS * 1000))
        sink.setVolume(self._level)
        io = sink.start()
        if io is None or sink.error() != QtAudio.Error.NoError:
            sink.deleteLater()
            self._give_up("the card did not open (%s)" % sink.error())
            return False
        self._sink, self._io, self._low = sink, io, None
        if self._paused:
            sink.suspend()
        return True

    def _give_up(self, why: str):
        """The card cannot be played this way: the route goes back to Qt's
        own output on the whole card rather than silence."""
        self.drop()
        self._fmt = None
        self.gaveUp.emit(why)

    def _close(self):
        if self._sink is not None:
            self._sink.stop()
            self._sink.deleteLater()
        self._sink = self._io = None
        self._low = None


# ── the GUI's half: the player and its way to the card ──────────────────────

class PairRoute(QObject):
    """One player's way to its output: its QAudioOutput on a whole device
    (Qt's own path, as it always was), or tapped: channel pair `pair` of a
    wider card, and/or through the 🎚 EQ. The QAudioOutput stays the source's
    level either way: the owner fades it as before, and a tapped player's
    sink follows it.

    Nothing of the player is touched until it is first tapped, so a source on
    a whole device without EQ runs exactly the code it did."""

    _configure = Signal(object, int, object)
    _bands = Signal(object)
    _rate = Signal(float)
    _level = Signal(float)
    _paused = Signal(bool)
    _drop_now = Signal()
    _end_now = Signal()

    def __init__(self, player, out, parent=None):
        super().__init__(parent)
        self._player = player
        self._out = out
        self.pair = 0
        self._eq_bands: tuple[Band, ...] | None = None   # None: no EQ path
        self._device = None
        self._released = False
        self._wired = False
        self._watching = False
        self._ended = False
        self._stopped = False   # a stop whose queue has not gone yet
        self._tap: QAudioBufferOutput | None = None
        self._pump: _Pump | None = None
        self._sent_level = 0.0   # the level the pump has

    @property
    def tapped(self) -> bool:
        """Whether the audio is taken off before Qt's output."""
        return bool(self.pair) or self._eq_bands is not None

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
        if pair == self.pair == 0 and not self.tapped:
            self._device = device
            self._out.setDevice(device)
            return
        if (pair == self.pair and self._device is not None
                and device_id(self._device) == device_id(device)):
            return
        self._out.setDevice(device)   # so out.device() still says where
        self._device = device
        self.pair = pair
        self._reroute()
        log.info("🔀 Output on a channel pair\n"
                 "output: %s\n"
                 "channels: %s", device.description(),
                 pair_label(pair) if pair else "the whole device")

    def set_eq(self, bands) -> None:
        """🎚 The EQ: a tuple of player.audio.eq.Band to filter through (empty:
        through the EQ path but as it is, the A/B bypass), or None for Qt's
        own output. All of it is heard at once, on the title playing: going
        on or off the path re-opens the card, a short gap, but the operator
        hears what the switch does."""
        bands = None if bands is None else tuple(bands)
        was = self.tapped
        self._eq_bands = bands
        if self._pump is not None and bands is not None:
            self._bands.emit(bands)
        if self.tapped != was:
            if self._device is None:
                self._device = self._out.device()
            self._reroute()

    def release(self) -> None:
        """🔇 Let go of the card (see AudioDevice.release)."""
        self._released = True
        self._player.setAudioOutput(None)
        if self._wired:
            self._player.setAudioBufferOutput(None)
        if self._pump is not None:
            self._drop_now.emit()

    def restore(self) -> None:
        """Take the card back before anything is heard."""
        if self._released:
            self._released = False
            self._attach()
        elif not self.tapped and self._player.audioOutput() is None:
            self._player.setAudioOutput(self._out)

    def _reroute(self):
        if self._pump is not None:
            self._drop_now.emit()
        if not self._released:
            self._attach()

    def _attach(self):
        # Never neither output while it plays, not even between two calls:
        # Qt's FFmpeg backend drops the renderer of a playing player left
        # without both, and a tap attached after that hears nothing for the
        # rest of the title. So the new output first, the old one after.
        if not self.tapped:
            self._player.setAudioOutput(self._out)
            if self._wired:
                self._player.setAudioBufferOutput(None)
            if self._pump is not None:
                self._configure.emit(None, 0, None)
            return
        self._wire()
        fmt = self._sink_format(self._device, self.pair)
        self._configure.emit(self._device, self.pair, fmt)
        self._bands.emit(self._eq_bands or ())
        self._rate.emit(self._player.playbackRate() or 1.0)
        self._send_level(self._volume())
        self._paused.emit(self._player.playbackState()
                          == QMediaPlayer.PlaybackState.PausedState)
        tap_fmt = QAudioFormat()
        tap_fmt.setSampleRate(fmt.sampleRate())
        tap_fmt.setChannelCount(2)
        tap_fmt.setSampleFormat(QAudioFormat.SampleFormat.Float)
        # Kept, never deleted while the player lives: Qt 6.12 clears the
        # player's tap when ANY tap it was once given is destroyed, and the
        # title goes silent (scratchpad retap_probe.py, delete_old: 0.00 s).
        # A new one only for a card at another rate; the old stays too. The
        # player's child, so none outlives it: a tap still alive after its
        # player points into freed memory, and destroying it crashes.
        if self._tap is None or self._tap.format() != tap_fmt:
            self._tap = QAudioBufferOutput(tap_fmt, self._player)
            # Emitted on Qt's renderer thread: queued to the pump's own.
            if self._pump is not None:   # _wire() above made it
                self._tap.audioBufferReceived.connect(self._pump.on_buffer)
        self._player.setAudioBufferOutput(self._tap)
        self._player.setAudioOutput(None)

    def _wire(self):
        if self._wired:
            return
        self._wired = True
        pump = self._pump = _Pump()
        if _USE_WORKER:
            _thread_, closer = _audio_thread()
            pump.moveToThread(_thread_)
            closer.pumps.add(pump)
            # Not parented across threads: it goes when the route does.
            self.destroyed.connect(pump.deleteLater)
        else:
            pump.setParent(self)
        self._configure.connect(pump.configure)
        self._bands.connect(pump.set_bands)
        self._rate.connect(pump.set_rate)
        self._level.connect(pump.set_level)
        self._paused.connect(pump.set_paused)
        self._drop_now.connect(pump.drop)
        self._end_now.connect(pump.end)
        pump.gaveUp.connect(self._on_gave_up)
        self._watch()
        if hasattr(self._player, "playbackRateChanged"):
            self._player.playbackRateChanged.connect(self._on_rate)
        self._out.volumeChanged.connect(self._apply_volume)
        self._out.mutedChanged.connect(self._apply_volume)

    def _watch(self):
        """Follow the player's state once tapped."""
        if self._watching:
            return
        self._watching = True
        self._player.playbackStateChanged.connect(self._on_state)
        self._player.mediaStatusChanged.connect(self._on_status)

    @staticmethod
    def _sink_format(device, pair: int) -> QAudioFormat:
        """At the card's own rate, nothing for Windows to resample. For a pair
        as wide as the card; for the whole device (the EQ) stereo."""
        fmt = QAudioFormat()
        fmt.setSampleRate(device.preferredFormat().sampleRate() or 48000)
        fmt.setChannelCount(2 * channel_pairs(device) if pair else 2)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Float)
        return fmt

    @Slot(str)
    def _on_gave_up(self, why: str):
        device = self._device
        log.warning("🔀 Tapped output unavailable\n"
                    "output: %s\n"
                    "reason: %s\n"
                    "playing on: the whole device, without the EQ",
                    device.description() if device is not None else "-", why)
        self.pair = 0
        self._eq_bands = None
        if not self._released:
            self._attach()

    # ── following the player ─────────────────────────────────────────────────

    def _volume(self) -> float:
        return 0.0 if self._out.isMuted() else self._out.volume()

    def _apply_volume(self, *_):
        if not self.tapped:
            return
        level = self._volume()
        if (level > self._sent_level and self._player.playbackState()
                == QMediaPlayer.PlaybackState.StoppedState):
            # Held until the next play: the stop's queue goes a moment later
            # (_after_stop), and a level raised before that played the old
            # title's tail loud. A title that ran out keeps its tail's level.
            return
        self._send_level(level)

    def _send_level(self, level: float):
        self._sent_level = level
        self._level.emit(level)

    def _on_rate(self, rate):
        if self.tapped:
            self._rate.emit(float(rate) or 1.0)

    def _on_state(self, state):
        if not self.tapped:
            return
        if state == QMediaPlayer.PlaybackState.PausedState:
            self._paused.emit(True)
        elif state == QMediaPlayer.PlaybackState.PlayingState:
            if self._stopped and not self._ended:
                # Stopped and played again before _after_stop ran (the same
                # title, no reload): what the stop left queued goes now, or it
                # plays on at the level the play brings back. Inside play():
                # nothing of the replay is queued yet.
                self._drop_now.emit()
            self._stopped = False
            self._ended = False
            self._send_level(self._volume())   # one held while stopped
            self._paused.emit(False)
        else:
            # Qt reports Stopped before EndOfMedia, so only after both have
            # landed can a stop be told apart from the title running out.
            self._stopped = True
            QTimer.singleShot(0, self._after_stop)

    def _after_stop(self):
        self._stopped = False
        # Ordered with the next title's pieces: a drop sent here goes out
        # while the player is still stopped, before anything new is decoded,
        # and a play that came first leaves the player playing (no drop).
        if self._ended or (self._player.mediaStatus()
                           == QMediaPlayer.MediaStatus.EndOfMedia):
            self._end()
        elif (self._player.playbackState()
                == QMediaPlayer.PlaybackState.StoppedState):
            self._drop_now.emit()

    def _on_status(self, status):
        if not self.tapped:
            return
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._end()
        elif status == QMediaPlayer.MediaStatus.LoadingMedia and not self._ended:
            # A new title loads over one that was cut off (⏭, a fade's end):
            # what that one still queued goes now. _after_stop would come too
            # late when play() follows at once, and the old tail would play at
            # the level the new title brings back. Before play(): nothing of
            # the new title is queued yet. A title that ran out keeps its tail.
            self._stopped = False
            self._drop_now.emit()

    def _end(self):
        self._ended = True
        self._end_now.emit()
