#!/usr/bin/env python3
"""❔ F1 — the cheat sheet, in the language the rest of the app is in.

Run:  py -m unittest tests.gui.test_shortcuts_i18n -v

The window title and the Close button came along on their own — both go
through patched Qt calls. The table between them did not: forty rows of
`("Space", "Play / stop the selected song")` are glued into HTML and handed
to `QTextBrowser.setHtml`, which is not a patched method and could not be
one — by then the strings are inside markup.

So every row has to ask for its own translation, and every row needs a
catalog entry. The left half is the key on a German keyboard (Strg, Entf,
Umschalt, Leertaste) — the wording the OS itself uses; the right half is the
sentence. A handful of left halves are the same in both languages (F1, the
arrow keys on their own) and are left alone on purpose: the catalog forbids
an entry that translates to itself.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_keys_i18n_"))

from gui.shortcuts import shortcut_rows, shortcut_sheet_html  # noqa: E402
from planner import i18n  # noqa: E402

# Left halves that read the same on a German keyboard as on an English one.
_SAME_IN_BOTH = {"F1", "Esc", "🎛  Cartwall"}


class ShortcutRowsI18nTest(unittest.TestCase):

    def tearDown(self):
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    @staticmethod
    def rows():
        return shortcut_rows()

    def test_the_sheet_is_still_the_whole_sheet(self):
        """Keyboard, mouse and cartwall, headings included."""
        rows = self.rows()
        self.assertGreater(len(rows), 30)
        self.assertEqual(sum(1 for _l, r in rows if not r), 3,
                         "a section heading was lost or gained")

    def test_the_sheet_is_built_from_the_translated_rows(self):
        i18n.set_active("de")
        html = shortcut_sheet_html()
        self.assertIn(i18n.t("Play / stop the selected song"), html)
        self.assertNotIn("Play / stop the selected song", html)
        self.assertEqual(html.count("colspan=2"), 3, "one heading per section")

    def test_every_description_is_translated(self):
        i18n.set_active("de")
        for left, right in self.rows():
            if not right:
                continue
            self.assertNotEqual(i18n.t(right), right,
                                f"{left!r}: the description stayed English")

    def test_every_key_name_is_translated(self):
        i18n.set_active("de")
        for left, _right in self.rows():
            if left in _SAME_IN_BOTH:
                continue
            self.assertNotEqual(i18n.t(left), left,
                                f"{left!r} stayed English")

    def test_the_modifiers_are_the_ones_windows_uses(self):
        i18n.set_active("de")
        german = {i18n.t(left) for left, _r in self.rows()}
        joined = " ".join(german)
        self.assertIn("Leertaste", german)
        self.assertIn("Strg", joined)
        self.assertIn("Entf", joined)
        self.assertIn("Umschalt", joined)
        self.assertNotIn("Ctrl", joined)
        self.assertNotIn("Del", joined)

    def test_the_key_column_is_no_wider_than_it_is_in_english(self):
        """The left cells are `white-space:nowrap` in a 620 px dialog, so a
        German key name longer than the longest English one squeezes the
        description column and the whole sheet scrolls sideways. A literal
        translation did exactly that — "▶ / Doppelklick auf eine 📚
        Bibliothekszeile" for "▶ / double-click a 📚 library row" — which is
        why a few of them are shortened rather than translated word for word.
        """
        from PySide6.QtGui import QFontMetrics
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])
        fm = QFontMetrics(app.font())

        def widest(language):
            i18n.set_active(language)
            return max((fm.horizontalAdvance(i18n.t(left)), i18n.t(left))
                       for left, _r in self.rows())

        budget, _english = widest("en")
        width, german = widest("de")
        self.assertLessEqual(width, budget,
                             f"{german!r} is wider than any English key name")

    def test_english_is_untouched(self):
        i18n.set_active("en")
        for left, right in self.rows():
            self.assertEqual(i18n.t(left), left)
            if right:
                self.assertEqual(i18n.t(right), right)


if __name__ == "__main__":
    unittest.main(verbosity=2)
