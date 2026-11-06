"""💥 Reading the faulting module out of a Windows minidump."""
import os
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from shared import crash_dump


def _dump(code=0xC0000005, addr=0x7FF0_0000_0100, params=(0, 0xFFFF_FFFF_FFFF_FFFF)) -> bytes:
    """A minimal minidump: header, directory, exception and module streams."""
    exc = bytearray(168)
    struct.pack_into("<IIQQI", exc, 8, code, 0, 0, addr, len(params))
    for i, v in enumerate(params):
        struct.pack_into("<Q", exc, 40 + 8 * i, v)
    name = r"C:\app\Qt6Widgets.dll".encode("utf-16-le")
    name_blob = struct.pack("<I", len(name)) + name
    dir_rva = 32
    exc_rva = dir_rva + 24
    mod_rva = exc_rva + len(exc)
    name_rva = mod_rva + 4 + 108
    mod = bytearray(4 + 108)
    struct.pack_into("<I", mod, 0, 1)
    struct.pack_into("<QIIII", mod, 4, 0x7FF0_0000_0000, 0x1000, 0, 0, name_rva)
    head = struct.pack("<4sIII", b"MDMP", 0xA793, 2, dir_rva).ljust(32, b"\0")
    directory = (struct.pack("<III", 6, len(exc), exc_rva)
                 + struct.pack("<III", 4, len(mod), mod_rva))
    return head + directory + bytes(exc) + bytes(mod) + name_blob


class CrashDumpTest(unittest.TestCase):
    def test_access_violation_names_module_and_offset(self):
        self.assertEqual(
            crash_dump.describe(_dump()),
            "access violation (read at 0xffffffffffffffff) in Qt6Widgets.dll+0x100")

    def test_an_address_outside_every_module_still_gives_the_code(self):
        text = crash_dump.describe(_dump(code=0xC0000409, addr=0x10, params=()))
        self.assertIn("0xc0000409", text)
        self.assertIn("no listed module", text)

    def test_not_a_dump_is_refused(self):
        with self.assertRaises(ValueError):
            crash_dump.describe(b"x" * 64)

    def test_latest_dump_text_takes_the_newest_python_dump_since(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            old = folder / "python.exe.1.dmp"
            new = folder / "python.exe.2.dmp"
            other = folder / "other.exe.3.dmp"
            for p in (old, new, other):
                p.write_bytes(_dump())
            os.utime(old, (1000, 1000))
            self.assertEqual(crash_dump.latest_dump_text(2000, folder)[:16], "python.exe.2.dmp")
            self.assertEqual(crash_dump.latest_dump_text(10**10, folder), "")
            new.write_bytes(b"junk")
            self.assertIn("could not be read", crash_dump.latest_dump_text(2000, folder))

    def test_a_dump_that_vanishes_between_listing_and_stat_is_skipped(self):
        """Another process may delete a dump while it is being looked at."""
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            gone = folder / "python.exe.1.dmp"
            kept = folder / "python.exe.2.dmp"
            for p in (gone, kept):
                p.write_bytes(_dump())
            real = Path.stat

            def stat(self, *args, **kwargs):
                if self.name == gone.name:
                    raise FileNotFoundError(self.name)
                return real(self, *args, **kwargs)
            with mock.patch.object(Path, "stat", stat):
                self.assertEqual(crash_dump.latest_dump_text(0, folder)[:16],
                                 "python.exe.2.dmp")


if __name__ == "__main__":
    unittest.main()
