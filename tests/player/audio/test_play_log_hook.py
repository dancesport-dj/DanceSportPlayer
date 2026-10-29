"""📜 A title heard >10 s in playing mode goes into the play log, once."""
import datetime as dt
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from mutagen.id3 import ID3, TCOM, TIT2
from PySide6.QtMultimedia import QMediaPlayer

from gui.decks.deck_set import DeckSet
from planner.models import MusicEntry
from planner.playing import play_counts, play_log
from player.audio.fade_now import FadeNow
from player.audio.playback_state import PlaybackState
from player.window.main_player import PlayerControlMixin
from tests.db_support import use_scratch_db

PLAYING = QMediaPlayer.PlaybackState.PlayingState
# One MPEG-1 Layer III frame header (128 kbit/s, 44.1 kHz): 417 bytes a frame.
_FRAME = b"\xff\xfb\x90\x64" + b"\x00" * 413


def _tagged_mp3(path: Path, composer: str = "") -> Path:
    path.write_bytes(_FRAME * 100)
    tags = ID3()
    tags.add(TIT2(encoding=3, text="Moon River"))
    if composer:
        tags.add(TCOM(encoding=3, text=composer))
    tags.save(path)
    return path


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
        self.table = SimpleNamespace(_current_play_row=0, _played_paths=set(),
                                     _row_meta=[SimpleNamespace(entry=self.entry)],
                                     refresh_play_counts=lambda: None)
        self._deckset = DeckSet()
        self._deckset.all_tables = [self.table]
        self.refreshed = []
        self._lib_browser = SimpleNamespace(
            refresh_play_counts=lambda: self.refreshed.append("library"))
        self._tourney_tree = SimpleNamespace(
            refresh_play_counts=lambda: self.refreshed.append("tournaments"))
        self._player = _Media(12_000)
        self._playback = PlaybackState(path=self.entry.path, dance="WW")
        self._library = SimpleNamespace(cache=object())
        self._playing = playing
        self._between = SimpleNamespace(pending=None,
                                        xfade=SimpleNamespace(state="idle"))
        self._play_panel = SimpleNamespace(stop_fade_due=lambda now, played: False)
        self._fade_now = FadeNow()
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

    def _maybe_crossfade(self):
        pass   # tests/player/test_crossfade.py

    def _set_countdown(self, text):
        pass


class PlayLogHookTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_play_hook_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")
        self.addCleanup(play_counts.clear)

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

    def test_skipped_or_resumed_ground_is_not_heard_time(self):
        """L14: the 10 s rule read the raw position, so a ↩ resume at 1:20 or
        a start past a long silent intro counted as played on the first tick.
        Both land in offset_ms, which the log's own 'heard' already uses."""
        desk = _Desk()
        desk._player.pos_ms = 85_000
        desk._playback.offset_ms = 80_000      # picked up at 1:20, 5 s heard
        desk._on_play_tick()
        self.assertEqual(desk.marked, [])
        self.assertEqual(self.logged(), [])
        desk._player.pos_ms = 90_500
        desk._on_play_tick()
        self.assertEqual(len(desk.marked), 1)

    def test_the_composer_comes_from_the_file(self):
        """No deck row knows the composer: the tag of the file that played does."""
        song = _tagged_mp3(self.dir / "Moon River.mp3", composer="Henry Mancini")
        desk = _Desk()
        desk.entry.path = song
        desk._log_play(song)
        self.assertEqual(self.logged()[0].composer, "Henry Mancini")

    def test_a_file_without_a_composer_logs_none(self):
        song = _tagged_mp3(self.dir / "Moon River.mp3")
        desk = _Desk()
        desk.entry.path = song
        desk._log_play(song)
        self.assertEqual(self.logged()[0].composer, "")

    def test_a_missing_file_still_logs_the_play(self):
        _Desk()._log_play(Path(r"C:\music\Moon River.mp3"))
        self.assertEqual([p.composer for p in self.logged()], [""])

    def test_a_logged_play_counts_in_the_plays_column(self):
        desk = _Desk()
        desk._log_play(desk.entry.path)
        self.assertEqual(play_counts.count(desk.entry.path), 1)

    def test_a_logged_play_shows_in_the_library_and_tournaments_too(self):
        # Marcel: "Plays Counter should aslo be available in library column
        # and in tournament column"
        desk = _Desk()
        desk._log_play(desk.entry.path)
        self.assertEqual(desk.refreshed, ["library", "tournaments"])

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
