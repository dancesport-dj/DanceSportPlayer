"""⏹ A title heard to its end lets go of its file.

Run:  py -m unittest tests.player.test_end_releases_file -v

The media backend keeps a finished title's file open for as long as it is
the player's source — measured on Windows: renaming it after EndOfMedia
failed with WinError 32 ("in use"), after ``setSource(QUrl())`` it worked.
⏹ and every error path already cleared the source; the plain end did not,
so the last title of a list could not be retagged, renamed or deleted
until another one was played.
"""
import unittest

from PySide6.QtCore import QUrl

from tests.player.test_resume_mark import _FakePanel, _FakePlayer, _FakeWindow, _player_mixin


class _SourcePlayer(_FakePlayer):
    def __init__(self):
        super().__init__()
        self.sources = []

    def setSource(self, url):
        self.sources.append(url)


class _EditingPanel(_FakePanel):
    def pd_editing(self):
        return True


class EndReleasesFileTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        class Win(_FakeWindow, _player_mixin()):
            pass
        cls.Win = Win

    def end(self, w):
        from PySide6.QtMultimedia import QMediaPlayer
        w._player = _SourcePlayer()
        w._on_media_status(QMediaPlayer.MediaStatus.EndOfMedia)
        return w._player.sources

    def test_the_end_clears_the_source(self):
        self.assertEqual(self.end(self.Win()), [QUrl()])

    def test_the_overlay_end_clears_it_too(self):
        self.assertEqual(self.end(self.Win(big=False)), [QUrl()])

    def test_an_armed_advance_keeps_the_next_title_it_preloaded(self):
        w = self.Win()
        w._queue_auto_advance = lambda: setattr(w._between, "pending", ("t", 1, "next.mp3"))
        self.assertEqual(self.end(w), [])

    def test_hand_marking_keeps_the_title_loaded(self):
        w = self.Win()
        w._play_panel = _EditingPanel()
        self.assertEqual(self.end(w), [])


if __name__ == "__main__":
    unittest.main()
