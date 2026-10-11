"""🎛 MIDI input on macOS — CoreMIDI through raw ctypes.

Use it through shared.midi_input. CoreMIDI ships with every Mac, so nothing
is installed. One CoreMIDI client serves the whole run (Apple advises against
disposing of clients); each `MidiInput` is an input port on it, connected to
one source.

CoreMIDI calls the read proc on a high-priority thread of its own with a
MIDIPacketList: raw bytes, possibly several messages to a packet and running
status across them, which `MidiStreamParser` turns into messages.

The layout, from MIDIServices.h: both structs are `#pragma pack(4)`, so in a
MIDIPacketList the first packet starts at byte 4 (after `UInt32 numPackets`),
and a MIDIPacket is `UInt64 timeStamp` at 0, `UInt16 length` at 8 and the data
from 10. MIDIPacketNext steps to right after the data on Intel, but on ARM
rounds that address up to a multiple of 4.
"""
from __future__ import annotations

import ctypes
import logging
import platform
import struct
import sys

from shared.midi_input import MidiStreamParser, unique_names

log = logging.getLogger("dancesport.midi")

_CF_UTF8 = 0x08000100
_PACKET_DATA = 10           # offset of data[] in a MIDIPacket
_LIST_FIRST = 4             # offset of packet[0] in a MIDIPacketList

_ReadProc = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)

_api = None                 # (CoreMIDI, CoreFoundation), loaded on first use
_client = None


def packet_aligned() -> bool:
    """Whether MIDIPacketNext rounds up to 4 bytes: on ARM (Apple silicon),
    not on Intel — nor under Rosetta, where this process is Intel too."""
    return platform.machine().lower() in ("arm64", "aarch64")


def packet_list_bytes(addr: int, aligned: bool) -> list[bytes]:
    """The data of every packet in the MIDIPacketList at `addr`."""
    count = struct.unpack("=I", ctypes.string_at(addr, 4))[0]
    out, pkt = [], addr + _LIST_FIRST
    for _ in range(count):
        length = struct.unpack("=H", ctypes.string_at(pkt + 8, 2))[0]
        out.append(ctypes.string_at(pkt + _PACKET_DATA, length))
        pkt += _PACKET_DATA + length
        if aligned:
            pkt = (pkt + 3) & ~3
    return out


def _load():
    global _api
    if _api is None:
        if sys.platform != "darwin":
            raise OSError("CoreMIDI needs macOS")
        midi = ctypes.CDLL("/System/Library/Frameworks/CoreMIDI.framework/CoreMIDI")
        cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        cf.CFStringCreateWithCString.restype = ctypes.c_void_p
        cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                                 ctypes.c_uint32]
        cf.CFStringGetCString.restype = ctypes.c_bool
        cf.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                          ctypes.c_long, ctypes.c_uint32]
        cf.CFRelease.argtypes = [ctypes.c_void_p]
        midi.MIDIGetNumberOfSources.restype = ctypes.c_ulong
        midi.MIDIGetSource.restype = ctypes.c_uint32
        midi.MIDIGetSource.argtypes = [ctypes.c_ulong]
        midi.MIDIObjectGetStringProperty.restype = ctypes.c_int32
        midi.MIDIObjectGetStringProperty.argtypes = [ctypes.c_uint32, ctypes.c_void_p,
                                                     ctypes.POINTER(ctypes.c_void_p)]
        midi.MIDIClientCreate.restype = ctypes.c_int32
        midi.MIDIClientCreate.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                          ctypes.c_void_p,
                                          ctypes.POINTER(ctypes.c_uint32)]
        midi.MIDIInputPortCreate.restype = ctypes.c_int32
        midi.MIDIInputPortCreate.argtypes = [ctypes.c_uint32, ctypes.c_void_p, _ReadProc,
                                             ctypes.c_void_p,
                                             ctypes.POINTER(ctypes.c_uint32)]
        midi.MIDIPortConnectSource.restype = ctypes.c_int32
        midi.MIDIPortConnectSource.argtypes = [ctypes.c_uint32, ctypes.c_uint32,
                                               ctypes.c_void_p]
        midi.MIDIPortDisconnectSource.restype = ctypes.c_int32
        midi.MIDIPortDisconnectSource.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
        midi.MIDIPortDispose.restype = ctypes.c_int32
        midi.MIDIPortDispose.argtypes = [ctypes.c_uint32]
        _api = midi, cf
    return _api


def _cfstr(cf, text: str):
    return cf.CFStringCreateWithCString(None, text.encode("utf-8"), _CF_UTF8)


def _client_ref() -> int:
    """The one client, made on first use. Called from the GUI thread, whose
    run loop then carries CoreMIDI's hot-plug news, so a controller plugged in
    later shows up in the source list."""
    global _client
    if _client is None:
        midi, cf = _load()
        name = _cfstr(cf, "DancePlaylist")
        ref = ctypes.c_uint32()
        err = midi.MIDIClientCreate(name, None, None, ctypes.byref(ref))
        cf.CFRelease(name)
        if err:
            raise OSError(f"MIDIClientCreate failed ({err})")
        _client = ref.value
    return _client


def _sources() -> list[tuple[str, int]]:
    """(name, endpoint) per MIDI source, names made unique."""
    midi, cf = _load()
    _client_ref()
    key = ctypes.c_void_p.in_dll(midi, "kMIDIPropertyDisplayName")
    names, refs = [], []
    for idx in range(midi.MIDIGetNumberOfSources()):
        src = midi.MIDIGetSource(idx)
        text = ctypes.c_void_p()
        name = ""
        if midi.MIDIObjectGetStringProperty(src, key, ctypes.byref(text)) == 0 and text.value:
            buf = ctypes.create_string_buffer(256)
            if cf.CFStringGetCString(text, buf, len(buf), _CF_UTF8):
                name = buf.value.decode("utf-8", "replace")
            cf.CFRelease(text)
        names.append(name or f"MIDI source {idx + 1}")
        refs.append(src)
    return list(zip(unique_names(names), refs))


def list_inputs() -> list[str]:
    try:
        return [name for name, _ref in _sources()]
    except OSError as exc:
        log.info("🎛 No CoreMIDI\n"
                 "reason: %s", exc)
        return []


class MidiInput:
    """One CoreMIDI source, connected to a port of the app's client."""

    def __init__(self, name: str, on_message):
        midi, cf = _load()
        found = dict(_sources())
        if name not in found:
            raise OSError(f"MIDI input not found: {name}")
        self.name = name
        self._on_message = on_message
        self._parser = MidiStreamParser()
        self._aligned = packet_aligned()
        self._source = found[name]

        def read(pktlist, _ref, _conn):
            try:
                for data in packet_list_bytes(pktlist, self._aligned):
                    for msg in self._parser.feed(data):
                        self._on_message(*msg)
            except Exception:   # a raise here would unwind into CoreMIDI
                log.exception("🎛 MIDI message handler failed")

        # Kept on the instance: CoreMIDI calls it until the port is gone, and
        # a collected ctypes callback is a crash, not an exception.
        self._proc = _ReadProc(read)
        port_name = _cfstr(cf, "Controller in")
        port = ctypes.c_uint32()
        err = midi.MIDIInputPortCreate(_client_ref(), port_name, self._proc, None,
                                       ctypes.byref(port))
        cf.CFRelease(port_name)
        if err:
            raise OSError(f"MIDIInputPortCreate failed ({err}) for {name}")
        self._port = port.value
        err = midi.MIDIPortConnectSource(self._port, self._source, None)
        if err:
            midi.MIDIPortDispose(self._port)
            self._port = None
            raise OSError(f"MIDIPortConnectSource failed ({err}) for {name}")

    def close(self) -> None:
        port, self._port = getattr(self, "_port", None), None
        if port:
            midi, _cf = _load()
            midi.MIDIPortDisconnectSource(port, self._source)
            midi.MIDIPortDispose(port)
