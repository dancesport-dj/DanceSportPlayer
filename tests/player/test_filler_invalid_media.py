#!/usr/bin/env python3
"""🎵 A filler title that cannot be decoded does not leave the pause silent.

Run:  py -m unittest tests.player.test_filler_invalid_media -v

The pause player acted on EndOfMedia only. A corrupt filler never gets there:
it stopped at InvalidMedia while the card went on naming it, the countdown ran
in silence, and since only EndOfMedia rotates, every later pause started on
the same broken title.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_filler_invalid_"))

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QMediaPlayer

from player.audio.between_dances import BetweenDances
from player.audio.pause_filler import PauseFiller
from player.window.main_pause import PauseMusicMixin

_INVALID = QMediaPlayer.MediaStatus.InvalidMedia


class _Win:
    _on_pause_media_status = PauseMusicMixin._on_pause_media_status
    _skip_broken_filler = PauseMusicMixin._skip_broken_filler

    def __init__(self, titles):
        self._filler = PauseFiller()
        self._filler.load(titles)
        self._filler.active = True
        self._between = BetweenDances()
        self._between.pending = (None, 0, None)     # the pause is running
        self._pause_player = mock.Mock()
        self._pause_player.errorString.return_value = "could not decode"
        self.shown = 0

    def _show_pause_status(self):
        self.shown += 1


class FillerInvalidMediaTest(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.paths = []
        for n in ("broken", "good"):
            p = Path(tmp.name) / f"{n}.mp3"
            p.write_bytes(b"")
            self.paths.append(str(p))

    def test_the_next_title_plays_instead(self):
        w = _Win(self.paths)
        w._on_pause_media_status(_INVALID)
        w._pause_player.setSource.assert_called_once_with(
            QUrl.fromLocalFile(self.paths[1]))
        w._pause_player.play.assert_called_once()
        self.assertTrue(w._filler.active)
        self.assertEqual(w.shown, 1)

    def test_without_another_title_the_pause_shows_no_filler(self):
        w = _Win(self.paths[:1])
        w._on_pause_media_status(_INVALID)
        w._pause_player.play.assert_not_called()
        self.assertFalse(w._filler.active)
        self.assertEqual(w.shown, 1)


if __name__ == "__main__":
    unittest.main()
