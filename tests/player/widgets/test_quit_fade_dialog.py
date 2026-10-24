"""🔉 While ✕ fades the music out, a small window says the app is closing.

Run:  py -m unittest tests.player.widgets.test_quit_fade_dialog -v

Marcel: "when shutdown fading activated show a splash dialog wich states the
shutdown ongoing", "so the user not think that it stucks". The bar fills
up with the fade, and the window does not block the desk: a second ✕ on
it still quits at once.
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_quit_fade_dlg_"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QWidget

from tests.qt_test_support import qapp, reap_widget


class QuitFadeDialogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = qapp()

    def setUp(self):
        from player.widgets.quit_fade import QuitFadeDialog
        self.win = QWidget()
        self.addCleanup(reap_widget, self.win)
        self.dlg = QuitFadeDialog(self.win, 3000)

    def test_it_says_the_app_is_closing(self):
        text = " ".join(lbl.text() for lbl in self.dlg.findChildren(QLabel))
        self.assertIn("closes", text)
        self.assertTrue(self.dlg.isVisible())

    def test_the_bar_fills_up_with_the_fade(self):
        # Marcel: "fill the bar progress the other way around"
        bar = self.dlg.findChild(QProgressBar)
        self.assertEqual(bar.maximum(), 3000)
        self.assertEqual(bar.value(), 0)
        self.dlg.tick(1000)
        self.assertEqual(bar.value(), 1000)
        self.dlg.tick(5000)
        self.assertEqual(bar.value(), 3000)

    def test_it_does_not_block_the_desk(self):
        self.assertEqual(self.dlg.windowModality(), Qt.WindowModality.NonModal)

    def test_it_goes_with_the_window(self):
        self.assertIs(self.dlg.parent(), self.win)


if __name__ == "__main__":
    unittest.main()
