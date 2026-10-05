"""Run the tests a commit has to pass, read off the files it stages.

The whole suite is too slow to carry every commit (~3400 tests, ~4.5 min), and
a gate that slow ends up skipped with --no-verify. So the pre-commit hook asks
this tool which part of the suite the staged change can actually break:

* A commit that stays inside ONE logic area — planner, gui, player, app —
  runs that area's test package.
* A commit that spans two or more areas, or is a bigger refactoring (8+ Python
  files or 400+ changed lines), runs the whole suite.
* The shared test plumbing, the dependencies and the lint/hook config run the
  whole suite too: they reach every test. So does shared/, the widget code
  both the desk and the evening build on.
* planner/lang_de.py, the German catalog, is not an area of its own logic. It
  adds the *_i18n tests from every package instead of turning a player change
  that brought three new captions into a two-area commit.
* A commit without Python in it (docs, clips, playlists) runs no tests.
* FULL_SUITE=1 forces the whole suite.

The pre-push hook always runs everything, so what a scoped commit misses is
caught before it leaves the machine.

    .venv\\Scripts\\python.exe -m tools.commit_scope          # decide + run
    .venv\\Scripts\\python.exe -m tools.commit_scope --plan   # decide only
"""
import os
import subprocess
import sys

AREAS = ("planner", "gui", "player", "app")

# Where a path's code lives, by prefix. tools/ and the build shims are tested
# from tests/app.
AREA_PREFIXES = {
    "planner/": "planner",
    "dancesport_planner.py": "planner",
    "gui/": "gui",
    "dancesport_gui.py": "gui",
    "player/": "player",
    "tools/": "app",
    "_build_shims/": "app",
}

FULL_TRIGGERS = (
    "tests/qt_test_support.py",
    "tests/__init__.py",
    "shared/",
    "requirements",
    "pyproject.toml",
    ".githooks/",
    ".github/",
)

CATALOG = "planner/lang_de.py"
I18N_PATTERN = "test_*i18n*.py"
ALL_TESTS = "test_*.py"

BIG_FILES = 8
BIG_LINES = 400


def area_of(path: str) -> str | None:
    """The area a staged path belongs to, 'full', 'i18n', or None (no tests)."""
    if path.startswith(FULL_TRIGGERS):
        return "full"
    if path == CATALOG:
        return "i18n"
    parts = path.split("/")
    if parts[0] == "tests" and len(parts) > 2 and parts[1] in AREAS:
        return parts[1]
    for prefix, area in AREA_PREFIXES.items():
        if path.startswith(prefix):
            return area if path.endswith(".py") else None
    return None


def plan(changes: list[tuple[str, int]]) -> tuple[list[tuple[str, str]] | None, str]:
    """Decide from (path, changed lines) pairs.

    Returns the (start dir, pattern) runs to make — None for the whole suite —
    and the reason in one line.
    """
    areas = set()
    i18n = False
    py_files = 0
    py_lines = 0
    for path, lines in changes:
        area = area_of(path)
        if area == "full":
            return None, f"{path} reaches every test"
        if area == "i18n":
            i18n = True
            continue
        if area is not None:
            areas.add(area)
        if path.endswith(".py"):
            py_files += 1
            py_lines += lines
    if len(areas) > 1:
        return None, f"spans {len(areas)} areas: {', '.join(sorted(areas))}"
    if py_files >= BIG_FILES or py_lines >= BIG_LINES:
        return None, f"big change: {py_files} Python files, {py_lines} lines"
    runs = [(f"tests/{area}", ALL_TESTS) for area in sorted(areas)]
    if i18n:
        runs.append(("tests", I18N_PATTERN))
    if not runs:
        return [], "no Python code staged"
    return runs, f"stays in {', '.join(sorted(areas)) or 'the catalog'}" + (" + i18n" if i18n else "")


def staged_changes() -> list[tuple[str, int]]:
    """(path, added + deleted lines) for every staged file; renames as delete + add."""
    out = subprocess.run(
        ["git", "diff", "--cached", "--numstat", "--no-renames"],
        capture_output=True, text=True, encoding="utf-8", check=True).stdout
    changes = []
    for line in out.splitlines():
        added, deleted, path = line.split("\t", 2)
        lines = 0 if added == "-" else int(added) + int(deleted)
        changes.append((path, lines))
    return changes


def run(runs: list[tuple[str, str]] | None) -> int:
    if runs is None:
        runs = [(".", ALL_TESTS)]
    failed = 0
    for start, pattern in runs:
        print(f"🧪 {start} {pattern}", flush=True)
        failed |= subprocess.run(
            [sys.executable, "-m", "unittest", "discover",
             "-s", start, "-t", ".", "-p", pattern, "-q"]).returncode
    return failed


def main(argv: list[str]) -> int:
    # The console is cp1252; the decision line leads with an emoji.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    if os.environ.get("FULL_SUITE") == "1":
        runs, reason = None, "FULL_SUITE=1"
    else:
        runs, reason = plan(staged_changes())
    print(f"🎯 {'whole suite' if runs is None else 'scoped'} — {reason}", flush=True)
    if "--plan" in argv:
        return 0
    return run(runs)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
