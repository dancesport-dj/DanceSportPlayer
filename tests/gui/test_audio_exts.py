#!/usr/bin/env python3
"""The audio allowlist (_AUDIO_EXTS) is the one the comment documents.

Run:  .venv\\Scripts\\python.exe -m unittest tests.gui.test_audio_exts -v

gui/common.py defined the tuple twice. The second, shorter definition further
down the module won, so .m4b, .oga, .opus, .aiff and .aif were refused by the
open verb, the drop zones and the cartwall although the allowlist names them.
"""

import ast
import os
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui import common  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DOCUMENTED = (".mp3", ".m4a", ".m4b", ".flac", ".wav", ".ogg",
              ".oga", ".opus", ".aac", ".wma", ".aiff", ".aif")


class AudioExtsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_every_documented_format_passes_the_open_gate(self):
        for ext in DOCUMENTED:
            with self.subTest(ext=ext), mock.patch.object(common, "QMessageBox") as box:
                common._open_in_default_player(Path(f"Z:/nowhere/track{ext}"))
                text = box.warning.call_args.args[2]
                # Past the suffix gate, a missing file is the only complaint.
                self.assertIn("File not found", text)

    def test_a_script_is_still_refused(self):
        with mock.patch.object(common, "QMessageBox") as box:
            common._open_in_default_player(Path("Z:/nowhere/run.bat"))
        self.assertIn("not an audio file", box.warning.call_args.args[2])

    def test_the_tuple_is_defined_once(self):
        defs = []
        for pkg in ("gui", "player", "shared"):
            for py in (REPO / pkg).rglob("*.py"):
                tree = ast.parse(py.read_text(encoding="utf-8"))
                defs += [f"{py.relative_to(REPO)}:{n.lineno}" for n in tree.body
                         if isinstance(n, ast.Assign) and any(
                             isinstance(t, ast.Name) and t.id == "_AUDIO_EXTS"
                             for t in n.targets)]
        self.assertEqual(len(defs), 1, f"_AUDIO_EXTS assigned at {defs}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
