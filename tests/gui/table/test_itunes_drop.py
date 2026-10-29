#!/usr/bin/env python3
"""A drag out of iTunes for Windows, as it really arrives.

Run:  py -m unittest tests.gui.table.test_itunes_drop -v

Recorded 2026-10-25 with a drop probe (iTunes for Windows, Windows 11): iTunes
hands over no Explorer file list (CF_HDROP) and no text of its own — only a
`text/uri-list` of percent-encoded file:/// URLs, CRLF after each, beside its
own binary formats (iTunesObjectList, iTunesSourceViewTrackField, the drag
image). The names keep what the library has in them: blanks, a double blank,
brackets. Every drop target of the app must read the files out of exactly that.
"""

import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_itunes_"))

from PySide6.QtCore import QByteArray, QMimeData
from PySide6.QtWidgets import QApplication

from gui.table.playlist_table import PlaylistTable
from player.widgets.cartwall import CartPadButton
from player.widgets.player import BigPlayerWidget
from tests.qt_test_support import reap_widget

# The two iTunes formats beside the URLs, byte for byte from the probe.
_OBJECT_LIST = bytes.fromhex(
    "0100000000000000080000000000000001000000"
    "2b010000e619840000000000" "20a44cfe2b010000")
_TRACK_FIELD = bytes.fromhex(
    "0100000000000000040000000000000001000000"
    "2b010000e619840000000000" "03000000")


def _itunes_mime(*paths: Path) -> QMimeData:
    """What iTunes puts on the drag for these files."""
    md = QMimeData()
    uris = "".join("file:///" + quote(p.as_posix(), safe="/:()") + "\r\n"
                   for p in paths)
    md.setData("text/uri-list", QByteArray(uris.encode("ascii")))
    md.setData('application/x-qt-windows-mime;value="iTunesObjectList"',
               QByteArray(_OBJECT_LIST))
    md.setData('application/x-qt-windows-mime;value="iTunesSourceViewTrackField"',
               QByteArray(_TRACK_FIELD))
    return md


class _Drop:
    """The bit of a drag event the deck's checks read; the source is not one
    of our own tables."""

    def __init__(self, md):
        self._md = md

    def mimeData(self):
        return self._md

    def source(self):
        return None


class ITunesDropTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        root = Path(tempfile.mkdtemp(prefix="dp_itunes_f_")) / "my music" / "vlt"
        root.mkdir(parents=True)
        cls.samba = root / "02 Ah Ta  (Samba 50).mp3"
        cls.chacha = root / "15 La Sitiera (Cha Cha 31).mp3"
        for p in (cls.samba, cls.chacha):
            p.write_bytes(b"x")

    def test_the_payload_reads_as_local_files(self):
        md = _itunes_mime(self.samba)
        self.assertEqual([Path(u.toLocalFile()) for u in md.urls()],
                         [self.samba])

    def test_a_deck_takes_one_track(self):
        t = PlaylistTable()
        self.addCleanup(reap_widget, t)
        drop = _Drop(_itunes_mime(self.samba))
        self.assertTrue(t._has_droppable(drop))
        self.assertEqual(t._droppable_path(drop), self.samba)

    def test_a_deck_or_wishlist_takes_every_track_in_order(self):
        t = PlaylistTable()
        self.addCleanup(reap_widget, t)
        drop = _Drop(_itunes_mime(self.chacha, self.samba))
        self.assertEqual(t._wishlist_droppables(drop), [self.chacha, self.samba])
        self.assertEqual(t._dropped_m3us(drop), [])

    def test_a_cartwall_pad_takes_them(self):
        got = CartPadButton._audio_urls(_itunes_mime(self.samba, self.chacha))
        self.assertEqual(got, [os.path.normpath(self.samba),
                               os.path.normpath(self.chacha)])

    def test_the_player_card_takes_the_first(self):
        got = BigPlayerWidget._dropped_path(_itunes_mime(self.samba, self.chacha))
        self.assertEqual(Path(got), self.samba)


if __name__ == "__main__":
    unittest.main()
