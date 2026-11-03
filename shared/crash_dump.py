"""💥 What a Windows minidump says about the crash, in a few lines of text.

faulthandler writes only the Python stack into crash.log. When the fault is in
native code (Qt, a codec) Windows also leaves a minidump in
%LOCALAPPDATA%\\CrashDumps, and the module plus offset in it is what tells two
crashes apart. This reads just the exception record and the module list, with no
extra package, so the next start can put them under the crash report.
"""
import os
import struct
from pathlib import Path

_EXCEPTION_STREAM = 6
_MODULE_LIST_STREAM = 4
_MODULE_SIZE = 108
_ACCESS = {0: "read", 1: "write", 8: "execute"}


def _streams(data: bytes) -> dict[int, tuple[int, int]]:
    sig, _ver, count, dir_rva = struct.unpack_from("<4sIII", data, 0)
    if sig != b"MDMP":
        raise ValueError("not a minidump")
    return {t: (size, rva) for t, size, rva in
            (struct.unpack_from("<III", data, dir_rva + 12 * i) for i in range(count))}


def _module_name(data: bytes, rva: int) -> str:
    (length,) = struct.unpack_from("<I", data, rva)
    return data[rva + 4:rva + 4 + length].decode("utf-16-le", "replace")


def describe(data: bytes) -> str:
    """'access violation (read at 0xffff…) in Qt6Widgets.dll+0x3ee270', or
    just the exception code when the address lies in no listed module."""
    streams = _streams(data)
    if _EXCEPTION_STREAM not in streams:
        return "no exception record in the dump"
    _size, rva = streams[_EXCEPTION_STREAM]
    code, _flags, _record, addr, nparams = struct.unpack_from("<IIQQI", data, rva + 8)
    info = struct.unpack_from("<15Q", data, rva + 40)
    text = "exception %#010x at %#x" % (code, addr)
    if code == 0xC0000005:
        kind = _ACCESS.get(info[0], "access") if nparams >= 2 else "access"
        text = "access violation (%s at %#x)" % (kind, info[1] if nparams >= 2 else 0)
    if _MODULE_LIST_STREAM in streams:
        _size, mrva = streams[_MODULE_LIST_STREAM]
        (count,) = struct.unpack_from("<I", data, mrva)
        for i in range(count):
            base, size, _chk, _ts, name_rva = struct.unpack_from(
                "<QIIII", data, mrva + 4 + _MODULE_SIZE * i)
            if base <= addr < base + size:
                name = _module_name(data, name_rva).replace("\\", "/").rsplit("/", 1)[-1]
                return "%s in %s+%#x" % (text, name, addr - base)
    return text + " (in no listed module)"


def dump_dir() -> Path | None:
    root = os.environ.get("LOCALAPPDATA")
    return Path(root) / "CrashDumps" if root else None


def latest_dump_text(since: float, folder: Path | None = None) -> str:
    """One line about the newest python minidump written at or after `since`
    (epoch seconds), or '' when there is none or it cannot be read."""
    folder = folder or dump_dir()
    if folder is None or not folder.is_dir():
        return ""
    found = [p for p in folder.glob("python*.dmp") if p.stat().st_mtime >= since]
    if not found:
        return ""
    newest = max(found, key=lambda p: p.stat().st_mtime)
    try:
        return "%s: %s" % (newest.name, describe(newest.read_bytes()))
    except (OSError, ValueError, struct.error):
        return "%s: could not be read" % newest.name
