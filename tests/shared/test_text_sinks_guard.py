"""A new label or tooltip that shows outside text must say it is text.

Run:  py -m unittest tests.shared.test_text_sinks_guard -v

Qt reads text that looks like markup as markup, and an `<img src>` in it opens
that path (an SMB login for a UNC path): security audit run-2 #3. Message boxes
are covered once, for all of them, by `shared.plain_text.install_message_boxes`;
labels and tooltips have no such switch, so each site is made safe by hand:
`plain_label(text)` for a label, `plain_tip(text)` for a tooltip.

This test finds every `QLabel(x)` and `.setToolTip(x)` in the app whose `x` is
not a literal (or a translated literal) and is not made safe. The sites that
exist today were each read and hold text of ours (fixed wording, counts, enum
names), a value that is escaped on the way in, or a label whose text format is
set to plain text. `BASELINE` is that reviewed count per file. A file that
goes over it has a new site:

* text that can come from a tag, a playlist, a pack or a server: wrap it in
  `plain_label` / `plain_tip`;
* text that is ours: raise the number here, in the same commit.

A file that goes under it is a cleanup: lower the number, so the room it freed
cannot hide a new site later.
"""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCANNED = ("gui", "player", "planner", "shared", "speech")
SCANNED_FILES = ("dancesport_gui.py", "dancesport_planner.py")

# file -> (QLabel sites, setToolTip sites), as reviewed.
BASELINE: dict[str, tuple[int, int]] = {
    "dancesport_gui.py": (0, 3),
    "gui/background_bar.py": (1, 0),
    "gui/common.py": (5, 2),
    "gui/config_panel.py": (0, 4),
    "gui/dialogs/__init__.py": (13, 0),
    "gui/dialogs/about.py": (1, 0),
    "gui/dialogs/ai_dialogs.py": (3, 2),
    "gui/dialogs/drop_check.py": (1, 0),
    "gui/dialogs/drop_duplicates_dialog.py": (1, 0),
    "gui/dialogs/duplicate_dialog.py": (8, 1),
    "gui/dialogs/duplicate_titles_dialog.py": (1, 0),
    "gui/dialogs/event_compare.py": (1, 2),
    "gui/dialogs/look_editor.py": (4, 3),
    "gui/dialogs/readiness_dialog.py": (2, 0),
    "gui/dialogs/reset_db_dialog.py": (1, 0),
    "gui/dialogs/settings_dialog.py": (3, 0),
    "gui/dialogs/settings_play_sets.py": (5, 1),
    "gui/dialogs/settings_sound.py": (3, 4),
    "gui/dialogs/similar_dialog.py": (0, 4),
    "gui/dialogs/tag_edit_dialog.py": (2, 2),
    "gui/dialogs/warmup_dialog.py": (0, 1),
    "gui/library_browser.py": (1, 2),
    "gui/library_load_bar.py": (1, 3),
    "gui/table/find_bar.py": (0, 2),
    "gui/table/playlist_table.py": (0, 6),
    "gui/table/table_dnd.py": (0, 1),
    "gui/table/table_load.py": (0, 1),
    "gui/tournament_tiles.py": (1, 1),
    "gui/tournament_tree.py": (0, 2),
    "gui/window/main_deck_setup.py": (0, 1),
    "gui/window/main_decks.py": (0, 2),
    "gui/window/main_fold.py": (0, 3),
    "gui/window/main_generate.py": (0, 1),
    "gui/window/main_music.py": (6, 5),
    "gui/window/main_paths.py": (3, 0),
    "player/dialogs/cart_pad_dialog.py": (2, 0),
    "player/dialogs/desk_keys_dialog.py": (1, 1),
    "player/dialogs/play_log_dialog.py": (1, 0),
    "player/presenter/presenter.py": (0, 2),
    "player/presenter/timetable_dialog.py": (0, 1),
    "player/widgets/cart_keys.py": (3, 1),
    "player/widgets/cartwall.py": (0, 3),
    "player/widgets/play_mode_panel.py": (0, 6),
    "player/widgets/play_mode_setup.py": (0, 3),
    "player/widgets/player.py": (0, 6),
    "player/widgets/player_setup.py": (0, 6),
    "shared/audio/eq_panel.py": (1, 0),
    "shared/plain_text.py": (1, 0),
    "shared/widgets.py": (1, 0),
    "shared/xfade_view.py": (0, 3),
}


def isLiteral(node) -> bool:
    """A string we wrote: a literal, an f-string of literals, a translated literal."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.JoinedStr):
        return all(isinstance(v, ast.Constant) for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return isLiteral(node.left) and isLiteral(node.right)
    if isinstance(node, ast.Call):
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
        return name == "t" and len(node.args) == 1 and isLiteral(node.args[0])
    return False


def isMadeSafe(node) -> bool:
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "plain_tip")


def sourceFiles():
    for top in SCANNED:
        yield from sorted((ROOT / top).rglob("*.py"))
    for name in SCANNED_FILES:
        yield ROOT / name


def scan() -> dict[str, tuple[int, int]]:
    found: dict[str, tuple[int, int]] = {}
    for path in sourceFiles():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        labels = tips = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func, arg = node.func, node.args[0]
            if isinstance(func, ast.Name) and func.id == "QLabel" and not isLiteral(arg):
                labels += 1
            elif (isinstance(func, ast.Attribute) and func.attr == "setToolTip"
                    and not isLiteral(arg) and not isMadeSafe(arg)):
                tips += 1
        if labels or tips:
            found[path.relative_to(ROOT).as_posix()] = (labels, tips)
    return found


class TextSinksGuardTest(unittest.TestCase):

    def test_no_new_label_or_tooltip_shows_outside_text_unmarked(self):
        found = scan()
        over = []
        for name, (labels, tips) in sorted(found.items()):
            ok_labels, ok_tips = BASELINE.get(name, (0, 0))
            if labels > ok_labels:
                over.append(f"{name}: {labels} QLabel(...) with non-literal text, "
                            f"{ok_labels} reviewed -> plain_label(...) if it can hold "
                            f"tag, playlist or pack text")
            if tips > ok_tips:
                over.append(f"{name}: {tips} setToolTip(...) with non-literal text, "
                            f"{ok_tips} reviewed -> plain_tip(...) if it can hold "
                            f"tag, playlist or pack text")
        self.assertEqual(over, [], "\n" + "\n".join(over))

    def test_a_cleaned_up_file_lowers_its_number(self):
        found = scan()
        slack = []
        for name, (ok_labels, ok_tips) in sorted(BASELINE.items()):
            labels, tips = found.get(name, (0, 0))
            if labels < ok_labels or tips < ok_tips:
                slack.append(f"{name}: BASELINE says ({ok_labels}, {ok_tips}), "
                             f"the file has ({labels}, {tips})")
        self.assertEqual(slack, [], "\n" + "\n".join(slack))

    def test_the_scan_sees_what_it_should(self):
        # A scan that finds nothing would pass both tests above for ever.
        sample = ast.parse("QLabel(title)\nx.setToolTip(path)\n"
                           "x.setToolTip(plain_tip(path))\nQLabel('ok')")
        calls = [n for n in ast.walk(sample) if isinstance(n, ast.Call)]
        self.assertEqual([isLiteral(c.args[0]) for c in calls
                          if c.args and isinstance(c.args[0], ast.Constant)], [True])
        self.assertGreater(len(scan()), 10)


if __name__ == "__main__":
    unittest.main()
