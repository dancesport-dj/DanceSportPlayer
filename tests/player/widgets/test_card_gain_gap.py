"""The player card's subtitle and its dB value sit close.

Run:  py -m unittest tests.player.widgets.test_card_gain_gap -v

Marcel: "in the player allow a smaller gap between bpm value and db amount,
often it is only a little bit to small in screen size to fit". Between the
subtitle (… · 🥁 117 bpm) and the 🔊 −0.2 dB stood the row's spacing twice,
round the empty pause countdown, and once more between 🔊 and the value —
18 px the bpm could have used before it has to walk.
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_gain_gap_"))

from tests.qt_test_support import qapp, reap_widget


class GainGapTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = qapp()

    def card(self):
        from PySide6.QtMultimedia import QMediaPlayer
        from player.widgets.player import BigPlayerWidget
        card = BigPlayerWidget(QMediaPlayer())
        self.addCleanup(reap_widget, card)
        card.show()
        card.resize(400, card.sizeHint().height())
        card.set_now("002 LW When winter comes T28")
        card.set_gain(0.977)              # −0.2 dB
        self.app.processEvents()
        return card

    def test_the_db_value_sits_close_to_the_subtitle(self):
        card = self.card()
        sub, icon, lbl = card._sub, card._gain_icon, card._gain_lbl
        # Marcel then: "make spacing to 5px".
        self.assertEqual(icon.geometry().left() - sub.geometry().right() - 1, 5)
        self.assertEqual(lbl.geometry().left() - icon.geometry().right() - 1, 5)

    def test_the_pause_countdown_still_gets_its_place(self):
        card = self.card()
        self.assertFalse(card._countdown_lbl.isVisible())
        card.set_pause_active(True)
        card.set_countdown("⏸ 12 s")
        self.app.processEvents()
        self.assertTrue(card._countdown_lbl.isVisible())
        self.assertGreater(card._countdown_lbl.geometry().left(),
                           card._sub.geometry().right())
        card.set_pause_active(False)
        self.app.processEvents()
        self.assertFalse(card._countdown_lbl.isVisible())


if __name__ == "__main__":
    unittest.main()
