"""🛡 Text that arrives from a phone or from a dance name stays text (review #26):
a clip name cannot walk out of its folder, and a phone's text cannot start a
fake line in the log."""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_clipcmd_"))

from player.audio import announce
from player.window import main_remote


class FindClipTest(unittest.TestCase):

    def test_a_stem_cannot_leave_its_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "voice").mkdir()
            (root / "secret.mp3").write_bytes(b"x")
            (root / "voice" / "ok.mp3").write_bytes(b"x")
            folders = [root / "voice"]
            self.assertEqual(announce.find_clip(folders, "ok"), root / "voice" / "ok.mp3")
            for stem in ("../secret", "..\\secret", "sub/x", "C:secret", ".."):
                with self.subTest(stem=stem):
                    self.assertIsNone(announce.find_clip(folders, stem))


class CommandLogLineTest(unittest.TestCase):

    def test_a_phone_text_cannot_add_a_line(self):
        line = main_remote.command_log_line("jump", (3, "x\n2026-01-01 W fake line"))
        self.assertNotIn("\n", line)
        self.assertIn("fake line", line)

    def test_no_argument_adds_nothing(self):
        self.assertEqual(main_remote.command_log_line("next", None), "📱 Remote: next")
        self.assertEqual(main_remote.command_log_line("seek", 0.5), "📱 Remote: seek 0.5")


if __name__ == "__main__":
    unittest.main()
