#!/usr/bin/env python3
"""Qt's FFmpeg writes nothing to stderr.

Run:  .venv\\Scripts\\python.exe -m unittest tests.player.test_ffmpeg_quiet -v

Qt Multimedia's FFmpeg DLLs carry a C runtime of their own (on Windows they
import none), and that runtime keeps the stderr handle it found when they
loaded. A `dup2(…, 2)` — `quiet_native_stderr`, a test, pytest's capture —
closes that handle; the next file opened can get the same number, and every
"Input #0 …" FFmpeg prints when it opens a track lands in that file. In the
suite it landed in audio_features.db, mid-page: "database disk image is
malformed". With FFmpeg's log off there is no writer left.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.gui.monkey_support import _silent_mp3

_REPO = Path(__file__).resolve().parents[2]

_CHILD = r"""
import sys
from PySide6.QtCore import QEventLoop, QTimer, QUrl
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

app = QApplication([])
from player.audio.cue_player import CuePlayer
cue = CuePlayer()
player = cue.media_player
loop = QEventLoop()
player.mediaStatusChanged.connect(
    lambda s: loop.quit() if s in (QMediaPlayer.MediaStatus.LoadedMedia,
                                   QMediaPlayer.MediaStatus.InvalidMedia) else None)
QTimer.singleShot(10000, loop.quit)
player.setSource(QUrl.fromLocalFile(sys.argv[1]))
loop.exec()
print(player.mediaStatus().name)
"""


class FfmpegQuietTest(unittest.TestCase):

    def test_opening_a_track_prints_nothing_from_ffmpeg(self):
        tmp = Path(tempfile.mkdtemp(prefix="dp_ffquiet_"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        track = tmp / "Song (LW 29).mp3"
        _silent_mp3(track, 5)
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen",
                   DANCEPLAYLIST_DATA_DIR=str(tmp))
        proc = subprocess.run([sys.executable, "-c", _CHILD, str(track)],
                              cwd=_REPO, env=env, capture_output=True, timeout=60)
        self.assertEqual(proc.stdout.strip(), b"LoadedMedia", proc.stderr)
        self.assertNotIn(b"Input #0", proc.stderr)
        self.assertNotIn(b"Estimating duration", proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
