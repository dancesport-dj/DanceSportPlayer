"""Golden files: a whole output compared with a checked-in copy of it.

The example tests check the lines they name ('# ══ Finale (1 Heat) ══' is in
the file); a golden file checks everything else too — the order of the lines,
the blank lines, the BOM, a marker nobody thought to assert. A change to the
output then shows up as a diff to review instead of passing unseen.

    UPDATE_GOLDEN=1 .venv\\Scripts\\python.exe -m pytest tests/planner/playlist/test_m3u_golden.py

rewrites the files from what the code writes now; review `git diff` and commit
them with the change that made them differ. A golden file that does not exist
yet is written and its test fails once, so that a new one is looked at.

Line ends are compared as LF: the exports write the platform's (CRLF on
Windows), and git may change them on checkout.
"""
import difflib
import os
from pathlib import Path

UPDATE_ENV = "UPDATE_GOLDEN"


def normalized(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def assert_golden(test, golden: Path, actual: bytes) -> None:
    actual = normalized(actual)
    if os.environ.get(UPDATE_ENV) == "1" or not golden.exists():
        existed = golden.exists()
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_bytes(actual)
        if not existed:
            test.fail(f"New golden file {golden}: review it, then commit it.")
        return
    expected = normalized(golden.read_bytes())
    if actual != expected:
        diff = difflib.unified_diff(expected.decode("utf-8", "replace").splitlines(),
                                    actual.decode("utf-8", "replace").splitlines(),
                                    f"{golden.name} (golden)", f"{golden.name} (now)", lineterm="")
        test.fail(f"{golden.name} differs from its golden file ({UPDATE_ENV}=1 accepts the new one):\n"
                  + "\n".join(diff))
