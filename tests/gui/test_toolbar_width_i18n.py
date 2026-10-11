#!/usr/bin/env python3
"""The toolbar over the playlists must not get wider just because it is translated.

Run:  py -m unittest tests.gui.test_toolbar_width_i18n -v

The row is responsive already: `resizeEvent` measures the natural width of
every visible button and drops to one of two compaction stages when the window
is narrower than that — first the view buttons collapse to their leading emoji,
then all of them do. Nothing there is broken.

What broke is the input to it. German captions are simply longer words —
"💾  Alles speichern" for "💾  Save all", "🧭  Pfade reparieren" for
"🧭  Fix paths" — and 250 px spread across eighteen buttons is enough to push
a row that fitted on a wide screen past the threshold. The user then sees the
whole toolbar as bare squares in German and as full labels in English, on the
same monitor, which reads as the translation having broken the layout.

So the budget is the assertion: whatever German the catalog carries, the row
it builds may not be wider than the English one it replaces. That keeps the
compaction stages landing on the same screens in both languages, and it fails
the next over-long translation instead of letting it quietly eat the labels.

Spanish, Dutch and Russian follow the same rule since their captions were cut
the German way ("Save all" → "Save", "Save state" → "State"). They get a
TOLERANCE on top: the offscreen platform these tests run on is only a proxy
for the real font (it ranks German narrower than English, where real Windows
metrics put it ~4 % wider), and a few percent there is tens of pixels, not the
250 px that turned a whole row into squares. Real Windows widths after the
cut: en 1440, de 1501, es 1511, nl 1528, ru 1610 px.

Measured off the real window: `_toolbar_btns` is the production list, so a
button added later is covered without touching this file.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_toolbar_i18n_"))

from PySide6.QtWidgets import QApplication

from gui import dialogs
from planner import i18n
from gui.main_persist import layout_settings

# How much wider than the English row a translated one may measure offscreen.
TOLERANCE = 0.02
from tests.qt_test_support import (
    reap_widget, stub_window_startup)


class ToolbarWidthI18nTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        layout_settings().clear()
        dialogs.AUTOSAVE.remove()

    def tearDown(self):
        i18n._restore_text_hook()
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def widths(self, language):
        """The natural width of every visible toolbar button, by caption.

        The hook has to be in place before the window is built — a button
        already wearing its English text is never revisited."""
        i18n.set_active(language)
        i18n.install_text_hook()
        win = self.gui.MainWindow()
        win._loading_dlg.accept()          # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, win)
        out = {b.property("fullText"): b.sizeHint().width()
               for b in win._toolbar_btns if not b.isHidden()}
        i18n._restore_text_hook()
        return out

    def translations(self):
        return [code for code, _caption, _blurb in i18n.LANGUAGES
                if code != i18n.DEFAULT_LANGUAGE]

    def test_no_translated_row_is_wider_than_the_english_one(self):
        english = self.widths("en")
        budget = sum(english.values()) * (1 + TOLERANCE)
        for language in self.translations():
            with self.subTest(language=language):
                row = self.widths(language)
                self.assertEqual(len(english), len(row),
                                 "the two rows hold a different number of buttons")
                self.assertLessEqual(
                    sum(row.values()), budget,
                    "the %s toolbar is %d px wider than the English one, so it "
                    "compacts to icons on screens where English still shows "
                    "labels.\nEnglish: %s\n%s: %s"
                    % (language, sum(row.values()) - sum(english.values()),
                       sorted(english.items()), language, sorted(row.items())))

    def test_every_caption_keeps_its_emoji_separator(self):
        """`_toolbar_icon_text` splits the leading emoji off on a DOUBLE space.
        A translation that comes back with one would make the compact form the
        whole label — the row would then 'compact' to exactly its full width
        and the buttons would be squeezed instead."""
        for language in self.translations():
            for caption in self.widths(language):
                if caption[0].isalnum():
                    continue           # the cycle buttons carry no emoji
                with self.subTest(language=language, caption=caption):
                    self.assertIn("  ", caption)


if __name__ == "__main__":
    unittest.main()
