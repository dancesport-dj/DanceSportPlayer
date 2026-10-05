#!/usr/bin/env python3
"""A10: production code imports the planner module that owns a name, not the
`dancesport_planner` facade.

Run:  py -m unittest tests.app.test_facade_imports -v

The facade re-exports every public planner name so the command line and old
call sites keep working. Production modules that went through it hid where a
name lives, and `planner/embeddings.py` imported its own package's facade. The
facade stays for the CLI and the tests; nothing under planner/, gui/, player/
or tools/, nor the GUI launcher, may import it.

Importing the facade also re-wrapped a cp1252 console as UTF-8, and the GUI
logs emoji to stdout. The launcher now does that itself, which the second test
holds.
"""

import ast
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACKAGES = ("planner", "gui", "player", "shared", "tools")


def facadeImports(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name == "dancesport_planner" for a in node.names):
                lines.append(node.lineno)
        elif isinstance(node, ast.ImportFrom) and node.module == "dancesport_planner":
            lines.append(node.lineno)
    return lines


class FacadeImportTest(unittest.TestCase):

    def test_no_production_module_imports_the_facade(self):
        files = [REPO / "dancesport_gui.py"]
        for pkg in PACKAGES:
            files += sorted((REPO / pkg).rglob("*.py"))
        found = {str(f.relative_to(REPO)): facadeImports(f) for f in files}
        found = {k: v for k, v in found.items() if v}
        self.assertEqual(found, {})

    def test_the_gui_console_is_utf8_without_the_facade(self):
        env = dict(os.environ,
                   PYTHONIOENCODING="cp1252",
                   QT_QPA_PLATFORM="offscreen",
                   DANCEPLAYLIST_STATE_DIR=tempfile.mkdtemp(prefix="dp_facade_"))
        code = ("import sys, dancesport_gui\n"
                "print('facade loaded' if 'dancesport_planner' in sys.modules else 'facade not loaded')\n"
                "print(sys.stdout.encoding)\n"
                "print('\\U0001f3b5')\n")
        run = subprocess.run([sys.executable, "-c", code], cwd=REPO, env=env,
                             capture_output=True, timeout=120)
        self.assertEqual(run.returncode, 0, run.stderr.decode("utf-8", "replace"))
        facade, encoding, note = run.stdout.decode("utf-8").splitlines()[-3:]
        self.assertEqual(facade, "facade not loaded")
        self.assertEqual(encoding.lower().replace("_", "-"), "utf-8")
        self.assertEqual(note, "\U0001f3b5")


if __name__ == "__main__":
    unittest.main(verbosity=2)
