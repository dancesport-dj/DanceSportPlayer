#!/usr/bin/env python3
"""The preview overlay has to stay put while the list under it scrolls.

Run:  py -m unittest tests.player.test_preview_anchor -v

A scroll area scrolls by MOVING its viewport's children, and the overlay is one
of them — so a single turn of the wheel over a long library list carried the
mini player off the top edge and it looked like playback had lost its window.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_anchor_"))

from PySide6.QtCore import QPoint  # noqa: E402
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer  # noqa: E402
from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from player.player import PreviewOverlay  # noqa: E402

_app = QApplication.instance() or QApplication([])


class PreviewAnchorTest(unittest.TestCase):

    def setUp(self):
        self.table = QTableWidget(200, 1)
        for r in range(200):
            self.table.setItem(r, 0, QTableWidgetItem(f"row {r}"))
        self.table.resize(400, 200)
        self.table.show()
        self.addCleanup(reap_widget, self.table)
        self.ov = PreviewOverlay(QMediaPlayer(), QAudioOutput())
        self.addCleanup(reap_widget, self.ov)

    def _scroll(self, value: int):
        self.table.verticalScrollBar().setValue(value)
        _app.processEvents()

    def test_it_survives_a_scroll(self):
        self.ov.show_for(self.table, 2, "some song")
        was = self.ov.pos()
        self._scroll(40)
        self.assertEqual(self.ov.pos(), was)

    def test_a_dragged_overlay_keeps_its_new_spot(self):
        """The user's own placement is the one position that outranks the anchor."""
        self.ov.show_for(self.table, 2, "some song")
        self.ov._drag_off = QPoint(10, 5)      # as if the title bar were held
        self.ov.move(20, 60)
        self.ov._drag_off = None
        self.ov._user_pos = self.ov._anchor = self.ov.pos()
        self._scroll(40)
        self.assertEqual(self.ov.pos(), QPoint(20, 60))

    def test_the_next_song_may_place_it_again(self):
        """Anchoring must not freeze the overlay for the rest of the evening —
        the next ▶ places it anew, and THAT spot is the one held from then on."""
        self.ov.show_for(self.table, 8, "some song")
        self._scroll(40)
        self.ov.show_for(self.table, 0, "the next one")
        top = self.ov.pos()
        self.assertEqual(self.ov._anchor, top)
        self._scroll(80)
        self.assertEqual(self.ov.pos(), top)


if __name__ == "__main__":
    unittest.main()
