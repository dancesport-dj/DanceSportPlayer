"""List the app lines that only the GUI walks reach: run, but never asserted.

Line coverage counts a line as covered when any test ran it. The random monkey
walks (tests/gui/test_monkey.py) run a large part of gui/ without checking what
the code did — they fail on an escaped exception and on a few invariants, not
on a wrong result. A line no other test reaches is covered by the number and
untested in fact. This tool reads a coverage file recorded with one context
per test and lists those lines.

Record it from the repo root (the loopback HTTP tests need their own serial
call, see the Testing Practices note), with the C tracer: on Python 3.14
coverage defaults to sys.monitoring, which stops watching a line once it ran,
so each line keeps only the first test that reached it — a walk that came first
would own lines a unit test checks.

    set COVERAGE_CORE=ctrace
    .venv\\Scripts\\python.exe -m pytest --cov --cov-context=test --cov-report= \\
        --ignore=tests/shared/remote --ignore=tests/player/window/test_remote_mixin.py
    .venv\\Scripts\\python.exe -m pytest -n0 --cov --cov-append --cov-context=test \\
        --cov-report= tests/shared/remote tests/player/window/test_remote_mixin.py

Then:

    .venv\\Scripts\\python.exe -m tools.dev.coverage_contexts            # per file
    .venv\\Scripts\\python.exe -m tools.dev.coverage_contexts gui/x.py   # its lines
"""
import argparse
import os
import sys

from coverage import CoverageData

# Test ids whose coverage does not count as checked: the random walks.
WALK_TESTS = ("tests/gui/test_monkey.py",)


def test_file_of(context: str) -> str:
    """'tests/gui/test_x.py::Cls::test_y|run' -> 'tests/gui/test_x.py'."""
    return context.split("::", 1)[0].replace("\\", "/")


def is_walk(context: str) -> bool:
    return test_file_of(context) in WALK_TESTS


def walk_only_lines(data: CoverageData, path: str) -> list[int]:
    """The lines of `path` that a walk ran and no other test did.

    A line with only the empty context ran at import time, before any test
    (a `def`, a module constant): no test owns it, so it is left out."""
    by_line = data.contexts_by_lineno(path)
    out = []
    for line, contexts in by_line.items():
        named = [c for c in contexts if c]
        if named and all(is_walk(c) for c in named):
            out.append(line)
    return sorted(out)


def ranges(lines: list[int]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for n in lines:
        if out and n == out[-1][1] + 1:
            out[-1] = (out[-1][0], n)
        else:
            out.append((n, n))
    return out


def relative(path: str) -> str:
    return os.path.relpath(path).replace("\\", "/")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("files", nargs="*", help="show the line ranges of these files")
    ap.add_argument("--data", default=".coverage", help="coverage data file")
    ap.add_argument("--top", type=int, default=40, help="files to list")
    args = ap.parse_args(argv)

    data = CoverageData(args.data)
    data.read()
    if not data.measured_contexts() - {""}:
        print("No per-test contexts in this file: record it with --cov-context=test.")
        return 2
    measured = {relative(p): p for p in data.measured_files()}

    if args.files:
        for name in args.files:
            path = measured.get(name.replace("\\", "/"))
            if path is None:
                print(f"{name}: not in the coverage data")
                continue
            spans = ranges(walk_only_lines(data, path))
            print(f"{name}: {sum(b - a + 1 for a, b in spans)} lines only the walks reach")
            for a, b in spans:
                print(f"  {a}" if a == b else f"  {a}-{b}")
        return 0

    rows = []
    for name, path in measured.items():
        walk = walk_only_lines(data, path)
        if walk:
            rows.append((len(walk), len(data.lines(path) or ()), name))
    rows.sort(reverse=True)
    print(f"{sum(r[0] for r in rows)} lines in {len(rows)} files are reached only by {', '.join(WALK_TESTS)}")
    for count, total, name in rows[: args.top]:
        print(f"{count:5d} of {total:5d}  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
