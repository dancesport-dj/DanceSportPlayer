"""The player card offers "Next dance" while the pause runs.

Run:  py -m unittest tests.player.widgets.test_card_next_dance -v

Marcel asked for a button in the pause that goes on to the next dance. ⏭
already did that, but nothing said so; the button shows beside ⏱➕ only
while the pause runs, and asks for the same thing ⏭ does.
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_next_dance_"))

from tests.qt_test_support import qapp, reap_widget


class NextDanceButtonTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = qapp()

    def card(self):
        from PySide6.QtMultimedia import QMediaPlayer

        from player.widgets.player import BigPlayerWidget
        card = BigPlayerWidget(QMediaPlayer())
        self.addCleanup(reap_widget, card)
        card.show()
        card.set_now("002 LW When winter comes T28")
        self.app.processEvents()
        return card

    def test_it_shows_only_while_the_pause_runs(self):
        card = self.card()
        self.assertFalse(card._skip_pause_btn.isVisible())
        card.set_pause_active(True)
        self.app.processEvents()
        self.assertTrue(card._skip_pause_btn.isVisible())
        self.assertTrue(card._extend_btn.isVisible())
        card.set_pause_active(False)
        self.app.processEvents()
        self.assertFalse(card._skip_pause_btn.isVisible())

    def test_a_click_asks_for_the_next_title_like_skip(self):
        card = self.card()
        card.set_pause_active(True)
        asked = []
        card.nextRequested.connect(lambda: asked.append(True))
        card._skip_pause_btn.click()
        self.assertEqual(asked, [True])


if __name__ == "__main__":
    unittest.main()
