"""🛡 Names from files and playlists are shown as text (review #41): `<b>` is not
markup and `&` is not a keyboard mnemonic."""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_plainlbl_"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from gui.dialogs.duplicate_dialog import DuplicateResolveDialog
from gui.tournament_tiles import _SlotTile
from tests.qt_test_support import qapp, reap_widget


class TileTest(unittest.TestCase):

    def test_the_tile_labels_are_plain_text(self):
        qapp()
        meta = {"m3u": "x.m3u", "missing": 0, "style": "", "subtitle": "<b>s</b>",
                "name": "<i>n</i>", "rounds": "<u>r</u>", "tip": "t"}
        tile = _SlotTile("k", meta)
        self.addCleanup(reap_widget, tile)
        labels = tile.findChildren(QLabel)
        self.assertEqual(len(labels), 3)
        for lbl in labels:
            self.assertEqual(lbl.textFormat(), Qt.TextFormat.PlainText, lbl.text())


class DuplicateBoxTest(unittest.TestCase):

    def test_an_ampersand_in_a_file_name_is_not_a_mnemonic(self):
        qapp()
        host = mock.Mock()
        host._dup_badge = DuplicateResolveDialog._dup_badge
        box = DuplicateResolveDialog._within_box(host, {"file": "Tom & Jerry.m3u", "clusters": []})
        self.addCleanup(reap_widget, box)
        self.assertEqual(box.title(), "📁  Tom && Jerry.m3u")


if __name__ == "__main__":
    unittest.main()
