"""📨 The guest QR code on the presenter screen: in the corner while guests can
ask, scannable, and clear of everything the hall reads.
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_presqr_"))

from PySide6.QtCore import QPoint

from tests.qt_test_support import qapp, reap_widget

_STATE = ("Langsamer Walzer", "Fascination", ("01:12", "− 01:48", False, 0.4),
          [("Tango", "Jealousy"), ("Rumba", "Besame Mucho"), ("Jive", "Hound Dog")],
          ("Cha Cha Cha", "Sway"))
_LINK = "https://moon-river-tango-waltz.trycloudflare.com/#e=ABC234"


def _modules():
    from player.dialogs.remote_dialog import qr_pixmap
    pix = qr_pixmap(_LINK, 1)
    if pix is None:
        raise unittest.SkipTest("segno is not installed")
    return pix


class GuestQrTest(unittest.TestCase):
    def _presenter(self, w=1280, h=720):
        from player.presenter.presenter import PresenterWindow
        qapp()
        win = PresenterWindow(lambda: _STATE)
        self.addCleanup(reap_widget, win)
        win.resize(w, h)
        win.show()
        win._refresh()
        return win

    def _rect(self, win, widget):
        """`widget`'s rectangle in the window's coordinates."""
        top_left = widget.mapTo(win, QPoint(0, 0))
        return top_left.x(), top_left.y(), widget.width(), widget.height()

    def test_no_code_until_one_is_handed_over(self):
        win = self._presenter()
        self.assertFalse(win.qr_card.isVisible())

    def test_the_code_stands_in_the_corner_clear_of_the_queue_and_the_foot(self):
        for size in ((1280, 720), (1920, 1080), (1024, 768)):
            win = self._presenter(*size)
            win.set_guest_qr(_modules())
            self.assertTrue(win.qr_card.isVisible(), size)
            x, y, w, h = self._rect(win, win.qr_card)
            col_x, _cy, col_w, _ch = self._rect(win, win.next_box)
            self.assertGreaterEqual(x, col_x + col_w, f"over the queue at {size}")
            self.assertLessEqual(x + w, win.width(), size)
            self.assertLessEqual(y + h, self._rect(win, win.close_btn)[1],
                                 f"over the foot row at {size}")
            self.assertGreater(win.qr_lbl.pixmap().width(), 100, size)

    def test_every_module_is_a_whole_number_of_pixels(self):
        """A code scaled by a fraction blurs at its module edges, and a scanner
        across a hall is the reader with the least to spare."""
        win = self._presenter(1920, 1080)
        modules = _modules()
        win.set_guest_qr(modules)
        self.assertEqual(win.qr_lbl.pixmap().width() % modules.width(), 0)

    def test_it_follows_a_resize(self):
        win = self._presenter(1280, 720)
        win.set_guest_qr(_modules())
        small = win.qr_lbl.pixmap().width()
        win.resize(1920, 1080)
        qapp().processEvents()
        self.assertGreater(win.qr_lbl.pixmap().width(), small)
        x, y, w, h = self._rect(win, win.qr_card)
        self.assertLessEqual(x + w, 1920)
        self.assertLessEqual(y + h, self._rect(win, win.close_btn)[1])

    def test_none_takes_it_away_again(self):
        win = self._presenter()
        win.set_guest_qr(_modules())
        win.set_guest_qr(None)
        self.assertFalse(win.qr_card.isVisible())

    def test_the_caption_speaks_the_halls_language(self):
        from unittest import mock

        from planner import terms
        with mock.patch.object(terms, "hall_language", lambda: "de"):
            win = self._presenter()
        self.assertEqual(win.qr_caption.text(), "Musikwunsch? Hier scannen")


if __name__ == "__main__":
    unittest.main()
