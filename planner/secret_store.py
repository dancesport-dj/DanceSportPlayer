"""🔐 A secret kept in the operating system's credential store, not in a file.

Windows only (Credential Manager, through ctypes — no extra package to bundle).
Elsewhere `put` says False and the caller keeps its own file, which on macOS and
Linux is already readable by its owner alone. Every call returns instead of
raising: a locked-down or roaming profile must not break the feature, only fall
back to the file.
"""
import ctypes
import logging
import os
from ctypes import wintypes

log = logging.getLogger("dancesport.secrets")

_PREFIX = "DancePlaylist:"
_TYPE_GENERIC = 1
_PERSIST_LOCAL_MACHINE = 2      # stays on this PC, never roams
_ERROR_NOT_FOUND = 1168
_BLOB_MAX = 2560                # CRED_MAX_CREDENTIAL_BLOB_SIZE


class _Credential(ctypes.Structure):
    _fields_ = [("Flags", wintypes.DWORD), ("Type", wintypes.DWORD),
                ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
                ("LastWritten", wintypes.FILETIME),
                ("CredentialBlobSize", wintypes.DWORD),
                ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD),
                ("Attributes", ctypes.c_void_p), ("TargetAlias", wintypes.LPWSTR),
                ("UserName", wintypes.LPWSTR)]


def _advapi():
    if os.name != "nt" or os.environ.get("DANCEPLAYLIST_NO_SECRET_STORE"):
        return None
    lib = ctypes.WinDLL("advapi32", use_last_error=True)
    lib.CredWriteW.argtypes = [ctypes.POINTER(_Credential), wintypes.DWORD]
    lib.CredWriteW.restype = wintypes.BOOL
    lib.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                              ctypes.POINTER(ctypes.POINTER(_Credential))]
    lib.CredReadW.restype = wintypes.BOOL
    lib.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    lib.CredDeleteW.restype = wintypes.BOOL
    lib.CredFree.argtypes = [ctypes.c_void_p]
    return lib


def put(name: str, value: str) -> bool:
    """Keep `value` under `name`; False when there is no store or it refused."""
    try:
        lib = _advapi()
        blob = value.encode("utf-16-le")
        if lib is None or not value or len(blob) > _BLOB_MAX:
            return False
        buf = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
        cred = _Credential(Type=_TYPE_GENERIC, TargetName=_PREFIX + name,
                           CredentialBlobSize=len(blob),
                           CredentialBlob=ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)),
                           Persist=_PERSIST_LOCAL_MACHINE, UserName=name)
        if lib.CredWriteW(ctypes.byref(cred), 0):
            return True
        log.warning("⚠️ Credential store refused a secret\n"
                    "name: %s\n"
                    "error: %s", name, ctypes.get_last_error())
    except Exception as exc:
        log.warning("⚠️ Credential store not usable\n"
                    "error: %s", exc)
    return False


def get(name: str) -> str | None:
    """The secret kept under `name`, None when there is none (or no store)."""
    try:
        lib = _advapi()
        if lib is None:
            return None
        out = ctypes.POINTER(_Credential)()
        if not lib.CredReadW(_PREFIX + name, _TYPE_GENERIC, 0, ctypes.byref(out)):
            if ctypes.get_last_error() != _ERROR_NOT_FOUND:
                log.warning("⚠️ Credential store could not be read\n"
                            "name: %s\n"
                            "error: %s", name, ctypes.get_last_error())
            return None
        try:
            c = out.contents
            return ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize).decode("utf-16-le")
        finally:
            lib.CredFree(out)
    except Exception as exc:
        log.warning("⚠️ Credential store not usable\n"
                    "error: %s", exc)
    return None


def delete(name: str) -> bool:
    """Forget `name`; True when it is gone afterwards."""
    try:
        lib = _advapi()
        if lib is None:
            return False
        if lib.CredDeleteW(_PREFIX + name, _TYPE_GENERIC, 0):
            return True
        return ctypes.get_last_error() == _ERROR_NOT_FOUND
    except Exception as exc:
        log.warning("⚠️ Credential store not usable\n"
                    "error: %s", exc)
    return False
