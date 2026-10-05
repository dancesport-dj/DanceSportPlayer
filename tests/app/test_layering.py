#!/usr/bin/env python3
"""A1: the desk (gui/) never imports the evening (player/).

Run:  py -m unittest tests.app.test_layering -v

gui/ reached into player/ for pure settings logic: the play-set values, the
play-length parser and ladder, the style-for-dances pick and the cartwall
dock width. Those imports were partly local, only to dodge an import cycle,
so a cycle hid behind them. They now live where both sides can reach them.
The launcher dancesport_gui.py wires both and is exempt.

R5 closed the other direction: player/ reached into gui/ for the theme, the
icons, the settings file, the ffmpeg probes and small widgets. Those moved to
shared/, which holds what both sides use and imports neither. An import under
`if TYPE_CHECKING:` never runs, so it does not count; that is how player still
names PlaylistTable in its annotations. planner/ is the no-Qt core and imports
none of the three.
"""

import ast
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def typeCheckingOnly(tree: ast.AST) -> set[int]:
    """ids of the nodes inside an `if TYPE_CHECKING:` body, which never runs."""
    skip = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and (
                getattr(node.test, "id", None) == "TYPE_CHECKING"
                or getattr(node.test, "attr", None) == "TYPE_CHECKING"):
            for stmt in node.body:
                skip.update(id(n) for n in ast.walk(stmt))
    return skip


def importsOf(path: Path, roots: tuple[str, ...]) -> list[str]:
    """Every import in `path` that runs, local ones included, whose top package
    is in `roots`."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = typeCheckingOnly(tree)
    found = []
    for node in ast.walk(tree):
        if id(node) in skip:
            continue
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        else:
            continue
        found += [f"{n} (line {node.lineno})" for n in names if n.split(".")[0] in roots]
    return found


def violations(pkg: str, roots: tuple[str, ...]) -> dict[str, list[str]]:
    out = {}
    for f in sorted((REPO / pkg).rglob("*.py")):
        hits = importsOf(f, roots)
        if hits:
            out[str(f.relative_to(REPO))] = hits
    return out


class LayeringTest(unittest.TestCase):

    def test_gui_never_imports_player(self):
        self.assertEqual(violations("gui", ("player",)), {})

    def test_player_never_imports_gui(self):
        self.assertEqual(violations("player", ("gui",)), {})

    def test_shared_imports_neither_gui_nor_player(self):
        self.assertEqual(violations("shared", ("gui", "player")), {})

    def test_planner_imports_no_widget_package(self):
        self.assertEqual(violations("planner", ("gui", "player", "shared")), {})


class ImportsOfTest(unittest.TestCase):

    def test_a_type_checking_import_does_not_count(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "m.py"
            f.write_text("""from typing import TYPE_CHECKING
import typing
if TYPE_CHECKING:
    from gui.playlist_table import PlaylistTable
if typing.TYPE_CHECKING:
    import gui.deck
else:
    import gui.common
def f():
    from gui.dialogs import load_settings
""", encoding="utf-8")
            self.assertEqual(importsOf(f, ("gui",)),
                             ["gui.common (line 8)", "gui.dialogs (line 10)"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
