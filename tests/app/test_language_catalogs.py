#!/usr/bin/env python3
"""Every offered language's catalog, held to the same shape as the German one.

Run:  py -m unittest tests.app.test_language_catalogs -v

The German catalog is the complete one — test_i18n_catalog_keys checks every
literal key against it — so the others are measured against it: a key it does
not have is stale, and a catalog that covers too little of it would leave a
screen half English. The shape checks are the ones test_i18n makes for German:
`&&`, `%s`, `%d` and `{}` survive, nothing is blank, nothing translates to
itself (a key that reads the same is left out and falls back on its own).
"""

import importlib
import unittest

from planner import i18n
from planner.lang_de import CATALOG as GERMAN

# How much of the German catalog another language must cover. Short of 1.0
# because a word that reads the same in that language is left out on purpose.
MIN_COVERAGE = 0.95


def _catalogs():
    for code, _caption, _blurb in i18n.LANGUAGES:
        if code != i18n.DEFAULT_LANGUAGE:
            yield code, importlib.import_module(f"planner.lang_{code}").CATALOG


class LanguageCatalogTest(unittest.TestCase):

    def test_no_catalog_carries_a_key_the_app_no_longer_has(self):
        for code, catalog in _catalogs():
            with self.subTest(lang=code):
                stale = [k for k in catalog if k not in GERMAN]
                self.assertEqual(stale, [], f"{len(stale)} stale keys in lang_{code}")

    def test_each_catalog_covers_the_app(self):
        for code, catalog in _catalogs():
            with self.subTest(lang=code):
                self.assertGreaterEqual(len(catalog) / len(GERMAN), MIN_COVERAGE)

    def test_nothing_is_blank_or_translates_to_itself(self):
        for code, catalog in _catalogs():
            with self.subTest(lang=code):
                bad = [k for k, v in catalog.items() if not str(v).strip() or k == v]
                self.assertEqual(bad, [])

    def test_the_accelerator_and_placeholder_shape_survives(self):
        for code, catalog in _catalogs():
            for key, value in catalog.items():
                for token in ("&&", "%s", "%d", "{}"):
                    self.assertEqual(
                        key.count(token), str(value).count(token),
                        f"lang_{code}: {key!r} -> {value!r} changed the count of {token!r}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
