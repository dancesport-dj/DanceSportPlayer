#!/usr/bin/env python3
"""✏️ The empty mark row names the 🎯 button with the button's own icon.

Run:  py -m unittest tests.player.widgets.test_pd_marks_hint -v

Under a 🎨 look the "🎯  Mark highlight now" button wears the painted target
icon, but the hint "…scrub to a crash and hit 🎯" carried the glyph at its end,
where nothing dresses it — so it pointed at a colour emoji the button does not
show. With the glyph leading, the label gets the same painted icon.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pd_hint_"))

from PySide6.QtWidgets import QLabel

from player.widgets.play_mode_panel import PlayModePanel
from tests.shared.appearance.test_look_icons import LOOK, _Base


class EmptyMarkRowHint(_Base):

    def _hint(self, language: str) -> str:
        self.use(LOOK, language)
        panel = self.keep(PlayModePanel({"pd_highlight_stop": True}))
        panel.set_pd_marks([])
        labels = [w for w in panel.pd_marks_box.findChildren(QLabel)]
        self.assertEqual(len(labels), 1)
        return labels[0].text()

    def test_the_hint_wears_the_buttons_icon(self):
        for language in ("en", "de"):
            with self.subTest(language=language):
                text = self._hint(language)
                self.assertIn("<img", text)
                self.assertNotIn("🎯", text)


if __name__ == "__main__":
    unittest.main()
