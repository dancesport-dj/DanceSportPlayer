"""Tests for the 🗜 three-state header view (full → compact → 🚫 no grouping)
and for the 🖥 presenter screen's state feed (running title + the next three).
"""
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

# Offscreen BEFORE any QApplication, state files into a temp dir (the gui
# modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_presenter_"))

from planner.models import MusicEntry, RoundConfig   # noqa: E402
from player.presenter import PAUSE_TEXT   # noqa: E402
from tests.qt_test_support import reap_widget   # noqa: E402
from player.playback_state import PlaybackState  # noqa: E402
from player.between_dances import BetweenDances  # noqa: E402


def _e(dance, n):
    return MusicEntry(path=Path(rf"C:\music\{dance}{n}.mp3"),
                      title=f"{dance} {n}", dance=dance, bpm=None)


def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _deck():
    """A deck holding two one-heat rounds of LW + TG (4 songs)."""
    from gui.playlist_table import PlaylistTable
    t = PlaylistTable()
    playlist = {"Vorrunde": [[_e("LW", 1), _e("TG", 2)]],
                "Finale":   [[_e("LW", 3), _e("TG", 4)]]}
    rounds = [RoundConfig(name="Vorrunde", heats=1, tier="early"),
              RoundConfig(name="Finale", heats=1, tier="final")]
    t.load(playlist, ["LW", "TG"], rounds, "S",
           play_cb=lambda *a: None, suggester=None, use_timbre=False)
    return t


def _rows(table):
    """(song rows, header rows) of a rendered table."""
    songs = [r for r, m in enumerate(table._row_meta)
             if m and m.entry is not None]
    return songs, [r for r in range(table.rowCount()) if r not in songs]


class GroupingViewTest(unittest.TestCase):
    """What each of the three header states actually renders."""

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def test_full_view_has_round_and_dance_headers(self):
        t = _deck()
        songs, headers = _rows(t)
        self.assertEqual(len(songs), 4)
        # 2 round headers + 2 dance headers per round.
        self.assertEqual(len(headers), 6)
        self.assertEqual(len(t._round_hdr_rows), 2)
        self.assertEqual(len(t._dance_hdr_rows), 4)

    def test_compact_drops_only_the_dance_headers(self):
        t = _deck()
        t.set_grouping(1)
        songs, headers = _rows(t)
        self.assertEqual(len(songs), 4)
        self.assertEqual(len(headers), 2)
        self.assertEqual(len(t._round_hdr_rows), 2)
        self.assertEqual(t._dance_hdr_rows, set())

    def test_no_grouping_leaves_a_flat_song_list(self):
        t = _deck()
        t.set_grouping(2)
        songs, headers = _rows(t)
        self.assertEqual(len(songs), 4)
        self.assertEqual(headers, [])
        self.assertEqual(t._round_hdr_rows, set())
        # The songs still know their round — only the header row is gone.
        self.assertEqual([t._row_meta[r].round_name for r in songs],
                         ["Vorrunde", "Vorrunde", "Finale", "Finale"])

    def test_back_to_full_restores_every_header(self):
        t = _deck()
        t.set_grouping(2)
        t.set_grouping(0)
        _songs, headers = _rows(t)
        self.assertEqual(len(headers), 6)

    def test_no_grouping_drops_the_party_section_headers(self):
        """The ETDS party / Eintanzen list groups by ─── section headers."""
        from gui.playlist_table import PlaylistTable
        t = PlaylistTable()
        entries = [_e("LW", 1), _e("TG", 2), _e("SA", 3), _e("CC", 4)]
        t.load_warmup(entries, "Eintanzen", "standard", "S", True,
                      play_cb=lambda *a: None, suggester=None)
        songs, headers = _rows(t)
        self.assertEqual(len(songs), 4)
        self.assertTrue(headers, "party list should start out grouped")
        t.set_grouping(2)
        songs, headers = _rows(t)
        self.assertEqual(len(songs), 4)
        self.assertEqual(headers, [])

    def test_the_party_sections_collapse(self):
        """⊟ / ⊞ acted on round headers only, and the party list's ─── strips
        were never registered as such — so the buttons did nothing at all on the
        one list that is alone on screen in the no-playlist view."""
        from gui.playlist_table import PlaylistTable
        t = PlaylistTable()
        entries = [_e("LW", 1), _e("TG", 2), _e("SA", 3), _e("CC", 4)]
        t.load_warmup(entries, "Party", "standard", "S", True,
                      play_cb=lambda *a: None, suggester=None)
        songs, headers = _rows(t)
        self.assertEqual(t._round_hdr_rows, set(headers))
        t.collapse_all()
        self.assertTrue(all(t.isRowHidden(r) for r in songs))
        self.assertFalse(any(t.isRowHidden(r) for r in headers))
        t.expand_all()
        self.assertFalse(any(t.isRowHidden(r) for r in songs))


class GroupingSelectionTest(unittest.TestCase):
    """🗜 Cycling the header view keeps the selection on the same SONG.

    Dropping the dance headers moves every song under them up two rows, so a
    selection kept by row number lands on whatever slid into its place — which,
    in the middle of an evening, is the wrong track to be looking at."""

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    @staticmethod
    def _path_at(table, row):
        m = table._row_meta.at(row)
        return m.path_str if m is not None else ""

    def test_the_selected_song_is_still_selected_after_the_cycle(self):
        t = _deck()
        songs, _headers = _rows(t)
        want = self._path_at(t, songs[-1])
        t.setCurrentCell(songs[-1], 0)
        t.set_grouping(2)                      # 🚫 no grouping: 6 header rows go
        self.assertEqual(self._path_at(t, t.currentRow()), want)
        self.assertIn(t.currentRow(), [i.row() for i in t.selectedIndexes()])

    def test_it_follows_the_song_back_when_the_headers_return(self):
        t = _deck()
        songs, _headers = _rows(t)
        want = self._path_at(t, songs[2])
        t.setCurrentCell(songs[2], 0)
        t.set_grouping(2)
        t.set_grouping(0)
        self.assertEqual(self._path_at(t, t.currentRow()), want)

    def test_the_party_list_keeps_its_selection_too(self):
        from gui.playlist_table import PlaylistTable
        t = PlaylistTable()
        entries = [_e("LW", 1), _e("TG", 2), _e("SA", 3), _e("CC", 4)]
        t.load_warmup(entries, "Party", "standard", "S", True,
                      play_cb=lambda *a: None, suggester=None)
        songs, _headers = _rows(t)
        want = self._path_at(t, songs[-1])
        t.setCurrentCell(songs[-1], 0)
        t.set_grouping(2)
        self.assertEqual(self._path_at(t, t.currentRow()), want)

    def test_nothing_selected_stays_nothing_selected(self):
        """No current row, no song to follow — and no exception on the way."""
        t = _deck()
        t.setCurrentCell(-1, -1)
        t.set_grouping(2)
        self.assertEqual(t.selectedIndexes(), [])


class PresenterStateTest(unittest.TestCase):
    """What the 🖥 presenter screen is fed."""

    @classmethod
    def setUpClass(cls):
        cls.app = _app()
        from player.main_player import PlayerControlMixin

        class Win(PlayerControlMixin):
            def __init__(self, table):
                self._all_tables = [table]
                self._between = BetweenDances()
                self._between.pending = None
                self._between.shown = True     # a pause the hall should see
                self._playback = PlaybackState()
                self._playback.path = None
                self._playback.dance = ""
                self._player = None          # no media backend in the test
                self._playback.offset_ms = 0
                self._pd_stop_at = None
                self._between.advance_at = time.monotonic() + 12.4
                self._last_played = None     # 🕘 nothing played before
        cls.Win = Win

    def setUp(self):
        self.t = _deck()
        self.win = self.Win(self.t)

    def _play(self, row):
        self.t._current_play_row = row
        meta = self.t._row_meta[row]
        self.win._playback.path = meta.entry.path
        self.win._playback.dance = meta.dance

    def test_running_title_with_its_dance(self):
        songs, _ = _rows(self.t)
        self._play(songs[0])
        dance, title, _times, _nxt, _last = self.win._presenter_state()
        self.assertEqual(dance, "Langsamer Walzer")
        self.assertEqual(title, "LW1")

    def test_the_next_three_follow_the_playing_row(self):
        songs, _ = _rows(self.t)
        self._play(songs[0])
        *_head, nxt, _last = self.win._presenter_state()
        self.assertEqual(nxt, [("Tango", "TG2"),
                               ("Langsamer Walzer", "LW3"),
                               ("Tango", "TG4")])

    def test_the_end_of_the_list_just_runs_short(self):
        songs, _ = _rows(self.t)
        self._play(songs[-1])
        *_head, nxt, _last = self.win._presenter_state()
        self.assertEqual(nxt, [])

    def test_the_pause_shows_the_armed_song_first(self):
        """Between songs nothing is playing — the armed advance leads the list."""
        songs, _ = _rows(self.t)
        row = songs[1]
        self.win._between.pending = (self.t, row,
                                     self.t._row_meta[row].entry.path)
        dance, title, times, nxt, _last = self.win._presenter_state()
        self.assertEqual((dance, title), (PAUSE_TEXT, ""))
        # No song runs — the clock counts the pause down instead.
        self.assertEqual(times, ("", "−  00:12", False, 0.0))
        self.assertEqual(nxt, [("Tango", "TG2"),
                               ("Langsamer Walzer", "LW3"),
                               ("Tango", "TG4")])

    def test_a_pause_nobody_configured_never_reaches_the_screen(self):
        """⏸ switched off: the advance still goes through a zero-second pause,
        and the hall used to see the break mark blink between every two
        titles. It now shows the title that is about to start."""
        songs, _ = _rows(self.t)
        row = songs[1]
        self.win._between.pending = (self.t, row,
                                     self.t._row_meta[row].entry.path)
        self.win._between.shown = False
        dance, title, times, nxt, _last = self.win._presenter_state()
        self.assertEqual((dance, title), ("Tango", "TG2"))
        self.assertEqual(times, ("", "", False, 0.0))
        # …and the queue behind it, without naming TG2 a second time.
        self.assertEqual(nxt, [("Langsamer Walzer", "LW3"), ("Tango", "TG4")])

    def test_nothing_playing_shows_nothing(self):
        self.assertEqual(self.win._presenter_state(),
                         ("", "", ("", "", False, 0.0), [], ("", "")))

    def test_the_title_before_this_one_is_carried_along(self):
        songs, _ = _rows(self.t)
        self._play(songs[0])
        self.assertEqual(self.win._presenter_state()[4], ("", ""))
        self.win._last_played = ("Tango", "TG0")
        self.assertEqual(self.win._presenter_state()[4], ("Tango", "TG0"))

    def test_during_the_break_it_names_the_title_that_just_ended(self):
        """The hero line is 'Pause' then, and what the hall just heard is the
        one still loaded — not the one before that."""
        songs, _ = _rows(self.t)
        self._play(songs[0])
        self.win._last_played = ("Tango", "TG0")
        row = songs[1]
        self.win._between.pending = (self.t, row,
                                     self.t._row_meta[row].entry.path)
        self.assertEqual(self.win._presenter_state()[4],
                         ("Langsamer Walzer", "LW1"))

    def test_the_moment_between_two_songs_names_it_too(self):
        """No pause configured: the hero already shows what is about to start,
        so the title that just ended belongs on the 🕘 line, not in limbo."""
        songs, _ = _rows(self.t)
        self._play(songs[0])
        row = songs[1]
        self.win._between.pending = (self.t, row,
                                     self.t._row_meta[row].entry.path)
        self.win._between.shown = False
        dance, title, _times, _nxt, last = self.win._presenter_state()
        self.assertEqual((dance, title), ("Tango", "TG2"))
        self.assertEqual(last, ("Langsamer Walzer", "LW1"))

    def test_the_clock_counts_a_running_title_down(self):
        """No media backend here — drive _presenter_times with a fake player."""
        songs, _ = _rows(self.t)
        self._play(songs[0])
        self.win._player = SimpleNamespace(
            playbackRate=lambda: 1.0,
            position=lambda: 99_000,      # 1:39 in
            duration=lambda: 137_000)     # 0:38 to go
        self.t._play_vals = {"secs": 0}    # the playing list: full length
        played, left, ending, frac = self.win._presenter_times()
        self.assertEqual((played, left, ending), ("▶  01:39", "−  00:38", False))
        self.assertAlmostEqual(frac, 99 / 137, places=3)

    def test_the_last_seconds_flag_the_end(self):
        songs, _ = _rows(self.t)
        self._play(songs[0])
        self.win._player = SimpleNamespace(
            playbackRate=lambda: 1.0,
            position=lambda: 130_000,
            duration=lambda: 137_000)
        self.t._play_vals = {"secs": 0}    # the playing list: full length
        played, left, ending, _frac = self.win._presenter_times()
        self.assertEqual((played, left), ("▶  02:10", "−  00:07"))
        self.assertTrue(ending)

    def test_the_play_length_wins_over_the_track_end(self):
        """A 1:45 cut ends the title long before the file does."""
        songs, _ = _rows(self.t)
        self._play(songs[0])
        self.win._player = SimpleNamespace(
            playbackRate=lambda: 1.0,
            position=lambda: 60_000,
            duration=lambda: 300_000)
        self.t._play_vals = {"secs": 105}  # the playing list cuts at 1:45
        played, left, ending, frac = self.win._presenter_times()
        self.assertEqual((played, left, ending), ("▶  01:00", "−  00:45", False))
        # The bar runs against the cut, not against the file's own length.
        self.assertAlmostEqual(frac, 60 / 105, places=3)


class PresenterWindowTest(unittest.TestCase):
    """The window itself renders the state it is handed."""

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def _win(self, state):
        from player.presenter import PresenterWindow
        w = PresenterWindow(lambda: state.v if hasattr(state, "v") else state)
        self.addCleanup(reap_widget, w)
        w.resize(1280, 720)
        w.show()
        self.addCleanup(w.close)
        self.app.processEvents()
        w._refresh()
        return w

    def test_labels_follow_the_state_callback(self):
        state = SimpleNamespace(
            v=("Tango", "Jealousy", ("▶  00:42", "−  01:03", False, 0.4),
               [("Wiener Walzer", "Sail Along")], ("", "")))
        w = self._win(state)
        self.assertEqual(w.dance_lbl.full_text(), "Tango")
        self.assertEqual(w.title_lbl.full_text(), "Jealousy")
        self.assertEqual(w.played_lbl.full_text(), "▶  00:42")
        self.assertEqual(w.left_lbl.full_text(), "−  01:03")
        self.assertEqual(w.bar._frac, 0.4)
        # Dance and title on their own lines, as on the iPad screen.
        self.assertEqual(w.next_lbls[0].full_text(), "Wiener Walzer")
        self.assertEqual(w.next_sub_lbls[0].full_text(), "Sail Along")
        self.assertFalse(w._next_rows[1][0].isVisible())
        state.v = ("", "", ("", "", False, 0.0), [], ("", ""))
        w._refresh()
        self.assertEqual(w.dance_lbl.full_text(), "—")

    def test_the_last_played_line_is_off_until_it_is_asked_for(self):
        """A presentation screen shows the programme; history is opt-in."""
        state = SimpleNamespace(
            v=("Tango", "Jealousy", ("", "", False, 0.0), [],
               ("Langsamer Walzer", "Fascination")))
        w = self._win(state)
        self.assertEqual(w.last_lbl.full_text(), "Langsamer Walzer")
        self.assertEqual(w.last_sub_lbl.full_text(), "Fascination")
        self.assertFalse(w.last_wrap.isVisible())
        w.set_last_played_shown(True)
        self.assertTrue(w.last_wrap.isVisible())
        # …and it brings its own column up: nothing is queued behind it.
        self.assertTrue(w.next_box.isVisible())
        self.assertFalse(w.next_hdr.isVisible())

    def test_nothing_played_yet_shows_no_empty_line(self):
        state = SimpleNamespace(
            v=("Tango", "Jealousy", ("", "", False, 0.0), [], ("", "")))
        w = self._win(state)
        w.set_last_played_shown(True)
        self.assertEqual(w.last_lbl.full_text(), "")
        self.assertFalse(w.last_wrap.isVisible())

    def test_the_button_reports_the_switch_for_saving(self):
        """Like the 🎛 transport, the setting is made on the screen itself and
        remembered by the main window."""
        state = SimpleNamespace(
            v=("Tango", "Jealousy", ("", "", False, 0.0), [], ("Tango", "TG0")))
        w = self._win(state)
        seen = []
        w.lastToggled.connect(seen.append)
        w.last_btn.click()
        self.assertEqual(seen, [True])
        self.assertTrue(w.last_wrap.isVisible())
        w.last_btn.click()
        self.assertEqual(seen, [True, False])
        self.assertFalse(w.last_wrap.isVisible())

    def test_a_new_last_played_title_is_re_fitted(self):
        """It is a measured line like the others — a longer one has to be
        re-measured, or it would stand unscrolled and cut off."""
        state = SimpleNamespace(
            v=("Tango", "Jealousy", ("▶  00:42", "−  01:03", False, 0.4), [],
               ("Tango", "TG0")))
        w = self._win(state)
        w.set_last_played_shown(True)
        fits = []
        w._fit = lambda: fits.append(1)
        state.v = ("Tango", "Jealousy", ("▶  00:43", "−  01:02", False, 0.41),
                   [], ("Langsamer Walzer", "Fascination"))
        w._refresh()
        self.assertEqual(fits, [1])

    def test_the_last_played_row_lines_up_with_the_queue(self):
        """It is the head of the same column: its dance stands on the same left
        edge as the queue's, and it carries no number of its own — it is not
        step 0 of the running order."""
        state = SimpleNamespace(
            v=("Tango", "Jealousy", ("", "", False, 0.0),
               [("Wiener Walzer", "Sail Along")],
               ("Langsamer Walzer", "Fascination")))
        w = self._win(state)
        w.set_last_played_shown(True)
        w.layout().activate()
        left = w.last_lbl.mapTo(w.next_box, w.last_lbl.rect().topLeft()).x()
        queue_left = w.next_lbls[0].mapTo(
            w.next_box, w.next_lbls[0].rect().topLeft()).x()
        self.assertEqual(left, queue_left)
        self.assertEqual(w.last_num.width(), w.next_num_lbls[0].width())
        self.assertEqual(w.last_num.text(), "")
        # …and it stands above the queue, not inside it.
        self.assertLess(w.last_wrap.y(), w.next_hdr.y())

    def test_the_block_never_pushes_the_screen_past_its_window(self):
        """Switching it on adds a queue row's worth of height. A presenter
        screen that outgrows its monitor loses its foot row behind the taskbar
        and falls out of full screen — so what is shown is sized to fit."""
        state = SimpleNamespace(
            v=("Tango", "Jealousy", ("▶  00:42", "−  01:03", False, 0.4),
               [("Wiener Walzer", "Sail Along"), ("Samba", "Ven A Vivir"),
                ("Cha-Cha", "Sunshine Day Medley")],
               ("Langsamer Walzer", "Fascination")))
        w = self._win(state)
        for h in (1080, 906, 768):
            w.resize(1280, h)
            self.app.processEvents()
            for on in (True, False, True):   # …and switching back and forth
                w.set_last_played_shown(on)
                w.layout().activate()
                self.assertLessEqual(w.layout().minimumSize().height(),
                                     w.height(), f"{h} px tall, shown={on}")

    def test_the_history_stands_where_the_third_queue_row_would(self):
        """The column holds three rows either way: switched on, the 🕘 block
        stands where the third of the next dances would, so the screen keeps
        the proportions — and the font sizes — it has without it."""
        state = SimpleNamespace(
            v=("Samba", "Ven A Vivir", ("▶  01:40", "−  01:28", False, 0.5),
               [("Samba", "Para Ti"), ("Cha-Cha", "Sunshine Day Medley"),
                ("Rumba", "Feels")],
               ("Langsamer Walzer", "Fascination")))
        w = self._win(state)
        self.assertTrue(w._next_rows[2][0].isVisible())   # off: all three
        w.set_last_played_shown(True)
        self.app.processEvents()
        self.assertTrue(w.last_wrap.isVisible())
        self.assertTrue(w._next_rows[1][0].isVisible())
        self.assertFalse(w._next_rows[2][0].isVisible())
        w.set_last_played_shown(False)
        self.app.processEvents()
        self.assertTrue(w._next_rows[2][0].isVisible())   # …and back again

    def test_the_first_title_it_ever_names_is_sized_for(self):
        """Switched on at the start of an evening the block has nothing to name
        yet and costs no height — so the first Zuletzt title is the moment the
        column really grows, and everything has to be measured again for it.
        Skip that pass and the hero dance keeps a size the window no longer has
        room for, and it is the first thing to be cut off."""
        state = SimpleNamespace(
            v=("Samba", "01 Allegro Ventigo (SB 50)",
               ("▶  01:40", "−  01:28", False, 0.5),
               [("Samba", "Ven A Vivir"), ("Samba", "Para Ti"),
                ("Cha-Cha", "Sunshine Day Medley")],
               ("", "")))
        w = self._win(state)
        w.resize(1600, 906)
        self.app.processEvents()
        w.set_last_played_shown(True)
        self.assertFalse(w.last_wrap.isVisible())   # nothing to name yet
        sized_for = w._font_h
        state.v = state.v[:4] + (("Langsamer Walzer", "Fascination"),)
        w._refresh()
        w.layout().activate()
        self.assertTrue(w.last_wrap.isVisible())
        self.assertNotEqual(w._font_h, sized_for)
        self.assertLessEqual(w.layout().minimumSize().height(), w.height())

    def test_the_clock_is_read_often_enough_to_step_evenly(self):
        """The refresh IS the clock's resolution: poll it every 400 ms and the
        displayed second changes 0.8 s after one boundary and 1.2 s after the
        next, which reads as a stopwatch running unevenly beside the player's
        own."""
        from player.presenter import _REFRESH_MS
        self.assertLessEqual(_REFRESH_MS, 100)

    def test_a_tick_that_only_moves_the_clock_skips_the_fitting_pass(self):
        """What pays for the fast poll: the fitting pass measures the dance,
        the title and the queue, and none of them move when only the seconds
        do."""
        state = SimpleNamespace(
            v=("Tango", "Jealousy", ("▶  00:42", "−  01:03", False, 0.4), [], ("", "")))
        w = self._win(state)
        fits = []
        w._fit = lambda: fits.append(1)
        state.v = ("Tango", "Jealousy", ("▶  00:43", "−  01:02", False, 0.41), [], ("", ""))
        w._refresh()
        self.assertEqual(w.played_lbl.full_text(), "▶  00:43")
        self.assertEqual(fits, [])
        state.v = ("Slowfox", "Jealousy", ("▶  00:44", "−  01:01", False, 0.42), [], ("", ""))
        w._refresh()
        self.assertEqual(fits, [1])

    def test_the_break_is_the_bare_word_for_now(self):
        """The painted ⏸ is built and ready, but switched off (_PAUSE_MARK):
        what the hall gets is the word, and no emoji anywhere near it."""
        w = self._win((PAUSE_TEXT, "", ("", "−  00:12", False, 0.0),
                       [("Tango", "TG2")], ("", "")))
        self.assertEqual(w.dance_lbl.full_text(), PAUSE_TEXT)
        self.assertEqual(w.dance_lbl.icon_width(), 0)

    def test_a_line_can_carry_a_painted_mark_beside_its_word(self):
        """What flipping _PAUSE_MARK back on gets: the icon goes IN the line —
        beside the word and as tall as its letters, not stacked over it, which
        made the hero block a head too tall."""
        w = self._win(("Tango", "Jealousy", ("", "", False, 0.0), [], ("", "")))
        plain = w.dance_lbl.text_width()
        w.dance_lbl.set_icon(w._pause_mark)
        self.assertGreater(w.dance_lbl.icon_width(), 0)
        self.assertEqual(w.dance_lbl.text_width(),
                         plain + w.dance_lbl.icon_width())
        self.assertLessEqual(w._pause_mark.height(),
                             w.dance_lbl.font().pixelSize() * 1.2)

    def test_a_long_dance_line_shrinks_instead_of_widening_the_screen(self):
        w = self._win(("Langsamer Walzer und noch ein sehr langer Zusatz",
                       "Fascination", ("▶  00:42", "−  01:03", False, 0.3), [], ("", "")))
        self.assertEqual(w.width(), 1280)
        self.assertLess(w.dance_lbl.font().pixelSize(), w._base_px[w.dance_lbl])

    def test_a_short_dance_keeps_the_full_font(self):
        w = self._win(("Tango", "Jealousy", ("", "", False, 0.0), [], ("", "")))
        self.assertEqual(w.dance_lbl.font().pixelSize(), w._base_px[w.dance_lbl])
        self.assertEqual(w.dance_lbl.text(), "Tango")

    def test_a_long_title_wanders_instead_of_shrinking(self):
        long_title = "Fascination — " + "André Rieu and his Orchestra " * 5
        w = self._win(("Langsamer Walzer", long_title,
                       ("▶  00:42", "−  01:03", False, 0.3), [], ("", "")))
        self.assertEqual(w.title_lbl.font().pixelSize(), w._base_px[w.title_lbl])
        self.assertTrue(w.title_lbl._timer.isActive())

    def test_the_queue_keeps_one_font_size_and_scrolls_what_is_too_long(self):
        """Every queue line reads the same size; an over-long one wanders."""
        long_one = ("Slowfox", "Fly Me To The Moon — " + "in the Big Band way " * 6)
        w = self._win(("Tango", "Jealousy", ("", "", False, 0.0),
                       [("Wiener Walzer", "Sail Along"), long_one], ("", "")))
        sizes = {lbl.font().pixelSize() for lbl in w.next_sub_lbls}
        self.assertEqual(len(sizes), 1)
        self.assertFalse(w.next_sub_lbls[0]._timer.isActive())
        self.assertTrue(w.next_sub_lbls[1]._timer.isActive())
        # It really moves, and never cuts the text short.
        w.next_sub_lbls[1]._advance()
        self.assertGreater(w.next_sub_lbls[1]._offset, 0)
        self.assertIn("Big Band way", w.next_sub_lbls[1].full_text())

    def test_the_last_seconds_blink_the_remaining_time_red(self):
        from player.presenter_theme import DEFAULT_KEY, theme_for
        theme = theme_for(DEFAULT_KEY)
        state = SimpleNamespace(v=("Tango", "Jealousy",
                                   ("▶  02:10", "−  00:07", True, 0.95), [], ("", "")))
        w = self._win(state)
        self.assertTrue(w._blink.isActive())
        w._blink_left()
        self.assertEqual(w.left_lbl._color.name(), theme.end)
        w._blink_left()
        self.assertEqual(w.left_lbl._color.name(), theme.left)
        # Next title starts → back to the calm colour, no blinking.
        state.v = ("Tango", "Jealousy", ("▶  00:02", "−  02:15", False, 0.01), [], ("", ""))
        w._refresh()
        self.assertFalse(w._blink.isActive())
        self.assertEqual(w.left_lbl._color.name(), theme.left)


class PresenterControlsTest(unittest.TestCase):
    """🎛 The optional transport on the presenter screen."""

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def _win(self):
        from player.presenter import PresenterWindow
        w = PresenterWindow(lambda: ("Tango", "Jealousy",
                                     ("▶  00:42", "−  01:03", False, 0.4),
                                     [], ("", "")))
        self.addCleanup(reap_widget, w)
        w.resize(1280, 720)
        return w

    def test_the_header_names_the_queue(self):
        """English in the source; German comes from the catalog now."""
        self.assertEqual(self._win().next_hdr.text(), "Next dances")

    def test_the_screen_starts_without_controls(self):
        w = self._win()
        self.assertFalse(w.ctl_box.isVisible())
        self.assertFalse(w._controls_on)

    def test_the_switch_shows_them_and_says_so(self):
        w = self._win()
        w.show()
        self.addCleanup(w.close)
        seen = []
        w.controlsToggled.connect(seen.append)
        w._toggle_controls()
        self.assertTrue(w.ctl_box.isVisible())
        self.assertEqual(seen, [True])
        w._toggle_controls()
        self.assertFalse(w.ctl_box.isVisible())
        self.assertEqual(seen, [True, False])

    def test_the_saved_setting_reopens_them(self):
        w = self._win()
        w.set_controls_shown(True)
        self.assertTrue(w._controls_on)

    def test_the_buttons_ask_the_main_window(self):
        w = self._win()
        w.set_controls_shown(True)
        got = []
        w.prevRequested.connect(lambda: got.append("prev"))
        w.playPauseRequested.connect(lambda: got.append("play"))
        w.nextRequested.connect(lambda: got.append("next"))
        w.breakRequested.connect(lambda: got.append("break"))
        for btn in (w.prev_btn, w.play_btn, w.next_btn, w.break_btn):
            btn.click()
        self.assertEqual(got, ["prev", "play", "next", "break"])

    def test_the_play_glyph_follows_the_music(self):
        """The state tuple stands still while paused, so the icon is polled."""
        running = SimpleNamespace(v=False)
        w = self._win()
        w.playing_cb = lambda: running.v
        w.set_controls_shown(True)
        self.assertFalse(w._play_shown)
        paused_icon = w.play_btn.icon().pixmap(48).toImage()
        running.v = True
        w._refresh()
        self.assertTrue(w._play_shown)
        self.assertNotEqual(w.play_btn.icon().pixmap(48).toImage(), paused_icon)

    def test_a_hidden_transport_is_not_repainted(self):
        w = self._win()
        w.playing_cb = lambda: True
        w._refresh()
        self.assertIsNone(w._play_shown)


class ContextMenuPlaybackTest(unittest.TestCase):
    """⏹ / ⏭ in the right-click menu of a playlist."""

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def _menu(self, playing: bool, pick: str = ""):
        """Open a deck's context menu with a MainWindow-ish parent; return the
        (actions, window) after choosing the entry starting with `pick`.

        The menu is opened for real, so `exec` has to be neutralised — and
        patching QMenu.exec doesn't take: the Shiboken slot ignores an attribute
        set on the type, and the real modal exec then blocks the test run.
        Swapping the module's QMenu for a subclass does work, because the code
        builds its menu through that global name."""
        from unittest import mock
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QContextMenuEvent
        from PySide6.QtWidgets import QMenu, QWidget
        from gui import table_actions

        opened = []

        class _Menu(QMenu):
            def exec(self, *_args):
                opened.append(self.actions())
                return next((a for a in self.actions()
                             if pick and a.text().startswith(pick)), None)

        class _Win(QWidget):
            def __init__(self):
                super().__init__()
                self._playback = PlaybackState()
                self._playback.path = Path(r"C:\music\LW1.mp3") if playing else None
                self._between = BetweenDances()
                self._between.pending = None
                self.did = []

            def _on_stop_btn(self):
                self.did.append("stop")

            def _on_player_next(self):
                self.did.append("skip")

        win = _Win()
        self.addCleanup(reap_widget, win)
        t = _deck()
        t.setParent(win)
        with mock.patch.object(table_actions, "QMenu", _Menu):
            t.contextMenuEvent(QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, QPoint(5, 5)))
        self.assertTrue(opened, "the context menu never opened")
        return opened[0], win

    def test_they_lead_the_menu(self):
        acts, _win = self._menu(playing=True)
        self.assertEqual([a.text() for a in acts[:2]],
                         ["⏹  Stop the music", "⏭  Skip to the next title"])

    def test_choosing_them_reaches_the_player(self):
        _acts, win = self._menu(playing=True, pick="⏹")
        self.assertEqual(win.did, ["stop"])
        _acts, win = self._menu(playing=True, pick="⏭")
        self.assertEqual(win.did, ["skip"])

    def test_they_are_greyed_out_while_nothing_plays(self):
        acts, _win = self._menu(playing=False)
        self.assertEqual([a.isEnabled() for a in acts[:2]], [False, False])


class PartySetTest(unittest.TestCase):
    """🎉 The party play set on the Playing panel."""

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def _panel(self):
        from player.play_mode_panel import PlayModePanel
        p = PlayModePanel({"play_secs": 105, "timed_enabled": True,
                           "auto_advance": False, "pause_enabled": True})
        self.addCleanup(reap_widget, p)
        return p

    def test_applying_it_reports_every_change(self):
        p = self._panel()
        p.loudness_check.setChecked(False)
        before = p.play_set()
        changed = p.apply_play_set(secs=0, advance=True, pause_off=True,
                                   loudness=True)
        self.assertEqual(before, {"secs": 105, "fade": 3.0, "advance": False,
                                  "pause_off": False, "loudness": False,
                                  "announce": False, "dblclick": False})
        self.assertEqual(p.play_set(), {"secs": 0, "fade": 3.0,
                                        "advance": True, "pause_off": True,
                                        "loudness": True, "announce": False,
                                        "dblclick": False})
        self.assertEqual(len(changed), 4)
        self.assertTrue(any("full" in c for c in changed))
        # Full length = no timed cut, pause off = no break music.
        self.assertFalse(p.timed_enabled())
        self.assertEqual(p.pause_secs(), 0)

    def test_the_previous_settings_come_back_unchanged(self):
        p = self._panel()
        before = p.play_set()
        p.apply_play_set(secs=0, advance=True, pause_off=True)
        p.apply_play_set(**before)
        self.assertEqual(p.play_set(), before)
        self.assertEqual(p.pause_setting_secs(), 15)   # never lost the seconds

    def test_applying_what_is_already_set_changes_nothing(self):
        p = self._panel()
        p.apply_play_set(secs=0, advance=True, pause_off=True, loudness=True)
        self.assertEqual(p.apply_play_set(secs=0, advance=True,
                                          pause_off=True, loudness=True), [])

    def test_a_party_set_saved_before_the_eq_joined_it_still_restores(self):
        """Old settings files have no "loudness" key — the rest must still
        come back, and the box stay where the user left it."""
        p = self._panel()
        p.loudness_check.setChecked(True)
        p.apply_play_set(secs=0, advance=True, pause_off=True)
        self.assertTrue(p.loudness_check.isChecked())


if __name__ == "__main__":
    unittest.main()
