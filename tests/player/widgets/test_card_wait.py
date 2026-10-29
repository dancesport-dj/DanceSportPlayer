"""🐂 The Paso Doble's Start-after wait stands where the title's stats stand.

Run:  py -m unittest tests.player.widgets.test_card_wait -v

Marcel: "the paso doble countdown cant be seen because the text is too long,
it must be more like the auto advance shown coundown, replacing the stats of
the title till it is start playing". So during the wait the subtitle row
says what is coming, the seconds count in the pause's gold, and the stats
(dance · takt · bpm) come back when the music starts.
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_card_wait_"))

from tests.qt_test_support import qapp, reap_widget

STATS = "PD  ·  T60  ·  🥁 120 bpm"


class CardWaitTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = qapp()

    def setUp(self):
        from PySide6.QtMultimedia import QMediaPlayer

        from player.widgets.player import BigPlayerWidget
        self.card = BigPlayerWidget(QMediaPlayer())
        self.addCleanup(reap_widget, self.card)
        self.card.show()
        self.card.set_now("15 Espana Cani", STATS)
        self.app.processEvents()

    def test_the_wait_takes_the_place_of_the_stats(self):
        self.card.set_wait("Paso Doble in", "5 s")
        self.assertEqual(self.card._full_sub, "Paso Doble in")
        self.assertEqual(self.card._countdown_lbl.text(), "5 s")
        self.assertFalse(self.card._countdown_lbl.isHidden())

    def test_the_seconds_run_down_in_place(self):
        self.card.set_wait("Paso Doble in", "5 s")
        self.card.set_wait("Paso Doble in", "4 s")
        self.assertEqual(self.card._countdown_lbl.text(), "4 s")
        self.card.set_wait("", "")
        self.assertEqual(self.card._full_sub, STATS)

    def test_the_stats_come_back_when_the_music_starts(self):
        self.card.set_wait("Paso Doble in", "5 s")
        self.card.set_wait("", "")
        self.assertEqual(self.card._full_sub, STATS)
        self.assertTrue(self.card._countdown_lbl.isHidden())

    def test_another_title_is_not_given_the_old_stats(self):
        self.card.set_wait("Paso Doble in", "5 s")
        self.card.set_now("16 Next title", "SA  ·  T50")
        self.card.set_wait("", "")
        self.assertEqual(self.card._full_sub, "SA  ·  T50")

    def test_no_wait_leaves_the_stats_alone(self):
        self.card.set_wait("", "")
        self.assertEqual(self.card._full_sub, STATS)

    def test_the_seconds_follow_the_words_without_a_gap(self):
        # Marcel: "the PD in is now with a gap".
        self.card.resize(900, self.card.height())
        self.card.set_wait("🐂  PD T60 in", "5 s")
        self.app.processEvents()
        sub, cd = self.card._sub, self.card._countdown_lbl
        words_end = sub.x() + sub.fontMetrics().horizontalAdvance(sub.text())
        self.assertLess(cd.x() - words_end, 20)

    def test_the_seconds_read_in_the_words_font(self):
        # Marcel: "not complety align with pd t60 in text". The seconds kept
        # the pause countdown's 13 px Consolas beside the 11 px words.
        self.card.resize(900, self.card.height())
        self.card.set_wait("🐂  PD T60 in", "5 s")
        self.app.processEvents()
        sub, cd = self.card._sub, self.card._countdown_lbl
        self.assertEqual(cd.font().pixelSize(), sub.font().pixelSize())
        self.assertEqual(cd.font().family(), sub.font().family())

        def baseline(lbl):
            fm = lbl.fontMetrics()
            return lbl.y() + (lbl.height() - fm.height()) / 2 + fm.ascent()
        self.assertLessEqual(abs(baseline(cd) - baseline(sub)), 1)

    def test_the_pause_countdown_keeps_its_own_font(self):
        size = self.card._countdown_lbl.font().pixelSize()
        self.card.set_wait("🐂  PD T60 in", "5 s")
        self.card.set_wait("", "")
        self.card.set_countdown("⏸ 9 s")
        self.assertEqual(self.card._countdown_lbl.font().pixelSize(), size)

    def test_the_stats_get_the_row_back_after_the_wait(self):
        self.card.resize(900, self.card.height())
        width = self.card._sub.width()
        self.card.set_wait("🐂  PD T60 in", "5 s")
        self.app.processEvents()
        self.card.set_wait("", "")
        self.app.processEvents()
        self.assertEqual(self.card._sub.width(), width)

    def test_the_played_takt_is_the_pitched_one(self):
        self.card.set_takt(59)
        self.card._tempo.setValue(17)          # +1.7 %
        self.assertEqual(self.card.played_takt(), "T60")
        self.card.set_takt(None)
        self.assertEqual(self.card.played_takt(), "")


if __name__ == "__main__":
    unittest.main()
