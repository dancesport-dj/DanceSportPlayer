"""🖼 Cover art for the player card: which picture wins, and that there is
always one to show."""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from player.artwork import cover, embedded_art, placeholder, playlist_art  # noqa: E402


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _png(path: Path, colour: str = "#3366cc"):
    """A tiny real PNG on disk (Qt writes it, Qt reads it back)."""
    from PySide6.QtGui import QColor, QPixmap
    pm = QPixmap(8, 8)
    pm.fill(QColor(colour))
    pm.save(str(path))
    return path


class PlaylistArtTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_art_"))
        self.m3u = self.dir / "Hauptgruppe S Standard.m3u"
        self.m3u.write_text("#EXTM3U\nC:/music/LW1.mp3\n", encoding="utf-8")

    def test_no_picture_anywhere_is_none(self):
        self.assertIsNone(playlist_art(self.m3u))
        self.assertIsNone(playlist_art(None))

    def test_an_extimg_line_names_the_picture(self):
        _png(self.dir / "logo.png")
        self.m3u.write_text("#EXTM3U\n#EXTIMG: logo.png\nC:/music/LW1.mp3\n",
                            encoding="utf-8")
        self.assertEqual(playlist_art(self.m3u), self.dir / "logo.png")

    def test_a_named_picture_that_is_not_there_falls_through(self):
        _png(self.dir / "cover.jpg")
        self.m3u.write_text("#EXTM3U\n#EXTIMG:gone.png\n", encoding="utf-8")
        self.assertEqual(playlist_art(self.m3u), self.dir / "cover.jpg")

    def test_an_image_of_the_same_name_beside_it_counts(self):
        _png(self.dir / "cover.jpg")
        same = _png(self.dir / (self.m3u.stem + ".jpg"))
        # The playlist's own name beats the generic cover file.
        self.assertEqual(playlist_art(self.m3u), same)

    def test_a_cover_file_in_the_folder_counts(self):
        _png(self.dir / "folder.png")
        self.assertEqual(playlist_art(self.m3u), self.dir / "folder.png")


class CoverTest(unittest.TestCase):
    """The chain: the playlist's picture, then the track's, then the tile."""

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_cov_"))
        self.m3u = self.dir / "list.m3u"
        self.m3u.write_text("#EXTM3U\n", encoding="utf-8")
        self.track = self.dir / "LW1.mp3"
        self.track.write_bytes(b"not really an mp3")

    def test_the_playlist_picture_wins(self):
        _png(self.dir / "cover.jpg", "#cc3333")
        pm = cover(self.track, self.m3u, 40)
        self.assertEqual((pm.width(), pm.height()), (40, 40))
        # Not the ♪ tile: that one is built from the title, not from a file.
        self.assertNotEqual(pm.toImage(), placeholder(40, "LW1").toImage())

    def test_a_track_without_any_cover_still_gets_a_tile(self):
        pm = cover(self.track, None, 40)
        self.assertFalse(pm.isNull())
        self.assertEqual(pm.toImage(), placeholder(40, "LW1").toImage())

    def test_the_tile_is_stable_per_title_and_differs_between_them(self):
        self.assertEqual(placeholder(24, "LW1").toImage(),
                         placeholder(24, "LW1").toImage())
        self.assertNotEqual(placeholder(24, "LW1").toImage(),
                            placeholder(24, "TG2").toImage())

    def test_a_file_that_is_no_audio_has_no_embedded_cover(self):
        self.assertIsNone(embedded_art(self.track))
        self.assertIsNone(embedded_art(None))


class PlayerCardArtworkTest(unittest.TestCase):
    """The 🖼 option on the player card: off costs no width, on shows a cover."""

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def setUp(self):
        from PySide6.QtMultimedia import QMediaPlayer
        from player.player import BigPlayerWidget
        self.dir = Path(tempfile.mkdtemp(prefix="dp_card_"))
        self.track = self.dir / "LW1.mp3"
        self.track.write_bytes(b"not really an mp3")
        self.card = BigPlayerWidget(QMediaPlayer())

    def tearDown(self):
        self.card.deleteLater()

    def test_the_cover_stays_hidden_until_the_option_is_on(self):
        self.card.set_artwork(self.track)
        self.assertFalse(self.card._art.isVisible())
        self.assertTrue(self.card._art.pixmap().isNull())

    def test_switching_it_on_shows_the_track_already_playing(self):
        self.card.set_artwork(self.track)
        self.card.set_artwork_enabled(True)
        self.assertFalse(self.card._art.pixmap().isNull())

    def test_the_playlist_picture_reaches_the_card(self):
        _png(self.dir / "cover.jpg", "#118844")
        m3u = self.dir / "list.m3u"
        m3u.write_text("#EXTM3U\n", encoding="utf-8")
        self.card.set_artwork_enabled(True)
        self.card.set_artwork(self.track, m3u)
        self.assertEqual(self.card._art.pixmap().toImage(),
                         cover(self.track, m3u, self.card._art.width()).toImage())

    def test_stopping_clears_the_cover(self):
        self.card.set_artwork_enabled(True)
        self.card.set_artwork(self.track)
        self.card.set_artwork(None)
        self.assertTrue(self.card._art.pixmap().isNull())


if __name__ == "__main__":
    unittest.main()
