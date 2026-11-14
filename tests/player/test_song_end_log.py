"""⏹ Every way a title can end leaves a "Song ended" line with its reason.

Only the four play-length rules logged one; a title heard to its last note or
stopped by hand left no trace, so an early stop could not be told from a
natural end in the session log.

Run:  py -m unittest tests.player.test_song_end_log -v
"""
import unittest

from tests.player.test_resume_mark import _FakeWindow, _player_mixin


class SongEndLogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        class Win(_FakeWindow, _player_mixin()):
            pass
        cls.Win = Win

    def test_a_title_heard_to_its_end_says_so(self):
        from PySide6.QtMultimedia import QMediaPlayer
        w = self.Win(pos_ms=179_900, dur_ms=180_000)
        with self.assertLogs("dancesport.gui.player", "INFO") as logs:
            w._on_media_status(QMediaPlayer.MediaStatus.EndOfMedia)
        text = "\n".join(r.getMessage() for r in logs.records)
        self.assertIn("Song ended", text)
        self.assertIn("reason: end of file", text)
        self.assertIn("position: 179900 / 180000 ms", text)

    def test_a_late_end_of_the_previous_title_logs_nothing(self):
        from PySide6.QtMultimedia import QMediaPlayer
        w = self.Win()
        w._player.mediaStatus = lambda: QMediaPlayer.MediaStatus.LoadingMedia
        with self.assertNoLogs("dancesport.gui.player", "INFO"):
            w._on_media_status(QMediaPlayer.MediaStatus.EndOfMedia)


if __name__ == "__main__":
    unittest.main()
