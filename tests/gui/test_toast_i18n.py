#!/usr/bin/env python3
"""💬 A toast built at runtime speaks German too, not only the literal ones.

Run:  py -m unittest tests.gui.test_toast_i18n -v

`_show_toast` ends in `QLabel.setText`, which the i18n hook patches — so a
toast whose text is a whole literal ("✅  Kept all titles") was German all
along, and every toast that carried a number or a name was not:

    _show_toast(self, f"🧹  Removed {n} duplicate {titles}")

reaches the label as "🧹  Removed 3 duplicate titles", which is no catalog
key. Same class as the analysis passes (test_analyze_i18n): nothing is missing
from the catalog, nothing reaches a widget as a whole literal. The fix is the
project's pattern — `i18n.t("🧹  Removed %d duplicate titles") % n`, one whole
sentence per singular/plural, because German moves the verb.

The guard below reads the source, so a new f-string toast fails here the day
it is written instead of the day someone switches the app to German.
"""

import ast
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_toast_i18n_"))

from gui.table_dynamic import DynamicModeMixin  # noqa: E402
from planner import i18n  # noqa: E402
from planner.models import MusicEntry  # noqa: E402

_ROOT = Path(__file__).resolve().parents[2]
_SOURCES = [*sorted((_ROOT / "gui").glob("*.py")),
            *sorted((_ROOT / "player").glob("*.py")),
            *sorted((_ROOT / "shared").glob("*.py")),
            _ROOT / "dancesport_gui.py"]


def _is_toast(call: ast.Call) -> bool:
    f = call.func
    name = f.id if isinstance(f, ast.Name) else getattr(f, "attr", None)
    return name == "_show_toast"


def _toast_text(call: ast.Call):
    for kw in call.keywords:
        if kw.arg == "text":
            return kw.value
    return call.args[1] if len(call.args) > 1 else None


def _has_fstring(node) -> bool:
    return any(isinstance(n, ast.JoinedStr) for n in ast.walk(node))


def _untranslated_toasts() -> list[str]:
    """Every toast whose text is an f-string, directly or through the local
    variable it is handed — an f-string can never be a catalog key."""
    found = []
    for path in _SOURCES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            built = {}
            for n in ast.walk(fn):
                if isinstance(n, ast.Assign):
                    for tgt in n.targets:
                        if isinstance(tgt, ast.Name):
                            built.setdefault(tgt.id, []).append(n.value)
                elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
                    built.setdefault(n.target.id, []).append(n.value)
            for call in ast.walk(fn):
                if not (isinstance(call, ast.Call) and _is_toast(call)):
                    continue
                text = _toast_text(call)
                if text is None:
                    continue
                parts = [text]
                if isinstance(text, ast.Name):
                    parts = built.get(text.id, [])
                if any(_has_fstring(p) for p in parts):
                    found.append(f"{path.relative_to(_ROOT).as_posix()}:{call.lineno}")
    return sorted(set(found))


class ToastSourceTest(unittest.TestCase):
    def test_no_toast_is_an_fstring(self):
        self.assertEqual(_untranslated_toasts(), [])


class _Drop(DynamicModeMixin):
    pass


def _entry(title):
    return MusicEntry(path=Path(f"C:/lib/{title}.mp3"), title=title,
                      dance="SA", bpm=51)


class ToastGermanTest(unittest.TestCase):
    def setUp(self):
        i18n.set_active("de")

    def tearDown(self):
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def test_a_drop_that_placed_nothing_says_why_in_german(self):
        skipped = {"dup": [_entry("A"), _entry("B")], "dance": [_entry("C")]}
        self.assertEqual(_Drop()._nothing_added(skipped),
                         "Nichts hinzugefügt — 2 schon eingeplant, 1 ohne Tanz")

    def test_the_one_track_is_named_and_stays_itself(self):
        # "Time" is a column header elsewhere — as a title it is data.
        self.assertEqual(
            _Drop()._nothing_added({"dup": [_entry("Time")]}),
            "⚠  „Time“ ist schon in dieser Playlist — nichts hinzugefügt")


if __name__ == "__main__":
    unittest.main()
