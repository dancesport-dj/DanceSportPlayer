#!/usr/bin/env python3
"""Every source file compiles without a SyntaxWarning.

Run:  py -m unittest tests.app.test_source_warnings -v

An invalid escape such as "\\/" or "\\S" in a plain string is a SyntaxWarning
on Python 3.14 and an error under `-W error`; the string means one thing
today and fails to compile tomorrow. config.folders_below meant both
separators and wrote "\\/".
"""

import unittest
import warnings
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCE_DIRS = ("planner", "gui", "player", "shared", "speech", "tools", "tests")


def sourceFiles() -> list[Path]:
    files = sorted(REPO.glob("*.py"))
    for name in SOURCE_DIRS:
        files += sorted((REPO / name).rglob("*.py"))
    return files


class SourceWarningsTest(unittest.TestCase):

    def test_no_file_compiles_with_a_syntax_warning(self):
        offenders = []
        for path in sourceFiles():
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                compile(path.read_bytes(), str(path), "exec")
            offenders += [f"{path.relative_to(REPO)}:{w.lineno} {w.message}"
                          for w in caught if issubclass(w.category, SyntaxWarning)]
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
