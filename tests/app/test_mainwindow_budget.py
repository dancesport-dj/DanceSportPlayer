#!/usr/bin/env python3
"""H1: MainWindow's own state may only shrink.

Run:  py -m unittest tests.app.test_mainwindow_budget -v

MainWindow is one object assembled from ~25 mixins, and every mixin can read
and write every attribute on it. The way out is to move state into owning
objects the window composes (ResumeMarks, LibraryService, ...), one seam at a
time. This test keeps that moving in one direction: it counts the distinct
attribute names the window's own classes store on `self` (plus their
class-level assignments) and holds the count to BUDGET.

- More than BUDGET: a new attribute landed on the window. Put it on the
  object that owns that part of the state instead.
- Fewer than BUDGET: an extraction worked. Lower BUDGET to the new count, so
  the room it freed cannot quietly fill up again.

Counted from the source, not from a live window: an attribute set only on a
rare path (a dialog opened once) counts as well. Names are counted once, so a
mixin writing an attribute the window already has costs nothing.
"""

import ast
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

BUDGET = 226


def ownClasses() -> list[tuple[type, Path]]:
    """MainWindow and every class in its MRO that is defined in this repo."""
    import dancesport_gui
    out = []
    for cls in dancesport_gui.MainWindow.__mro__:
        file = getattr(sys.modules.get(cls.__module__), "__file__", None)
        if not file:
            continue
        path = Path(file).resolve()
        if path.is_relative_to(REPO) and ".venv" not in path.parts:
            out.append((cls, path))
    return out


def storedNames(cls: type, path: Path) -> set[str]:
    """Names `cls` assigns at class level or stores on `self` in its body."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(n for n in ast.walk(tree)
                if isinstance(n, ast.ClassDef) and n.name == cls.__name__)
    names = set()
    for stmt in node.body:
        targets = (stmt.targets if isinstance(stmt, ast.Assign)
                   else [stmt.target] if isinstance(stmt, ast.AnnAssign) else [])
        names.update(t.id for t in targets if isinstance(t, ast.Name))
    for n in ast.walk(node):
        if (isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Store)
                and isinstance(n.value, ast.Name) and n.value.id == "self"):
            names.add(n.attr)
    return names


def windowNames() -> dict[str, list[str]]:
    """Each attribute name → the classes that store it."""
    found = {}
    for cls, path in ownClasses():
        for name in storedNames(cls, path):
            found.setdefault(name, []).append(cls.__name__)
    return found


class MainWindowBudgetTest(unittest.TestCase):

    def test_the_window_holds_no_more_attributes_than_its_budget(self):
        count = len(windowNames())
        self.assertLessEqual(
            count, BUDGET,
            f"MainWindow now stores {count} attribute names, budget {BUDGET}. "
            "Put the new state on the object that owns it, not on the window.")

    def test_the_budget_follows_every_extraction_down(self):
        count = len(windowNames())
        self.assertGreaterEqual(
            count, BUDGET,
            f"MainWindow stores {count} attribute names, fewer than its budget "
            f"{BUDGET}. Lower BUDGET in {Path(__file__).name} to {count}.")

    def test_the_scan_sees_the_mixins_and_their_state(self):
        # Guards the counter itself: a scan that finds nothing passes any budget.
        names = windowNames()
        self.assertIn("DeckLayoutMixin", [c.__name__ for c, _ in ownClasses()])
        self.assertIn("_resume", names)            # set in MainWindow.__init__
        self.assertIn("_space_at", names)          # a class-level assignment
        self.assertIn("GenerateMixin", names["_suggester"])  # set in a mixin


if __name__ == "__main__":
    unittest.main()
