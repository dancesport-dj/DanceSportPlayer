"""🎛 MIDI input on Linux — the ALSA sequencer through raw ctypes.

Use it through shared.midi_input. libasound.so.2 is on every desktop Linux,
PipeWire or not, so nothing is installed. The sequencer rather than raw MIDI
(/dev/snd/midiC*D*): a raw MIDI input opens exclusively, and the sound server
usually holds it already, while any number of sequencer clients can subscribe
to one port.

Each `MidiInput` is a sequencer client of its own with one writable port,
connected from the controller's port, and a daemon thread that polls it and
turns each event into a (status, data1, data2) message.

The event, from alsa/seq_event.h: `snd_seq_event_t` is 28 bytes — type at 0,
the data union from 16. Notes are channel, note, velocity bytes there; a
controller or pitch bend is the channel byte, then `unsigned int param` at 20
and `signed int value` at 24.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import logging
import select
import struct
import threading

from shared.midi_input import unique_names

log = logging.getLogger("dancesport.midi")

_OPEN_INPUT = 2
_CAP_READ = 1 << 0
_CAP_WRITE = 1 << 1
_CAP_SUBS_READ = 1 << 5
_CAP_SUBS_WRITE = 1 << 6
_CAP_NO_EXPORT = 1 << 7
_TYPE_MIDI_GENERIC = 1 << 1
_TYPE_APPLICATION = 1 << 20
_POLLIN = 1
_ENOSPC = 28                # input overrun: events were lost, keep reading

_EVENT_SIZE = 28
_EV_NOTEON, _EV_NOTEOFF, _EV_CONTROLLER, _EV_PITCHBEND = 6, 7, 10, 13

_lib = None


class _PollFd(ctypes.Structure):
    _fields_ = [("fd", ctypes.c_int), ("events", ctypes.c_short),
                ("revents", ctypes.c_short)]


def event_message(raw: bytes):
    """(status, data1, data2) for a sequencer event, or None for an event
    no control sends."""
    kind, ch = raw[0], raw[16] & 0x0F
    if kind in (_EV_NOTEON, _EV_NOTEOFF):
        return (0x90 if kind == _EV_NOTEON else 0x80) | ch, raw[17] & 0x7F, raw[18] & 0x7F
    if kind in (_EV_CONTROLLER, _EV_PITCHBEND):
        param, value = struct.unpack_from("=Ii", raw, 20)
        if kind == _EV_CONTROLLER:
            return 0xB0 | ch, param & 0x7F, value & 0x7F
        value = min(max(value + 8192, 0), 16383)
        return 0xE0 | ch, value & 0x7F, value >> 7
    return None


def _load():
    global _lib
    if _lib is None:
        lib = ctypes.CDLL(ctypes.util.find_library("asound") or "libasound.so.2")
        vp, i, ui = ctypes.c_void_p, ctypes.c_int, ctypes.c_uint
        for fn, res, args in (
                ("snd_seq_open", i, [ctypes.POINTER(vp), ctypes.c_char_p, i, i]),
                ("snd_seq_close", i, [vp]),
                ("snd_seq_client_id", i, [vp]),
                ("snd_seq_set_client_name", i, [vp, ctypes.c_char_p]),
                ("snd_seq_client_info_malloc", i, [ctypes.POINTER(vp)]),
                ("snd_seq_client_info_free", None, [vp]),
                ("snd_seq_client_info_set_client", None, [vp, i]),
                ("snd_seq_client_info_get_client", i, [vp]),
                ("snd_seq_client_info_get_name", ctypes.c_char_p, [vp]),
                ("snd_seq_query_next_client", i, [vp, vp]),
                ("snd_seq_port_info_malloc", i, [ctypes.POINTER(vp)]),
                ("snd_seq_port_info_free", None, [vp]),
                ("snd_seq_port_info_set_client", None, [vp, i]),
                ("snd_seq_port_info_set_port", None, [vp, i]),
                ("snd_seq_port_info_get_port", i, [vp]),
                ("snd_seq_port_info_get_name", ctypes.c_char_p, [vp]),
                ("snd_seq_port_info_get_capability", ui, [vp]),
                ("snd_seq_query_next_port", i, [vp, vp]),
                ("snd_seq_create_simple_port", i, [vp, ctypes.c_char_p, ui, ui]),
                ("snd_seq_connect_from", i, [vp, i, i, i]),
                ("snd_seq_nonblock", i, [vp, i]),
                ("snd_seq_poll_descriptors_count", i, [vp, ctypes.c_short]),
                ("snd_seq_poll_descriptors", i, [vp, ctypes.POINTER(_PollFd), ui,
                                                 ctypes.c_short]),
                ("snd_seq_event_input", i, [vp, ctypes.POINTER(vp)])):
            func = getattr(lib, fn)
            func.restype, func.argtypes = res, args
        _lib = lib
    return _lib


def _open(name: bytes = b"DancePlaylist"):
    lib = _load()
    seq = ctypes.c_void_p()
    err = lib.snd_seq_open(ctypes.byref(seq), b"default", _OPEN_INPUT, 0)
    if err < 0:
        raise OSError(f"snd_seq_open failed ({err})")
    lib.snd_seq_set_client_name(seq, name)
    return lib, seq


def _sources() -> dict[str, tuple[int, int]]:
    """name → (client, port) per readable hardware or app port."""
    lib, seq = _open()
    cinfo, pinfo = ctypes.c_void_p(), ctypes.c_void_p()
    lib.snd_seq_client_info_malloc(ctypes.byref(cinfo))
    lib.snd_seq_port_info_malloc(ctypes.byref(pinfo))
    found = []          # (client name, port name, client, port)
    try:
        own = lib.snd_seq_client_id(seq)
        lib.snd_seq_client_info_set_client(cinfo, -1)
        while lib.snd_seq_query_next_client(seq, cinfo) >= 0:
            client = lib.snd_seq_client_info_get_client(cinfo)
            cname = (lib.snd_seq_client_info_get_name(cinfo) or b"").decode("utf-8", "replace")
            if client in (0, own) or cname == "Midi Through":
                continue
            lib.snd_seq_port_info_set_client(pinfo, client)
            lib.snd_seq_port_info_set_port(pinfo, -1)
            while lib.snd_seq_query_next_port(seq, pinfo) >= 0:
                caps = lib.snd_seq_port_info_get_capability(pinfo)
                want = _CAP_READ | _CAP_SUBS_READ
                if caps & want != want or caps & _CAP_NO_EXPORT:
                    continue
                pname = (lib.snd_seq_port_info_get_name(pinfo) or b"").decode("utf-8",
                                                                             "replace")
                found.append((cname, pname, client, lib.snd_seq_port_info_get_port(pinfo)))
    finally:
        lib.snd_seq_port_info_free(pinfo)
        lib.snd_seq_client_info_free(cinfo)
        lib.snd_seq_close(seq)
    clients = [entry[2] for entry in found]
    names = [cname if clients.count(client) == 1 else f"{cname}: {pname}"
             for cname, pname, client, _port in found]
    return dict(zip(unique_names(names), [(c, p) for _cn, _pn, c, p in found]))


def list_inputs() -> list[str]:
    try:
        return list(_sources())
    except OSError as exc:
        log.info("🎛 No ALSA sequencer\n"
                 "reason: %s", exc)
        return []


class MidiInput:
    """One sequencer port, read on a daemon thread of its own."""

    def __init__(self, name: str, on_message):
        found = _sources()
        if name not in found:
            raise OSError(f"MIDI input not found: {name}")
        self.name = name
        self._on_message = on_message
        lib, self._seq = _open()
        try:
            port = lib.snd_seq_create_simple_port(
                self._seq, b"Controller in", _CAP_WRITE | _CAP_SUBS_WRITE,
                _TYPE_MIDI_GENERIC | _TYPE_APPLICATION)
            if port < 0:
                raise OSError(f"snd_seq_create_simple_port failed ({port})")
            client, src_port = found[name]
            err = lib.snd_seq_connect_from(self._seq, port, client, src_port)
            if err < 0:
                raise OSError(f"snd_seq_connect_from failed ({err}) for {name}")
            lib.snd_seq_nonblock(self._seq, 1)
            count = lib.snd_seq_poll_descriptors_count(self._seq, _POLLIN)
            fds = (_PollFd * count)()
            lib.snd_seq_poll_descriptors(self._seq, fds, count, _POLLIN)
        except OSError:
            lib.snd_seq_close(self._seq)
            raise
        self._poll = select.poll()
        for pfd in fds:
            self._poll.register(pfd.fd, select.POLLIN)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="midi-alsa", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        lib = _load()
        event = ctypes.c_void_p()
        while not self._stop.is_set():
            if not self._poll.poll(200):
                continue
            while not self._stop.is_set():
                left = lib.snd_seq_event_input(self._seq, ctypes.byref(event))
                if left == -_ENOSPC:
                    continue
                if left < 0:
                    break
                msg = event_message(ctypes.string_at(event, _EVENT_SIZE))
                if msg is None:
                    continue
                try:
                    self._on_message(*msg)
                except Exception:
                    log.exception("🎛 MIDI message handler failed")

    def close(self) -> None:
        seq, self._seq = getattr(self, "_seq", None), None
        if seq:
            self._stop.set()
            self._thread.join(1.0)
            if not self._thread.is_alive():     # never free it under a reader
                _load().snd_seq_close(seq)
