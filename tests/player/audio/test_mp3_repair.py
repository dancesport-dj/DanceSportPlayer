"""🔧 A CBR mp3 the ffmpeg backend takes for a program stream gets a repaired copy.

Run:  py -m unittest tests.player.audio.test_mp3_repair -v

Marcel's "JV42_Golden Days.mp3" and "PD2HL60_Arena Del Toro…" play in Explorer, but
ffmpeg misreads the container (a few stray 00 00 01 E0 byte runs in a 320 kbps CBR
file without a Xing/Info frame) and "ends" them at once. A leading Info frame, and
for a large ID3 tag the tag taken off, makes it read them as mp3. The original is
never touched: the repair is a copy in the temp folder.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from player.audio import mp3_repair

HEADER = bytes([0xFF, 0xFB, 0xE0, 0x40])   # MPEG-1 layer 3, 320 kbps, 44.1 kHz, joint stereo
FRAME = 1044                               # 144 * 320000 / 44100, no padding


def audio(frames=4):
    return b"".join(HEADER + bytes([i + 1]) * (FRAME - 4) for i in range(frames))


def id3(size):
    s = bytes([(size >> 21) & 0x7F, (size >> 14) & 0x7F, (size >> 7) & 0x7F, size & 0x7F])
    return b"ID3\x04\x00\x00" + s + b"\x00" * size


class RepairTest(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_repair_"))

    def make(self, data, name="t.mp3"):
        p = self.dir / name
        p.write_bytes(data)
        return p

    def test_an_info_frame_goes_in_front_of_the_audio(self):
        src = self.make(audio())
        out = mp3_repair.repaired_copy(src)
        data = out.read_bytes()
        self.assertEqual(data[:4], HEADER)
        self.assertEqual(data[36:40], b"Info")
        self.assertEqual(data[FRAME:], audio())   # a frame as long as the audio's own

    def test_the_id3_tag_is_taken_off_the_copy(self):
        src = self.make(id3(5900) + audio())
        data = mp3_repair.repaired_copy(src).read_bytes()
        self.assertEqual(data[FRAME:], audio())
        self.assertNotIn(b"ID3", data[:10])

    def test_the_original_stays_as_it_was(self):
        raw = id3(361) + audio()
        src = self.make(raw)
        mp3_repair.repaired_copy(src)
        self.assertEqual(src.read_bytes(), raw)

    def test_a_file_without_a_frame_is_not_repaired(self):
        self.assertIsNone(mp3_repair.repaired_copy(self.make(b"\x00" * 5000)))

    def test_a_missing_file_is_not_repaired(self):
        self.assertIsNone(mp3_repair.repaired_copy(self.dir / "gone.mp3"))

    def test_a_second_call_reuses_the_copy(self):
        src = self.make(audio())
        a = mp3_repair.repaired_copy(src)
        b = mp3_repair.repaired_copy(src)
        self.assertEqual(a, b)

    def test_a_cached_copy_is_found_but_never_made(self):
        src = self.make(audio())
        self.assertIsNone(mp3_repair.cached_copy(src))
        copy = mp3_repair.repaired_copy(src)
        self.assertEqual(mp3_repair.cached_copy(src), copy)

    def test_a_changed_file_has_no_cached_copy(self):
        src = self.make(audio(4))
        mp3_repair.repaired_copy(src)
        src.write_bytes(audio(6))
        os.utime(src, (1, 1))
        self.assertIsNone(mp3_repair.cached_copy(src))

    def test_a_missing_file_has_no_cached_copy(self):
        self.assertIsNone(mp3_repair.cached_copy(self.dir / "gone.mp3"))

    def test_another_instances_part_file_is_not_shared(self):
        """Review F3: the .part name was fixed, so two instances repairing the
        same file wrote into one temp file."""
        src = self.make(audio())
        other = mp3_repair._copy_path(src).with_suffix(".part")
        other.parent.mkdir(parents=True, exist_ok=True)
        other.write_bytes(b"the other instance's half-written copy")
        self.addCleanup(lambda: other.unlink(missing_ok=True))
        out = mp3_repair.repaired_copy(src)
        self.assertEqual(other.read_bytes(), b"the other instance's half-written copy")
        self.assertEqual(out.read_bytes()[FRAME:], audio())
        mine = [p for p in out.parent.glob(out.stem + "*.part") if p != other]
        self.assertEqual(mine, [])

    def test_on_posix_the_folder_is_the_users_own(self):
        """Review F3: on a shared Linux/macOS temp dir the folder name was
        predictable, so another user could make it first and hand in copies."""
        tmp = Path(tempfile.mkdtemp(prefix="dp_repair_tmp_"))
        with mock.patch.object(mp3_repair.sys, "platform", "linux"), \
                mock.patch.object(mp3_repair.os, "getuid", create=True, return_value=4242), \
                mock.patch.object(mp3_repair.tempfile, "gettempdir", return_value=str(tmp)):
            self.assertEqual(mp3_repair.copies_dir(), tmp / "danceplaylist_repaired-4242")
            src = self.make(audio())
            foreign = mp3_repair.copies_dir()
            foreign.mkdir()                      # owned by someone else (uid 0 here)
            planted = mp3_repair._copy_path(src)
            planted.write_bytes(b"someone else's audio")
            self.assertIsNone(mp3_repair.cached_copy(src))
            self.assertIsNone(mp3_repair.repaired_copy(src))

    def test_a_changed_file_gets_a_new_copy(self):
        src = self.make(audio(4))
        a = mp3_repair.repaired_copy(src)
        src.write_bytes(audio(6))
        os.utime(src, (1, 1))
        self.assertNotEqual(mp3_repair.repaired_copy(src), a)


if __name__ == "__main__":
    unittest.main()
