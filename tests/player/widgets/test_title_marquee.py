"""The player card's title walks when it does not fit the space the title
label actually has — beside the cover, in the wide strip, after a resize —
and stands still again once it fits."""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_marquee_"))

from tests.qt_test_support import qapp, reap_widget


class TitleMarqueeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = qapp()

    def _card(self, wide=False, width=900):
        from PySide6.QtMultimedia import QMediaPlayer

        from player.widgets.player import BigPlayerWidget
        card = BigPlayerWidget(QMediaPlayer())
        self.addCleanup(reap_widget, card)
        card.set_wide(wide)
        card.show()
        card.resize(width, card.sizeHint().height())
        self.app.processEvents()
        return card

    def _title_between(self, card):
        """A title wider than the title label, yet narrower than the whole
        card — the one the old card-width test let through uncut."""
        fm = card._title.fontMetrics()
        title = "002 LW"
        while fm.horizontalAdvance(title) <= card._title.width() + 10:
            title += " When winter comes"
        self.assertLess(fm.horizontalAdvance(title), card.width() - 28,
                        "test setup: the title must fit the card's width")
        return title

    def test_the_wide_strip_walks_a_title_its_column_cannot_hold(self):
        """🎵 Marcel: "the laufband text is not everytime working". Wide, the
        title has a column of the strip, not the strip's width."""
        card = self._card(wide=True, width=1400)
        card.set_now(self._title_between(card))
        self.app.processEvents()
        self.assertTrue(card._marquee.isActive())

    def test_a_narrower_card_starts_it_and_a_wider_one_stops_it(self):
        card = self._card(width=900)
        card.set_now("002 LW When winter comes T28")
        self.app.processEvents()
        self.assertFalse(card._marquee.isActive())
        card.resize(140, card.height())
        self.app.processEvents()
        self.assertTrue(card._marquee.isActive())
        card.resize(900, card.height())
        self.app.processEvents()
        self.assertFalse(card._marquee.isActive())
        self.assertEqual(card._title.text(), "002 LW When winter comes T28")

    def test_the_cover_coming_in_takes_width_from_the_title(self):
        """The cover shows without the card changing size — the title label
        still loses its width and has to walk."""
        card = self._card(width=420)
        card.set_artwork_enabled(False)
        self.app.processEvents()
        fm = card._title.fontMetrics()
        title = "002 LW"
        while fm.horizontalAdvance(title) <= card._title.width() - 30:
            title += " x"
        card.set_now(title)
        self.app.processEvents()
        self.assertFalse(card._marquee.isActive())
        card.set_artwork_enabled(True)
        self.app.processEvents()
        self.assertTrue(card._marquee.isActive())


class SubtitleMarqueeTest(unittest.TestCase):
    """🥁 The line under the title (dance · takt · bpm) was cut at its right
    end, so the bpm went first. Marcel picked "let it walk like the title"."""

    @classmethod
    def setUpClass(cls):
        cls.app = qapp()

    _card = TitleMarqueeTest._card

    def _too_wide_sub(self, card):
        fm = card._sub.fontMetrics()
        sub = "LW · T29"
        while fm.horizontalAdvance(sub + " · 🥁 87 bpm") <= card._sub.width() + 10:
            sub += " · Langsamer Walzer"
        return sub + " · 🥁 87 bpm"

    def test_a_subtitle_too_wide_walks_until_the_bpm_has_been_shown(self):
        card = self._card(width=420)
        card.set_now("002 LW When winter comes", self._too_wide_sub(card))
        self.app.processEvents()
        self.assertTrue(card._marquee.isActive())
        shown = set()
        for _ in range(len(card._full_sub) + 8):
            card._marquee_step()
            shown.add(card._sub.text())
        self.assertTrue(any("87 bpm" in s for s in shown),
                        "the bpm walks into view")

    def test_a_short_title_does_not_stop_a_long_subtitle(self):
        card = self._card(width=420)
        card.set_now("LW", self._too_wide_sub(card))
        self.app.processEvents()
        self.assertTrue(card._marquee.isActive())
        self.assertEqual(card._title.text(), "LW", "the title stands")

    def test_a_subtitle_that_fits_stands_still(self):
        card = self._card(width=900)
        card.set_now("LW", "LW · T29 · 🥁 87 bpm")
        self.app.processEvents()
        self.assertFalse(card._marquee.isActive())
        self.assertEqual(card._sub.text(), "LW · T29 · 🥁 87 bpm")

    _HEAD = "LW  ·  T29  ·  "
    _SUB = _HEAD + "🥁 87 bpm"

    def _bpm_squeezed(self, card):
        """The real subtitle in a label with room for the head and a few
        characters of the bpm."""
        card.set_now("LW", self._SUB)
        self.app.processEvents()
        fm = card._sub.fontMetrics()
        card._sub.resize(fm.horizontalAdvance(self._HEAD + "🥁 ") + 40, card._sub.height())
        return card

    def test_only_the_bpm_walks_and_the_head_stands(self):
        """🥁 Marcel: "dont let whole subtilte walk only bmp value if
        necessary"."""
        card = self._bpm_squeezed(self._card(width=900))
        self.assertTrue(card._marquee.isActive())
        shown = []
        for _ in range(len(self._SUB) + 8):
            card._marquee_step()
            shown.append(card._sub.text())
        for s in shown:
            self.assertTrue(s.startswith(self._HEAD), s)
        self.assertGreater(len(set(shown)), 1, "the bpm part walks")
        self.assertTrue(any("87" in s for s in shown), "the bpm walks into view")
        fm = card._sub.fontMetrics()
        for s in shown:
            self.assertLessEqual(fm.horizontalAdvance(s), card._sub.width(), s)

    def test_the_drum_and_the_loop_dot_do_not_walk(self):
        """🥁 Marcel: "you should not walk the dot icon with it" — only the
        value walks: the 🥁 stands with the head, and the loop has no •."""
        card = self._bpm_squeezed(self._card(width=900))
        shown = []
        for _ in range(len(self._SUB) + 8):
            card._marquee_step()
            shown.append(card._sub.text())
        for s in shown:
            self.assertTrue(s.startswith(self._HEAD + "🥁 "), s)
            self.assertNotIn("•", s)
            self.assertEqual(s.count("🥁"), 1, s)

    def test_a_head_too_wide_for_any_bpm_walks_the_whole_line(self):
        card = self._card(width=900)
        card.set_now("LW", self._SUB)
        self.app.processEvents()
        fm = card._sub.fontMetrics()
        card._sub.resize(fm.horizontalAdvance(self._HEAD) - 10, card._sub.height())
        self.assertTrue(card._marquee.isActive())
        shown = set()
        for _ in range(len(self._SUB) + 8):
            card._marquee_step()
            shown.add(card._sub.text())
        self.assertTrue(any(not s.startswith("LW") for s in shown),
                        "no room for the bpm: the whole line walks")

    def test_resizing_the_subtitle_alone_re_measures_it(self):
        card = self._card(width=900)
        card.set_now("LW", "LW · T29 · 🥁 87 bpm")
        self.app.processEvents()
        card._sub.resize(30, card._sub.height())
        self.assertTrue(card._marquee.isActive())


if __name__ == "__main__":
    unittest.main()
