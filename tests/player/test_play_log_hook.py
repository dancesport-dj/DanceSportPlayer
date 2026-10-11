"""📜 A title heard >10 s in playing mode goes into the play log, once."""
import datetime as dt
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtMultimedia import QMediaPlayer

import planner.db as pdb
from planner import play_log
from planner.models import MusicEntry
from player.main_player import PlayerControlMixin
from player.playback_state import PlaybackState

PLAYING = QMediaPlayer.PlaybackState.PlayingState


class _Media:
    def __init__(self, pos_ms):
        self.pos_ms = pos_ms

    def position(self):
        return self.pos_ms

    def playbackRate(self):
        return 1.0

    def playbackState(self):
        return PLAYING


class _Desk(PlayerControlMixin):
    """Just what the played mark and the log read."""

    def __init__(self, playing=True):
        self.entry = MusicEntry(path=Path(r"C:\music\Moon River.mp3"), title="Moon River",
                                dance="WW", duration=150, tag_artist="Henry Mancini")
        self.table = SimpleNamespace(_current_play_row=0,
                                     _row_meta=[SimpleNamespace(entry=self.entry)])
        self._all_tables = [self.table]
        self._player = _Media(12_000)
        self._playback = PlaybackState(path=self.entry.path, dance="WW")
        self._cache = object()
        self._playing = playing
        self._between = SimpleNamespace(pending=None)
        self._fade_now_end = None
        self._played_marked = False
        self._PLAYED_AFTER_MS = 10_000
        self._mix = SimpleNamespace(fade=1.0)
        self.marked = []

    def _is_playing_mode(self):
        return self._playing

    def deck(self, table):
        return SimpleNamespace(title="Hauptgruppe S")

    def _maybe_skip_silence(self):
        return False

    def _mark_path_played(self, path):
        self.marked.append(path)

    def _pd_runs_to_its_highlight(self):
        return False

    def _play_limit_secs(self):
        return 0

    def _set_countdown(self, text):
        pass


class PlayLogHookTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_play_hook_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        saved = (pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED)
        pdb.AUDIO_DB_FILE = self.dir / "scratch.db"
        pdb._DB_LOCAL = threading.local()
        pdb._DB_INITIALIZED = False

        def restore():
            try:
                pdb._DB_LOCAL.conn.close()
            except Exception:
                pass
            pdb.AUDIO_DB_FILE, pdb._DB_LOCAL, pdb._DB_INITIALIZED = saved
        self.addCleanup(restore)

    def logged(self):
        return [p for e in play_log.evenings() for p in play_log.plays(e)]

    def test_the_tick_logs_a_title_once_when_it_greys(self):
        desk = _Desk()
        desk._on_play_tick()
        desk._on_play_tick()
        self.assertEqual(len(desk.marked), 1)
        got = self.logged()
        self.assertEqual(len(got), 1)
        p = got[0]
        self.assertEqual((p.artist, p.title, p.dance, p.list_name, p.length),
                         ("Henry Mancini", "Moon River", "WW", "Hauptgruppe S", 150))
        # It started when the music did, not when it greyed.
        ago = (dt.datetime.now() - p.started_at).total_seconds()
        self.assertTrue(11 <= ago <= 14, ago)

    def test_planning_mode_logs_nothing(self):
        _Desk(playing=False)._log_play(Path(r"C:\music\Moon River.mp3"))
        self.assertEqual(self.logged(), [])

    def test_a_title_off_the_decks_still_gets_its_file_name(self):
        desk = _Desk()
        desk.table._current_play_row = -1
        desk._playback = PlaybackState(path=Path(r"C:\other\Tango Jalousie.mp3"), dance="TG")
        desk._log_play(desk._playback.path)
        p = self.logged()[0]
        self.assertEqual((p.title, p.dance, p.list_name), ("Tango Jalousie", "TG", ""))


if __name__ == "__main__":
    unittest.main()
