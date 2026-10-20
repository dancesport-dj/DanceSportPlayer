#!/usr/bin/env python3
"""Every literal `i18n.t(...)` key has a German entry in the catalog.

Run:  py -m unittest tests.app.test_i18n_catalog_keys -v

`t` falls back to the English key when the catalog has no entry, so a missing
key shows up only as an English word in the German UI. This walks the source
for `t("...")` calls with a literal first argument and asks the catalog for
each one; keys built at runtime (f-strings, variables) are out of its reach.

A key that reads the same in German gets no entry: test_i18n refuses an entry
that translates to itself. Such keys are named in SAME_IN_GERMAN instead, so
leaving one out is a decision, not an oversight.
"""

import ast
import unittest
from pathlib import Path

from planner.i18n.lang_de import CATALOG

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ("gui", "player", "planner", "shared")

SAME_IN_GERMAN = frozenset({
    "🎚️ librosa: %s",
    "🎼 Chroma: %s",
    "🧠 MERT: %s",
    " (%s)",
    "Album",
    "Custom:",
    "Frame",
    "Looks (*.json)",
    "Slot %d",
    "Tags",
    "Version",
})


def _source_files():
    for folder in SOURCES:
        yield from sorted((ROOT / folder).rglob("*.py"))
    yield ROOT / "dancesport_gui.py"


def _literal_keys(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and getattr(node.func, "attr", None) == "t"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)):
            yield node.lineno, node.args[0].value


class CatalogKeysTest(unittest.TestCase):

    def test_the_walk_finds_keys(self):
        keys = [k for f in _source_files() for _, k in _literal_keys(f)]
        self.assertGreater(len(keys), 500)

    def test_every_literal_key_has_a_german_entry(self):
        missing = [f"{f.relative_to(ROOT)}:{line}  {key!r}"
                   for f in _source_files()
                   for line, key in _literal_keys(f)
                   if key not in CATALOG and key not in SAME_IN_GERMAN]
        self.assertEqual(missing, [], "keys missing from planner/i18n/lang_de.py:\n"
                         + "\n".join(missing))


if __name__ == "__main__":
    unittest.main(verbosity=2)
