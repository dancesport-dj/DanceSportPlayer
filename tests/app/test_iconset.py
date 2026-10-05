"""Every icon name the GUI asks for must exist in the icon set.

The names are plain strings scattered over ~20 modules, so a typo (or a rename
in tools/make_iconset.py) only shows up as a blank button at runtime — and only on the
one dialog nobody opened. This walks the source instead.
"""
import ast
import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from shared import icons

_ROOT = Path(__file__).resolve().parents[2]

# The three entry points that take an icon name as their first string argument.
_BY_FIRST_ARG = {"icon", "pixmap", "icon_pixmap", "html", "icon_html"}
# button(widget, name, …) / icon_button(widget, name, …) take it second.
_BY_SECOND_ARG = {"button", "icon_button"}


def _icon_names_in(path: Path):
    """(name, lineno) for every literal icon name passed to the shared.icons API."""
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        fn = node.func.id
        if fn in _BY_FIRST_ARG:
            args = node.args[:1]
        elif fn in _BY_SECOND_ARG:
            args = node.args[1:2]
        else:
            continue
        for a in args:
            if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value:
                yield a.value, node.lineno


class IconNamesTest(unittest.TestCase):
    def test_every_name_used_in_the_app_exists(self):
        known = set(icons.names())
        missing = []
        for py in sorted(p for d in ("", "gui/", "player/", "planner/", "shared/", "tools/")
                         for p in _ROOT.glob(d + "*.py")):
            rel = py.relative_to(_ROOT).as_posix()
            if rel in ("shared/icons.py", "shared/iconset.py", "tools/make_iconset.py"):
                continue
            for name, line in _icon_names_in(py):
                if name not in known:
                    missing.append(f"{rel}:{line}  {name!r}")
        self.assertEqual(missing, [], "unknown icon name(s):\n" + "\n".join(missing))

    def test_the_api_actually_paints_something(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        for name in ("play", "stop", "star", "gear", "regen"):
            self.assertFalse(icons.pixmap(name, 16).isNull(), name)
            self.assertIn("<img", icons.html(name, 16))


if __name__ == "__main__":
    unittest.main()
