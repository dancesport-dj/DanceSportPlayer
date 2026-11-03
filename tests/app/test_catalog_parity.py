#!/usr/bin/env python3
"""No screen is left half English by accident (review #87).

Run:  py -m unittest tests.app.test_catalog_parity -v

A key the German catalog has and another catalog lacks falls back to English.
That is right for a word that reads the same in that language (Heat, Model,
Manual) and for keyboard shortcuts, and wrong for a sentence somebody forgot.
So every such gap has to be named here: a new German entry without its Spanish,
Dutch and Russian one fails until it is translated or listed on purpose.
"""

import importlib
import re
import unittest

from planner.i18n.lang_de import CATALOG as GERMAN

# Key names and separators only: Ctrl + Shift + PgUp, F12 / Ctrl + Alt + S ...
SHORTCUT = re.compile(r"^(?:Ctrl|Shift|Alt|Del|Enter|Home|PgUp|PgDown|F\d+|[A-Z0-9]|[←→↑↓…/+ ])+$")

SAME_IN_LANGUAGE = {
    "es": frozenset({
        "▼  Slow Waltz", "📖  Manual", "⚙ General", "✋  Manual", "  (%s pads)", "Final ",
        "Semifinal ", "instrumental", "timbre top %d %%", "groove top %d %%",
        "MERT top %d %%", "Manual", "Control",
    }),
    "nl": frozenset({
        "Label", "Model:", "Context:", "Volume", "Console", "Accent", "Focus:", "Planning",
        "Heat %d", "▼  PRELIMINARY ROUND  (2 heats)", "▼  Slow Waltz", "Project", "Model",
        "— Latin —", "📝  Planning", "🗜  Compact", "Later", "Heat", "  (%s pads)", "Amber",
        "Frame:", "🧠  MERT (deep embedding)", "label", "genre", "album", "groove top %d %%",
        "MERT top %d %%", "AI: %s", "Variant:", "Log", "🎛  Controller", "Presets ▾", "Inbox",
        "🤖 AI",
    }),
    "ru": frozenset({"▼  Slow Waltz"}),
}


class CatalogParityTest(unittest.TestCase):

    def test_every_gap_against_german_is_on_purpose(self):
        for code, allowed in SAME_IN_LANGUAGE.items():
            catalog = importlib.import_module(f"planner.i18n.lang_{code}").CATALOG
            with self.subTest(lang=code):
                gaps = [k for k in GERMAN
                        if k not in catalog and k not in allowed and not SHORTCUT.match(k)]
                self.assertEqual(gaps, [], f"lang_{code} lacks {len(gaps)} keys that German has")

    def test_the_allowed_list_has_no_stale_entry(self):
        for code, allowed in SAME_IN_LANGUAGE.items():
            catalog = importlib.import_module(f"planner.i18n.lang_{code}").CATALOG
            with self.subTest(lang=code):
                stale = sorted(k for k in allowed if k in catalog or k not in GERMAN)
                self.assertEqual(stale, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
