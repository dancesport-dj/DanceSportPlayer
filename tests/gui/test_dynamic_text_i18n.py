#!/usr/bin/env python3
"""🌐 No text reaches a translated widget as an English f-string.

Run:  py -m unittest tests.gui.test_dynamic_text_i18n -v

The i18n hook translates a string on its way into Qt by looking it up whole,
so a literal — `setText("Nothing to save.")` — is German the day it gets a
catalog entry. A string BUILT at runtime is not:

    self.statusBar().showMessage(f"Saved {n} playlists → {out}")

reaches Qt as "Saved 3 playlists → C:\\…", which is no catalog key, and stays
English in a German app while every button around it is translated. The
toasts were the first batch of this (test_toast_i18n); this is the rest —
the status bar, the message boxes, the labels and tooltips.

The fix is always the same: `i18n.t("Saved %d playlists → %s") % (n, out)`,
one whole sentence per singular/plural, because German moves the verb.

What counts as "English": a word of three letters or more in the literal part
of the built string, HTML tags stripped. `f"{ms / 1000:.1f} s"` has none and
passes. A line that builds text which really is data — a file name in a
group-box title, a German unit that is German in both languages — says so
with a `# i18n: data` comment, on the call or the line above it, and is
skipped.

The second half is the other way round: a literal is only German once it HAS
an entry. Every English literal a sink gets, and every literal handed to
i18n.t, must be a catalog key. A text that reads the same in German
("Cartwall", "⏭  Auto") goes into _SAME_IN_GERMAN instead — the catalog may
not hold an entry that translates to itself (test_i18n).
"""

import ast
import re
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SOURCES = [*sorted((_ROOT / "gui").glob("*.py")),
            *sorted((_ROOT / "player").glob("*.py")),
            *sorted((_ROOT / "shared").glob("*.py")),
            _ROOT / "dancesport_gui.py"]

# Every call whose text the hook translates → the positions that carry text.
_SINKS = {
    "setText": (0,), "setWindowTitle": (0,), "setToolTip": (0,),
    "setStatusTip": (0,), "setTitle": (0,), "setPlaceholderText": (0,),
    "addAction": (0, 1), "addMenu": (0, 1), "addTab": (1,), "setTabText": (1,),
    "addItem": (0,), "showMessage": (0,), "setLabelText": (0,),
    "addButton": (0,), "setSuffix": (0,), "setInformativeText": (0,),
    "information": (1, 2), "question": (1, 2), "warning": (1, 2),
    "critical": (1, 2), "about": (1, 2), "getText": (1, 2), "getItem": (1, 2),
    "QLabel": (0,), "QPushButton": (0,), "QCheckBox": (0,),
    "QRadioButton": (0,), "QGroupBox": (0,), "QToolButton": (0,),
    "QMenu": (0,), "QAction": (0, 1),
    "_show_toast": (1,), "_confirm_delete": (0, 1),
    # The app's own helpers that end in a label.
    "BusyDialog": (1,), "set_message": (0,), "_finish_ai_log": (0,),
    "add_step": (1, 2), "_set_countdown": (0,), "_run_export": (0,),
    "finish": (0,), "set_countdown": (0,), "set_status": (0,), "show_status": (0,),
    "_show_hints": (0,), "_reset_playback_ui": (0,), "mark_done": (1,),
    "_lbl": (0,), "_b": (0,), "_section": (0,), "_section_heading": (0,),
    "_col_header": (0,), "_foot_btn": (0,), "_set_btn": (1,), "chk": (1, 3),
    "spin_row": (0, 2), "_tempo_step_btn": (0, 2), "_run_library_pass": (1, 3),
}
# Keyword arguments that carry the text, wherever the sink takes them.
_TEXT_KWARGS = ("message", "text")
_MARKER = "# i18n: data"
# Texts that read the same in German: names, and words German borrowed. The
# catalog may not map them to themselves, so they are listed here instead.
_SAME_IN_GERMAN = {
    "DanceSport Planner & Player", "Eintanzen", "🤸  Eintanzen / Party",
    "🤸  Eintanzen / Party ▾", "Cartwall", "🎛  Cartwall", "Slot %d", "Pool", "TSO",
    "Name:", "⏭  Auto", "🔈  Test", "♪ Takt", "≈ Takt", "— Standard —",
    "🎻 Instrumental", "🎚️ librosa: %s", "🎼 Chroma: %s", "🧠 OpenL3: %s",
    "Social Modetänze (Discofox, Salsa, Bachata, WCS, …)", "Tags", "Frame",
    "Custom:", "Version",
}
_TAG = re.compile(r"<[^>]*>|&\w+;|\w*_\w*")   # tags, entities, file_name_parts
_WORD = re.compile(r"[A-Za-z]{3,}")


def _english(text: str) -> bool:
    return bool(_WORD.search(_TAG.sub(" ", text)))


def _call_name(call: ast.Call):
    f = call.func
    return f.id if isinstance(f, ast.Name) else getattr(f, "attr", None)


def _is_t(node) -> bool:
    return isinstance(node, ast.Call) and _call_name(node) == "t"


class _Scope:
    """What each local name was assigned, appended or added in one function."""

    def __init__(self, fn):
        self.values: dict[str, list] = {}
        for n in ast.walk(fn):
            if isinstance(n, ast.Assign):
                for tgt in n.targets:
                    if isinstance(tgt, ast.Name):
                        self.values.setdefault(tgt.id, []).append((n.value, False))
            elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) \
                    and n.value is not None:
                self.values.setdefault(n.target.id, []).append((n.value, False))
            elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
                self.values.setdefault(n.target.id, []).append((n.value, True))
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                    and isinstance(n.func.value, ast.Name) \
                    and n.func.attr in ("append", "extend", "insert") and n.args:
                self.values.setdefault(n.func.value.id, []).append((n.args[-1], True))


def _built(node, scope: _Scope, dyn: bool, seen: frozenset = frozenset()) -> bool:
    """Whether `node` puts English text together at runtime, outside i18n.t.

    `dyn` says the node is already part of a built string, where even a plain
    literal is lost: `"In playlist: " + name` is no catalog key."""
    if _is_t(node):
        return False
    if isinstance(node, ast.Constant):
        return dyn and isinstance(node.value, str) and _english(node.value)
    if isinstance(node, ast.JoinedStr):
        # The literal parts as one text, so a tag split by a placeholder
        # (`f'<a href="{i}">'`) is still stripped whole.
        literal = "\x00".join(v.value for v in node.values if isinstance(v, ast.Constant))
        return _english(literal) or any(
            _built(v.value, scope, True, seen)
            for v in node.values if isinstance(v, ast.FormattedValue))
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Constant):
            return isinstance(node.left.value, str) and _english(node.left.value)
        if isinstance(node.op, ast.Mod) and _is_t(node.left):
            # What fills the placeholders is data; only a built string there
            # (an f-string) can still hide English.
            return _built(node.right, scope, False, seen)
        if isinstance(node.op, ast.Div):
            return False                         # a path: OUTPUT_DIR / "wishlists"
        both_dyn = dyn or isinstance(node.op, ast.Add)
        return (_built(node.left, scope, both_dyn, seen)
                or _built(node.right, scope, both_dyn, seen))
    if isinstance(node, ast.IfExp):
        return _built(node.body, scope, dyn, seen) or _built(node.orelse, scope, dyn, seen)
    if isinstance(node, ast.BoolOp):
        return any(_built(v, scope, dyn, seen) for v in node.values)
    if isinstance(node, (ast.List, ast.Tuple)):
        return any(_built(v, scope, dyn, seen) for v in node.elts)
    if isinstance(node, (ast.GeneratorExp, ast.ListComp)):
        return _built(node.elt, scope, dyn, seen)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        owner = node.func.value
        if node.func.attr == "format" and isinstance(owner, ast.Constant):
            return isinstance(owner.value, str) and _english(owner.value)
        if node.func.attr == "join":
            if isinstance(owner, ast.Constant) and isinstance(owner.value, str) \
                    and _english(owner.value):
                return True
            return any(_built(a, scope, True, seen) for a in node.args)
        return False
    if isinstance(node, ast.Name) and node.id not in seen:
        return any(_built(v, scope, dyn or force, seen | {node.id})
                   for v, force in scope.values.get(node.id, []))
    return False


def _untranslated() -> list[str]:
    found = []
    for path in _SOURCES:
        source = path.read_text(encoding="utf-8")
        lines = source.splitlines()
        tree = ast.parse(source)
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            scope = _Scope(fn)
            for call in ast.walk(fn):
                if not isinstance(call, ast.Call):
                    continue
                positions = _SINKS.get(_call_name(call))
                if positions is None:
                    continue
                span = lines[call.lineno - 2:call.end_lineno]   # + the line above
                if any(_MARKER in line for line in span):
                    continue
                texts = [call.args[i] for i in positions if i < len(call.args)]
                texts += [k.value for k in call.keywords if k.arg in _TEXT_KWARGS]
                if any(_built(t, scope, False) for t in texts):
                    found.append(f"{path.relative_to(_ROOT).as_posix()}:{call.lineno}")
    return sorted(set(found), key=lambda s: (s.split(":")[0], int(s.split(":")[1])))


def _literals(node):
    """The plain texts a sink argument can be: a literal, or either branch of
    `a if c else b` / `a or b`."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        yield node
    elif isinstance(node, ast.IfExp):
        yield from _literals(node.body)
        yield from _literals(node.orelse)
    elif isinstance(node, ast.BoolOp):
        for v in node.values:
            yield from _literals(v)


def _uncataloged() -> list[str]:
    from planner.lang_de import CATALOG
    found = []
    for path in [*_SOURCES, *sorted((_ROOT / "planner").glob("*.py"))]:
        source = path.read_text(encoding="utf-8")
        lines = source.splitlines()
        in_planner = path.parent.name == "planner"
        for call in ast.walk(ast.parse(source)):
            if not isinstance(call, ast.Call):
                continue
            if _is_t(call):
                texts = call.args[:1]
            elif _call_name(call) in _SINKS and not in_planner:
                texts = [call.args[i] for i in _SINKS[_call_name(call)]
                         if i < len(call.args)]
                texts += [k.value for k in call.keywords if k.arg in _TEXT_KWARGS]
            else:
                continue
            span = lines[call.lineno - 2:call.end_lineno]
            if any(_MARKER in line for line in span):
                continue
            for arg in texts:
                for lit in _literals(arg):
                    if _english(lit.value) and lit.value not in CATALOG \
                            and lit.value not in _SAME_IN_GERMAN:
                        found.append(f"{path.relative_to(_ROOT).as_posix()}:{lit.lineno}"
                                     f"  {lit.value[:60]!r}")
    return sorted(set(found))


class DynamicTextSourceTest(unittest.TestCase):
    def test_no_widget_text_is_built_in_english(self):
        self.assertEqual(_untranslated(), [])

    def test_every_english_literal_has_a_german_entry(self):
        self.assertEqual(_uncataloged(), [])


if __name__ == "__main__":
    unittest.main()
